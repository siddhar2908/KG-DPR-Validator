import json
import re


def safe_json_parse(response: str):
    if not response:
        return []

    response = response.strip()

    try:
        parsed = json.loads(response)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            return [parsed]
    except Exception:
        pass

    array_match = re.search(r"\[[\s\S]*\]", response)
    if array_match:
        try:
            parsed = json.loads(array_match.group(0))
            return parsed if isinstance(parsed, list) else []
        except Exception:
            pass

    obj_match = re.search(r"\{[\s\S]*\}", response)
    if obj_match:
        try:
            parsed = json.loads(obj_match.group(0))
            return [parsed] if isinstance(parsed, dict) else []
        except Exception:
            pass

    return []


def safe_single_json(response: str):
    data = safe_json_parse(response)
    if isinstance(data, list) and data:
        return data[0]
    return {}