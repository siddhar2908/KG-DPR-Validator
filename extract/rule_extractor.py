import os
from extract.pdf_reader import read_pdf_pages
from extract.table_extractor import extract_tables_as_rules
from llm.ollama_client import call_llm
from utils.json_utils import safe_json_parse
from utils.page_filters import should_skip_page
from utils.text_utils import chunk_paragraphs
from utils.value_utils import (
    clean_sentence,
    clean_text,
    extract_operator,
    extract_range,
    make_readable_rule_id,
    normalize_numeric_value_and_unit,
    normalize_text,
    safe_slug,
    stable_id,
    try_float,
)
from ontology.mapper import normalize_parameter, normalize_entity, infer_domain_from_parameter
from config import DEBUG_MAX_RULE_PAGES, EXTRACTION_MODEL_NAME


DOC_FORBIDDEN_PARAMETERS = {
    "60850": {"track_gauge", "headway", "cbtc_signalling", "ato", "atp", "ohe_system"},
    "60913": {"track_gauge", "headway", "cbtc_signalling", "ato", "atp"},
    "713": {"traction_voltage", "traction_frequency", "ohe_system", "headway", "cbtc_signalling"},
    "cbtc": {"traction_voltage", "traction_frequency", "ohe_system", "track_gauge"},
}

DOC_ALLOWED_PARAMETERS = {
    "60850": {"traction_voltage", "traction_frequency"},
    "60913": {"ohe_system", "traction_voltage"},
    "713": {"track_gauge"},
    "cbtc": {"cbtc_signalling", "headway", "ato", "atp"},
}


def _doc_key(source_document: str) -> str:
    s = normalize_text(source_document)

    if "60850" in s:
        return "60850"
    if "60913" in s:
        return "60913"
    if "713" in s or "uic" in s:
        return "713"
    if "cbtc" in s:
        return "cbtc"

    return ""


def _contains_normative_signal(text: str) -> bool:
    t = normalize_text(text)

    signals = [
        "shall",
        "must",
        "nominal",
        "minimum",
        "maximum",
        "not exceed",
        "not less",
        "standard",
        "table 1",
        "u min",
        "u max",
        "25 kv",
        "50 hz",
        "17.5",
        "27.5",
        "29",
        "1435",
        "90 s",
        "90 second",
        "moving block",
        "cbtc",
        "ato",
        "atp",
        "rigid ohe",
        "flexible ohe",
        "overhead contact line",
    ]

    return any(s in t for s in signals)


def _is_low_value_page(text: str) -> bool:
    t = normalize_text(text)

    low_value_markers = [
        "table of contents",
        "list of tables",
        "list of figures",
        "foreword",
        "preface",
        "bibliography",
        "references",
        "blank intentionally",
        "copyright",
        "all rights reserved",
    ]

    if any(m in t for m in low_value_markers):
        return True

    definition_markers = [
        "terms and definitions",
        "for the purposes of this document",
    ]

    if any(m in t for m in definition_markers):
        return True

    return False


def _has_numeric_payload(rule: dict) -> bool:
    return (
        try_float(rule.get("value")) is not None
        or try_float(rule.get("value_min")) is not None
        or try_float(rule.get("value_max")) is not None
    )


def infer_rule_type(raw_rule: dict, value, value_min, value_max) -> str:
    if value_min is not None and value_max is not None:
        return "range"

    operator = extract_operator(
        str(raw_rule.get("constraint_type", "")) + " " + str(raw_rule.get("value", ""))
    )

    if try_float(value) is not None:
        if operator in {">=", "<=", ">", "<"}:
            return "numeric"
        return "exact"

    return "semantic"


def is_bad_rule_candidate(item: dict) -> bool:
    parameter = item.get("parameter", "")
    requirement_text = normalize_text(item.get("requirement_text", ""))
    context = normalize_text(item.get("context_snippet", ""))
    source = normalize_text(item.get("source_document", ""))

    if not parameter or parameter == "unknown_parameter":
        return True

    if len(requirement_text) < 10:
        return True

    if "table of contents" in context or "list of tables" in context or "list of figures" in context:
        return True

    junk = [
        "copyright",
        "all rights reserved",
        "blank intentionally",
        "committee",
        "foreword",
        "preface",
        "bibliography",
    ]
    if any(j in context for j in junk):
        return True

    doc_key = _doc_key(source)

    if doc_key:
        if parameter in DOC_FORBIDDEN_PARAMETERS.get(doc_key, set()):
            return True

        allowed = DOC_ALLOWED_PARAMETERS.get(doc_key, set())
        if allowed and parameter not in allowed:
            return True

    if parameter == "track_gauge" and "pressure gauge" in context:
        return True

    if item.get("rule_type") in {"numeric", "range"} and not _has_numeric_payload(item):
        return True

    return False


def final_rule_filter(rule: dict) -> bool:
    text = normalize_text(
        " ".join(
            [
                str(rule.get("parameter", "")),
                str(rule.get("display_value", "")),
                str(rule.get("requirement_text", "")),
                str(rule.get("comparison_sentence", "")),
                str(rule.get("context_snippet", "")),
            ]
        )
    )

    source = normalize_text(rule.get("source_document", ""))
    parameter = rule.get("parameter", "")

    bad_phrases = [
        "designated value for a system",
        "maximum value of the voltage likely to be present",
        "minimum value of the voltage likely to be present",
        "voltage variation",
        "voltage dip",
        "supply interruption",
        "lack of insulation distance",
        "difficulties to find",
        "appropriate power supply connection",
        "very long distance between substations",
        "need to solve difficulties",
        "independent from frequency",
        "terms and definitions",
        "for the purposes of this document",
        "bibliography",
        "scope",
        "note see bibliography",
    ]

    if any(p in text for p in bad_phrases):
        return False

    if "60850" in source:
        if parameter not in {"traction_voltage", "traction_frequency"}:
            return False

        useful_60850 = [
            "25 kv",
            "50 hz",
            "17.5",
            "19",
            "27.5",
            "29",
            "umin",
            "umax",
            "u min",
            "u max",
            "table 1",
            "standard voltage",
            "nominal voltage",
            "supply voltages of traction systems",
            "generic voltages",
        ]

        if not any(x in text for x in useful_60850):
            return False

    if "713" in source or "uic" in source:
        if parameter != "track_gauge":
            return False

        useful_gauge_terms = [
            "1435",
            "1 435",
            "1.435",
            "standard gauge",
            "standard-gauge",
            "main line standard gauge",
            "main-line standard-gauge",
        ]

        if not any(x in text for x in useful_gauge_terms):
            return False

    if "cbtc" in source:
        if parameter not in {"cbtc_signalling", "headway", "ato", "atp"}:
            return False

    if rule.get("rule_type") in {"numeric", "range"} and not _has_numeric_payload(rule):
        return False

    return True


def normalize_rule(
    raw_rule: dict,
    source_document: str,
    page: int,
    context: str,
    domain: str,
    seq: int,
) -> dict | None:
    raw_parameter = clean_sentence(raw_rule.get("parameter", ""))
    raw_entity = clean_sentence(raw_rule.get("entity", ""))
    raw_value = clean_sentence(raw_rule.get("value", ""))
    raw_unit = clean_sentence(raw_rule.get("unit", ""))
    raw_condition = clean_sentence(raw_rule.get("condition_text", ""))
    raw_requirement = clean_sentence(raw_rule.get("requirement_text", ""))
    raw_reference = clean_sentence(raw_rule.get("reference", ""))

    if not raw_parameter and not raw_requirement:
        return None

    parameter = normalize_parameter(raw_parameter, source_document, context)
    entity = normalize_entity(raw_entity, parameter, context)
    domain = infer_domain_from_parameter(parameter, domain)

    _, _, value, unit = normalize_numeric_value_and_unit(raw_value, explicit_unit=raw_unit)

    lo, hi, range_unit = extract_range(raw_value)
    value_min = None
    value_max = None

    if lo is not None and hi is not None:
        _, _, value_min, unit_min = normalize_numeric_value_and_unit(lo, explicit_unit=range_unit)
        _, _, value_max, unit_max = normalize_numeric_value_and_unit(hi, explicit_unit=range_unit)
        unit = unit_min or unit_max or unit

    rule_type = infer_rule_type(raw_rule, value, value_min, value_max)

    if rule_type == "range":
        value = None

    if rule_type == "numeric" and try_float(value) is None:
        rule_type = "semantic"

    requirement_text = raw_requirement or clean_sentence(context, max_len=350)
    document_name = source_document or "unknown_document"

    rule_id = make_readable_rule_id(document_name, parameter, page, seq)
    internal_id = stable_id(
        document_name,
        page,
        parameter,
        entity,
        value,
        value_min,
        value_max,
        requirement_text,
        prefix="rule",
    )

    display_value = ""
    if value_min is not None and value_max is not None:
        display_value = f"{value_min} to {value_max} {unit}".strip()
    elif value is not None and value != "":
        display_value = f"{value} {unit}".strip()
    elif raw_value:
        display_value = raw_value

    node_name = f"{rule_id} | {parameter} | {display_value}".strip(" |")

    item = {
        "id": internal_id,
        "rule_id": rule_id,
        "node_name": node_name,
        "display_name": node_name,
        "document_name": document_name,
        "source_document": document_name,
        "domain": domain,
        "page": page,
        "page_label": f"p.{page}",
        "rule_type": rule_type,
        "parameter": parameter,
        "entity": entity,
        "operator": extract_operator(str(raw_rule.get("constraint_type", "")) + " " + raw_value),
        "value": value,
        "value_min": value_min,
        "value_max": value_max,
        "unit": unit,
        "display_value": display_value,
        "requirement_text": requirement_text,
        "comparison_sentence": requirement_text,
        "condition_text": raw_condition,
        "reference": raw_reference,
        "context_snippet": clean_sentence(context, max_len=500),
        "confidence": float(raw_rule.get("confidence", 0.70) or 0.70),
    }

    if is_bad_rule_candidate(item):
        return None

    return item


def _extract_rules_from_prose(
    pages: list[dict],
    source_document: str,
    domain: str,
) -> list[dict]:
    all_rules = []
    page_count = 0
    seq = 1

    for page_data in pages:
        page_no = page_data["page"]
        page_text = clean_text(page_data["text"])

        if DEBUG_MAX_RULE_PAGES > 0 and page_count >= DEBUG_MAX_RULE_PAGES:
            break

        if not page_text:
            continue

        if should_skip_page(page_text) or _is_low_value_page(page_text):
            print(f"⏭️  Skipping page {page_no} (low-value)")
            continue

        if not _contains_normative_signal(page_text):
            continue

        page_count += 1
        chunks = chunk_paragraphs(page_text, max_chars=2200, overlap_paragraphs=0)

        for chunk_idx, chunk in enumerate(chunks, start=1):
            if not _contains_normative_signal(chunk):
                continue

            print(f"⚙️  Rule page {page_no} | chunk {chunk_idx}/{len(chunks)}", end="\r")

            prompt = f"""
Extract only REAL engineering compliance rules from the text.

Return ONLY valid JSON array.

Reject:
- definitions
- scope descriptions
- bibliography/reference lists
- table of contents
- notes or explanatory text
- values not explicitly stated in this text

Schema:
[
  {{
    "parameter": "",
    "entity": "",
    "value": "",
    "unit": "",
    "constraint_type": "",
    "requirement_text": "",
    "condition_text": "",
    "reference": "",
    "confidence": 0.7
  }}
]

Rules:
- requirement_text must be a clean sentence showing the actual requirement.
- Do not invent gauge, headway, CBTC, voltage, or any value unless explicitly stated.
- Numeric rules must have numeric value only.
- If the text only defines a term, return [].
- For IEC 60850, only extract actual traction voltage/frequency limits or nominal standard values.

TEXT:
{chunk}
"""

            response = call_llm(prompt, model_name=EXTRACTION_MODEL_NAME)
            parsed = safe_json_parse(response)

            for raw_rule in parsed:
                if not isinstance(raw_rule, dict):
                    continue

                item = normalize_rule(
                    raw_rule=raw_rule,
                    source_document=source_document,
                    page=page_no,
                    context=chunk,
                    domain=domain,
                    seq=seq,
                )

                if item:
                    all_rules.append(item)
                    seq += 1

    return all_rules


def _extract_rules_from_tables(
    pdf_path: str,
    source_document: str,
    domain: str,
    start_seq: int,
) -> list[dict]:
    raw_table_rules = extract_tables_as_rules(pdf_path, domain=domain)
    result = []
    seq = start_seq

    for raw_rule in raw_table_rules:
        page = raw_rule.pop("_page", 0)
        context = f"Table extracted from {source_document}, page {page}"

        item = normalize_rule(
            raw_rule=raw_rule,
            source_document=source_document,
            page=page,
            context=context,
            domain=domain,
            seq=seq,
        )

        if item:
            result.append(item)
            seq += 1

    return result


def _dedup(rules: list[dict]) -> list[dict]:
    seen = set()
    result = []

    for r in rules:
        key = (
            r.get("source_document"),
            r.get("page"),
            r.get("parameter"),
            r.get("entity"),
            str(r.get("value")),
            str(r.get("value_min")),
            str(r.get("value_max")),
            r.get("unit"),
            r.get("requirement_text"),
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(r)

    return result


def _renumber_rules(rules: list[dict]) -> list[dict]:
    for idx, rule in enumerate(rules, start=1):
        rule["serial_no"] = idx

        source = rule.get("source_document", "RULEBOOK").upper().replace("_", "-")
        param = rule.get("parameter", "RULE").upper()

        rule["rule_id"] = f"R-{source}-{idx:03d}-{param}"

        display_value = rule.get("display_value", "")
        rule["node_name"] = f"{rule['rule_id']} | {rule.get('parameter')} | {display_value}".strip(" |")
        rule["display_name"] = rule["node_name"]

    return rules


def extract_rules(
    pdf_path: str,
    domain: str = "generic",
    pages: list[dict] | None = None,
) -> list[dict]:
    print(f"\n📄 Extracting rules: {pdf_path}")

    if pages is None:
        pages = read_pdf_pages(pdf_path)

    source_document = safe_slug(os.path.basename(pdf_path).replace(".pdf", ""))

    prose_rules = _extract_rules_from_prose(pages, source_document, domain)
    print(f"\n   ✔ Prose rules before final filter: {len(prose_rules)}")

    table_rules = _extract_rules_from_tables(
        pdf_path,
        source_document,
        domain,
        start_seq=len(prose_rules) + 1,
    )
    print(f"   ✔ Table rules before final filter: {len(table_rules)}")

    rules = _dedup(prose_rules + table_rules)
    rules = [r for r in rules if final_rule_filter(r)]
    rules = _renumber_rules(rules)

    print(f"✅ Final clean rules extracted: {len(rules)}")
    return rules