"""
OCR Service for SafeSight AI - Milestone 2.
Attempts to use pytesseract if installed and Tesseract binary is available.
Gracefully falls back with clear status flags if Tesseract or pytesseract is not present.
Never crashes.
"""
import os
import logging
from typing import Tuple
from PIL import Image
import config

logger = logging.getLogger(__name__)

_pytesseract = None
_tesseract_checked = False
_tesseract_available = False


def is_ocr_available() -> bool:
    """Checks whether pytesseract and Tesseract engine are available."""
    global _pytesseract, _tesseract_checked, _tesseract_available
    if _tesseract_checked:
        return _tesseract_available

    _tesseract_checked = True
    try:
        import pytesseract
        _pytesseract = pytesseract
        if hasattr(config, "TESSERACT_CMD") and os.path.exists(config.TESSERACT_CMD):
            _pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD
        # Test basic version check
        _ = _pytesseract.get_tesseract_version()
        _tesseract_available = True
        logger.info("Tesseract OCR is available and initialized.")
    except Exception as e:
        logger.info(f"Tesseract OCR not available ({e}). Running in fallback mode.")
        _tesseract_available = False

    return _tesseract_available


def ocr_image(image_input) -> Tuple[str, bool]:
    """
    Extracts text from an image (filepath or PIL Image).
    Returns (extracted_text, success_bool).
    """
    if not is_ocr_available():
        return ("", False)

    try:
        img = Image.open(image_input) if isinstance(image_input, str) else image_input
        text = _pytesseract.image_to_string(img)
        return (text.strip(), True)
    except Exception as e:
        logger.warning(f"OCR extraction failed: {e}")
        return ("", False)
