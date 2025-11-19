# backend/ocr_module/qr_generator.py
import qrcode
import os

QR_FOLDER = os.path.join(os.path.dirname(__file__), "../../static/qrcodes")
os.makedirs(QR_FOLDER, exist_ok=True)

sample_texts = ["Product 1", "Product 2", "Product 3"]

for i, text in enumerate(sample_texts, start=1):
    img = qrcode.make(text)
    filename = f"qr{i}.png"
    img.save(os.path.join(QR_FOLDER, filename))

print("Sample QR codes generated successfully!")


