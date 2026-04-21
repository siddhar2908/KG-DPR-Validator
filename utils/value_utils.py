import re


def clean_numeric_string(value_str: str) -> str:
    return str(value_str).strip().replace(",", "")


def extract_operator(text: str) -> str:
    if not text:
        return ""
    t = str(text).strip().lower()
    if ">=" in t or "greater than or equal to" in t or "at least" in t or "minimum" in t or "not less than" in t:
        return ">="
    if "<=" in t or "less than or equal to" in t or "at most" in t or "maximum" in t or "not more than" in t:
        return "<="
    if re.search(r"(?<![<>=])>(?![=])", t) or "greater than" in t:
        return ">"
    if re.search(r"(?<![<>=])<(?![=])", t) or "less than" in t:
        return "<"
    if "==" in t or "equal to" in t:
        return "=="
    return ""


def split_value_unit(value_str):
    if not value_str:
        return "", ""

    s = clean_numeric_string(value_str)
    s = re.sub(r"^[<>]=?\s*", "", s)

    # handle phrases like 'at least 10 m'
    s2 = re.sub(r"^(at least|not less than|minimum|not more than|at most|maximum)\s+", "", s, flags=re.I)

    match = re.match(r"(-?\d+(?:\.\d+)?)\s*([%a-zA-Z\/²³0-9\-\s]*)?$", s2)
    if match:
        value = match.group(1).strip()
        unit = (match.group(2) or "").strip()
        return value, unit

    return s, ""


def normalize_unit(unit: str) -> str:
    if not unit:
        return ""
    u = unit.strip().lower()
    u = u.replace("metre", "m").replace("meter", "m")
    u = u.replace("metres", "m").replace("meters", "m")
    u = u.replace("millimetre", "mm").replace("millimeter", "mm")
    u = u.replace("millimetres", "mm").replace("millimeters", "mm")
    u = u.replace("centimetre", "cm").replace("centimeter", "cm")
    u = u.replace("centimetres", "cm").replace("centimeters", "cm")
    u = u.replace("kilometre", "km").replace("kilometer", "km")
    u = u.replace("kilometres", "km").replace("kilometers", "km")
    u = u.replace("kmph", "km/h").replace("kph", "km/h")
    u = u.replace("cumecs", "cumec")
    u = u.replace("m3/s", "cumec")
    u = u.replace("ms", "m")
    u = re.sub(r"\s+", " ", u)
    return u.strip()


def to_base_unit(value, unit):
    if value in ("", None):
        return value, normalize_unit(unit)
    try:
        v = float(value)
    except Exception:
        return value, normalize_unit(unit)

    u = normalize_unit(unit)
    if u == "mm":
        return v / 1000.0, "m"
    if u == "cm":
        return v / 100.0, "m"
    if u == "m":
        return v, "m"
    if u == "km":
        return v * 1000.0, "m"
    return v, u


def normalize_numeric_value_and_unit(value_str: str, explicit_unit: str = ""):
    value, unit = split_value_unit(value_str)
    if explicit_unit and not unit:
        unit = explicit_unit
    norm_value, norm_unit = to_base_unit(value, unit)
    return value, normalize_unit(unit), norm_value, norm_unit
