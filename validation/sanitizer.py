def is_valid_rule_for_parameter(parameter: str, unit: str, value) -> bool:
    parameter = (parameter or "").strip().lower()
    unit = (unit or "").strip().lower()

    try:
        if value is not None:
            float(value)
    except Exception:
        return False

    allowed_units = {
        "discharge": {"cumec", "m3/s"},
        "water level": {"m", "cm", "mm"},
        "scour depth": {"m", "cm", "mm"},
        "channel depth": {"m", "cm", "mm"},
        "channel width": {"m", "cm", "mm", "km"},
        "fairway width": {"m", "cm", "mm", "km"},
        "bend radius": {"m", "km"},
        "navigational clearance": {"m", "cm", "mm"},
        "bridge clearance": {"m", "cm", "mm"},
        "berth length": {"m", "cm", "mm"},
        "pontoon width": {"m", "cm", "mm"},
        "pontoon length": {"m", "cm", "mm"},
        "design vessel length": {"m", "cm", "mm"},
        "design vessel beam": {"m", "cm", "mm"},
        "design draft": {"m", "cm", "mm"},
        "embankment length": {"m", "km"},
        "gate size": {"m", "cm", "mm"},
        "pier width": {"m", "cm", "mm"},
        "distance": {"m", "km"}
    }

    if parameter not in allowed_units:
        return True

    return unit in allowed_units[parameter]


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

    return 0