"""
Parser Service Module
Intelligently parses OCR-extracted text to identify structured data
(amount, date, merchant, category)

Supports both Bengali (বাংলা) and English text from PaddleOCR
"""

import re
from datetime import datetime
from typing import Dict, Optional, Tuple


# Bengali digit mapping (০-৯ → 0-9)
BENGALI_DIGITS = {
    '০': '0', '১': '1', '২': '2', '৩': '3', '৪': '4',
    '৫': '5', '৬': '6', '৭': '7', '৮': '8', '৯': '9'
}

# Regex for matching Bengali digit sequences
BN_DIGIT = '[০-৯0-9]'


def normalize_digits(text: str) -> str:
    """Convert Bengali digits to ASCII digits for regex parsing."""
    for bn, en in BENGALI_DIGITS.items():
        text = text.replace(bn, en)
    return text


# Category keyword mapping (English + Bengali)
CATEGORY_KEYWORDS = {
    "Food": [
        # English
        "restaurant", "cafe", "coffee", "grocery", "supermarket", "market",
        "mcdonalds", "burger", "pizza", "kfc", "subway", "starbucks",
        "food", "bakery", "bar", "dining", "kitchen", "grill",
        # Bengali
        "রেস্তোরা", "রেস্তুরেন্ট", "খাবার", "হোটেল", "বাজার",
        "মুদিখানা", "চা", "কফি", "বেকারি", "মিষ্টি", "ভোজনালয়"
    ],
    "Transport": [
        # English
        "uber", "lyft", "taxi", "cab", "metro", "bus", "train",
        "parking", "fuel", "gas", "station", "transport", "airline", "flight",
        # Bengali
        "রিকশা", "সিএনজি", "বাস", "ট্রেন", "মেট্রো", "পরিবহন",
        "যাতায়াত", "ভাড়া", "পেট্রোল", "ডিজেল", "গ্যাস"
    ],
    "Shopping": [
        # English
        "mall", "store", "shop", "amazon", "ebay", "retail", "outlet",
        "clothing", "fashion", "apparel", "shoes", "electronics",
        # Bengali
        "দোকান", "শপিং", "কেনাকাটা", "শাড়ি", "কাপড়", "জুতা",
        "ইলেকট্রনিক্স"
    ],
    "Utilities": [
        # English
        "electric", "water", "internet", "phone", "mobile",
        "utility", "bill", "energy", "power",
        # Bengali
        "বিদ্যুৎ", "পানি", "ইন্টারনেট", "মোবাইল", "বিল",
        "গ্যাস বিল", "টেলিফোন"
    ],
    "Entertainment": [
        # English
        "cinema", "movie", "theater", "theatre", "netflix", "spotify",
        "game", "gaming", "concert", "ticket", "museum", "park",
        # Bengali
        "সিনেমা", "মুভি", "বিনোদন", "টিকিট", "পার্ক", "খেলা"
    ],
    "Rent": [
        # English
        "rent", "lease", "landlord", "property", "apartment", "housing",
        # Bengali
        "ভাড়া", "বাড়ি ভাড়া", "বাসা ভাড়া", "মাসিক ভাড়া"
    ]
}


def extract_amount(text: str) -> Tuple[Optional[float], float]:
    """
    Extract the total amount from receipt text.
    Supports English and Bengali digits/keywords.

    Returns:
        Tuple of (amount, confidence_score 0.0–1.0)
    """
    if not text:
        return None, 0.0

    # Normalize Bengali digits so regexes work uniformly
    normalized = normalize_digits(text)
    normalized_lower = normalized.lower()

    # Patterns in priority order — searched on normalized text
    priority_patterns = [
        # Bengali total keywords: মোট, সর্বমোট, টোটাল
        r'(?:মোট|সর্বমোট|টোটাল|total|amount|grand\s+total|sum)[\s:৳টাকা]*(\d+(?:,\d{3})*(?:\.\d{2})?)',
        # Taka symbol (৳) or word (টাকা)
        r'৳\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
        r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:টাকা|taka|tk)',
        # Dollar/generic currency
        r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
        # Any decimal number (last resort)
        r'(\d+(?:,\d{3})*\.\d{2})',
    ]

    best_amount = None
    confidence = 0.0

    for i, pattern in enumerate(priority_patterns):
        matches = re.findall(pattern, normalized_lower, re.IGNORECASE)
        if matches:
            amount_str = matches[-1].replace(',', '')
            try:
                amount = float(amount_str)
                confidence = 1.0 - (i * 0.15)
                best_amount = amount
                break
            except ValueError:
                continue

    return best_amount, max(0.0, min(1.0, confidence))


def extract_date(text: str) -> Tuple[Optional[str], float]:
    """
    Extract date from receipt text.
    Supports English and Bengali digits/date keywords.

    Returns:
        Tuple of (date_string YYYY-MM-DD, confidence_score)
    """
    if not text:
        return None, 0.0

    # Normalize Bengali digits first
    normalized = normalize_digits(text).lower()

    date_patterns = [
        # DD/MM/YYYY or MM/DD/YYYY
        r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})',
        # YYYY-MM-DD
        r'(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})',
        # Month name: Feb 10, 2026
        r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2}),?\s+(\d{4})',
    ]

    month_map = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }

    for pattern in date_patterns:
        matches = re.findall(pattern, normalized, re.IGNORECASE)
        if matches:
            for match in matches:
                try:
                    if match[0].isalpha():
                        month = month_map.get(match[0][:3])
                        day = int(match[1])
                        year = int(match[2])
                    elif len(match[0]) == 4:
                        year, month, day = int(match[0]), int(match[1]), int(match[2])
                    else:
                        day, month, year = int(match[0]), int(match[1]), int(match[2])

                    if month and 1 <= month <= 12 and 1 <= day <= 31:
                        date_obj = datetime(year, month, day)
                        return date_obj.strftime('%Y-%m-%d'), 0.85
                except (ValueError, TypeError):
                    continue

    return None, 0.0


def extract_merchant(text: str) -> Tuple[Optional[str], float]:
    """
    Extract merchant/store name from receipt text.
    Works with both Bengali and English names.

    Returns:
        Tuple of (merchant_name, confidence_score)
    """
    if not text:
        return None, 0.0

    lines = text.strip().split('\n')
    normalized_lines = [normalize_digits(l) for l in lines]

    potential_names = []
    for line in lines[:4]:  # Check first 4 lines for merchant name
        line = line.strip()
        # Skip phone numbers
        if re.search(r'\d{3}[-\s]\d{3}[-\s]\d{4}', normalize_digits(line)):
            continue
        # Skip address-like lines
        if re.search(r'\d{1,5}\s+\w+\s+(st|street|ave|road|rd)', line, re.IGNORECASE):
            continue
        # Skip lines that are just numbers/dates
        normalized = normalize_digits(line)
        if re.match(r'^[\d/\-\s,.:]+$', normalized):
            continue
        if len(line) > 3:
            potential_names.append(line)

    if potential_names:
        merchant = potential_names[0][:60]
        confidence = 0.75 if len(potential_names) > 1 else 0.60
        return merchant, confidence

    return None, 0.0


def detect_category(text: str) -> Tuple[str, float]:
    """
    Detect transaction category from Bengali + English keyword matching.

    Returns:
        Tuple of (category_name, confidence_score)
    """
    if not text:
        return "Other", 0.0

    text_lower = text.lower()

    category_scores: Dict[str, int] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            category_scores[category] = score

    if category_scores:
        best_category = max(category_scores, key=lambda k: category_scores[k])
        max_score = category_scores[best_category]
        confidence = min(0.95, 0.6 + (max_score * 0.1))
        return best_category, confidence

    return "Other", 0.3


def parse_receipt(text: str) -> Dict:
    """
    Parse receipt text (Bengali + English) and extract structured data.

    Args:
        text: OCR extracted text from receipt

    Returns:
        Dictionary with parsed data and confidence scores
    """
    amount, amount_conf = extract_amount(text)
    date, date_conf = extract_date(text)
    merchant, merchant_conf = extract_merchant(text)
    category, category_conf = detect_category(text)

    return {
        "amount": amount,
        "date": date,
        "merchant": merchant,
        "category": category,
        "confidence": {
            "amount": round(amount_conf, 2),
            "date": round(date_conf, 2),
            "merchant": round(merchant_conf, 2),
            "category": round(category_conf, 2)
        }
    }