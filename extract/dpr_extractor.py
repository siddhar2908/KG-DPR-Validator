from extract.pdf_reader import read_pdf
from llm.ollama_client import call_llm
from utils.json_utils import safe_json_parse
from config import DPR_PDF


def extract_dpr():

    text = read_pdf(DPR_PDF)

    prompt = f"""
Extract DPR parameters.

Return JSON:

[
  {{
    "parameter": "",
    "value": "",
    "unit": "",
    "context": ""
  }}
]

TEXT:
{text[:6000]}
"""

    return safe_json_parse(call_llm(prompt))