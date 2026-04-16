from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


def init_schema():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    with driver.session() as session:
        session.run("""
        CREATE CONSTRAINT IF NOT EXISTS
        FOR (p:Parameter)
        REQUIRE p.name IS UNIQUE
        """)

    driver.close()