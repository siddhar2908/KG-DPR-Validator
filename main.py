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
    result = []
    for fname in sorted(os.listdir(folder)):
        if not fname.endswith('.json'):
            continue
        with open(os.path.join(folder, fname), 'r', encoding='utf-8') as f:
            result.append(json.load(f))
    return result


def _collect_dpr_facts(dpr_files: list[dict]) -> list[dict]:
    facts = []
    for df in dpr_files:
        facts.extend(df.get('data', []))
    return facts


def _print_summary(results: list[dict]) -> None:
    total = len(results)
    compliant = sum(1 for r in results if r['status'] == 'compliant')
    non_compliant = sum(1 for r in results if r['status'] == 'non-compliant')
    unit_mismatch = sum(1 for r in results if r['status'] == 'unit-mismatch')
    no_rule = sum(1 for r in results if r['status'] == 'no-rule')
    flagged = sum(1 for r in results if r.get('flagged'))
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
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = os.path.join(REPORT_OUTPUT_DIR, f'validation_report_{timestamp}.json')
    flagged = [r for r in results if r.get('flagged')]
    ok = [r for r in results if not r.get('flagged')]
    report = {
        'generated_at': datetime.now().isoformat(),
        'total': len(results),
        'compliant': len(ok),
        'flagged': len(flagged),
        'flagged_results': flagged,
        'compliant_results': ok,
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n📄 Report saved: {path}")
    return path


def main() -> None:
    print('🚀 Starting KG Validation\n')
    print('── Step 1: Initialising KG ──')
    clear_graph()
    init_schema()
    rule_files = _load_json_files(RULES_OUTPUT_DIR)
    if not rule_files:
        print(f"⚠️  No rule files found in '{RULES_OUTPUT_DIR}'. Run pipeline.py first.")
        return
    kg = KGLoader()
    total_rules_loaded = 0
    for rf in rule_files:
        rules = rf.get('data', [])
        for rule in rules:
            kg.insert_rule(rule)
        total_rules_loaded += len(rules)
        print(f"   📥 Loaded {len(rules):>4} rules from '{rf.get('source')}'")
    kg.close()
    print(f"\n   ✅ Total rules in KG: {total_rules_loaded}")

    print('\n── Step 2: Loading DPR facts ──')
    dpr_files = _load_json_files(DPR_OUTPUT_DIR)
    if not dpr_files:
        print(f"⚠️  No DPR files found in '{DPR_OUTPUT_DIR}'. Run pipeline.py first.")
        return
    dpr_facts = _collect_dpr_facts(dpr_files)
    print(f"   ✅ Total DPR facts (in-memory): {len(dpr_facts)}")

    print('\n── Step 3: Running validation ──')
    results = run_validation(dpr_facts)

    seen = set()
    deduped = []
    for r in results:
        key = (r.get('parameter'), r.get('entity'), r.get('status'), r.get('rule', ''), r.get('dpr_value', ''))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)

    _print_summary(deduped)
    _save_report(deduped)


if __name__ == '__main__':
    main()
