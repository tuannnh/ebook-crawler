import logging
from io import BytesIO

import requests
from PIL import Image

logger = logging.getLogger(__name__)


def extract_text_from_image_url(image_url: str, language: str = "vie") -> str:
    try:
        import pytesseract
    except ImportError:
        logger.warning("pytesseract not installed. Skipping OCR for %s", image_url)
        return "[Hình ảnh - OCR không khả dụng]"

    try:
        response = requests.get(image_url, timeout=15)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content))
        return pytesseract.image_to_string(image, lang=language).strip()
    except Exception as e:
        logger.warning("OCR thất bại cho %s: %s", image_url, e)
        return "[Hình ảnh - OCR thất bại]"
