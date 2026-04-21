import os
from llm.ollama_client import call_llm
from utils.json_utils import safe_single_json
from config import CLASSIFIER_MODEL_NAME


def classify_pages(pages, pdf_path: str):
    sample_text = "\n\n".join([p["text"][:1200] for p in pages[:4] if p["text"]])[:3500]
    filename = os.path.basename(pdf_path).lower()

    prompt = f"""
Classify this technical PDF for a validation pipeline.

Return ONLY valid JSON.

Schema:
{{
  "document_kind": "",
  "domain": "",
  "subdomain": "",
  "confidence": 0.0
}}

Allowed values:
- document_kind: "rulebook", "dpr", "unknown"
- domain: "highway", "railway", "inland_waterway", "building", "irrigation", "generic", "unknown"

Classification guidance:
- "rulebook" = standards, codes, guidelines, manuals, specifications, rule documents
- "dpr" = detailed project report, feasibility report, project-specific report
- "unknown" = cannot confidently decide

Filename: {filename}
TEXT:
{sample_text}
"""

    response = call_llm(prompt, model_name=CLASSIFIER_MODEL_NAME)
    result = safe_single_json(response)
    if not isinstance(result, dict):
        result = {}

    doc_kind = str(result.get("document_kind", "")).strip().lower()
    domain = str(result.get("domain", "")).strip().lower()

    if doc_kind not in {"rulebook", "dpr", "unknown"}:
        if any(x in filename for x in ["is-", "is ", "irc", "code", "standard", "guideline", "specification", "pianc", "iwai"]):
            doc_kind = "rulebook"
        elif "dpr" in filename:
            doc_kind = "dpr"
        else:
            doc_kind = "unknown"

    if domain in {"", "unknown", "generic"}:
        text_hint = sample_text.lower()
        if any(x in filename for x in ["kosi", "waterway", "iwt", "pianc", "iwai", "river", "barrage", "fairway", "channel"]) or any(x in text_hint for x in ["inland waterway", "iwt", "fairway", "navigational", "barrage", "river", "channel depth", "design discharge"]):
            domain = "inland_waterway"
        elif any(x in filename for x in ["rail", "railway", "track", "station", "rds0", "platform"]) or any(x in text_hint for x in ["track gauge", "platform", "railway", "axle load"]):
            domain = "railway"
        elif any(x in filename for x in ["road", "highway", "irc", "bridge", "culvert", "expressway", "nh"]) or any(x in text_hint for x in ["carriageway", "shoulder width", "median", "design speed", "highway"]):
            domain = "highway"
        else:
            domain = "generic"

    confidence = float(result.get("confidence", 0.0) or 0.0)
    if confidence <= 0:
        confidence = 0.3

    return {
        "document_kind": doc_kind,
        "domain": domain,
        "subdomain": str(result.get("subdomain", "")).strip(),
        "confidence": confidence,
        "source_document": os.path.basename(pdf_path).replace(".pdf", "").strip().lower(),
        "file_path": pdf_path,
    }
