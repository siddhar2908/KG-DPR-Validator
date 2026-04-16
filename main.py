from extract.rule_extractor import extract_rules
from extract.dpr_extractor import extract_dpr
from kg.schema import init_schema
from kg.loader import KGLoader
from validation.validator import run_validation


def main():

    print("🚀 KG DPR Validator")

    init_schema()

    rules = extract_rules()
    dpr_data = extract_dpr()

    kg = KGLoader()

    for r in rules:
        kg.insert_rule(r)

    for d in dpr_data:
        kg.insert_dpr(d)

    kg.close()

    results = run_validation()

    print("\n📊 RESULTS:\n")
    for r in results:
        print(r)


if __name__ == "__main__":
    main()