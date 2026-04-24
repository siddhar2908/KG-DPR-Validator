import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

CLASSIFIER_MODEL_NAME = os.getenv("CLASSIFIER_MODEL_NAME", "llama3:8b")
EXTRACTION_MODEL_NAME = os.getenv("EXTRACTION_MODEL_NAME", "llama3:8b")
MAPPER_MODEL_NAME = os.getenv("MAPPER_MODEL_NAME", "llama3:8b")

OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "180"))

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

INPUT_DIR = os.getenv("INPUT_DIR", "data/input")
RULES_OUTPUT_DIR = os.getenv("RULES_OUTPUT_DIR", "data/intermediate/rules")
DPR_OUTPUT_DIR = os.getenv("DPR_OUTPUT_DIR", "data/intermediate/dpr")
CLASSIFIED_OUTPUT_DIR = os.getenv("CLASSIFIED_OUTPUT_DIR", "data/intermediate/classified")
REPORT_OUTPUT_DIR = os.getenv("REPORT_OUTPUT_DIR", "data/output")

DEBUG_MAX_RULE_PAGES = int(os.getenv("DEBUG_MAX_RULE_PAGES", "0"))
DEBUG_MAX_DPR_PAGES = int(os.getenv("DEBUG_MAX_DPR_PAGES", "0"))
FORCE_REPROCESS = os.getenv("FORCE_REPROCESS", "1") == "1"

VALIDATION_MATCH_THRESHOLD = float(os.getenv("VALIDATION_MATCH_THRESHOLD", "0.35"))
VALIDATION_TOP_K = int(os.getenv("VALIDATION_TOP_K", "15"))
STRICT_DOMAIN_FILTER = os.getenv("STRICT_DOMAIN_FILTER", "0") == "1"