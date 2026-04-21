import os
from extract.pdf_reader import read_pdf_pages
from extract.table_extractor import extract_tables_as_rules
from llm.ollama_client import call_llm
from utils.json_utils import safe_json_parse
from utils.page_filters import should_skip_page
from utils.text_utils import chunk_paragraphs
from utils.value_utils import extract_operator, normalize_numeric_value_and_unit
from ontology.mapper import map_to_ontology
from config import DEBUG_MAX_RULE_PAGES, EXTRACTION_MODEL_NAME


def is_bad_rule_candidate(item: dict) -> bool:
    parameter = str(item.get("parameter", "")).strip().lower()
    entity = str(item.get("entity", "")).strip().lower()
    context = str(item.get("context_snippet", "")).strip().lower()
    value = item.get("value")
    unit = str(item.get("unit", "")).strip().lower()
    if not parameter:
        return True
    if parameter in {"number", "size", "value"} and entity in {"", "unknown"}:
        return True
    junk_terms = ["contents", "appendix", "acknowledgements", "chapter", "page", "committee", "member", "table of contents"]
    if sum(1 for t in junk_terms if t in context) >= 2:
        return True
    if value in ("", None):
        return True
    if value is not None and unit == "" and parameter in {"length", "width", "height", "depth"} and entity in {"", "unknown"}:
        return True
    return False


def normalize_rule(raw_rule: dict, source_document: str, page: int, context: str, domain: str) -> dict | None:
    raw_parameter = str(raw_rule.get("parameter", "")).strip()
    raw_entity = str(raw_rule.get("entity", "")).strip()
    raw_value = str(raw_rule.get("value", "")).strip()
    raw_constraint_type = str(raw_rule.get("constraint_type", "")).strip()
    raw_condition = str(raw_rule.get("condition_text", "")).strip()
    try:
        confidence = float(raw_rule.get("confidence", 0.70) or 0.70)
    except Exception:
        confidence = 0.70
    if not raw_parameter or not raw_value:
        return None
    operator = extract_operator(raw_constraint_type) or extract_operator(raw_value) or ">="
    _, _, normalized_value, normalized_unit = normalize_numeric_value_and_unit(raw_value, explicit_unit=str(raw_rule.get("unit", "")).strip())
    if normalized_value in ("", None):
        return None
    mapped = map_to_ontology(raw_parameter, raw_entity, domain=domain, context=context)
    parameter = str(mapped.get("parameter_canonical", "") or raw_parameter.strip().lower()).strip().lower()
    entity = str(mapped.get("entity_canonical", "") or (raw_entity.strip().lower() if raw_entity.strip() else "unknown")).strip().lower()
    if not parameter:
        return None
    return {
        "source_document": source_document,
        "page": page,
        "domain": domain,
        "parameter": parameter,
        "entity": entity if entity else "unknown",
        "operator": operator,
        "value": normalized_value,
        "unit": normalized_unit,
        "condition_text": raw_condition,
        "context_snippet": context[:250].strip(),
        "parameter_raw": raw_parameter,
        "entity_raw": raw_entity,
        "mapping_confidence": float(mapped.get("mapping_confidence", 0.60) or 0.60),
        "confidence": confidence,
        "extraction_source": raw_rule.get("source", "llm"),
    }


def _extract_rules_from_prose(pages: list[dict], source_document: str, domain: str) -> list[dict]:
    all_rules = []
    page_count = 0
    for page_data in pages:
        page_no = page_data["page"]
        page_text = page_data["text"]
        if DEBUG_MAX_RULE_PAGES > 0 and page_count >= DEBUG_MAX_RULE_PAGES:
            break
        if not page_text:
            continue
        if should_skip_page(page_text):
            print(f"⏭️  Skipping page {page_no} (low-value content)")
            continue
        page_count += 1
        chunks = chunk_paragraphs(page_text, max_chars=2200, overlap_paragraphs=0)
        for chunk_idx, chunk in enumerate(chunks, start=1):
            print(f"⚙️  Rule (prose) page {page_no} | chunk {chunk_idx}/{len(chunks)}", end="\r")
            prompt = f"""
Extract only measurable engineering/design rules from this technical text.

Return ONLY valid JSON array.
If no measurable rule exists, return [].

Schema:
[
  {{
    "parameter": "",
    "entity": "",
    "value": "",
    "unit": "",
    "constraint_type": "",
    "condition_text": "",
    "confidence": 0.7
  }}
]

Extract rules like:
- depth >= ...
- width >= ...
- clearance >= ...
- discharge <= ...
- radius >= ...
- gauge == ...
- speed >= ...
- berth length >= ...
- pond level >= ...
- scour depth <= ...

Do NOT extract headings, section titles, page numbers, committee text, or narrative statements without measurable constraint.

TEXT:
{chunk}
"""
            response = call_llm(prompt, model_name=EXTRACTION_MODEL_NAME)
            parsed = safe_json_parse(response)
            print(f"\n   [DEBUG] raw parsed rule count page {page_no}: {len(parsed)}")
            for raw_rule in parsed:
                if not isinstance(raw_rule, dict):
                    continue
                raw_rule.setdefault("source", "llm")
                raw_rule.setdefault("confidence", 0.70)
                item = normalize_rule(raw_rule=raw_rule, source_document=source_document, page=page_no, context=chunk, domain=domain)
                if not item:
                    print("   [DEBUG] dropped: normalize_rule -> None")
                    continue
                if not item["parameter"]:
                    print(f"   [DEBUG] dropped empty parameter: {item.get('parameter_raw', '')}")
                    continue
                if item["mapping_confidence"] < 0.20:
                    print(f"   [DEBUG] dropped low mapping confidence: {item['mapping_confidence']}")
                    continue
                if item["confidence"] < 0.30:
                    print(f"   [DEBUG] dropped low extraction confidence: {item['confidence']}")
                    continue
                if is_bad_rule_candidate(item):
                    print(f"   [DEBUG] dropped bad rule candidate: {item.get('parameter_raw', '')}")
                    continue
                all_rules.append(item)
    return all_rules


def _extract_rules_from_tables(pdf_path: str, source_document: str, domain: str) -> list[dict]:
    raw_table_rules = extract_tables_as_rules(pdf_path, domain=domain)
    result = []
    for raw_rule in raw_table_rules:
        page = raw_rule.pop("_page", 0)
        item = normalize_rule(raw_rule=raw_rule, source_document=source_document, page=page, context=f"[table extracted, page {page}]", domain=domain)
        if _passes_filters(item):
            result.append(item)
    return result


def _passes_filters(item: dict | None) -> bool:
    if not item:
        return False
    if not item["parameter"]:
        return False
    if item["mapping_confidence"] < 0.20:
        return False
    if item["confidence"] < 0.30:
        return False
    if is_bad_rule_candidate(item):
        return False
    return True


def _dedup(rules: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for rule in rules:
        key = (rule["domain"], rule["parameter"], rule["entity"], rule["operator"], str(rule["value"]), rule["unit"], rule["condition_text"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(rule)
    return deduped


def extract_rules(pdf_path: str, domain: str = "generic", pages: list[dict] | None = None) -> list[dict]:
    print(f"\n📄 Extracting rules: {pdf_path}")
    if pages is None:
        pages = read_pdf_pages(pdf_path)
    source_document = os.path.basename(pdf_path).replace(".pdf", "").strip().lower()
    prose_rules = _extract_rules_from_prose(pages, source_document, domain)
    print(f"\n   ✔ Prose rules (pre-dedup): {len(prose_rules)}")
    table_rules = _extract_rules_from_tables(pdf_path, source_document, domain)
    print(f"   ✔ Table rules (pre-dedup): {len(table_rules)}")
    deduped = _dedup(table_rules + prose_rules)
    print(f"✅ Final rules extracted: {len(deduped)}")
    return deduped
