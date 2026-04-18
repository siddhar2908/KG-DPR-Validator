import os
import json
from kg.schema import init_schema, clear_graph
from kg.loader import KGLoader
from validation.validator import run_validation
from config import RULES_OUTPUT_DIR, DPR_OUTPUT_DIR


def load_json_files(folder):
    all_data = []

    if not os.path.exists(folder):
        return all_data

    for file in os.listdir(folder):
        if not file.endswith(".json"):
            continue

        path = os.path.join(folder, file)

        with open(path, "r", encoding="utf-8") as f:
            all_data.append(json.load(f))

    return all_data


def main():
    print("🚀 Running KG Validation")

    clear_graph()
    init_schema()

    kg = KGLoader()

    rule_files = load_json_files(RULES_OUTPUT_DIR)
    for rf in rule_files:
        for rule in rf.get("data", []):
            kg.insert_rule(rule)

    dpr_files = load_json_files(DPR_OUTPUT_DIR)
    for df in dpr_files:
        for item in df.get("data", []):
            kg.insert_dpr(item)

    kg.close()

    results = run_validation()

    seen = set()
    deduped = []

    for r in results:
        key = (
            r.get("parameter"),
            r.get("entity"),
            r.get("status"),
            r.get("rule", ""),
            r.get("dpr_value", "")
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)

    print("\n📊 RESULTS:\n")
    for r in deduped:
        print(json.dumps(r, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()