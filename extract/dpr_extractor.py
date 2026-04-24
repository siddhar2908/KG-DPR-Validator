import os
from extract.pdf_reader import read_pdf_pages
from llm.ollama_client import call_llm
from utils.json_utils import safe_json_parse
from utils.page_filters import should_skip_page
from utils.text_utils import chunk_paragraphs
from utils.value_utils import (
    clean_sentence,
    clean_text,
    extract_range,
    make_readable_fact_id,
    normalize_numeric_value_and_unit,
    safe_slug,
    stable_id,
)
from ontology.mapper import normalize_parameter, normalize_entity, infer_domain_from_parameter
from config import DEBUG_MAX_DPR_PAGES, EXTRACTION_MODEL_NAME


def is_bad_dpr_candidate(item: dict) -> bool:
    parameter = item.get("parameter", "")
    text = item.get("fact_text", "").lower()
    context = item.get("context_snippet", "").lower()

    if not parameter or parameter == "unknown_parameter":
        return True

    if "table of contents" in context or "list of tables" in context or "list of figures" in context:
        return True

    bad_terms = [
        "cost",
        "budget",
        "crore",
        "landuse",
        "cash flow",
        "tax",
        "parking",
        "humidity",
        "rainfall",
        "weather",
        "fare",
        "afc",
        "maintenance schedule",
        "coach dimensions",
    ]

    if any(t in parameter for t in bad_terms):
        return True

    if "pressure gauge" in text or "pressure gauge" in context:
        return True

    if len(text) < 5:
        return True

    return False


def normalize_dpr_item(raw_item: dict, source_document: str, page: int, context: str, domain: str, seq: int) -> dict | None:
    raw_parameter = clean_sentence(raw_item.get("parameter", ""))
    raw_entity = clean_sentence(raw_item.get("entity", ""))
    raw_value = clean_sentence(raw_item.get("value", ""))
    raw_unit = clean_sentence(raw_item.get("unit", ""))
    raw_fact_text = clean_sentence(raw_item.get("fact_text", ""))

    if not raw_parameter and not raw_fact_text:
        return None

    parameter = normalize_parameter(raw_parameter, source_document, context)
    entity = normalize_entity(raw_entity, parameter, context)
    domain = infer_domain_from_parameter(parameter, domain)

    value_raw, unit_raw, value, unit = normalize_numeric_value_and_unit(raw_value, explicit_unit=raw_unit)

    lo, hi, range_unit = extract_range(raw_value)
    value_min = None
    value_max = None

    if lo is not None and hi is not None:
        _, _, value_min, unit_min = normalize_numeric_value_and_unit(lo, explicit_unit=range_unit)
        _, _, value_max, unit_max = normalize_numeric_value_and_unit(hi, explicit_unit=range_unit)
        unit = unit_min or unit_max or unit

    document_name = source_document
    fact_text = raw_fact_text or clean_sentence(context, max_len=350)

    fact_id = make_readable_fact_id(document_name, parameter, page, seq)
    internal_id = stable_id(document_name, page, parameter, entity, value, value_min, value_max, fact_text, prefix="fact")

    display_value = ""
    if value_min is not None and value_max is not None:
        display_value = f"{value_min} to {value_max} {unit}".strip()
    elif value is not None and value != "":
        display_value = f"{value} {unit}".strip()
    elif raw_value:
        display_value = raw_value

    item = {
        "id": internal_id,
        "fact_id": fact_id,
        "node_name": f"{fact_id} | {parameter} | {display_value}".strip(" |"),
        "display_name": f"{fact_id} | {parameter} | {display_value}".strip(" |"),
        "document_name": document_name,
        "source_document": document_name,
        "domain": domain,
        "page": page,
        "page_label": f"p.{page}",
        "parameter": parameter,
        "entity": entity,
        "value": value,
        "value_min": value_min,
        "value_max": value_max,
        "unit": unit,
        "display_value": display_value,
        "fact_text": fact_text,
        "comparison_sentence": fact_text,
        "context_snippet": clean_sentence(context, max_len=500),
        "confidence": float(raw_item.get("confidence", 0.70) or 0.70),
    }

    if is_bad_dpr_candidate(item):
        return None

    return item


def extract_dpr(pdf_path: str, domain: str = "generic", pages: list[dict] | None = None) -> list[dict]:
    print(f"\n📄 Reading DPR: {pdf_path}")

    if pages is None:
        pages = read_pdf_pages(pdf_path)

    source_document = safe_slug(os.path.basename(pdf_path).replace(".pdf", ""))
    all_items = []
    page_count = 0
    seq = 1

    for page_data in pages:
        page_no = page_data["page"]
        page_text = clean_text(page_data["text"])

        if DEBUG_MAX_DPR_PAGES > 0 and page_count >= DEBUG_MAX_DPR_PAGES:
            break

        if not page_text:
            continue

        if should_skip_page(page_text):
            continue

        low = page_text.lower()
        if "table of contents" in low or "list of tables" in low or "list of figures" in low:
            continue

        useful_signals = [
            "1435",
            "standard gauge",
            "25 kv",
            "50 hz",
            "cbtc",
            "moving block",
            "headway",
            "ato",
            "atp",
            "rigid ohe",
            "flexible overhead",
            "overhead equipment",
        ]

        if not any(s in low for s in useful_signals):
            continue

        page_count += 1
        chunks = chunk_paragraphs(page_text, max_chars=2200, overlap_paragraphs=0)

        for chunk_idx, chunk in enumerate(chunks, start=1):
            chunk_low = chunk.lower()
            if not any(s in chunk_low for s in useful_signals):
                continue

            print(f"⚙️  DPR page {page_no} | chunk {chunk_idx}/{len(chunks)}", end="\r")

            prompt = f"""
Extract only DPR engineering facts that can be validated against standards.

Return ONLY valid JSON array.

Reject:
- table of contents
- list of tables
- list of figures
- cost, finance, parking, humidity, weather, maintenance schedule
- anything that is not an engineering design fact

Schema:
[
  {{
    "parameter": "",
    "entity": "",
    "value": "",
    "unit": "",
    "fact_text": "",
    "confidence": 0.7
  }}
]

Valid facts include:
- track gauge
- traction voltage / frequency
- OHE type
- CBTC signalling
- moving block
- headway
- ATO / ATP

The fact_text must be the clean sentence where the value is mentioned.

TEXT:
{chunk}
"""

            response = call_llm(prompt, model_name=EXTRACTION_MODEL_NAME)
            parsed = safe_json_parse(response)

            for raw_item in parsed:
                if not isinstance(raw_item, dict):
                    continue

                item = normalize_dpr_item(raw_item, source_document, page_no, chunk, domain, seq)

                if item:
                    all_items.append(item)
                    seq += 1

    print()

    seen = set()
    result = []

    for item in all_items:
        key = (
            item["parameter"],
            item["entity"],
            str(item.get("value")),
            str(item.get("value_min")),
            str(item.get("value_max")),
            item.get("unit"),
            item.get("fact_text"),
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(item)

    print(f"✅ Final clean DPR facts extracted: {len(result)}")
    return result