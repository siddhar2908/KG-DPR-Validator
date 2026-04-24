import os
import json
from datetime import datetime

from kg.schema import init_schema, clear_graph
from kg.loader import KGLoader
from validation.validator import run_validation
from config import RULES_OUTPUT_DIR, DPR_OUTPUT_DIR, REPORT_OUTPUT_DIR


def _load_json_files(folder: str) -> list[dict]:
    if not os.path.exists(folder):
        return []

    out = []
    for fname in sorted(os.listdir(folder)):
        if fname.endswith(".json"):
            with open(os.path.join(folder, fname), "r", encoding="utf-8") as f:
                out.append(json.load(f))
    return out


def _collect_dpr_facts(dpr_files: list[dict]) -> list[dict]:
    facts = []
    for f in dpr_files:
        facts.extend(f.get("data", []))
    return facts


def _print_summary(results: list[dict]) -> None:
    total = len(results)
    compliant = sum(1 for r in results if r["status"] == "compliant")
    non_compliant = sum(1 for r in results if r["status"] == "non-compliant")
    unit_mismatch = sum(1 for r in results if r["status"] == "unit-mismatch")
    no_rule = sum(1 for r in results if r["status"] == "no-rule")
    flagged = sum(1 for r in results if r.get("flagged"))

    print("\n" + "═" * 60)
    print("  VALIDATION SUMMARY")
    print("═" * 60)
    print(f"  Total checks    : {total}")
    print(f"  ✅ Compliant     : {compliant}")
    print(f"  ❌ Non-compliant : {non_compliant}")
    print(f"  ⚠️  Unit mismatch : {unit_mismatch}")
    print(f"  ❓ No rule found : {no_rule}")
    print(f"  🚩 Total flagged : {flagged}")
    print("═" * 60)


def _save_report(results: list[dict]) -> str:
    os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(REPORT_OUTPUT_DIR, f"validation_report_{timestamp}.json")

    report = {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_checks": len(results),
            "compliant": sum(1 for r in results if r["status"] == "compliant"),
            "non_compliant": sum(1 for r in results if r["status"] == "non-compliant"),
            "unit_mismatch": sum(1 for r in results if r["status"] == "unit-mismatch"),
            "no_rule_found": sum(1 for r in results if r["status"] == "no-rule"),
            "flagged": sum(1 for r in results if r.get("flagged")),
        },
        "results": results,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n📄 Full validation report saved: {path}")
    return path


def main():
    print("🚀 Starting KG Validation\n")

    print("── Step 1: Initialising KG ──")
    clear_graph()
    init_schema()

    rule_files = _load_json_files(RULES_OUTPUT_DIR)
    dpr_files = _load_json_files(DPR_OUTPUT_DIR)

    if not rule_files:
        print(f"⚠️ No rule JSON files found in {RULES_OUTPUT_DIR}")
        return

    if not dpr_files:
        print(f"⚠️ No DPR JSON files found in {DPR_OUTPUT_DIR}")
        return

    kg = KGLoader()

    total_rules = 0
    for rf in rule_files:
        rules = rf.get("data", [])
        for rule in rules:
            kg.insert_rule(rule)

        total_rules += len(rules)
        print(f"   📥 Loaded {len(rules):>4} rules from '{rf.get('source')}'")

    print(f"\n   ✅ Total rules in KG: {total_rules}")

    print("\n── Step 2: Loading DPR facts ──")
    dpr_facts = _collect_dpr_facts(dpr_files)

    total_facts = 0
    for df in dpr_files:
        facts = df.get("data", [])
        for fact in facts:
            kg.insert_fact(fact)

        total_facts += len(facts)

    print(f"   ✅ Total DPR facts in memory: {len(dpr_facts)}")
    print(f"   ✅ Total DPR facts in KG    : {total_facts}")

    print("\n── Step 3: Running validation ──")
    results = run_validation(dpr_facts)

    for r in results:
        kg.insert_validation_result(r)

    kg.close()

    _print_summary(results)
    _save_report(results)


if __name__ == "__main__":
    main()