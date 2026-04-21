def is_rule_applicable(rule_condition_text: str, fact_context: str) -> bool:
    if not rule_condition_text:
        return True
    if not fact_context:
        return False
    rc = rule_condition_text.lower().strip()
    fc = fact_context.lower().strip()
    tokens = [t for t in rc.split() if len(t) > 3]
    if not tokens:
        return True
    overlap = sum(1 for t in tokens if t in fc)
    return overlap > 0
