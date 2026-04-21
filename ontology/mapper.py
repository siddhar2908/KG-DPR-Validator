from llm.ollama_client import call_llm
from utils.json_utils import safe_single_json
from config import MAPPER_MODEL_NAME


def _fallback_parameter(raw_parameter: str) -> str:
    rp = (raw_parameter or "").strip().lower()
    if not rp:
        return "unknown"
    replacements = {
        "lacey’s scour depth": "scour depth",
        "lacey's scour depth": "scour depth",
        "present pond level": "pond level",
        "future pond level": "pond level",
        "piers width": "pier width",
        "length of barrage": "barrage length",
        "design discharge": "design discharge",
        "intensity of discharge": "discharge intensity",
        "water depth": "depth",
        "basic width": "width",
        "extra width in curves": "width",
    }
    return replacements.get(rp, rp)


def _fallback_entity(raw_entity: str) -> str:
    re_ = (raw_entity or "").strip().lower()
    return re_ if re_ else "unknown"


def map_to_ontology(raw_parameter: str, raw_entity: str, domain: str = "generic", context: str = ""):
    prompt = f"""
You are normalizing engineering concepts extracted from technical documents.

Return ONLY valid JSON object.

Schema:
{{
  "is_validatable": true,
  "parameter_canonical": "",
  "entity_canonical": "",
  "parameter_family": "",
  "entity_family": "",
  "aliases": [],
  "mapping_confidence": 0.0,
  "reason": ""
}}

Instructions:
- Normalize the extracted rule/fact into a concise engineering concept.
- If the concept is truly non-technical, policy/economic only, or not useful for engineering validation, set is_validatable=false.
- Very common engineering parameters such as depth, width, clearance, discharge, radius, height, gauge, speed, draft, length, scour depth, pond level should usually remain validatable.

Domain: {domain}
Raw parameter: {raw_parameter}
Raw entity: {raw_entity}
Context: {context[:1200]}
"""

    response = call_llm(prompt, model_name=MAPPER_MODEL_NAME)
    result = safe_single_json(response)
    if not isinstance(result, dict):
        result = {}

    result.setdefault("is_validatable", True)
    result.setdefault("parameter_canonical", "")
    result.setdefault("entity_canonical", "")
    result.setdefault("parameter_family", "unknown")
    result.setdefault("entity_family", "unknown")
    result.setdefault("aliases", [])
    result.setdefault("mapping_confidence", 0.0)
    result.setdefault("reason", "")

    if not isinstance(result["aliases"], list):
        result["aliases"] = []
    try:
        result["mapping_confidence"] = float(result["mapping_confidence"] or 0.0)
    except Exception:
        result["mapping_confidence"] = 0.0

    param = str(result.get("parameter_canonical", "") or "").strip().lower()
    entity = str(result.get("entity_canonical", "") or "").strip().lower()
    if not param or param == "unknown":
        param = _fallback_parameter(raw_parameter)
    if not entity or entity == "":
        entity = _fallback_entity(raw_entity)
    if not param:
        param = "unknown"
    if not entity:
        entity = "unknown"

    result["parameter_canonical"] = param
    result["entity_canonical"] = entity
    if result["mapping_confidence"] <= 0:
        result["mapping_confidence"] = 0.60 if param != "unknown" else 0.0

    if param != "unknown" and result.get("is_validatable") is False:
        lower_param = (raw_parameter or "").lower()
        bad_terms = ["cost", "budget", "ratio", "expenditure", "investment", "crores", "network length", "statewise breakup", "wto", "seventh plan"]
        if not any(t in lower_param for t in bad_terms):
            result["is_validatable"] = True

    result["parameter_family"] = str(result.get("parameter_family", "unknown") or "unknown").strip().lower()
    result["entity_family"] = str(result.get("entity_family", "unknown") or "unknown").strip().lower()
    result["reason"] = str(result.get("reason", "") or "").strip()
    return result
