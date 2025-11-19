# backend/documents.py

import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename

# Folder to save uploaded documents
UPLOAD_FOLDER = "static/uploads"
DOCUMENTS_FILE = "documents.json"

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}

# Ensure upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Initialize documents.json if not exists
if not os.path.exists(DOCUMENTS_FILE):
    with open(DOCUMENTS_FILE, "w") as f:
        json.dump([], f, indent=4)

# Utility to load documents metadata
def load_documents():
    with open(DOCUMENTS_FILE, "r") as f:
        return json.load(f)

# Utility to save documents metadata
def save_documents(documents):
    with open(DOCUMENTS_FILE, "w") as f:
        json.dump(documents, f, indent=4)

# Check allowed file type
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Handle document upload
def upload_document(file, user):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{timestamp}_{filename}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)

        # AI-based verification simulation
        ai_result = simulate_ai_verification(file_path)

        # Save document metadata
        documents = load_documents()
        documents.append({
            "filename": filename,
            "user": user,
            "status": "Pending",
            "ai_result": ai_result,
            "uploaded_at": timestamp,
            "extracted_text": ""  # optional, can fill with OCR
        })
        save_documents(documents)
        return True, "Document uploaded successfully"
    return False, "Invalid file type"

# Simulate AI verification (replace with real AI model)
def simulate_ai_verification(file_path):
    # Randomly approve or flag for demo
    import random
    verdict = random.choice(["Valid", "Suspicious"])
    return verdict

# Approve or reject document
def update_document_status(filename, action):
    documents = load_documents()
    for doc in documents:
        if doc["filename"] == filename:
            if action.lower() == "approve":
                doc["status"] = "Approved"
            elif action.lower() == "reject":
                doc["status"] = "Rejected"
            break
    save_documents(documents)

# Get documents pending verification
def get_pending_documents():
    documents = load_documents()
    return [doc for doc in documents if doc["status"] == "Pending"]
