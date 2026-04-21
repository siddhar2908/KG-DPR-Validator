from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


def init_schema() -> None:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:CanonicalParameter) REQUIRE p.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (e:CanonicalEntity) REQUIRE e.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (dom:Domain) REQUIRE dom.name IS UNIQUE")
        session.run("CREATE INDEX rule_domain_idx IF NOT EXISTS FOR (r:Rule) ON (r.domain)")
        session.run("CREATE INDEX rule_source_idx IF NOT EXISTS FOR (r:Rule) ON (r.source_document)")
    driver.close()
    print("✅ KG schema initialised")


def clear_graph() -> None:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    driver.close()
    print("🗑️  KG cleared")
