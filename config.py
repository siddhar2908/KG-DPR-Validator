import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3:8b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

RULES_PDFS = [
    "data/pianc-wg141.pdf",
    "data/is-6966.pdf",
    "data/iwai.pdf"
]

DPR_PDF = "data/kosi-river-dpr.pdf"

RULES_OUTPUT_DIR = "data/intermediate/rules"
DPR_OUTPUT_DIR = "data/intermediate/dpr"
CLASSIFIED_OUTPUT_DIR = "data/intermediate/classified"

# debugging / speed controls
DEBUG_MAX_RULE_PAGES = int(os.getenv("DEBUG_MAX_RULE_PAGES", "0"))   # 0 = all
DEBUG_MAX_DPR_PAGES = int(os.getenv("DEBUG_MAX_DPR_PAGES", "0"))     # 0 = all