import os
import json
from typing import Dict, List

from extract.pdf_reader import read_pdf_pages
from extract.rule_extractor import extract_rules
from extract.dpr_extractor import extract_dpr
from config import (
    INPUT_DIR,
    RULES_OUTPUT_DIR,
    DPR_OUTPUT_DIR,
    CLASSIFIED_OUTPUT_DIR,
    FORCE_REPROCESS,
)


def ensure_dirs():
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(RULES_OUTPUT_DIR, exist_ok=True)
    os.makedirs(DPR_OUTPUT_DIR, exist_ok=True)
    os.makedirs(CLASSIFIED_OUTPUT_DIR, exist_ok=True)


def list_pdf_files(folder: str) -> List[str]:
    if not os.path.exists(folder):
        return []

    return [
        os.path.join(folder, f)
        for f in sorted(os.listdir(folder))
        if f.lower().endswith(".pdf")
    ]


def infer_doc_type(file_name: str, first_pages_text: str) -> str:
    name = file_name.lower()
    text = first_pages_text.lower()

    if "dpr" in name or "detailed project report" in text:
        return "dpr"

    return "rulebook"


def infer_domain(file_name: str, first_pages_text: str) -> str:
    s = f"{file_name} {first_pages_text}".lower()

    if "60850" in s or "traction supply voltages" in s or "supply voltages of traction systems" in s:
        return "power"

    if "60913" in s or "overhead contact line" in s or "overhead contact lines" in s:
        return "power"

    if "cbtc" in s or "communications based train control" in s or "ieee 1474" in s:
        return "signalling"

    if "uic" in s or "713" in s or "sleeper" in s or "standard-gauge" in s:
        return "track"

    score = {
        "signalling": sum(k in s for k in ["cbtc", "signalling", "signal", "ato", "atp", "ats"]),
        "track": sum(k in s for k in ["gauge", "track", "rail", "sleeper", "permanent way"]),
        "power": sum(k in s for k in ["traction", "ohe", "power", "25 kv", "substation", "overhead"]),
        "rolling_stock": sum(k in s for k in ["rolling stock", "coach", "vehicle"]),
    }

    return max(score, key=score.get) if any(score.values()) else "generic"


def save_json(path: str, payload: Dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def output_exists(path: str) -> bool:
    return os.path.exists(path) and not FORCE_REPROCESS


def process_pdf(pdf_path: str):
    file_name = os.path.basename(pdf_path)
    stem = os.path.splitext(file_name)[0]

    pages = read_pdf_pages(pdf_path)
    first_pages_text = "\n".join((p.get("text", "") or "") for p in pages[:8])

    doc_type = infer_doc_type(file_name, first_pages_text)
    domain = infer_domain(file_name, first_pages_text)

    classified_payload = {
        "source_file": file_name,
        "source_path": pdf_path,
        "document_type": doc_type,
        "domain": domain,
        "page_count": len(pages),
    }

    save_json(os.path.join(CLASSIFIED_OUTPUT_DIR, f"{stem}.json"), classified_payload)

    print(f"\n📘 File: {file_name}")
    print(f"   • Type   : {doc_type}")
    print(f"   • Domain : {domain}")
    print(f"   • Pages  : {len(pages)}")

    if doc_type == "dpr":
        output_path = os.path.join(DPR_OUTPUT_DIR, f"{stem}.json")
        if output_exists(output_path):
            print(f"   ⏭️  Skipping DPR extraction: {output_path}")
            return

        data = extract_dpr(pdf_path, domain=domain, pages=pages)

        payload = {
            "source": stem,
            "source_file": file_name,
            "document_type": "dpr",
            "domain": domain,
            "data": data,
        }

        save_json(output_path, payload)
        print(f"   ✅ DPR facts saved: {output_path}")

    else:
        output_path = os.path.join(RULES_OUTPUT_DIR, f"{stem}.json")
        if output_exists(output_path):
            print(f"   ⏭️  Skipping rule extraction: {output_path}")
            return

        data = extract_rules(pdf_path, domain=domain, pages=pages)

        payload = {
            "source": stem,
            "source_file": file_name,
            "document_type": "rulebook",
            "domain": domain,
            "data": data,
        }

        save_json(output_path, payload)
        print(f"   ✅ Rules saved: {output_path}")


def main():
    ensure_dirs()

    pdfs = list_pdf_files(INPUT_DIR)
    if not pdfs:
        print(f"⚠️ No PDFs found in {INPUT_DIR}")
        return

    print("🚀 Starting extraction pipeline")
    print(f"📂 Input folder: {INPUT_DIR}")
    print(f"📄 PDFs found: {len(pdfs)}")

    for pdf in pdfs:
        try:
            process_pdf(pdf)
        except Exception as e:
            print(f"❌ Failed processing {pdf}: {e}")

    print("\n✅ Pipeline completed")


if __name__ == "__main__":
    main()