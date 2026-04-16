from extract.pdf_reader import read_pdf
from llm.ollama_client import call_llm
from utils.json_utils import safe_json_parse
from config import RULES_PDF


def extract_rules():

    text = read_pdf(RULES_PDF)

    prompt = f"""
You are a strict JSON generator.

Extract engineering rules into structured format.

Return ONLY JSON:

[
  {{
    "parameter": "",
    "constraint_type": ">=",
    "value": "",
    "unit": "",
    "context": ""
  }}
]

TEXT:
{text[:6000]}
"""

    response = call_llm(prompt)
    return safe_json_parse(response)