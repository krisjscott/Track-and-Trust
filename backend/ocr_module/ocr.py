import os
import qrcode
from pyzbar.pyzbar import decode
from PIL import Image
import pytesseract

# Use project-level static folders (two levels up from this file)
BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
QR_FOLDER = os.path.join(BASE, "static", "qrcodes")
UPLOAD_FOLDER = os.path.join(BASE, "static", "uploads")

os.makedirs(QR_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- QR generation & reading ----------------
def generate_sample_qrs():
    samples = {
        "product1": "Track&Trust|product1|Verified",
        "product2": "Track&Trust|product2|Unverified",
        "product3": "Track&Trust|product3|Verified"
    }
    for name, text in samples.items():
        path = os.path.join(QR_FOLDER, f"{name}.png")
        if not os.path.exists(path):
            img = qrcode.make(text)
            img.save(path)

def read_all_qrcodes_with_text():
    """
    Returns list of dicts: [{'filename':..., 'text':...}, ...]
    """
    out = []
    for fn in sorted(os.listdir(QR_FOLDER)):
        if not fn.lower().endswith(".png"):
            continue
        p = os.path.join(QR_FOLDER, fn)
        try:
            img = Image.open(p)
            decoded = decode(img)
            txt = decoded[0].data.decode("utf-8") if decoded else "Unreadable QR"
        except Exception as e:
            txt = f"Error: {e}"
        out.append({"filename": fn, "text": txt})
    return out

# ---------------- OCR verification ----------------
def verify_document_ocr(path):
    """
    Run OCR on image files. For PDF support, user must convert or use pdf2image/poppler.
    Returns: {"status": "Verified"/"Unverified"/"Error", "details": "..." }
    """
    try:
        img = Image.open(path)
        text = pytesseract.image_to_string(img)
    except Exception as e:
        return {"status": "Error ⚠️", "details": f"OCR failed: {e}"}

    # small heuristic: look for verification-like keywords
    keywords = ["verified", "certificate", "government", "approved", "authentic"]
    found = [k for k in keywords if k.lower() in text.lower()]
    if found:
        return {"status": "Verified ✅", "details": f"Keywords found: {', '.join(found)}", "text": text}
    else:
        return {"status": "Unverified ❌", "details": "No verification keywords found", "text": text}

# ---------------- helper sample customers (for UI/demo) ----------------
def get_sample_customers():
    return [
        {"username": "cust_user", "name": "Rahul Sharma", "email": "rahul@example.com", "product": "Diamond Ring", "qr": "product1.png"},
        {"username": "cust_user2", "name": "Priya Mehta", "email": "priya@example.com", "product": "Gold Necklace", "qr": "product2.png"},
    ]

