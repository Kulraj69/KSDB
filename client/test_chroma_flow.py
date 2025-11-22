import uuid
from sdk import KSdbClient

def main():
    client = KSdbClient()

    # 1. Check Health
    print("Checking health...")
    try:
        client.heartbeat()
        print("Server is up!")
    except:
        print("Server is down. Please start it first.")
        return

    # 2. Create Collections
    print("\nCreating collections...")
    docs_col = client.get_or_create_collection("documents", metadata={"type": "text"})
    imgs_col = client.get_or_create_collection("images", metadata={"type": "media"})
    print("Collections created.")

    # 3. Add Data to 'documents'
    print("\nAdding data to 'documents'...")
    docs_col.add(
        ids=["doc1", "doc2", "doc3"],
        documents=[
            "Python is a great programming language",
            "Java is an object oriented language",
            "The quick brown fox jumps over the lazy dog"
        ],
        metadatas=[
            {"category": "tech", "author": "guido"},
            {"category": "tech", "author": "gosling"},
            {"category": "animals", "author": "unknown"}
        ]
    )

    # 4. Add Data to 'images' (simulated text descriptions)
    print("Adding data to 'images'...")
    imgs_col.add(
        ids=["img1", "img2"],
        documents=[
            "A photo of a cat",
            "A screenshot of code"
        ],
        metadatas=[
            {"tag": "animal"},
            {"tag": "tech"}
        ]
    )

    # 5. Verify Isolation: Search in 'documents' for "cat"
    # Should NOT find "A photo of a cat" from images collection
    print("\n--- Test 1: Collection Isolation ---")
    query = "cat"
    print(f"Searching for '{query}' in 'documents'...")
    results = docs_col.query(query_texts=[query], n_results=3)
    
    found_img = False
    for res in results[0]:
        print(f"  Found: {res['text']} (Score: {res['score']:.4f})")
        if "photo of a cat" in res['text']:
            found_img = True
    
    if not found_img:
        print("✅ PASS: Did not find image data in documents collection.")
    else:
        print("❌ FAIL: Found image data in documents collection!")

    # 6. Verify Filtering: Search in 'documents' with filter
    print("\n--- Test 2: Metadata Filtering ---")
    query = "language"
    filter_criteria = {"category": "tech"}
    print(f"Searching for '{query}' with filter {filter_criteria}...")
    
    results = docs_col.query(query_texts=[query], n_results=5, where=filter_criteria)
    
    all_tech = True
    for res in results[0]:
        print(f"  Found: {res['text']} | Meta: {res['metadata']}")
        if res['metadata'].get('category') != 'tech':
            all_tech = False
            
    if all_tech and len(results[0]) > 0:
        print("✅ PASS: Only returned 'tech' documents.")
    elif len(results[0]) == 0:
        print("❌ FAIL: Returned no results.")
    else:
        print("❌ FAIL: Returned non-tech documents.")

    # 7. Cleanup
    print("\nCleaning up...")
    client.delete_collection("documents")
    client.delete_collection("images")
    print("Done.")

if __name__ == "__main__":
    main()
