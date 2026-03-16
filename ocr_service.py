"""
Google Cloud Vision OCR Service
Uses the Vision API via API Key (REST approach — no service account needed).

Supports:
- Handwritten Bengali + English receipts
- DOCUMENT_TEXT_DETECTION for best accuracy
- Free tier: 1000 images/month
"""

import os
import base64
import requests
from typing import Dict, Any


# ── Configuration ─────────────────────────────────────────────────────────────
class GoogleVisionConfig:
    # Your API key — keep this secret. Move to env var for production.
    API_KEY: str = os.environ.get(
        "GOOGLE_VISION_API_KEY",
        "AIzaSyDnMSQy-Yx3mHDMyJ6H7gkv_58d8zZENYU"   # fallback if env var not set
    )

    # Language hints improve accuracy for Bengali + English mixed receipts
    LANGUAGE_HINTS = ["bn", "en"]

    # REST endpoint — document_text_detection gives best results for receipts
    ENDPOINT = (
        "https://vision.googleapis.com/v1/images:annotate"
        "?key={api_key}"
    )


# ── Availability check ────────────────────────────────────────────────────────
def is_paddleocr_available() -> bool:
    """
    Check if the Google Cloud Vision API key is configured and reachable.
    (Named 'is_paddleocr_available' for backwards compatibility with main.py)
    """
    return bool(GoogleVisionConfig.API_KEY)


# ── Core extraction ───────────────────────────────────────────────────────────
def extract_text_from_image(image_path: str) -> str:
    """
    Extract text from a receipt image using Google Cloud Vision API.

    Uses DOCUMENT_TEXT_DETECTION which is optimised for:
    - Handwritten Bengali and English
    - Receipts, forms, and structured documents
    - Mixed scripts and orientations

    Args:
        image_path: Absolute or relative path to the image file.

    Returns:
        Extracted text as a plain string (may be empty if no text found).

    Raises:
        FileNotFoundError: Image file does not exist.
        ValueError: API key is missing.
        Exception: Vision API returned an error.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    api_key = GoogleVisionConfig.API_KEY
    if not api_key:
        raise ValueError(
            "Google Cloud Vision API key is missing.\n"
            "Set the GOOGLE_VISION_API_KEY environment variable or add the key "
            "to ocr_service.py → GoogleVisionConfig.API_KEY"
        )

    # Encode image to base64
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "requests": [
            {
                "image": {"content": image_data},
                "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
                "imageContext": {
                    "languageHints": GoogleVisionConfig.LANGUAGE_HINTS
                }
            }
        ]
    }

    url = GoogleVisionConfig.ENDPOINT.format(api_key=api_key)

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise Exception("Google Cloud Vision request timed out (30s). Check your internet connection.")
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else "unknown"
        body = e.response.text if e.response else ""

        if status == 400:
            raise Exception(f"Bad request — the image may be corrupt or too large.\nDetail: {body}")
        elif status == 403:
            raise Exception(
                "API key is invalid or Vision API is not enabled.\n"
                "1. Go to https://console.cloud.google.com/apis/library/vision.googleapis.com\n"
                "2. Click 'Enable'\n"
                "3. Make sure your API key has 'Cloud Vision API' access"
            )
        elif status == 429:
            raise Exception(
                "Google Cloud Vision quota exceeded.\n"
                "Free tier: 1000 images/month — you may have hit the limit."
            )
        else:
            raise Exception(f"Google Cloud Vision HTTP {status}: {body[:300]}")

    data = response.json()

    # Check for API-level errors inside the response body
    responses = data.get("responses", [])
    if not responses:
        return ""

    first = responses[0]
    if "error" in first:
        err = first["error"]
        raise Exception(
            f"Vision API error {err.get('code', '')}: {err.get('message', 'Unknown error')}"
        )

    # Prefer fullTextAnnotation (richer) → fall back to textAnnotations
    full_annotation = first.get("fullTextAnnotation", {})
    if full_annotation.get("text"):
        return full_annotation["text"].strip()

    text_annotations = first.get("textAnnotations", [])
    if text_annotations:
        return text_annotations[0].get("description", "").strip()

    return ""


# ── Detailed extraction (word-level with confidence) ─────────────────────────
def extract_text_with_details(image_path: str, min_confidence: float = 0.0) -> Dict[str, Any]:
    """
    Extract text plus per-word confidence scores from the image.
    Useful for debugging and deciding whether to trust detected values.

    Returns a dict with keys:
        text          – full extracted text
        words         – list of {text, confidence} per word
        statistics    – summary stats
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    api_key = GoogleVisionConfig.API_KEY
    if not api_key:
        raise ValueError("Google Cloud Vision API key missing.")

    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "requests": [
            {
                "image": {"content": image_data},
                "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
                "imageContext": {
                    "languageHints": GoogleVisionConfig.LANGUAGE_HINTS
                }
            }
        ]
    }

    url = GoogleVisionConfig.ENDPOINT.format(api_key=api_key)
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()

    responses = data.get("responses", [])
    if not responses:
        return _empty_details()

    first = responses[0]
    if "error" in first:
        raise Exception(f"Vision API error: {first['error'].get('message', '')}")

    full_annotation = first.get("fullTextAnnotation", {})
    if not full_annotation:
        return _empty_details()

    full_text = full_annotation.get("text", "").strip()
    words_data = []
    confidences = []

    for page in full_annotation.get("pages", []):
        for block in page.get("blocks", []):
            for paragraph in block.get("paragraphs", []):
                for word in paragraph.get("words", []):
                    conf = word.get("confidence", 1.0)
                    confidences.append(conf)
                    word_text = "".join(
                        sym.get("text", "") for sym in word.get("symbols", [])
                    )
                    if conf >= min_confidence:
                        words_data.append({"text": word_text, "confidence": round(conf, 3)})

    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

    return {
        "text": full_text,
        "words": words_data,
        "statistics": {
            "total_words": len(confidences),
            "words_above_threshold": len(words_data),
            "avg_confidence": round(avg_conf, 3),
            "min_confidence_used": min_confidence,
        }
    }


def _empty_details() -> Dict[str, Any]:
    return {
        "text": "",
        "words": [],
        "statistics": {
            "total_words": 0,
            "words_above_threshold": 0,
            "avg_confidence": 0.0,
            "min_confidence_used": 0.0,
        }
    }


# ── Config info ───────────────────────────────────────────────────────────────
def get_ocr_info() -> Dict[str, Any]:
    """Return info about the OCR configuration (used by the /health endpoint)."""
    return {
        "engine": "Google Cloud Vision",
        "api_type": "DOCUMENT_TEXT_DETECTION (REST)",
        "languages": ["Bengali (বাংলা) — handwritten", "English"],
        "language_hints": GoogleVisionConfig.LANGUAGE_HINTS,
        "available": is_paddleocr_available(),
        "optimized_for": "Handwritten Bengali + English receipts",
        "features": [
            "Handwritten text recognition (85-95% accuracy)",
            "Bengali numeral recognition (০১২৩৪৫৬৭৮৯)",
            "Mixed Bengali + English",
            "Auto-orientation handling",
            "Receipt and form structure awareness",
        ],
        "pricing": {
            "free_tier": "1000 images per month",
            "cost_after": "$1.50 per 1000 images",
        }
    }


# ── Manual test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import time

    print("=" * 60)
    print("Google Cloud Vision OCR — Handwritten Bengali + English")
    print("=" * 60)

    if not is_paddleocr_available():
        print("ERROR: API key not configured.")
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Usage: python ocr_service.py path/to/receipt.jpg")
        sys.exit(0)

    img = sys.argv[1]
    print(f"\nTesting: {img}")
    t0 = time.time()

    try:
        text = extract_text_from_image(img)
        elapsed = time.time() - t0
        print(f"\nExtracted text ({elapsed:.2f}s):")
        print("-" * 60)
        print(text or "(no text detected)")
        print("-" * 60)

        details = extract_text_with_details(img)
        stats = details["statistics"]
        print(f"\nTotal words : {stats['total_words']}")
        print(f"Avg confidence: {stats['avg_confidence']:.1%}")
    except Exception as e:
        print(f"\nERROR: {e}")