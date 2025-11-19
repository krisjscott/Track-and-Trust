# backend/app.py
import os
import json
import sqlite3
import logging
import random
import csv
from io import StringIO
from datetime import datetime
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory, abort, Response
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, join_room

# Local OCR module
from backend.ocr_module.ocr import generate_sample_qrs, read_all_qrcodes_with_text, verify_document_ocr

### NEW AI LAYER ###
import pytesseract, re
from PIL import Image

# -------------------- Sensor Simulation --------------------
def get_sensor_data():
    return {
        "temperature": round(20 + random.random() * 10, 2),
        "humidity": round(40 + random.random() * 20, 2),
        "smoke": round(random.random() * 10, 2)
    }

def check_alerts(sd):
    alerts = []
    if sd["smoke"] > 5:
        alerts.append(f"Smoke ALERT! {sd['smoke']:.2f} > 5.0")
    if sd["temperature"] > 45:
        alerts.append(f"Temperature ALERT! {sd['temperature']:.2f} > 45.0")
    return alerts

### NEW AI LAYER ###
def detect_anomaly(sd):
    """
    Enhanced anomaly detection using rule-based AI logic.
    """
    anomalies = []
    if not (15 <= sd["temperature"] <= 45):
        anomalies.append(f"Temperature anomaly: {sd['temperature']}°C")
    if not (20 <= sd["humidity"] <= 80):
        anomalies.append(f"Humidity anomaly: {sd['humidity']}%")
    if sd["smoke"] > 7:
        anomalies.append(f"High smoke detected: {sd['smoke']}")
    if not anomalies:
        anomalies.append("✅ No anomalies detected")
    return anomalies

### NEW AI LAYER ###
def ai_verify_document(filepath):
    """
    AI-based document verification using OCR and pattern matching.
    - Tries OCR (image files). If not an image, falls back to existing verify_document_ocr.
    - Produces a simple 'status' and an integer risk_score (0–100).
    """
    try:
        # Try to OCR image types; for non-images, delegate to existing OCR
        _, ext = os.path.splitext(filepath.lower())
        if ext in {".png", ".jpg", ".jpeg"}:
            text = pytesseract.image_to_string(Image.open(filepath))
        else:
            # Let your local module handle PDFs or other types,
            # still parse text and then run patterns below
            o = verify_document_ocr(filepath)
            text = o.get("text", "")

        text = (text or "").strip()

        if not text:
            return {"status": "Unreadable", "text": "", "risk_score": 100}

        # Example pattern: generic ID-like token AB123456
        if re.search(r'\b[A-Z]{2}\d{6}\b', text):
            status = "Valid Document"
            base_risk = 15
        elif len(text) < 80:
            status = "Incomplete Document"
            base_risk = 70
        else:
            status = "Suspicious Document"
            base_risk = 55

        # Simple jitter to avoid all docs sharing same score
        risk_score = min(100, max(0, base_risk + random.randint(-10, 10)))

        return {"status": status, "text": text, "risk_score": risk_score}

    except Exception as e:
        return {"status": "Error", "text": str(e), "risk_score": 100}

# -------------------- App & Paths --------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
STATIC_DIR = os.path.join(PROJECT_ROOT, "static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")
QR_DIR = os.path.join(STATIC_DIR, "qrcodes")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "track_and_trust.db")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(QR_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

generate_sample_qrs()  # Ensure sample QR codes exist

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("trackandtrust")

app = Flask(__name__, static_folder=STATIC_DIR, template_folder=TEMPLATE_DIR)
app.secret_key = "trackandtrust_secret_key_please_change"
socketio = SocketIO(app, async_mode="eventlet")

ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".pdf"}

# -------------------- Database --------------------
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _column_exists(cur, table, column):
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    # Create tables (documents includes risk_score for fresh installs)
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        email TEXT
    );
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        filename TEXT,
        filepath TEXT,
        status TEXT,
        ai_verification TEXT,
        ocr_text TEXT,
        remarks TEXT,
        uploaded_on TEXT,
        risk_score INTEGER DEFAULT 0,
        FOREIGN KEY(customer_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        qr_filename TEXT,
        verification_status TEXT DEFAULT 'Unverified'
    );
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        message TEXT,
        read_flag INTEGER DEFAULT 0,
        timestamp TEXT
    );
    CREATE TABLE IF NOT EXISTS routes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        driver_id INTEGER,
        route_info TEXT,
        status TEXT,
        assigned_on TEXT
    );
    """)
    conn.commit()

    # Safe migration: add risk_score if legacy DB exists without it
    try:
        if not _column_exists(cur, "documents", "risk_score"):
            cur.execute("ALTER TABLE documents ADD COLUMN risk_score INTEGER DEFAULT 0")
            conn.commit()
    except Exception as e:
        # Ignore if older SQLite without IF NOT EXISTS—best-effort migration
        logger.warning("risk_score migration warning: %s", e)

    # Seed default users if empty
    cur.execute("SELECT COUNT(*) AS c FROM users")
    if cur.fetchone()["c"] == 0:
        users = [
            ("gov_user", "gov123", "government", "gov@example.com"),
            ("seller_user", "sale123", "saler", "seller@example.com"),
            ("cust_user", "cust123", "customer", "cust@example.com"),
            ("driver_user", "drive123", "driver", "driver@example.com"),
        ]
        cur.executemany("INSERT INTO users (username,password,role,email) VALUES (?,?,?,?)", users)
        conn.commit()
    conn.close()

init_db()

# -------------------- DB Helpers --------------------
def fetchone(sql, params=()):
    conn = get_conn()
    row = conn.execute(sql, params).fetchone()
    conn.close()
    return row

def fetchall(sql, params=()):
    conn = get_conn()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows

def execute(sql, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    last = cur.lastrowid
    conn.close()
    return last

# -------------------- Auth Helpers --------------------
def current_user():
    if "user_id" in session:
        return fetchone("SELECT * FROM users WHERE id=?", (session["user_id"],))
    return None

def user_by_username(username):
    return fetchone("SELECT * FROM users WHERE username=?", (username,))

# -------------------- Routes --------------------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        uname = request.form.get("username","").strip()
        pwd = request.form.get("password","")
        user = user_by_username(uname)
        if user and user["password"] == pwd:
            session.update({"user_id": user["id"], "username": user["username"], "role": user["role"]})
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="Invalid username or password")
    return render_template("login.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        uname = request.form.get("username","").strip()
        email = request.form.get("email","").strip()
        pwd = request.form.get("password","")
        role = request.form.get("role","customer")
        if not uname or not pwd:
            return render_template("register.html", error="Username & password required")
        try:
            execute("INSERT INTO users (username,password,role,email) VALUES (?,?,?,?)", (uname,pwd,role,email))
            return redirect(url_for("login"))
        except Exception as e:
            logger.exception("Register error: %s", e)
            return render_template("register.html", error="Username exists or invalid data")
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# -------------------- Dashboard --------------------
@app.route("/")
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = current_user()
    role = user["role"]
    qr_list = read_all_qrcodes_with_text()
    sensor_data = get_sensor_data()
    alerts = check_alerts(sensor_data)

    context = {
        "username": user["username"],
        "role": role,
        "qr_data": qr_list,
        "sensor_data": sensor_data,
        "alerts": alerts
    }

    if role == "customer":
        docs = fetchall("SELECT * FROM documents WHERE customer_id=?", (user["id"],))
        context["documents"] = [dict(d) for d in docs]
    elif role == "saler":
        customers = fetchall("SELECT * FROM users WHERE role='customer'")
        cust_docs = {
            c["username"]: {
                "email": c["email"],
                "documents": [dict(d) for d in fetchall("SELECT * FROM documents WHERE customer_id=?", (c["id"],))]
            } for c in customers
        }
        context["customer_docs"] = cust_docs
        context["products"] = [dict(p) for p in fetchall("SELECT * FROM products")]
    elif role == "driver":
        route = fetchone("SELECT * FROM routes WHERE driver_id=? ORDER BY id DESC", (user["id"],))
        context["route"] = dict(route) if route else None
    else:  # government
        docs = fetchall("SELECT d.*, u.username as owner_username FROM documents d LEFT JOIN users u ON d.customer_id=u.id")
        context["documents"] = [dict(d) for d in docs]

    return render_template("dashboard.html", **context)

# -------------------- Upload Documents --------------------
@app.route("/upload", methods=["GET","POST"])
def upload():
    user = current_user()
    if not user or user["role"] not in ("customer","saler"):
        abort(403)
    message, success = "", False
    if request.method=="POST":
        f = request.files.get("document")
        if not f or f.filename == "":
            message = "No file selected"
        else:
            filename = secure_filename(f.filename)
            base, ext = os.path.splitext(filename)
            if ext.lower() not in ALLOWED_EXT:
                message = f"Extension {ext} not allowed"
            else:
                dest = os.path.join(UPLOAD_DIR, filename)
                counter = 1
                while os.path.exists(dest):
                    filename = f"{base}_{counter}{ext}"
                    dest = os.path.join(UPLOAD_DIR, filename)
                    counter += 1
                f.save(dest)

                # Existing OCR (kept)
                ocr_res = verify_document_ocr(dest)
                ocr_text = ocr_res.get("text", "")[:800]

                # New AI verification + risk score
                ai_res = ai_verify_document(dest)
                ai_ver = ai_res.get("status", "Unverified")
                risk_score = int(ai_res.get("risk_score", random.randint(0, 100)))

                execute("""INSERT INTO documents
                    (customer_id, filename, filepath, status, ai_verification, ocr_text, uploaded_on, risk_score)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    (user["id"], filename, dest, "Pending", ai_ver, ocr_text, datetime.utcnow().isoformat(), risk_score)
                )

                # Notify stakeholders
                for role_to_notify in ("saler","government"):
                    for u_notify in fetchall("SELECT id FROM users WHERE role=?", (role_to_notify,)):
                        execute("INSERT INTO notifications (user_id,message,timestamp) VALUES (?,?,?)",
                                (u_notify["id"], f"New document uploaded by {user['username']}: {filename} | AI Risk Score: {risk_score}", datetime.utcnow().isoformat()))
                message = f"Document uploaded. AI Verification: {ai_ver} | Risk Score: {risk_score}"
                success = True

    return render_template("upload.html", message=message, success=success, username=user["username"], role=user["role"])

# -------------------- Download --------------------
@app.route("/download/<int:doc_id>")
def download_doc(doc_id):
    doc = fetchone("SELECT * FROM documents WHERE id=?", (doc_id,))
    user = current_user()
    if not doc or not user:
        abort(404)
    if user["role"] in ("saler","government") or doc["customer_id"]==user["id"]:
        if os.path.exists(doc["filepath"]):
            return send_from_directory(os.path.dirname(doc["filepath"]), os.path.basename(doc["filepath"]), as_attachment=True)
    abort(403)

# -------------------- Update Document Status --------------------
@app.route("/update_status", methods=["POST"])
def update_status():
    user = current_user()
    if not user or user["role"] not in ("saler","government"):
        return jsonify({"error":"Unauthorized"}),403

    data = request.get_json() or {}
    filename = data.get("filename")
    action = data.get("action")
    remarks = data.get("remarks","")
    if not filename or action not in ("approve","reject"):
        return jsonify({"error":"Invalid request"}),400

    doc = fetchone("SELECT * FROM documents WHERE filename=? AND status='Pending' ORDER BY id ASC", (filename,))
    if not doc:
        return jsonify({"error":"Document not found or already processed"}),404

    new_status = "Approved" if action=="approve" else "Rejected"
    execute("UPDATE documents SET status=?, remarks=? WHERE id=?", (new_status, remarks, doc["id"]))
    execute("INSERT INTO notifications (user_id,message,timestamp) VALUES (?,?,?)",
            (doc["customer_id"], f"Your document {filename} has been {new_status} by {user['username']}", datetime.utcnow().isoformat()))

    # Emit real-time update
    socketio.emit("document_status_update", {"filename": filename, "status": new_status},
                  room=fetchone("SELECT username FROM users WHERE id=?", (doc["customer_id"],))["username"])
    return jsonify({"success": True, "status": new_status})

# -------------------- Notifications --------------------
@app.route("/notifications")
def notifications():
    if "user_id" not in session:
        return jsonify([]),403
    uid = session["user_id"]
    rows = fetchall("SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 50", (uid,))
    return jsonify([dict(r) for r in rows])

# -------------------- Assign Route --------------------
@app.route("/assign_route", methods=["POST"])
def assign_route():
    user = current_user()
    if not user or user["role"] not in ("saler","government"):
        return jsonify({"error":"Unauthorized"}),403

    data = request.json or {}
    driver_username = data.get("driver")
    route_info = data.get("route")
    if not driver_username or not route_info:
        return jsonify({"error":"Missing data"}),400

    driver = user_by_username(driver_username)
    if not driver or driver["role"] != "driver":
        return jsonify({"error":"Driver not found"}),404

    execute("INSERT INTO routes (driver_id, route_info, status, assigned_on) VALUES (?,?,?,?)",
            (driver["id"], json.dumps(route_info), "Assigned", datetime.utcnow().isoformat()))

    execute("INSERT INTO notifications (user_id,message,timestamp) VALUES (?,?,?)",
            (driver["id"], f"New route assigned: {route_info}", datetime.utcnow().isoformat()))

    socketio.emit("route_assigned", {"driver": driver_username, "route": route_info}, room=driver_username)
    return jsonify({"success": True})

# -------------------- Sensor Data API --------------------
@app.route("/sensor-data")
def sensor_data_route():
    sd = get_sensor_data()
    return jsonify({"data": sd, "alerts": check_alerts(sd), "anomalies": detect_anomaly(sd)})

# -------------------- Export Documents --------------------
@app.route("/export-documents")
def export_documents():
    user = current_user()
    if not user or user["role"] not in ("saler","government"):
        abort(403)

    docs = fetchall("SELECT d.*, u.username as owner_username FROM documents d LEFT JOIN users u ON d.customer_id=u.id")
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(["Filename","Owner","Status","AI Verification","Risk Score","Uploaded On"])
    for d in docs:
        cw.writerow([
            d["filename"],
            d["owner_username"],
            d["status"],
            d["ai_verification"],
            d.get("risk_score", 0),
            d["uploaded_on"]
        ])
    return Response(si.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition":"attachment;filename=documents_export.csv"})

# -------------------- SocketIO --------------------
@socketio.on("join")
def on_join(data):
    username = data.get("username")
    if username:
        join_room(username)

# -------------------- Products --------------------
@app.route("/products")
def products_list():
    return jsonify([dict(r) for r in fetchall("SELECT * FROM products")])

if __name__ == "__main__":
    socketio.run(app, debug=True)
