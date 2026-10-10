import json

from src.hypothesis_generator import generate_hypotheses


def main():
    profile = {
        "rows": 500,
        "columns": ["X", "Y", "Z"],
        "numeric_columns": ["X", "Y", "Z"],
        "missing_values": 0,
    }

    result = generate_hypotheses(profile)

    print("=" * 60)
    print("HYPOTHESIS GENERATOR | HU-003")
    print("=" * 60)

    print("\nPERFIL DEL DATASET:")
    print(json.dumps(profile, indent=2, ensure_ascii=False))

    print("\nHIPÓTESIS GENERADAS:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()