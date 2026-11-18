"""
Document Loader for SafeSight AI - Milestone 2.
Loads and parses PDF, DOCX, TXT, and Image files into per-page structured text.
Supports:
- PDF: PyMuPDF (fitz) or pdfplumber if installed; robust built-in fallback parser for standard PDF text streams.
- DOCX: python-docx if installed; native zipfile XML parser fallback for standard DOCX.
- TXT: UTF-8 with latin-1 fallback.
- Images: OCR service (pytesseract or graceful fallback).
Never crashes on corrupt, invalid, or unusual files.
"""
import os
import re
import zlib
import zipfile
import logging
from typing import List, Dict, Any, Tuple
from xml.etree import ElementTree as ET
from app.services.ocr_service import ocr_image, is_ocr_available
from app.services.text_cleaner import clean_text, remove_repeated_headers_footers

logger = logging.getLogger(__name__)


def load_document(file_path: str) -> Tuple[List[Dict[str, Any]], str]:
    """
    Loads text from file_path.
    Returns:
        (pages_list, error_message)
        where each page is a dict:
        {"page_no": int, "text": str, "used_ocr": bool, "image_path": Optional[str]}
    """
    if not os.path.exists(file_path):
        return ([], "File not found on disk.")

    ext = os.path.splitext(file_path)[1].lower().replace(".", "")

    try:
        if ext == "pdf":
            return _load_pdf(file_path)
        elif ext == "docx":
            return _load_docx(file_path)
        elif ext == "txt":
            return _load_txt(file_path)
        elif ext in ("png", "jpg", "jpeg"):
            return _load_image(file_path)
        else:
            return ([], f"Unsupported document format: {ext}")
    except Exception as e:
        logger.error(f"Error loading document {file_path}: {e}")
        return ([], f"Failed to parse document: {str(e)}")


def _load_txt(file_path: str) -> Tuple[List[Dict[str, Any]], str]:
    """Loads plain text files with UTF-8 or latin-1 encoding."""
    text = ""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, "r", encoding="latin-1") as f:
                text = f.read()
        except Exception as e:
            return ([], f"Text encoding error: {e}")

    cleaned = clean_text(text)
    if not cleaned:
        return ([{"page_no": 1, "text": "(Empty text file)", "used_ocr": False}], "")

    # Split into virtual pages of ~3000 chars if long
    pages = []
    chunk_size = 3000
    if len(cleaned) <= chunk_size:
        pages.append({"page_no": 1, "text": cleaned, "used_ocr": False})
    else:
        for idx, i in enumerate(range(0, len(cleaned), chunk_size)):
            pages.append({
                "page_no": idx + 1,
                "text": cleaned[i:i + chunk_size].strip(),
                "used_ocr": False
            })

    return (pages, "")


def _load_docx(file_path: str) -> Tuple[List[Dict[str, Any]], str]:
    """Loads DOCX files using python-docx if installed, or native XML extraction."""
    paragraphs = []
    try:
        import docx
        doc = docx.Document(file_path)
        for p in doc.paragraphs:
            if p.text.strip():
                paragraphs.append(p.text.strip())
        for table in doc.tables:
            for row in table.rows:
                row_txt = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_txt:
                    paragraphs.append(row_txt)
    except ImportError:
        # Native DOCX (zip with word/document.xml) parser
        try:
            with zipfile.ZipFile(file_path) as z:
                xml_content = z.read("word/document.xml")
            tree = ET.fromstring(xml_content)
            # Find all text elements
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            for p in tree.findall('.//w:p', ns):
                texts = [node.text for node in p.findall('.//w:t', ns) if node.text]
                if texts:
                    paragraphs.append("".join(texts).strip())
        except Exception as e:
            return ([], f"DOCX parsing failed: {e}")

    full_text = "\n\n".join(paragraphs)
    cleaned = clean_text(full_text)
    if not cleaned:
        cleaned = "(No text found in DOCX file)"

    return ([{"page_no": 1, "text": cleaned, "used_ocr": False}], "")


def _load_image(file_path: str) -> Tuple[List[Dict[str, Any]], str]:
    """Extracts text from scanned image using OCR."""
    text, success = ocr_image(file_path)
    if not success or not text.strip():
        text = "(Scanned Image: OCR engine not active or no text detected. Install Tesseract to enable automated OCR)."
        used_ocr = False
    else:
        used_ocr = True

    return ([{"page_no": 1, "text": clean_text(text), "used_ocr": used_ocr, "image_path": file_path}], "")


def _load_pdf(file_path: str) -> Tuple[List[Dict[str, Any]], str]:
    """
    Extracts text per page from PDF using PyMuPDF if present,
    or pure-Python decompressed stream reader.
    """
    # 1. Try PyMuPDF
    try:
        import fitz
        doc = fitz.open(file_path)
        pages = []
        for idx, page in enumerate(doc):
            p_text = page.get_text()
            used_ocr = False
            # Check if page is scanned (< 30 chars)
            if len(p_text.strip()) < 30 and is_ocr_available():
                try:
                    pix = page.get_pixmap(dpi=150)
                    from PIL import Image
                    import io
                    img = Image.open(io.BytesIO(pix.tobytes()))
                    ocr_t, ocr_ok = ocr_image(img)
                    if ocr_ok and len(ocr_t.strip()) > len(p_text.strip()):
                        p_text = ocr_t
                        used_ocr = True
                except Exception as oe:
                    logger.debug(f"Page OCR fallback failed: {oe}")

            pages.append({
                "page_no": idx + 1,
                "text": clean_text(p_text),
                "used_ocr": used_ocr
            })
        doc.close()
        return (pages, "")
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"fitz error on {file_path}: {e}")

    # 2. Pure-Python fallback using find()-based stream boundary detection.
    #    Handles ASCII85+FlateDecode (ReportLab default) AND plain FlateDecode.
    #    Uses find() instead of regex because ReportLab PDFs have no newline
    #    before 'endstream' — the ASCII85 block ends with '~>' immediately
    #    followed by 'endstream', so the old regex rb'stream[\r\n]+(.*?)[\r\n]+endstream'
    #    matches nothing.
    try:
        with open(file_path, "rb") as f:
            content = f.read()

        if b"/Encrypt" in content:
            return ([], "Password-protected PDFs are not supported.")

        import base64 as _b64
        extracted_strings = []
        search_start = 0

        while True:
            # Locate the next 'stream' keyword
            s_start = content.find(b'stream', search_start)
            if s_start == -1:
                break

            # Skip 'stream' (6 bytes) + optional CRLF or LF
            data_start = s_start + 6
            if data_start < len(content) and content[data_start] in (ord('\r'), ord('\n')):
                data_start += 1
                # Handle CRLF pair
                if (data_start < len(content)
                        and content[data_start - 1] == ord('\r')
                        and content[data_start] == ord('\n')):
                    data_start += 1

            e_start = content.find(b'endstream', data_start)
            if e_start == -1:
                break

            raw_stream = content[data_start:e_start].strip()
            search_start = e_start + 9  # advance past 'endstream'

            dec_data = None

            # --- Try plain FlateDecode (wbits variants) ---
            for wbits in (15, -15, 31, 47):
                try:
                    dec_data = zlib.decompress(raw_stream, wbits)
                    break
                except Exception:
                    pass

            # --- Try ASCII85Decode + FlateDecode (ReportLab default) ---
            if not dec_data:
                try:
                    a85 = re.sub(rb'\s+', b'', raw_stream)
                    if not a85.endswith(b'~>'):
                        a85 += b'~>'
                    decoded_a85 = _b64.a85decode(a85, adobe=True)
                    for wbits in (15, -15, 31):
                        try:
                            dec_data = zlib.decompress(decoded_a85, wbits)
                            break
                        except Exception:
                            pass
                except Exception:
                    pass

            if dec_data:
                # Extract PDF string objects: (text)
                for m in re.finditer(rb'\(([^)\\]*(?:\\.[^)\\]*)*)\)', dec_data):
                    raw_str = m.group(1)
                    try:
                        decoded = raw_str.decode('latin-1', errors='ignore')
                        # Filter noise: keep strings with visible content longer than 1 char
                        stripped = decoded.strip()
                        if stripped and len(stripped) > 1:
                            extracted_strings.append(stripped)
                    except Exception:
                        pass

        full_text = " ".join(extracted_strings)
        cleaned = clean_text(full_text)
        if not cleaned:
            cleaned = ("(Scanned or complex graphics PDF. "
                       "Install PyMuPDF and Tesseract for full visual OCR.)")

        return ([{"page_no": 1, "text": cleaned, "used_ocr": False}], "")
    except Exception as e:
        logger.error(f"PDF pure-Python fallback failed on {file_path}: {e}")
        return ([], f"PDF extraction failed: {e}")
