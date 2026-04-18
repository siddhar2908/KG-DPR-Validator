from collections import defaultdict
from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from validation.rule_matcher import is_rule_applicable
from validation.sanitizer import (
    is_valid_rule_for_parameter,
    is_valid_fact_for_parameter,
    entity_match_score
)


def evaluate(operator, rule_val, dpr_val):
    try:
        rv = float(rule_val)
        dv = float(dpr_val)
    except Exception:
        return "non-compliant"

    operator = str(operator).strip()

    if operator == ">=":
        return "compliant" if dv >= rv else "non-compliant"
    if operator == "<=":
        return "compliant" if dv <= rv else "non-compliant"
    if operator == ">":
        return "compliant" if dv > rv else "non-compliant"
    if operator == "<":
        return "compliant" if dv < rv else "non-compliant"
    if operator == "==":
        return "compliant" if dv == rv else "non-compliant"

    return "non-compliant"


def fetch_rules_and_facts(session):
    rules_query = """
    MATCH (r:Rule)-[:ON_PARAMETER]->(p:ParameterConcept)
    MATCH (r)-[:ON_ENTITY]->(e:EntityConcept)
    RETURN
        id(r) AS rule_id,
        p.name AS parameter,
        e.name AS entity,
        r.operator AS operator,
        r.value AS value,
        r.unit AS unit,
        r.page AS page,
        r.context AS context,
        r.condition_text AS condition_text,
        r.confidence AS confidence,
        r.mapping_confidence AS mapping_confidence
    """

    facts_query = """
    MATCH (f:ObservedFact)-[:ON_PARAMETER]->(p:ParameterConcept)
    MATCH (f)-[:ON_ENTITY]->(e:EntityConcept)
    RETURN
        id(f) AS fact_id,
        p.name AS parameter,
        e.name AS entity,
        f.value AS value,
        f.unit AS unit,
        f.page AS page,
        f.context AS context,
        f.confidence AS confidence,
        f.mapping_confidence AS mapping_confidence
    """

    rules = [dict(r) for r in session.run(rules_query)]
    facts = [dict(f) for f in session.run(facts_query)]

    return rules, facts


def run_validation():
    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD)
    )

    results = []

    with driver.session() as session:
        rules, facts = fetch_rules_and_facts(session)

    # filter out obviously bad rules/facts
    clean_rules = []
    for r in rules:
        if r["operator"] is None or r["value"] is None:
            continue
        if not is_valid_rule_for_parameter(r["parameter"], r["unit"], r["value"]):
            continue
        clean_rules.append(r)

    clean_facts = []
    for f in facts:
        if f["value"] is None:
            continue
        if not is_valid_fact_for_parameter(f["parameter"], f["unit"], f["value"]):
            continue
        clean_facts.append(f)

    # group rules by parameter
    rules_by_param = defaultdict(list)
    for r in clean_rules:
        rules_by_param[r["parameter"]].append(r)

    # validate each fact against best matching rule only
    for fact in clean_facts:
        parameter = fact["parameter"]
        fact_entity = fact["entity"]
        candidate_rules = rules_by_param.get(parameter, [])

        if not candidate_rules:
            results.append({
                "parameter": parameter,
                "entity": fact_entity,
                "status": "no-rule",
                "reason": "No matching rule found"
            })
            continue

        scored_candidates = []

        for rule in candidate_rules:
            score = entity_match_score(rule["entity"], fact_entity)
            if score == 0:
                continue

            if not is_rule_applicable(rule.get("condition_text", ""), fact.get("context", "")):
                continue

            # prefer same unit too
            unit_bonus = 1 if (rule.get("unit", "").strip().lower() == fact.get("unit", "").strip().lower()) else 0
            total_score = score * 10 + unit_bonus

            scored_candidates.append((total_score, rule))

        if not scored_candidates:
            results.append({
                "parameter": parameter,
                "entity": fact_entity,
                "status": "no-rule",
                "reason": "No applicable rule found after entity/context filtering"
            })
            continue

        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        best_rule = scored_candidates[0][1]

        rule_unit = (best_rule.get("unit") or "").strip()
        fact_unit = (fact.get("unit") or "").strip()

        if rule_unit != fact_unit:
            results.append({
                "parameter": parameter,
                "entity": fact_entity,
                "status": "unit-mismatch",
                "rule": f'{best_rule["operator"]} {best_rule["value"]} {rule_unit}'.strip(),
                "dpr_value": f'{fact["value"]} {fact_unit}'.strip(),
                "reason": "Best matching rule found, but normalized units do not match"
            })
            continue

        status = evaluate(best_rule["operator"], best_rule["value"], fact["value"])

        results.append({
            "parameter": parameter,
            "entity": fact_entity,
            "rule": f'{best_rule["operator"]} {best_rule["value"]} {rule_unit}'.strip(),
            "dpr_value": f'{fact["value"]} {fact_unit}'.strip(),
            "status": status,
            "rule_page": best_rule["page"],
            "dpr_page": fact["page"],
            "rule_context": best_rule["context"],
            "dpr_context": fact["context"],
            "rule_confidence": best_rule["confidence"],
            "dpr_confidence": fact["confidence"]
        })

    driver.close()
    return results