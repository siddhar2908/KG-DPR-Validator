import re
from typing import List, Dict, Any

try:
    import pdfplumber
except Exception:
    pdfplumber = None


HEADER_ALIASES = {
    "parameter": {
        "parameter", "design parameter", "item", "characteristic", "specification",
        "system parameter", "criteria", "feature"
    },
    "entity": {
        "entity", "system", "subsystem", "component", "application", "area"
    },
    "value": {
        "value", "normative value", "requirement", "required value", "standard value",
        "limit", "criteria value", "specified value"
    },
    "unit": {
        "unit", "units"
    },
    "constraint_type": {
        "constraint", "type", "operator", "comparison", "condition"
    },
    "requirement_text": {
        "requirement text", "requirement", "rule", "provision", "description",
        "remarks", "notes", "details", "specification details"
    },
    "reference": {
        "reference", "clause", "standard", "code", "source"
    },
}


def _normalize_header(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def _map_header(raw_header: str) -> str:
    h = _normalize_header(raw_header)
    for canonical, aliases in HEADER_ALIASES.items():
        if h in aliases:
            return canonical
    return h


def _looks_like_empty_row(row: list) -> bool:
    if not row:
        return True
    values = [str(c or "").strip() for c in row]
    return all(not v for v in values)


def _clean_cell(cell: Any) -> str:
    if cell is None:
        return ""
    text = str(cell).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _guess_columns_from_header(header_row: list[str]) -> dict[int, str]:
    mapping = {}
    for idx, col in enumerate(header_row):
        mapping[idx] = _map_header(col)
    return mapping


def _row_to_rule_dict(
    row: list[str],
    colmap: dict[int, str],
    page_no: int,
    default_reference: str = "",
) -> dict | None:
    item = {
        "parameter": "",
        "entity": "",
        "value": "",
        "unit": "",
        "constraint_type": "",
        "requirement_text": "",
        "condition_text": "",
        "reference": default_reference,
        "confidence": 0.72,
        "_page": page_no,
    }

    for idx, cell in enumerate(row):
        key = colmap.get(idx, "")
        value = _clean_cell(cell)
        if not value:
            continue

        if key in item:
            item[key] = value
        else:
            if item["requirement_text"]:
                item["requirement_text"] += f" | {value}"
            else:
                item["requirement_text"] = value

    if not item["parameter"] and item["requirement_text"]:
        req = item["requirement_text"]
        m = re.match(r"([A-Za-z][A-Za-z0-9 /\-\(\)]{2,50})[:\-]\s*(.+)", req)
        if m:
            item["parameter"] = m.group(1).strip()
            if not item["value"]:
                item["value"] = m.group(2).strip()

    if not item["parameter"]:
        return None

    return item


def _extract_tables_pdfplumber(pdf_path: str) -> List[Dict[str, Any]]:
    if pdfplumber is None:
        print("⚠️  pdfplumber not installed. Table extraction skipped.")
        return []

    extracted = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages, start=1):
            try:
                tables = page.extract_tables()
            except Exception:
                continue

            if not tables:
                continue

            for table in tables:
                if not table or len(table) < 2:
                    continue

                rows = [[_clean_cell(c) for c in row] for row in table if not _looks_like_empty_row(row)]
                if len(rows) < 2:
                    continue

                header = rows[0]
                colmap = _guess_columns_from_header(header)

                for row in rows[1:]:
                    item = _row_to_rule_dict(row=row, colmap=colmap, page_no=page_idx)
                    if item:
                        extracted.append(item)

    return extracted


def _dedup_rules(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    result = []

    for item in items:
        key = (
            item.get("_page"),
            item.get("parameter", ""),
            item.get("entity", ""),
            item.get("value", ""),
            item.get("unit", ""),
            item.get("requirement_text", ""),
            item.get("reference", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(item)

    return result


def extract_tables_as_rules(pdf_path: str, domain: str = "generic") -> List[Dict[str, Any]]:
    try:
        items = _extract_tables_pdfplumber(pdf_path)
        items = _dedup_rules(items)
        if items:
            print(f"   📊 Table-derived raw rules: {len(items)}")
        return items
    except Exception as e:
        print(f"⚠️  Table extraction failed for {pdf_path}: {e}")
        return []