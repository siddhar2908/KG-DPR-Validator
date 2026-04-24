from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


def init_schema() -> None:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        session.run("CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE")
        session.run("CREATE CONSTRAINT domain_name_unique IF NOT EXISTS FOR (dom:Domain) REQUIRE dom.name IS UNIQUE")
        session.run("CREATE CONSTRAINT rule_id_unique IF NOT EXISTS FOR (r:Rule) REQUIRE r.id IS UNIQUE")
        session.run("CREATE CONSTRAINT fact_id_unique IF NOT EXISTS FOR (f:Fact) REQUIRE f.id IS UNIQUE")

        session.run("CREATE INDEX document_name_idx IF NOT EXISTS FOR (d:Document) ON (d.name)")
        session.run("CREATE INDEX rule_parameter_idx IF NOT EXISTS FOR (r:Rule) ON (r.parameter)")
        session.run("CREATE INDEX rule_entity_idx IF NOT EXISTS FOR (r:Rule) ON (r.entity)")
        session.run("CREATE INDEX rule_type_idx IF NOT EXISTS FOR (r:Rule) ON (r.rule_type)")
        session.run("CREATE INDEX fact_parameter_idx IF NOT EXISTS FOR (f:Fact) ON (f.parameter)")
        session.run("CREATE INDEX fact_entity_idx IF NOT EXISTS FOR (f:Fact) ON (f.entity)")

    driver.close()
    print("✅ KG schema initialised")


def clear_graph() -> None:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    driver.close()
    print("🗑️  KG cleared")