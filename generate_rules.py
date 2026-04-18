import os
import json
from extract.pdf_reader import read_pdf_pages
from extract.document_classifier import classify_pages
from extract.rule_extractor import extract_rules
from config import RULES_PDFS, RULES_OUTPUT_DIR, CLASSIFIED_OUTPUT_DIR


def main():
    os.makedirs(RULES_OUTPUT_DIR, exist_ok=True)
    os.makedirs(CLASSIFIED_OUTPUT_DIR, exist_ok=True)

    total_files = len(RULES_PDFS)

    for idx, pdf in enumerate(RULES_PDFS, start=1):
        print(f"\n📄 [{idx}/{total_files}] Processing: {pdf}")

        pages = read_pdf_pages(pdf)
        classification = classify_pages(pages, pdf)
        domain = classification.get("domain", "generic") or "generic"

        class_file = os.path.basename(pdf).replace(".pdf", "-classification.json").lower()
        with open(os.path.join(CLASSIFIED_OUTPUT_DIR, class_file), "w", encoding="utf-8") as f:
            json.dump(classification, f, indent=2, ensure_ascii=False)

        rules = extract_rules(pdf, domain=domain, pages=pages)

        base_name = os.path.basename(pdf).replace(".pdf", "").strip().lower()
        filename = f"{base_name}-rules.json"
        out_path = os.path.join(RULES_OUTPUT_DIR, filename)

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({
                "type": "rule",
                "source": base_name,
                "file_path": pdf,
                "classification": classification,
                "total_rules": len(rules),
                "data": rules
            }, f, indent=2, ensure_ascii=False)

        print(f"✅ Saved: {out_path}")
        print(f"📊 Rules extracted: {len(rules)}")


if __name__ == "__main__":
    main()