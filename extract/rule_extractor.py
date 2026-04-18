import os
import re
from extract.pdf_reader import read_pdf_pages
from llm.ollama_client import call_llm
from utils.json_utils import safe_json_parse
from utils.page_filters import should_skip_page
from utils.text_utils import chunk_paragraphs
from utils.value_utils import extract_operator, normalize_numeric_value_and_unit
from ontology.mapper import map_to_ontology
from config import DEBUG_MAX_RULE_PAGES


def is_bad_rule_candidate(item):
    raw_param = str(item.get("parameter_raw", "")).strip().lower()
    raw_entity = str(item.get("entity_raw", "")).strip().lower()
    context = str(item.get("context", "")).strip().lower()
    constraint = item.get("constraint", {})
    value = constraint.get("value")
    unit = str(constraint.get("unit", "")).strip().lower()

    if not raw_param:
        return True

    bad_params = {"length", "width", "height", "depth", "number", "size", "value"}
    if raw_param in bad_params and not raw_entity:
        return True

    junk_context_terms = [
        "standards committee",
        "member-secretary",
        "acknowledgements",
        "appendix",
        "contents",
        "page",
        "chapter"
    ]
    if sum(1 for t in junk_context_terms if t in context) >= 2:
        return True

    if value is not None and unit == "":
        try:
            float(value)
            if raw_param in {"length", "width", "height", "depth"}:
                return True
        except Exception:
            pass

    if re.search(r"\btable_row\b", context) and unit == "":
        return True

    return False


def normalize_rule(raw_rule, source_document, page, context, domain):
    raw_parameter = str(raw_rule.get("parameter", "")).strip()
    raw_entity = str(raw_rule.get("entity", "")).strip()
    raw_value = str(raw_rule.get("value", "")).strip()
    raw_constraint_type = str(raw_rule.get("constraint_type", "")).strip()
    raw_condition = str(raw_rule.get("condition_text", "")).strip()
    confidence = float(raw_rule.get("confidence", 0.0) or 0.0)

    if not raw_parameter or not raw_value:
        return None

    operator = extract_operator(raw_constraint_type) or extract_operator(raw_value)
    if not operator:
        operator = ">="

    original_value, original_unit, normalized_value, normalized_unit = normalize_numeric_value_and_unit(
        raw_value,
        explicit_unit=str(raw_rule.get("unit", "")).strip()
    )

    mapped = map_to_ontology(raw_parameter, raw_entity, domain=domain)

    item = {
        "source_type": "rule",
        "source_document": source_document,
        "page": page,
        "context": context,
        "domain": domain,
        "parameter_raw": raw_parameter,
        "entity_raw": raw_entity,
        "parameter_canonical": mapped["parameter_canonical"],
        "entity_canonical": mapped["entity_canonical"],
        "mapping_confidence": float(mapped["mapping_confidence"] or 0.0),
        "condition_text": raw_condition,
        "confidence": confidence,
        "constraint": {
            "operator": operator,
            "value": normalized_value,
            "unit": normalized_unit,
            "original_value": original_value,
            "original_unit": original_unit
        }
    }

    return item


def extract_rules(pdf_path, domain="generic", pages=None):
    print(f"\n📄 Reading Rules: {pdf_path}")

    if pages is None:
        pages = read_pdf_pages(pdf_path)

    source_document = os.path.basename(pdf_path).replace(".pdf", "").strip().lower()
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
            print(f"⏭️ Skipping page {page_no} due to low-value structural content")
            continue

        page_count += 1
        chunks = chunk_paragraphs(page_text, max_chars=1800, overlap_paragraphs=0)

        for chunk_idx, chunk in enumerate(chunks, start=1):
            print(f"⚙️ Rule page {page_no} | Chunk {chunk_idx}/{len(chunks)}", end="\r")

            prompt = f"""
Extract measurable engineering rules.

Return ONLY valid JSON array.
If none found, return [].

Schema:
[
  {{
    "parameter": "",
    "entity": "",
    "value": "",
    "unit": "",
    "constraint_type": "",
    "condition_text": "",
    "confidence": 0.0
  }}
]

Extract only real engineering constraints.

Do NOT extract:
- contents/table of contents entries
- page numbers
- section numbers
- serial numbers
- member lists
- names
- addresses
- acknowledgements
- headings without measurable rules

Use only operators: >=, <=, >, <, ==

TEXT:
{chunk}
"""

            response = call_llm(prompt)
            parsed = safe_json_parse(response)

            for raw_rule in parsed:
                item = normalize_rule(
                    raw_rule=raw_rule,
                    source_document=source_document,
                    page=page_no,
                    context=chunk[:1200],
                    domain=domain
                )

                if not item:
                    continue
                if item["parameter_canonical"] == "unknown":
                    continue
                if item["mapping_confidence"] < 0.60:
                    continue
                if item["confidence"] < 0.45:
                    continue
                if is_bad_rule_candidate(item):
                    continue

                all_rules.append(item)

    print()

    deduped = []
    seen = set()

    for rule in all_rules:
        key = (
            rule["parameter_canonical"],
            rule["entity_canonical"],
            rule["constraint"]["operator"],
            str(rule["constraint"]["value"]),
            rule["constraint"]["unit"],
            rule["condition_text"]
        )

        if key in seen:
            continue
        seen.add(key)
        deduped.append(rule)

    print(f"✅ Final rules extracted: {len(deduped)}")
    return deduped