from neo4j import GraphDatabase
from config import (
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    VALIDATION_MATCH_THRESHOLD,
)
from utils.value_utils import clean_sentence, normalize_unit, try_float
from validation.rule_matcher import overall_match_score


FLAGGED_STATUSES = {"non-compliant", "unit-mismatch", "no-rule"}


def _fetch_rules(session) -> list[dict]:
    query = """
    MATCH (doc:Document)-[:HAS_RULE]->(r:Rule)
    RETURN
      r.id AS id,
      r.rule_id AS rule_id,
      r.parameter AS parameter,
      r.entity AS entity,
      r.domain AS domain,
      r.rule_type AS rule_type,
      r.operator AS operator,
      r.value AS value,
      r.value_min AS value_min,
      r.value_max AS value_max,
      r.unit AS unit,
      r.display_value AS display_value,
      r.requirement_text AS requirement_text,
      r.comparison_sentence AS comparison_sentence,
      r.source_document AS source_document,
      r.page AS page,
      r.page_label AS page_label,
      r.reference AS reference
    """
    return [dict(r) for r in session.run(query)]


def _units_match(rule_unit: str, fact_unit: str) -> bool:
    ru = normalize_unit(rule_unit or "")
    fu = normalize_unit(fact_unit or "")

    if not ru or not fu:
        return True

    return ru == fu


def _evaluate(rule: dict, fact: dict) -> tuple[str, str]:
    rule_type = rule.get("rule_type", "semantic")

    if not _units_match(rule.get("unit"), fact.get("unit")):
        return "unit-mismatch", "Units are different."

    fv = try_float(fact.get("value"))
    rv = try_float(rule.get("value"))
    rmin = try_float(rule.get("value_min"))
    rmax = try_float(rule.get("value_max"))

    if rule_type == "range" and rmin is not None and rmax is not None and fv is not None:
        if rmin <= fv <= rmax:
            return "compliant", "DPR value is within the permitted range."
        return "non-compliant", "DPR value is outside the permitted range."

    if rule_type in {"numeric", "exact"} and rv is not None and fv is not None:
        op = rule.get("operator") or "=="

        if op == ">=":
            ok = fv >= rv
        elif op == "<=":
            ok = fv <= rv
        elif op == ">":
            ok = fv > rv
        elif op == "<":
            ok = fv < rv
        else:
            ok = fv == rv

        return ("compliant", "DPR value satisfies the numeric rule.") if ok else (
            "non-compliant",
            "DPR value does not satisfy the numeric rule.",
        )

    return "compliant", "Semantic rule matched the DPR fact."


def run_validation(dpr_facts: list[dict]) -> list[dict]:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    with driver.session() as session:
        rules = _fetch_rules(session)

    driver.close()

    results = []

    for fact in dpr_facts:
        scored = []

        for rule in rules:
            score = overall_match_score(rule, fact)
            if score >= VALIDATION_MATCH_THRESHOLD:
                scored.append((score, rule))

        if not scored:
            results.append({
                "fact_internal_id": fact.get("id"),
                "fact_id": fact.get("fact_id"),
                "parameter": fact.get("parameter"),
                "entity": fact.get("entity"),
                "status": "no-rule",
                "flagged": True,
                "reason": "No sufficiently similar rule found.",
                "dpr_source": fact.get("source_document"),
                "dpr_page": fact.get("page"),
                "dpr_value": fact.get("display_value", ""),
                "dpr_sentence": clean_sentence(fact.get("comparison_sentence") or fact.get("fact_text")),
                "matched_rule_id": "",
                "matched_rulebook": "",
                "matched_rule_page": "",
                "matched_rule_value": "",
                "rule_sentence": "",
                "match_score": 0.0,
            })
            continue

        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_rule = scored[0]

        status, reason = _evaluate(best_rule, fact)

        results.append({
            "fact_internal_id": fact.get("id"),
            "fact_id": fact.get("fact_id"),
            "parameter": fact.get("parameter"),
            "entity": fact.get("entity"),
            "status": status,
            "flagged": status in FLAGGED_STATUSES,
            "reason": reason,
            "dpr_source": fact.get("source_document"),
            "dpr_page": fact.get("page"),
            "dpr_value": fact.get("display_value", ""),
            "dpr_sentence": clean_sentence(fact.get("comparison_sentence") or fact.get("fact_text")),
            "matched_rule_internal_id": best_rule.get("id"),
            "matched_rule_id": best_rule.get("rule_id"),
            "matched_rulebook": best_rule.get("source_document"),
            "matched_rule_page": best_rule.get("page"),
            "matched_rule_value": best_rule.get("display_value", ""),
            "rule_sentence": clean_sentence(best_rule.get("comparison_sentence") or best_rule.get("requirement_text")),
            "rule_reference": best_rule.get("reference", ""),
            "match_score": round(best_score, 4),
        })

    return results