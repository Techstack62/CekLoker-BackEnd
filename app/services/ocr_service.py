import re
import io
import numpy as np
from PIL import Image

# Lazy singleton for EasyOCR reader - only loaded when needed
_reader = None


def get_reader():
    """Get or create EasyOCR reader instance with lazy loading.

    This avoids importing EasyOCR at module load time, which prevents
    NumPy version incompatibility issues during testing.
    """
    global _reader
    if _reader is None:
        import easyocr
        _reader = easyocr.Reader(["id", "en"], gpu=False)
    return _reader


def extract_text_from_image(image_bytes: bytes) -> str:
    """Run OCR on raw image bytes and return a single concatenated text string.

    EasyOCR supports: str (path/url), bytes, or numpy array.
    We convert via PIL → numpy array for full format compatibility.
    """
    pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    np_image = np.array(pil_image)          # shape: (H, W, 3), dtype: uint8
    reader = get_reader()
    results = reader.readtext(np_image, detail=0, paragraph=True)
    return "\n".join(results)


def parse_ocr_text(raw_text: str) -> dict:
    """
    Parse a raw OCR string into structured loker fields using simple heuristics.
    Returns a dict with extracted fields (values may be None if not found).
    """
    text = raw_text

    def find_pattern(patterns: list[str]) -> str | None:
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    email = find_pattern([
        r"(?:email|e-mail|surel)[:\s]+([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})",
        r"([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})",
    ])

    phone = find_pattern([
        r"(?:telp|telepon|hp|whatsapp|wa|phone|no\.?\s*hp)[:\s]+([\d\s\+\-]{8,15})",
        r"(\+62[\d\s\-]{8,14})",
        r"(0\d{8,13})",
    ])

    salary = find_pattern([
        r"(?:gaji|salary|upah|penghasilan)[:\s]+([^\n]{3,50})",
        r"(Rp\.?\s*[\d.,]+(?:\s*[-–]\s*Rp\.?\s*[\d.,]+)?)",
    ])

    job_type = find_pattern([
        r"(?:jenis\s+pekerjaan|tipe\s+loker|status|employment\s+type)[:\s]+([^\n]{3,50})",
        r"\b(full.?time|part.?time|freelance|kontrak|magang|internship|remote|hybrid)\b",
    ])

    info_source = find_pattern([
        r"(?:sumber|source|via|melalui|info\s+dari)[:\s]+([^\n]{3,80})",
    ])

    company_name = find_pattern([
        r"(?:perusahaan|company|pt\.?|cv\.?|nama\s+perusahaan)[:\s]+([^\n]{2,80})",
    ])

    job_title = find_pattern([
        r"(?:posisi|jabatan|lowongan|dicari|dibutuhkan|job\s+title|position)[:\s]+([^\n]{3,80})",
    ])

    description_match = re.search(
        r"(?:deskripsi|kualifikasi|syarat|requirement|job\s+desc)[:\s]+(.+?)(?=\n\n|\Z)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    description = description_match.group(1).strip() if description_match else None

    return {
        "job_title": job_title,
        "job_type": job_type,
        "info_source": info_source,
        "company_name": company_name,
        "company_email": email,
        "phone_number": phone,
        "description": description,
        "salary": salary,
        "raw_ocr_text": raw_text,
    }