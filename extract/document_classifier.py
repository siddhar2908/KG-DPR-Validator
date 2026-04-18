import os
from llm.ollama_client import call_llm
from utils.json_utils import safe_single_json


def classify_pages(pages, pdf_path: str):
    sample_text = "\n\n".join([p["text"][:1000] for p in pages[:3] if p["text"]])[:2500]

    prompt = f"""
Classify this document.

Return ONLY valid JSON.

Schema:
{{
  "document_kind": "",
  "domain": "",
  "subdomain": "",
  "confidence": 0.0
}}

Allowed values:
- document_kind: "rulebook", "dpr", "report", "unknown"
- domain: "highway", "inland_waterway", "building", "irrigation", "generic", "unknown"

TEXT:
{sample_text}
"""

    response = call_llm(prompt)
    result = safe_single_json(response)

    if not result:
        filename = os.path.basename(pdf_path).lower()

        guessed_kind = "rulebook" if any(x in filename for x in ["is-", "iwai", "pianc", "irc"]) else "dpr"
        guessed_domain = "inland_waterway" if any(x in filename for x in ["kosi", "waterway", "iwt", "pianc", "iwai"]) else "generic"

        result = {
            "document_kind": guessed_kind,
            "domain": guessed_domain,
            "subdomain": "",
            "confidence": 0.2
        }

    result["source_document"] = os.path.basename(pdf_path).replace(".pdf", "").strip().lower()
    result["file_path"] = pdf_path
    return result


def classify_document(pdf_path: str):
    from extract.pdf_reader import read_pdf_pages
    pages = read_pdf_pages(pdf_path)
    return classify_pages(pages, pdf_path)