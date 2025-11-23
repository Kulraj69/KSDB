import requests
import time
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_hybrid():
    print("🚀 Testing Hybrid Search (Vector + Keyword)...")
    
    # 1. Setup
    requests.delete(f"{BASE_URL}/collections/hybrid_test")
    requests.post(f"{BASE_URL}/collections", json={"name": "hybrid_test"})
    
    # 2. Add Documents
    # Doc 1: Semantically related to "fruit", but contains specific code "X-99"
    # Doc 2: Semantically related to "tech", contains "X-99"
    # Doc 3: Just "fruit"
    docs = [
        "The apple is a tasty fruit. Code: X-99",
        "The server crashed with error X-99",
        "Bananas are yellow fruits."
    ]
    ids = ["doc1", "doc2", "doc3"]
    
    requests.post(f"{BASE_URL}/collections/hybrid_test/add_batch", json={
        "ids": ids,
        "documents": docs
    })
    
    # 3. Test Vector Search (Semantic)
    # Query: "something to eat" -> Should find fruit
    print("Testing Semantic Search...")
    res = requests.post(f"{BASE_URL}/collections/hybrid_test/query", json={
        "query": "something to eat",
        "k": 2
    }).json()
    print(f"Semantic Results: {[r['id'] for r in res]}")
    assert "doc1" in [r['id'] for r in res] or "doc3" in [r['id'] for r in res]
    
    # 4. Test Keyword Search (Exact Match)
    # Query: "X-99" -> Should find doc1 and doc2, even if semantics are weird
    print("Testing Hybrid/Keyword Search...")
    res = requests.post(f"{BASE_URL}/collections/hybrid_test/query", json={
        "query": "X-99",
        "k": 2
    }).json()
    print(f"Hybrid Results: {[r['id'] for r in res]}")
    
    found_ids = [r['id'] for r in res]
    assert "doc1" in found_ids, "Expected doc1 (contains X-99)"
    assert "doc2" in found_ids, "Expected doc2 (contains X-99)"
    
    # Cleanup
    requests.delete(f"{BASE_URL}/collections/hybrid_test")
    print("✅ Hybrid Search tests passed!")

if __name__ == "__main__":
    test_hybrid()
