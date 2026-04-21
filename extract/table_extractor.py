import re
import unicodedata
from typing import Optional
import pdfplumber

_TABLE_SETTINGS = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "snap_tolerance": 5,
    "join_tolerance": 3,
    "edge_min_length": 10,
    "min_words_vertical": 1,
    "min_words_horizontal": 1,
}

_HEADER_ROLE_MAP = [
    ("parameter", ["parameter", "param", "characteristic", "property", "description", "item", "criteria", "particulars", "specification"]),
    ("entity", ["entity", "component", "element", "structure", "reach", "section", "location", "type", "class", "category"]),
    ("value", ["value", "val", "magnitude", "quantity", "amount", "minimum", "maximum", "limit", "min", "max", "size"]),
    ("unit", ["unit", "units", "uom", "u/m"]),
    ("operator", ["constraint", "operator", "condition type", "op"]),
    ("condition", ["condition", "remarks", "notes", "note", "when", "applicable", "clause", "reference"]),
]


def _sanitize(cell) -> str:
    if cell is None:
        return ""
    text = str(cell)
    text = unicodedata.normalize("NFKC", text)
    for ch in ("\xad", "\u200b", "\u200c", "\u200d", "\ufeff"):
        text = text.replace(ch, "")
    text = re.sub(r"[\r\n]+", " ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _classify_header_token(token: str) -> Optional[str]:
    t = token.lower().strip()
    for role, keywords in _HEADER_ROLE_MAP:
        if any(kw in t for kw in keywords):
            return role
    return None


def _is_header_row(row: list[str]) -> bool:
    non_empty = [c for c in row if c]
    if not non_empty:
        return False
    label_count = sum(1 for c in non_empty if not re.search(r"\d", c) or len(c) < 6)
    return label_count / len(non_empty) >= 0.6


def _extract_operator_from_text(text: str) -> str:
    t = text.lower()
    if ">=" in t or "minimum" in t or "not less" in t or "at least" in t:
        return ">="
    if "<=" in t or "maximum" in t or "not more" in t or "at most" in t:
        return "<="
    if re.search(r"(?<![<>=])>(?![=])", t) or "greater than" in t:
        return ">"
    if re.search(r"(?<![<>=])<(?![=])", t) or "less than" in t:
        return "<"
    if "==" in t or "equal to" in t:
        return "=="
    return ">="


def _split_value_unit_cell(text: str):
    text = text.strip()
    op_hint = ""
    m = re.match(r"^([<>]=?|==|≥|≤|>|<)\s*", text)
    if m:
        sym = m.group(1)
        text = text[m.end():]
        op_hint = {"≥": ">=", "≤": "<="}.get(sym, sym)
    m2 = re.match(r"^(-?\d[\d,\.]*)\s*([a-zA-Z%/²³·\-\s]*)?$", text)
    if m2:
        raw_val = m2.group(1).replace(",", "")
        raw_unit = (m2.group(2) or "").strip()
        return op_hint, raw_val, raw_unit
    return op_hint, text, ""


def extract_tables_as_rules(pdf_path: str, domain: str = "generic") -> list[dict]:
    import os
    raw_rules = []
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        for page_num, page in enumerate(pdf.pages, start=1):
            print(f"📊 Table scan page {page_num}/{total}", end="\r")
            try:
                tables = page.extract_tables(_TABLE_SETTINGS)
            except Exception as exc:
                print(f"\n⚠️  Table extraction failed on page {page_num}: {exc}")
                continue
            if not tables:
                continue
            for table in tables:
                if not table or len(table) < 2:
                    continue
                clean_table = [[_sanitize(cell) for cell in row] for row in table]
                header_idx = 0
                for idx, row in enumerate(clean_table[:5]):
                    if _is_header_row(row):
                        header_idx = idx
                        break
                headers = clean_table[header_idx]
                col_roles: dict[int, str] = {}
                for col_i, h in enumerate(headers):
                    role = _classify_header_token(h)
                    if role:
                        col_roles[col_i] = role
                if "value" not in col_roles.values():
                    continue
                for row in clean_table[header_idx + 1:]:
                    if not any(row):
                        continue
                    cells: dict[str, list[str]] = {}
                    for col_i, role in col_roles.items():
                        if col_i < len(row) and row[col_i]:
                            cells.setdefault(role, []).append(row[col_i])
                    parameter = " ".join(cells.get("parameter", [])).strip()
                    entity = " ".join(cells.get("entity", [])).strip()
                    condition = " ".join(cells.get("condition", [])).strip()
                    raw_value_text = " ".join(cells.get("value", [])).strip()
                    raw_unit_text = " ".join(cells.get("unit", [])).strip()
                    raw_op_text = " ".join(cells.get("operator", [])).strip()
                    if not parameter or not raw_value_text:
                        continue
                    op_hint, parsed_value, parsed_unit = _split_value_unit_cell(raw_value_text)
                    final_unit = raw_unit_text or parsed_unit
                    if raw_op_text:
                        operator = _extract_operator_from_text(raw_op_text)
                    elif op_hint:
                        operator = op_hint
                    else:
                        operator = _extract_operator_from_text(parameter + " " + condition)
                    raw_rules.append({
                        "parameter": parameter,
                        "entity": entity,
                        "value": parsed_value,
                        "unit": final_unit,
                        "constraint_type": operator,
                        "condition_text": condition,
                        "confidence": 0.85,
                        "source": "table",
                        "_page": page_num,
                    })
    print()
    return raw_rules
