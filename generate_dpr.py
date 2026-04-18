import os
import json
from extract.pdf_reader import read_pdf_pages
from extract.document_classifier import classify_pages
from extract.dpr_extractor import extract_dpr
from config import DPR_PDF, DPR_OUTPUT_DIR, CLASSIFIED_OUTPUT_DIR


def main():
    os.makedirs(DPR_OUTPUT_DIR, exist_ok=True)
    os.makedirs(CLASSIFIED_OUTPUT_DIR, exist_ok=True)

    print(f"📄 Opening DPR once: {DPR_PDF}")
    pages = read_pdf_pages(DPR_PDF)

    classification = classify_pages(pages, DPR_PDF)
    domain = classification.get("domain", "generic") or "generic"

    class_file = os.path.basename(DPR_PDF).replace(".pdf", "-classification.json").lower()
    with open(os.path.join(CLASSIFIED_OUTPUT_DIR, class_file), "w", encoding="utf-8") as f:
        json.dump(classification, f, indent=2, ensure_ascii=False)

    print(f"📄 Extracting DPR: {DPR_PDF}")
    dpr = extract_dpr(DPR_PDF, domain=domain, pages=pages)

    filename = os.path.basename(DPR_PDF).replace(".pdf", ".json")
    out_path = os.path.join(DPR_OUTPUT_DIR, filename)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "type": "dpr",
            "source": DPR_PDF,
            "classification": classification,
            "data": dpr
        }, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved: {out_path}")


if __name__ == "__main__":
    main()