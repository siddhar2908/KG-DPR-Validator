from utils.value_utils import try_float, normalize_unit


def is_valid_rule(rule: dict) -> bool:
    if not rule:
        return False
    if not str(rule.get("parameter", "")).strip():
        return False
    if not str(rule.get("entity", "")).strip():
        rule["entity"] = "unknown_entity"
    if not str(rule.get("rule_type", "")).strip():
        rule["rule_type"] = "semantic"
    return True


def is_valid_fact(fact: dict) -> bool:
    if not fact:
        return False
    if not str(fact.get("parameter", "")).strip():
        return False
    if not str(fact.get("entity", "")).strip():
        fact["entity"] = "unknown_entity"
    return True


def unit_compatible(rule_unit: str, fact_unit: str) -> bool:
    ru = normalize_unit(rule_unit or "")
    fu = normalize_unit(fact_unit or "")
    if not ru and not fu:
        return True
    if not ru or not fu:
        return True
    return ru == fu


def numeric_payload_available(item: dict) -> bool:
    return (
        try_float(item.get("value")) is not None
        or (
            try_float(item.get("value_min")) is not None
            and try_float(item.get("value_max")) is not None
        )
    )