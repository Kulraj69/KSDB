from sdk import KSdbClient
import time

def main():
    client = KSdbClient()
    
    # Wait for server
    print("Checking server health...")
    try:
        client.health()
    except:
        print("Server not running. Please start the server first.")
        return

    print("Server is up!")

    # 1. Upsert data
    documents = [
        (1, "The quick brown fox jumps over the lazy dog", {"category": "animals"}),
        (2, "Machine learning is fascinating", {"category": "tech"}),
        (3, "Python is a great language for AI", {"category": "tech"}),
        (4, "Dogs are loyal pets", {"category": "animals"}),
    ]

    print(f"\nUpserting {len(documents)} documents...")
    for doc_id, text, meta in documents:
        client.upsert(doc_id, text, meta)
        print(f"Upserted {doc_id}")

    # 2. Search
    query = "programming tools"
    print(f"\nSearching for: '{query}'")
    results = client.search(query, k=2)
    
    for res in results:
        print(f"Found ID: {res['id']}, Score: {res['score']:.4f}")
        print(f"  Text: {res['text']}")
        print(f"  Meta: {res['metadata']}")

if __name__ == "__main__":
    main()
