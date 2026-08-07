"""
Utility functions: QR code generation and OCR text extraction.
Kept separate from views.py so they're easy to test independently.
"""
import io
import qrcode
from django.core.files.base import ContentFile

try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


def generate_qr_code(patient):
    """
    Generates a QR code encoding the patient's unique health_id.
    In a real deployment this would encode a lookup URL; for the demo
    we encode the raw health_id which the clinic lookup page can search.
    """
    qr_data = str(patient.health_id)
    qr_img = qrcode.make(qr_data)

    buffer = io.BytesIO()
    qr_img.save(buffer, format="PNG")
    filename = f"qr_{patient.health_id}.png"
    patient.qr_code.save(filename, ContentFile(buffer.getvalue()), save=False)
    return patient


def extract_text_from_document(image_field):
    """
    Runs OCR on an uploaded document image.
    Honest limitation (say this in the pitch): works reliably on printed/typed
    documents. Handwritten prescriptions are a known hard case for Tesseract
    and may return poor results - flagged clearly to the user in that case.
    """
    if not OCR_AVAILABLE:
        return "[OCR unavailable - pytesseract/PIL not installed]"

    try:
        image = Image.open(image_field)
        raw_text = pytesseract.image_to_string(image)
        cleaned = raw_text.strip()
        if not cleaned:
            return "[No text detected - document may be handwritten or low quality. Please verify manually.]"
        return cleaned
    except Exception as e:
        return f"[OCR failed: {str(e)}. Please verify document manually.]"


def generate_qr_data_uri(text):
    """
    Generates a QR code entirely in memory (no file saved to disk) and
    returns it as a base64 data URI the browser can display directly.
    Used for the Emergency SOS QR specifically, so there's no file that
    can go missing after a redeploy (unlike the main Health ID QR).
    """
    import base64
    qr_img = qrcode.make(text)
    buffer = io.BytesIO()
    qr_img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"