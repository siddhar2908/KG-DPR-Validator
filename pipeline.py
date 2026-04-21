import os
import json
import glob
from extract.pdf_reader import read_pdf_pages
from extract.document_classifier import classify_pages
from extract.rule_extractor import extract_rules
from extract.dpr_extractor import extract_dpr
from config import INPUT_DIR, RULES_OUTPUT_DIR, DPR_OUTPUT_DIR, CLASSIFIED_OUTPUT_DIR, FORCE_REPROCESS


def _ensure_dirs() -> None:
    for d in (INPUT_DIR, RULES_OUTPUT_DIR, DPR_OUTPUT_DIR, CLASSIFIED_OUTPUT_DIR):
        os.makedirs(d, exist_ok=True)


def _save_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved: {path}")


def _save_classification(pdf_path: str, classification: dict) -> None:
    stem = os.path.basename(pdf_path).replace(".pdf", "").strip().lower()
    out = os.path.join(CLASSIFIED_OUTPUT_DIR, f"{stem}-classification.json")
    _save_json(out, classification)


def process_rulebook(pdf_path: str, classification: dict, pages: list[dict]) -> None:
    domain = classification.get("domain", "generic") or "generic"
    stem = os.path.basename(pdf_path).replace(".pdf", "").strip().lower()
    out_path = os.path.join(RULES_OUTPUT_DIR, f"{stem}-rules.json")
    if os.path.exists(out_path) and not FORCE_REPROCESS:
        print(f"⏩ Already processed (rules): {stem}")
        return
    rules = extract_rules(pdf_path, domain=domain, pages=pages)
    _save_json(out_path, {
        "type": "rule",
        "source": stem,
        "file_path": pdf_path,
        "classification": classification,
        "total_rules": len(rules),
        "data": rules,
    })
    print(f"📊 Rules extracted: {len(rules)}")


def process_dpr(pdf_path: str, classification: dict, pages: list[dict]) -> None:
    domain = classification.get("domain", "generic") or "generic"
    stem = os.path.basename(pdf_path).replace(".pdf", "").strip().lower()
    out_path = os.path.join(DPR_OUTPUT_DIR, f"{stem}.json")
    if os.path.exists(out_path) and not FORCE_REPROCESS:
        print(f"⏩ Already processed (dpr): {stem}")
        return
    facts = extract_dpr(pdf_path, domain=domain, pages=pages)
    _save_json(out_path, {
        "type": "dpr",
        "source": stem,
        "file_path": pdf_path,
        "classification": classification,
        "total_facts": len(facts),
        "data": facts,
    })
    print(f"📊 DPR facts extracted: {len(facts)}")


def run_pipeline() -> None:
    _ensure_dirs()
    pdf_files = sorted(glob.glob(os.path.join(INPUT_DIR, "*.pdf")))
    if not pdf_files:
        print(f"⚠️  No PDFs found in '{INPUT_DIR}'.")
        return
    total = len(pdf_files)
    print(f"\n🗂️  Found {total} PDF(s) in '{INPUT_DIR}'\n{'─'*50}")
    for idx, pdf_path in enumerate(pdf_files, start=1):
        print(f"\n[{idx}/{total}] 📄 {os.path.basename(pdf_path)}")
        pages = read_pdf_pages(pdf_path)
        classification = classify_pages(pages, pdf_path)
        doc_kind = classification.get("document_kind", "unknown")
        print(f"   🏷️  Kind: {doc_kind} | Domain: {classification.get('domain')} | Confidence: {classification.get('confidence', 0):.2f}")
        _save_classification(pdf_path, classification)
        filename = os.path.basename(pdf_path).lower()
        if doc_kind == "rulebook":
            process_rulebook(pdf_path, classification, pages)
        elif doc_kind == "dpr":
            process_dpr(pdf_path, classification, pages)
        elif doc_kind == "unknown" and any(x in filename for x in ["is-", "irc", "code", "standard", "pianc", "iwai"]):
            print("   🔁 Fallback routing: treating as rulebook based on filename")
            classification["document_kind"] = "rulebook"
            process_rulebook(pdf_path, classification, pages)
        else:
            print(f"   ⚠️  Unknown document_kind '{doc_kind}' — skipping.")
    print(f"\n✅ Pipeline complete. Rules → '{RULES_OUTPUT_DIR}'  |  DPR → '{DPR_OUTPUT_DIR}'")


if __name__ == "__main__":
    run_pipeline()
