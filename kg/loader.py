from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


class KGLoader:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def close(self):
        self.driver.close()

    def insert_rule(self, rule: dict) -> None:
        query = """
        MERGE (dom:Domain {name: $domain})
        MERGE (doc:Document {name: $source_document})
          ON CREATE SET doc.type = 'rulebook', doc.domain = $domain
        MERGE (p:CanonicalParameter {name: $parameter})
        MERGE (e:CanonicalEntity {name: $entity})
        CREATE (r:Rule {
            domain: $domain,
            source_document: $source_document,
            operator: $operator,
            value: $value,
            unit: $unit,
            condition_text: $condition_text,
            page: $page,
            context_snippet: $context_snippet
        })
        MERGE (doc)-[:IN_DOMAIN]->(dom)
        MERGE (r)-[:DEFINED_IN]->(doc)
        MERGE (r)-[:ON_PARAMETER]->(p)
        MERGE (r)-[:ON_ENTITY]->(e)
        """
        with self.driver.session() as session:
            session.run(
                query,
                domain=rule["domain"],
                source_document=rule["source_document"],
                parameter=rule["parameter"],
                entity=rule["entity"],
                operator=rule["operator"],
                value=rule["value"],
                unit=rule["unit"],
                condition_text=rule.get("condition_text", ""),
                page=rule["page"],
                context_snippet=rule.get("context_snippet", ""),
            )
