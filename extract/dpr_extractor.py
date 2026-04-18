import os
import re
from extract.pdf_reader import read_pdf_pages
from llm.ollama_client import call_llm
from utils.json_utils import safe_json_parse
from utils.page_filters import should_skip_page
from utils.text_utils import chunk_paragraphs
from utils.value_utils import normalize_numeric_value_and_unit
from ontology.mapper import map_to_ontology
from config import DEBUG_MAX_DPR_PAGES


def is_bad_dpr_candidate(item):
    raw_param = str(item.get("parameter_raw", "")).strip().lower()
    raw_entity = str(item.get("entity_raw", "")).strip().lower()
    context = str(item.get("context", "")).strip().lower()
    observed = item.get("observed_value", {})
    value = observed.get("value")
    unit = str(observed.get("unit", "")).strip().lower()

    if not raw_param:
        return True

    bad_params = {"length", "width", "height", "depth", "number", "size", "value"}
    if raw_param in bad_params and not raw_entity:
        return True

    if "contents" in context and "chapter" in context:
        return True

    if "acknowledgements" in context:
        return True

    if re.search(r"\bpage\b", context) and unit == "":
        return True

    if value is not None and unit == "" and raw_param in {"length", "width", "height", "depth"}:
        return True

    return False


def normalize_dpr_item(raw_item, source_document, page, context, domain):
    raw_parameter = str(raw_item.get("parameter", "")).strip()
    raw_entity = str(raw_item.get("entity", "")).strip()
    raw_attribute = str(raw_item.get("attribute", "")).strip()
    raw_value = str(raw_item.get("value", "")).strip()
    confidence = float(raw_item.get("confidence", 0.0) or 0.0)

    if not raw_parameter or not raw_value:
        return None

    original_value, original_unit, normalized_value, normalized_unit = normalize_numeric_value_and_unit(
        raw_value,
        explicit_unit=str(raw_item.get("unit", "")).strip()
    )

    mapped = map_to_ontology(raw_parameter, raw_entity, domain=domain)

    item = {
        "source_type": "dpr",
        "source_document": source_document,
        "page": page,
        "context": context,
        "domain": domain,
        "parameter_raw": raw_parameter,
        "entity_raw": raw_entity,
        "attribute_raw": raw_attribute,
        "parameter_canonical": mapped["parameter_canonical"],
        "entity_canonical": mapped["entity_canonical"],
        "mapping_confidence": float(mapped["mapping_confidence"] or 0.0),
        "confidence": confidence,
        "observed_value": {
            "value": normalized_value,
            "unit": normalized_unit,
            "original_value": original_value,
            "original_unit": original_unit
        }
    }

    return item


def extract_dpr(pdf_path, domain="generic", pages=None):
    print(f"\n📄 Reading DPR: {pdf_path}")

    if pages is None:
        pages = read_pdf_pages(pdf_path)

    source_document = os.path.basename(pdf_path).replace(".pdf", "").strip().lower()
    all_items = []

    page_count = 0

    for page_data in pages:
        page_no = page_data["page"]
        page_text = page_data["text"]

        if DEBUG_MAX_DPR_PAGES > 0 and page_count >= DEBUG_MAX_DPR_PAGES:
            break

        if not page_text:
            continue

        if should_skip_page(page_text):
            print(f"⏭️ Skipping page {page_no} due to low-value structural content")
            continue

        page_count += 1
        chunks = chunk_paragraphs(page_text, max_chars=1800, overlap_paragraphs=0)

        for chunk_idx, chunk in enumerate(chunks, start=1):
            print(f"⚙️ DPR page {page_no} | Chunk {chunk_idx}/{len(chunks)}", end="\r")

            prompt = f"""
Extract measurable engineering facts from this DPR.

Return ONLY valid JSON array.
If none found, return [].

Schema:
[
  {{
    "parameter": "",
    "entity": "",
    "attribute": "",
    "value": "",
    "unit": "",
    "confidence": 0.0
  }}
]

Extract only real engineering values.

Do NOT extract:
- contents/table of contents entries
- page numbers
- serial numbers
- chapter numbers
- general narrative without measurable value
- names and addresses
- purely administrative text

TEXT:
{chunk}
"""

            response = call_llm(prompt)
            parsed = safe_json_parse(response)

            for raw_item in parsed:
                item = normalize_dpr_item(
                    raw_item=raw_item,
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
                if is_bad_dpr_candidate(item):
                    continue

                all_items.append(item)

    print()

    deduped = []
    seen = set()

    for item in all_items:
        key = (
            item["parameter_canonical"],
            item["entity_canonical"],
            str(item["observed_value"]["value"]),
            item["observed_value"]["unit"],
            item["attribute_raw"]
        )

        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    print(f"✅ Final DPR values extracted: {len(deduped)}")
    return deduped