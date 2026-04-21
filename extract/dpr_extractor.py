import os
from extract.pdf_reader import read_pdf_pages
from llm.ollama_client import call_llm
from utils.json_utils import safe_json_parse
from utils.page_filters import should_skip_page
from utils.text_utils import chunk_paragraphs
from utils.value_utils import normalize_numeric_value_and_unit
from ontology.mapper import map_to_ontology
from config import DEBUG_MAX_DPR_PAGES, EXTRACTION_MODEL_NAME


def is_bad_dpr_candidate(item: dict) -> bool:
    parameter = str(item.get("parameter", "")).strip().lower()
    entity = str(item.get("entity", "")).strip().lower()
    context = str(item.get("context_snippet", "")).strip().lower()
    value = item.get("value")
    unit = str(item.get("unit", "")).strip().lower()
    if not parameter:
        return True
    if parameter in {"number", "size", "value"} and entity in {"", "unknown"}:
        return True
    if value is not None and unit == "" and parameter in {"length", "width", "height", "depth"} and entity in {"", "unknown"}:
        return True
    banned_terms = ["cost", "budget", "ratio", "network length", "catchment area", "project cost", "expenditure", "investment", "crores"]
    if any(term in parameter for term in banned_terms):
        return True
    if any(term in context for term in ["wto", "seventh plan", "cost effectiveness", "crores"]):
        return True
    return False


def normalize_dpr_item(raw_item: dict, source_document: str, page: int, context: str, domain: str) -> dict | None:
    raw_parameter = str(raw_item.get("parameter", "")).strip()
    raw_entity = str(raw_item.get("entity", "")).strip()
    raw_attribute = str(raw_item.get("attribute", "")).strip()
    raw_value = str(raw_item.get("value", "")).strip()
    try:
        confidence = float(raw_item.get("confidence", 0.70) or 0.70)
    except Exception:
        confidence = 0.70
    if not raw_parameter or not raw_value:
        return None
    _, _, normalized_value, normalized_unit = normalize_numeric_value_and_unit(raw_value, explicit_unit=str(raw_item.get("unit", "")).strip())
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
        "value": normalized_value,
        "unit": normalized_unit,
        "attribute": raw_attribute,
        "context_snippet": context[:250].strip(),
        "parameter_raw": raw_parameter,
        "entity_raw": raw_entity,
        "mapping_confidence": float(mapped.get("mapping_confidence", 0.60) or 0.60),
        "confidence": confidence,
    }


def extract_dpr(pdf_path: str, domain: str = "generic", pages: list[dict] | None = None) -> list[dict]:
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
            print(f"⏭️  Skipping page {page_no} (low-value content)")
            continue
        page_count += 1
        chunks = chunk_paragraphs(page_text, max_chars=2200, overlap_paragraphs=0)
        for chunk_idx, chunk in enumerate(chunks, start=1):
            print(f"⚙️  DPR page {page_no} | chunk {chunk_idx}/{len(chunks)}", end="\r")
            prompt = f"""
Extract ONLY design/engineering facts from this DPR that can be checked against a technical rulebook.

Return ONLY valid JSON array.
If no validatable engineering/design fact exists, return [].

Schema:
[
  {{
    "parameter": "",
    "entity": "",
    "attribute": "",
    "value": "",
    "unit": "",
    "confidence": 0.7
  }}
]

Extract examples like design discharge, channel depth, channel width, bridge clearance, berth length, scour depth, gate size, pier width, embankment length, pond level, water level, vertical clearance, design draft, fairway width, barrage length.
Do NOT extract economics, background narrative, costs, budgets, crores, ratios, page numbers, section titles.

TEXT:
{chunk}
"""
            response = call_llm(prompt, model_name=EXTRACTION_MODEL_NAME)
            parsed = safe_json_parse(response)
            print(f"\n   [DEBUG] raw parsed dpr fact count page {page_no}: {len(parsed)}")
            for raw_item in parsed:
                if not isinstance(raw_item, dict):
                    continue
                raw_item.setdefault("confidence", 0.70)
                item = normalize_dpr_item(raw_item=raw_item, source_document=source_document, page=page_no, context=chunk, domain=domain)
                if not item:
                    print("   [DEBUG] dropped: normalize_dpr_item -> None")
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
                if is_bad_dpr_candidate(item):
                    print(f"   [DEBUG] dropped bad dpr candidate: {item.get('parameter_raw', '')}")
                    continue
                all_items.append(item)
    print()
    seen = set()
    deduped = []
    for item in all_items:
        key = (item["domain"], item["parameter"], item["entity"], str(item["value"]), item["unit"], item["attribute"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    print(f"✅ Final DPR facts extracted: {len(deduped)}")
    return deduped
