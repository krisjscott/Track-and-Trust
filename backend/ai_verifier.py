# backend/ai_verifier.py
import pytesseract
from PIL import Image

def verify_document(filepath):
    """
    AI-based document verification (simple version).
    Extracts text from the uploaded document using OCR and
    marks it as valid if text is found.
    """
    extracted_text = ""

    try:
        # If file is an image -> use OCR
        if filepath.lower().endswith((".png", ".jpg", ".jpeg")):
            extracted_text = pytesseract.image_to_string(Image.open(filepath))

        # If file is PDF -> you can extend logic (currently placeholder)
        elif filepath.lower().endswith(".pdf"):
            extracted_text = "PDF verification not fully implemented yet."

        else:
            extracted_text = "Unsupported file type."

    except Exception as e:
        extracted_text = f"Error reading document: {str(e)}"

    # Simple rule: if OCR extracts text longer than 20 chars, mark as valid
    is_valid = len(extracted_text.strip()) > 20

    return {
        "valid": is_valid,
        "extracted_text": extracted_text.strip()
    }
