from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


class KGLoader:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

    def close(self):
        self.driver.close()

    def insert_rule(self, rule):
        query = """
        MERGE (dom:Domain {name: $domain})
        MERGE (doc:Document {name: $source_document})
          ON CREATE SET doc.type = 'rule'

        MERGE (p:ParameterConcept {name: $parameter_canonical})
        MERGE (e:EntityConcept {name: $entity_canonical})

        CREATE (r:Rule {
            parameter_raw: $parameter_raw,
            entity_raw: $entity_raw,
            operator: $operator,
            value: $value,
            unit: $unit,
            original_value: $original_value,
            original_unit: $original_unit,
            condition_text: $condition_text,
            page: $page,
            context: $context,
            confidence: $confidence,
            mapping_confidence: $mapping_confidence
        })

        MERGE (doc)-[:IN_DOMAIN]->(dom)
        MERGE (r)-[:DEFINED_IN]->(doc)
        MERGE (r)-[:ON_PARAMETER]->(p)
        MERGE (r)-[:ON_ENTITY]->(e)
        """

        c = rule["constraint"]

        with self.driver.session() as session:
            session.run(
                query,
                domain=rule["domain"],
                source_document=rule["source_document"],
                parameter_canonical=rule["parameter_canonical"],
                entity_canonical=rule["entity_canonical"] or "unknown",
                parameter_raw=rule["parameter_raw"],
                entity_raw=rule["entity_raw"],
                operator=c["operator"],
                value=c["value"],
                unit=c["unit"],
                original_value=c["original_value"],
                original_unit=c["original_unit"],
                condition_text=rule["condition_text"],
                page=rule["page"],
                context=rule["context"],
                confidence=rule["confidence"],
                mapping_confidence=rule["mapping_confidence"]
            )

    def insert_dpr(self, item):
        query = """
        MERGE (dom:Domain {name: $domain})
        MERGE (doc:Document {name: $source_document})
          ON CREATE SET doc.type = 'dpr'

        MERGE (p:ParameterConcept {name: $parameter_canonical})
        MERGE (e:EntityConcept {name: $entity_canonical})

        CREATE (f:ObservedFact {
            parameter_raw: $parameter_raw,
            entity_raw: $entity_raw,
            attribute_raw: $attribute_raw,
            value: $value,
            unit: $unit,
            original_value: $original_value,
            original_unit: $original_unit,
            page: $page,
            context: $context,
            confidence: $confidence,
            mapping_confidence: $mapping_confidence
        })

        MERGE (doc)-[:IN_DOMAIN]->(dom)
        MERGE (f)-[:OBSERVED_IN]->(doc)
        MERGE (f)-[:ON_PARAMETER]->(p)
        MERGE (f)-[:ON_ENTITY]->(e)
        """

        v = item["observed_value"]

        with self.driver.session() as session:
            session.run(
                query,
                domain=item["domain"],
                source_document=item["source_document"],
                parameter_canonical=item["parameter_canonical"],
                entity_canonical=item["entity_canonical"] or "unknown",
                parameter_raw=item["parameter_raw"],
                entity_raw=item["entity_raw"],
                attribute_raw=item["attribute_raw"],
                value=v["value"],
                unit=v["unit"],
                original_value=v["original_value"],
                original_unit=v["original_unit"],
                page=item["page"],
                context=item["context"],
                confidence=item["confidence"],
                mapping_confidence=item["mapping_confidence"]
            )