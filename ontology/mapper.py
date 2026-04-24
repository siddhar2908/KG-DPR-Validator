from utils.value_utils import normalize_text


def normalize_parameter(parameter: str, source_document: str = "", context: str = "") -> str:
    text = normalize_text(f"{parameter} {context}")
    source = normalize_text(source_document)

    if any(k in text for k in ["25 kv", "25kv", "traction voltage", "supply voltage", "nominal voltage", "voltage range"]):
        return "traction_voltage"

    if any(k in text for k in ["frequency", "50 hz", "50hz"]):
        return "traction_frequency"

    if any(k in text for k in ["rigid ohe", "flexible ohe", "overhead equipment", "overhead contact line", "catenary"]):
        return "ohe_system"

    if any(k in text for k in ["standard gauge", "track gauge", "rail gauge", "gauge"]):
        if "pressure gauge" not in text:
            return "track_gauge"

    if any(k in text for k in ["cbtc", "communication based train control", "communications based train control", "moving block"]):
        return "cbtc_signalling"

    if any(k in text for k in ["headway", "90 second", "90 s", "90s"]):
        return "headway"

    if any(k in text for k in ["ato", "automatic train operation"]):
        return "ato"

    if any(k in text for k in ["atp", "automatic train protection"]):
        return "atp"

    if source:
        if "60850" in source and "voltage" in text:
            return "traction_voltage"
        if "60913" in source and "overhead" in text:
            return "ohe_system"

    return normalize_text(parameter).replace(" ", "_") or "unknown_parameter"


def normalize_entity(entity: str, parameter: str = "", context: str = "") -> str:
    text = normalize_text(f"{entity} {parameter} {context}")

    if "traction" in text or "voltage" in text or "ohe" in text or "overhead" in text:
        return "traction_power_system"

    if "gauge" in text or "track" in text or "rail" in text:
        return "track"

    if "cbtc" in text or "signalling" in text or "signaling" in text or "headway" in text:
        return "signalling_system"

    if "train" in text:
        return "train_operation"

    return normalize_text(entity).replace(" ", "_") or "unknown_entity"


def infer_domain_from_parameter(parameter: str, current_domain: str = "generic") -> str:
    p = normalize_text(parameter)

    if p in {"traction_voltage", "traction_frequency", "ohe_system"}:
        return "power"

    if p in {"track_gauge"}:
        return "track"

    if p in {"cbtc_signalling", "headway", "ato", "atp"}:
        return "signalling"

    return current_domain or "generic"