from app.sand_rag import get_sand_rag

def main():
    rag = get_sand_rag(use_mock_if_missing=True)

    print("Loaded docs:", len(rag.docs))
    print("-" * 50)

    queries = [
        "Riyadh cultural experiences",
        "family friendly tourism in Saudi Arabia",
        "تجارب ثقافية في الرياض",
        "أماكن مناسبة للعائلات",
    ]

    for q in queries:
        print("Query:", q)
        results = rag.search(q, lang=None, k=3)
        for i, d in enumerate(results, 1):
            print(f"  {i}) [{d.language}] {d.text[:140]}...")
        print("-" * 50)

if __name__ == "__main__":
    main()