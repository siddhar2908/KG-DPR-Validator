# KG DPR Validation Project

## Directory structure

```text
kg_dpr_project/
├── config.py
├── main.py
├── pipeline.py
├── requirements.txt
├── README.md
├── data/
│   ├── input/
│   ├── intermediate/
│   │   ├── classified/
│   │   ├── dpr/
│   │   └── rules/
│   └── output/
├── extract/
│   ├── __init__.py
│   ├── document_classifier.py
│   ├── dpr_extractor.py
│   ├── pdf_reader.py
│   ├── rule_extractor.py
│   └── table_extractor.py
├── kg/
│   ├── __init__.py
│   ├── loader.py
│   └── schema.py
├── llm/
│   ├── __init__.py
│   └── ollama_client.py
├── ontology/
│   ├── __init__.py
│   └── mapper.py
├── utils/
│   ├── __init__.py
│   ├── json_utils.py
│   ├── page_filters.py
│   ├── text_utils.py
│   └── value_utils.py
└── validation/
    ├── __init__.py
    ├── rule_matcher.py
    ├── sanitizer.py
    └── validator.py
```

## Run

```bash
python pipeline.py
python main.py
```

## Neo4j visualization query

```cypher
MATCH (r:Rule)-[:ON_PARAMETER]->(p:CanonicalParameter)
OPTIONAL MATCH (r)-[:ON_ENTITY]->(e:CanonicalEntity)
OPTIONAL MATCH (r)-[:DEFINED_IN]->(d:Document)-[:IN_DOMAIN]->(dom:Domain)
RETURN r, p, e, d, dom
LIMIT 200
```
