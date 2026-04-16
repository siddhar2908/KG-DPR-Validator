from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


class KGLoader:

    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

    def close(self):
        self.driver.close()

    def insert_rule(self, rule):

        query = """
        MERGE (p:Parameter {name: $param})
        MERGE (c:Constraint {
            type: $type,
            value: $value,
            unit: $unit
        })
        MERGE (p)-[:HAS_CONSTRAINT]->(c)
        """

        with self.driver.session() as session:
            session.run(query,
                        param=rule["parameter"],
                        type=rule["constraint_type"],
                        value=rule["value"],
                        unit=rule["unit"])

    def insert_dpr(self, dpr):

        query = """
        MERGE (p:Parameter {name: $param})
        MERGE (v:DPR_Value {
            value: $value,
            unit: $unit
        })
        MERGE (p)-[:HAS_VALUE]->(v)
        """

        with self.driver.session() as session:
            session.run(query,
                        param=dpr["parameter"],
                        value=dpr["value"],
                        unit=dpr["unit"])