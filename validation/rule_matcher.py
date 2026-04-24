from utils.value_utils import jaccard_similarity, normalize_text


def parameter_similarity(a: str, b: str) -> float:
    a = normalize_text(a)
    b = normalize_text(b)

    if not a or not b:
        return 0.0

    if a == b:
        return 1.0

    groups = [
        {"traction_voltage", "voltage", "nominal_voltage", "supply_voltage"},
        {"traction_frequency", "frequency"},
        {"ohe_system", "overhead_equipment", "overhead_contact_line"},
        {"track_gauge", "gauge", "standard_gauge"},
        {"cbtc_signalling", "signalling", "cbtc"},
        {"headway", "minimum_headway"},
        {"ato", "automatic_train_operation"},
        {"atp", "automatic_train_protection"},
    ]

    for g in groups:
        if a in g and b in g:
            return 0.95

    if a in b or b in a:
        return 0.75

    return jaccard_similarity(a, b)


def entity_similarity(a: str, b: str) -> float:
    a = normalize_text(a)
    b = normalize_text(b)

    if not a or not b or a == "unknown_entity" or b == "unknown_entity":
        return 0.45

    if a == b:
        return 1.0

    if a in b or b in a:
        return 0.75

    return jaccard_similarity(a, b)


def context_similarity(a: str, b: str) -> float:
    return jaccard_similarity(a, b)


def overall_match_score(rule: dict, fact: dict) -> float:
    p = parameter_similarity(rule.get("parameter", ""), fact.get("parameter", ""))
    e = entity_similarity(rule.get("entity", ""), fact.get("entity", ""))
    c = context_similarity(
        rule.get("comparison_sentence", "") or rule.get("requirement_text", ""),
        fact.get("comparison_sentence", "") or fact.get("fact_text", ""),
    )

    return (0.70 * p) + (0.20 * e) + (0.10 * c)