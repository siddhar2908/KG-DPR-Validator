from collections import defaultdict
from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from validation.rule_matcher import is_rule_applicable
from validation.sanitizer import is_valid_rule_for_parameter, is_valid_fact_for_parameter, entity_match_score

FLAGGED_STATUSES = {"non-compliant", "unit-mismatch", "no-rule"}


def _evaluate(operator: str, rule_val, dpr_val) -> str:
    try:
        rv = float(rule_val)
        dv = float(dpr_val)
    except Exception:
        return "non-compliant"
    mapping = {">=": dv >= rv, "<=": dv <= rv, ">": dv > rv, "<": dv < rv, "==": dv == rv}
    result = mapping.get(str(operator).strip())
    if result is None:
        return "non-compliant"
    return "compliant" if result else "non-compliant"


def _fetch_rules(session, domain: str) -> list[dict]:
    query = """
    MATCH (r:Rule)-[:ON_PARAMETER]->(p:CanonicalParameter)
    MATCH (r)-[:ON_ENTITY]->(e:CanonicalEntity)
    MATCH (r)-[:DEFINED_IN]->(d:Document)-[:IN_DOMAIN]->(dom:Domain)
    WHERE dom.name = $domain
    RETURN p.name AS parameter, e.name AS entity, r.operator AS operator,
           r.value AS value, r.unit AS unit, r.page AS page,
           r.context_snippet AS context_snippet, r.condition_text AS condition_text,
           r.source_document AS source_document, r.domain AS domain
    """
    return [dict(r) for r in session.run(query, domain=domain)]


def run_validation(dpr_facts: list[dict]) -> list[dict]:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    domains = sorted({f.get("domain", "generic") for f in dpr_facts})
    rules_by_domain = {}
    with driver.session() as session:
        for domain in domains:
            rules_by_domain[domain] = _fetch_rules(session, domain)
    driver.close()

    clean_rules_by_domain = {}
    for domain, rules in rules_by_domain.items():
        clean_rules_by_domain[domain] = [r for r in rules if is_valid_rule_for_parameter(r["parameter"], r["unit"], r["value"])]

    clean_facts = [f for f in dpr_facts if is_valid_fact_for_parameter(f["parameter"], f["unit"], f["value"])]

    indexed_rules = {}
    for domain, rules in clean_rules_by_domain.items():
        bucket = defaultdict(list)
        for r in rules:
            bucket[r["parameter"]].append(r)
        indexed_rules[domain] = bucket

    results = []
    for fact in clean_facts:
        parameter = fact["parameter"]
        entity = fact["entity"]
        domain = fact.get("domain", "generic")
        fact_unit = fact.get("unit", "")
        candidates = indexed_rules.get(domain, {}).get(parameter, [])
        if not candidates:
            results.append({
                "parameter": parameter,
                "entity": entity,
                "domain": domain,
                "source_document": fact["source_document"],
                "dpr_page": fact["page"],
                "dpr_value": f"{fact['value']} {fact['unit']}".strip(),
                "status": "no-rule",
                "flagged": True,
                "reason": "No rule found for parameter in same domain",
            })
            continue
        scored = []
        for rule in candidates:
            score = entity_match_score(rule["entity"], entity)
            if score == 0:
                continue
            if not is_rule_applicable(rule.get("condition_text", ""), fact.get("context_snippet", "")):
                continue
            unit_bonus = 1 if (rule.get("unit") or "").strip().lower() == (fact_unit or "").strip().lower() else 0
            scored.append((score * 10 + unit_bonus, rule))
        if not scored:
            results.append({
                "parameter": parameter,
                "entity": entity,
                "domain": domain,
                "source_document": fact["source_document"],
                "dpr_page": fact["page"],
                "dpr_value": f"{fact['value']} {fact['unit']}".strip(),
                "status": "no-rule",
                "flagged": True,
                "reason": "No applicable rule after entity/context filtering",
            })
            continue
        scored.sort(key=lambda x: x[0], reverse=True)
        best_rule = scored[0][1]
        if (best_rule.get("unit") or "").strip() != (fact_unit or "").strip():
            results.append({
                "parameter": parameter,
                "entity": entity,
                "domain": domain,
                "source_document": fact["source_document"],
                "dpr_page": fact["page"],
                "dpr_value": f"{fact['value']} {fact['unit']}".strip(),
                "status": "unit-mismatch",
                "flagged": True,
                "rule": f"{best_rule['operator']} {best_rule['value']} {best_rule['unit']}".strip(),
                "rule_page": best_rule.get("page"),
            })
            continue
        status = _evaluate(best_rule["operator"], best_rule["value"], fact["value"])
        results.append({
            "parameter": parameter,
            "entity": entity,
            "domain": domain,
            "source_document": fact["source_document"],
            "dpr_page": fact["page"],
            "dpr_value": f"{fact['value']} {fact['unit']}".strip(),
            "status": status,
            "flagged": status in FLAGGED_STATUSES,
            "rule": f"{best_rule['operator']} {best_rule['value']} {best_rule['unit']}".strip(),
            "rule_page": best_rule.get("page"),
        })
    return results
