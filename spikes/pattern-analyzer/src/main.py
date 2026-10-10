import json

from src.pattern_analyzer import analyze_patterns


def main():
    relations = [
        {
            "x": "X",
            "y": "Y",
            "coefficient": 0.82,
        },
        {
            "x": "X",
            "y": "Z",
            "coefficient": 0.20,
        },
        {
            "x": "Y",
            "y": "Z",
            "coefficient": -0.71,
        },
    ]

    result = analyze_patterns(relations)

    print("=" * 60)
    print("PATTERN ANALYZER | HU-006")
    print("=" * 60)

    print("\nRELACIONES ANALIZADAS:")
    print(json.dumps(relations, indent=2, ensure_ascii=False))

    print("\nPATRONES CANDIDATOS:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()