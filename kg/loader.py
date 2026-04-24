from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from utils.value_utils import safe_slug, stable_id


class KGLoader:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def close(self):
        self.driver.close()

    def _ensure_document(self, session, name: str, domain: str, doc_type: str):
        doc_name = safe_slug(name)
        doc_id = stable_id(doc_name, doc_type, prefix="doc")

        session.run(
            """
            MERGE (dom:Domain {name: $domain})
            MERGE (doc:Document {id: $doc_id})
              ON CREATE SET
                doc.name = $doc_name,
                doc.domain = $domain,
                doc.type = $doc_type,
                doc.display_name = $doc_name
            MERGE (doc)-[:IN_DOMAIN]->(dom)
            """,
            domain=domain or "generic",
            doc_id=doc_id,
            doc_name=doc_name,
            doc_type=doc_type,
        )

        return doc_id

    def insert_rule(self, rule: dict) -> None:
        with self.driver.session() as session:
            doc_id = self._ensure_document(
                session,
                rule.get("source_document", "unknown_document"),
                rule.get("domain", "generic"),
                "rulebook",
            )

            session.run(
                """
                MATCH (doc:Document {id: $doc_id})
                MERGE (r:Rule {id: $id})
                SET
                    r.rule_id = $rule_id,
                    r.node_name = $node_name,
                    r.display_name = $display_name,
                    r.document_name = $document_name,
                    r.source_document = $source_document,
                    r.domain = $domain,
                    r.page = $page,
                    r.page_label = $page_label,
                    r.rule_type = $rule_type,
                    r.parameter = $parameter,
                    r.entity = $entity,
                    r.operator = $operator,
                    r.value = $value,
                    r.value_min = $value_min,
                    r.value_max = $value_max,
                    r.unit = $unit,
                    r.display_value = $display_value,
                    r.requirement_text = $requirement_text,
                    r.comparison_sentence = $comparison_sentence,
                    r.condition_text = $condition_text,
                    r.reference = $reference,
                    r.context_snippet = $context_snippet,
                    r.confidence = $confidence
                MERGE (doc)-[:HAS_RULE]->(r)
                """,
                id=rule["id"],
                rule_id=rule["rule_id"],
                node_name=rule.get("node_name", rule["rule_id"]),
                display_name=rule.get("display_name", rule["rule_id"]),
                document_name=rule.get("document_name", ""),
                source_document=rule.get("source_document", ""),
                domain=rule.get("domain", "generic"),
                page=rule.get("page", 0),
                page_label=rule.get("page_label", ""),
                rule_type=rule.get("rule_type", "semantic"),
                parameter=rule.get("parameter", ""),
                entity=rule.get("entity", ""),
                operator=rule.get("operator", ""),
                value=rule.get("value"),
                value_min=rule.get("value_min"),
                value_max=rule.get("value_max"),
                unit=rule.get("unit", ""),
                display_value=rule.get("display_value", ""),
                requirement_text=rule.get("requirement_text", ""),
                comparison_sentence=rule.get("comparison_sentence", ""),
                condition_text=rule.get("condition_text", ""),
                reference=rule.get("reference", ""),
                context_snippet=rule.get("context_snippet", ""),
                confidence=rule.get("confidence", 0.0),
                doc_id=doc_id,
            )

    def insert_fact(self, fact: dict) -> None:
        with self.driver.session() as session:
            doc_id = self._ensure_document(
                session,
                fact.get("source_document", "unknown_document"),
                fact.get("domain", "generic"),
                "dpr",
            )

            session.run(
                """
                MATCH (doc:Document {id: $doc_id})
                MERGE (f:Fact {id: $id})
                SET
                    f.fact_id = $fact_id,
                    f.node_name = $node_name,
                    f.display_name = $display_name,
                    f.document_name = $document_name,
                    f.source_document = $source_document,
                    f.domain = $domain,
                    f.page = $page,
                    f.page_label = $page_label,
                    f.parameter = $parameter,
                    f.entity = $entity,
                    f.value = $value,
                    f.value_min = $value_min,
                    f.value_max = $value_max,
                    f.unit = $unit,
                    f.display_value = $display_value,
                    f.fact_text = $fact_text,
                    f.comparison_sentence = $comparison_sentence,
                    f.context_snippet = $context_snippet,
                    f.confidence = $confidence
                MERGE (doc)-[:HAS_FACT]->(f)
                """,
                id=fact["id"],
                fact_id=fact["fact_id"],
                node_name=fact.get("node_name", fact["fact_id"]),
                display_name=fact.get("display_name", fact["fact_id"]),
                document_name=fact.get("document_name", ""),
                source_document=fact.get("source_document", ""),
                domain=fact.get("domain", "generic"),
                page=fact.get("page", 0),
                page_label=fact.get("page_label", ""),
                parameter=fact.get("parameter", ""),
                entity=fact.get("entity", ""),
                value=fact.get("value"),
                value_min=fact.get("value_min"),
                value_max=fact.get("value_max"),
                unit=fact.get("unit", ""),
                display_value=fact.get("display_value", ""),
                fact_text=fact.get("fact_text", ""),
                comparison_sentence=fact.get("comparison_sentence", ""),
                context_snippet=fact.get("context_snippet", ""),
                confidence=fact.get("confidence", 0.0),
                doc_id=doc_id,
            )

    def insert_validation_result(self, result: dict) -> None:
        if not result.get("matched_rule_internal_id"):
            return

        with self.driver.session() as session:
            session.run(
                """
                MATCH (f:Fact {id: $fact_internal_id})
                MATCH (r:Rule {id: $rule_internal_id})
                MERGE (f)-[m:MATCHED_TO]->(r)
                SET
                    m.status = $status,
                    m.match_score = $match_score,
                    m.reason = $reason,
                    m.rulebook = $matched_rulebook,
                    m.fact_sentence = $dpr_sentence,
                    m.rule_sentence = $rule_sentence
                """,
                fact_internal_id=result.get("fact_internal_id"),
                rule_internal_id=result.get("matched_rule_internal_id"),
                status=result.get("status"),
                match_score=result.get("match_score"),
                reason=result.get("reason", ""),
                matched_rulebook=result.get("matched_rulebook", ""),
                dpr_sentence=result.get("dpr_sentence", ""),
                rule_sentence=result.get("rule_sentence", ""),
            )