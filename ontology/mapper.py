from llm.ollama_client import call_llm
from utils.json_utils import safe_single_json
from ontology.concepts import DOMAIN_ONTOLOGY


def map_to_ontology(raw_parameter: str, raw_entity: str, domain: str = "generic"):
    ontology = DOMAIN_ONTOLOGY.get(domain, DOMAIN_ONTOLOGY["generic"])

    prompt = f"""
Map the extracted engineering phrase to the closest ontology concepts.

Return ONLY valid JSON.

Important:
- If unclear, noisy, or not a real engineering concept, return "unknown"
- Do not force a mapping

Schema:
{{
  "parameter_canonical": "",
  "entity_canonical": "",
  "mapping_confidence": 0.0
}}

Allowed parameter concepts:
{ontology["parameters"]}

Allowed entity concepts:
{ontology["entities"]}

Raw parameter: {raw_parameter}
Raw entity: {raw_entity}
"""

    response = call_llm(prompt)
    result = safe_single_json(response)

    if not result:
        result = {
            "parameter_canonical": "unknown",
            "entity_canonical": "unknown",
            "mapping_confidence": 0.0
        }

    if not result.get("parameter_canonical"):
        result["parameter_canonical"] = "unknown"

    if not result.get("entity_canonical"):
        result["entity_canonical"] = "unknown"

    if "mapping_confidence" not in result:
        result["mapping_confidence"] = 0.0

    return result