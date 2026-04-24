import hashlib
import re
from typing import Any


def clean_text(text: Any) -> str:
    if text is None:
        return ""

    text = str(text)
    replacements = {
        "\uf6d9": "",
        "\uf0d8": "",
        "\uf0b7": "",
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2264": "<=",
        "\u2265": ">=",
        "\u00a9": "",
        "\u00ae": "",
        "\u2122": "",
        "\xa0": " ",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"[^\S\r\n]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def clean_sentence(text: Any, max_len: int = 500) -> str:
    text = clean_text(text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0] + "..."
    return text


def safe_slug(text: str, fallback: str = "unknown") -> str:
    text = clean_text(text).strip().lower()
    if not text:
        return fallback
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or fallback


def stable_id(*parts: Any, prefix: str = "id") -> str:
    raw = "||".join("" if p is None else str(p).strip() for p in parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{digest}"


def make_readable_rule_id(source_document: str, parameter: str, page: int, seq: int) -> str:
    doc = safe_slug(source_document).upper()
    doc = doc.replace("IEC_", "IEC").replace("UIC_", "UIC")
    param = safe_slug(parameter).upper()
    return f"R-{doc}-P{page}-{seq:03d}-{param}"


def make_readable_fact_id(source_document: str, parameter: str, page: int, seq: int) -> str:
    doc = safe_slug(source_document).upper()
    param = safe_slug(parameter).upper()
    return f"F-{doc}-P{page}-{seq:03d}-{param}"


def normalize_text(text: str) -> str:
    text = clean_text(text).lower()
    text = re.sub(r"[^a-z0-9\s\.\-/+]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> set[str]:
    return {t for t in normalize_text(text).split() if len(t) > 1}


def jaccard_similarity(a: str, b: str) -> float:
    ta = tokenize(a)
    tb = tokenize(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def clean_numeric_string(value_str: str) -> str:
    return clean_text(value_str).replace(",", "").strip()


def extract_operator(text: str) -> str:
    t = normalize_text(text)

    if ">=" in t or "greater than or equal" in t or "at least" in t or "minimum" in t or "not less than" in t:
        return ">="
    if "<=" in t or "less than or equal" in t or "at most" in t or "maximum" in t or "not more than" in t:
        return "<="
    if ">" in t or "greater than" in t:
        return ">"
    if "<" in t or "less than" in t:
        return "<"
    if "equal to" in t or "shall be" in t or "must be" in t:
        return "=="

    return ""


def normalize_unit(unit: str) -> str:
    u = clean_text(unit).lower()

    replacements = {
        "kilovolts": "kV",
        "kilovolt": "kV",
        "kv": "kV",
        "hz": "Hz",
        "hertz": "Hz",
        "mm": "mm",
        "millimeter": "mm",
        "millimetre": "mm",
        "millimeters": "mm",
        "millimetres": "mm",
        "m": "m",
        "metre": "m",
        "meter": "m",
        "metres": "m",
        "meters": "m",
        "seconds": "s",
        "second": "s",
        "sec": "s",
        "kmph": "km/h",
        "kph": "km/h",
    }

    for k, v in replacements.items():
        u = re.sub(rf"\b{k}\b", v, u)

    return u.strip()


def split_value_unit(value_str: str):
    s = clean_numeric_string(value_str)

    m = re.match(r"(-?\d+(?:\.\d+)?)\s*([a-zA-Z/%\-\s0-9]*)?$", s)
    if not m:
        return s, ""

    return m.group(1).strip(), normalize_unit(m.group(2) or "")


def extract_range(value_str: str):
    s = clean_numeric_string(value_str)

    patterns = [
        r"(-?\d+(?:\.\d+)?)\s*(?:to|-|–)\s*(-?\d+(?:\.\d+)?)\s*([a-zA-Z/%\-\s0-9]*)",
        r"between\s+(-?\d+(?:\.\d+)?)\s+and\s+(-?\d+(?:\.\d+)?)\s*([a-zA-Z/%\-\s0-9]*)",
        r"(-?\d+(?:\.\d+)?)\s*<=?.*<=?\s*(-?\d+(?:\.\d+)?)\s*([a-zA-Z/%\-\s0-9]*)",
    ]

    for pat in patterns:
        m = re.search(pat, s, flags=re.I)
        if m:
            return m.group(1), m.group(2), normalize_unit(m.group(3) or "")

    return None, None, ""


def try_float(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def to_base_unit(value, unit):
    v = try_float(value)
    u = normalize_unit(unit)

    if v is None:
        return value, u

    if u == "mm":
        return v / 1000.0, "m"
    if u == "cm":
        return v / 100.0, "m"
    if u == "m":
        return v, "m"

    return v, u


def normalize_numeric_value_and_unit(value_str: str, explicit_unit: str = ""):
    value, unit = split_value_unit(value_str)
    if explicit_unit and not unit:
        unit = explicit_unit

    normalized_value, normalized_unit = to_base_unit(value, unit)
    return value, normalize_unit(unit), normalized_value, normalized_unit