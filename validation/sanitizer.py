def is_valid_rule_for_parameter(parameter: str, unit: str, value) -> bool:
    try:
        if value is not None:
            float(value)
    except Exception:
        return False
    return True


def is_valid_fact_for_parameter(parameter: str, unit: str, value) -> bool:
    return is_valid_rule_for_parameter(parameter, unit, value)


def entity_match_score(rule_entity: str, fact_entity: str) -> int:
    rule_entity = (rule_entity or "").strip().lower()
    fact_entity = (fact_entity or "").strip().lower()
    if rule_entity == fact_entity and rule_entity not in {"", "unknown"}:
        return 3
    if rule_entity in {"", "unknown"}:
        return 2
    if fact_entity in {"", "unknown"}:
        return 1
    if rule_entity in fact_entity or fact_entity in rule_entity:
        return 2
    return 0
