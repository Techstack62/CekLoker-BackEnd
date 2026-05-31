"""
Scam Analysis Service
---------------------
This module provides a clean interface for analyzing job posting data for
potential scam indicators. Currently using a MOCK implementation.

To integrate a real AI model, replace the body of `analyze_scam()` while
keeping the function signature and return format identical.
"""

from dataclasses import dataclass


@dataclass
class ScamAnalysisResult:
    scam_percentage: float
    scam_category: str
    scam_reason: str


# --- Mock implementation ---
# RED-FLAG keywords and their weights (0.0 – 1.0)
_RED_FLAG_KEYWORDS: dict[str, float] = {
    "tanpa pengalaman": 0.15,
    "no experience": 0.15,
    "gaji besar": 0.20,
    "penghasilan jutaan": 0.20,
    "modal kecil": 0.25,
    "investasi": 0.20,
    "deposit": 0.25,
    "transfer uang": 0.30,
    "rekening pribadi": 0.30,
    "wa saja": 0.10,
    "tidak ada kantor": 0.20,
    "kerja dari rumah": 0.10,
    "bonus besar": 0.15,
    "komisi tinggi": 0.15,
    "langsung diterima": 0.20,
    "biaya pendaftaran": 0.35,
    "biaya administrasi": 0.35,
}

_SCAM_CATEGORIES = {
    (0, 30): "Aman",
    (30, 60): "Mencurigakan",
    (60, 80): "Berpotensi Scam",
    (80, 101): "Scam",
}


def _determine_category(percentage: float) -> str:
    for (low, high), label in _SCAM_CATEGORIES.items():
        if low <= percentage < high:
            return label
    return "Tidak Diketahui"


def analyze_scam(extracted_data: dict) -> ScamAnalysisResult:
    """
    Analyze extracted OCR data for scam indicators.

    Args:
        extracted_data: Dict with keys like job_title, company_name,
                        description, salary, raw_ocr_text, etc.

    Returns:
        ScamAnalysisResult with scam_percentage, scam_category, scam_reason.

    NOTE: This is a MOCK implementation. Replace this function body with
          a real AI model call when the model is ready.
    """
    text_blob = " ".join(
        str(v).lower()
        for v in extracted_data.values()
        if v is not None
    )

    matched_flags: list[str] = []
    total_weight = 0.0

    for keyword, weight in _RED_FLAG_KEYWORDS.items():
        if keyword in text_blob:
            matched_flags.append(keyword)
            total_weight += weight

    # Cap at 100%
    scam_percentage = min(round(total_weight * 100, 2), 100.0)
    scam_category = _determine_category(scam_percentage)

    if matched_flags:
        scam_reason = (
            f"Ditemukan {len(matched_flags)} indikator mencurigakan: "
            + ", ".join(f'"{f}"' for f in matched_flags)
            + "."
        )
    else:
        scam_reason = "Tidak ditemukan indikator mencurigakan yang signifikan."

    return ScamAnalysisResult(
        scam_percentage=scam_percentage,
        scam_category=scam_category,
        scam_reason=scam_reason,
    )
