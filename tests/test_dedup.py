import requests
import time
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_deduplication():
    print("🚀 Testing Auto-Deduplication...")
    
    # 1. Setup
    requests.delete(f"{BASE_URL}/collections/dedup_test")
    requests.post(f"{BASE_URL}/collections", json={"name": "dedup_test"})
    
    # 2. Add initial document
    print("Adding initial document...")
    requests.post(f"{BASE_URL}/collections/dedup_test/add_batch", json={
        "ids": ["doc1"],
        "documents": ["The quick brown fox jumps over the lazy dog"],
        "metadatas": [{"ver": 1}]
    })
    
    time.sleep(1)
    
    # 3. Try adding EXACT duplicate with deduplicate=True
    print("Attempting to add duplicate (should be skipped)...")
    res = requests.post(
        f"{BASE_URL}/collections/dedup_test/add_batch", 
        params={"deduplicate": "true"},
        json={
            "ids": ["doc2"],
            "documents": ["The quick brown fox jumps over the lazy dog"],
            "metadatas": [{"ver": 2}]
        }
    ).json()
    
    print(f"Result: {res}")
    assert res["skipped"] == 1, f"Expected 1 skipped, got {res.get('skipped')}"
    assert res["count"] == 0, f"Expected 0 added, got {res.get('count')}"
    
    # 4. Try adding SEMANTIC duplicate (slightly different text)
    print("Attempting to add semantic duplicate (should be skipped)...")
    res = requests.post(
        f"{BASE_URL}/collections/dedup_test/add_batch", 
        params={"deduplicate": "true", "similarity_threshold": "0.2"},
        json={
            "ids": ["doc3"],
            "documents": ["The quick brown fox jumped over a lazy dog"], # slightly changed
            "metadatas": [{"ver": 3}]
        }
    ).json()
    
    print(f"Result: {res}")
    assert res["skipped"] == 1, f"Expected 1 skipped, got {res.get('skipped')}"
    
    # 5. Add unique document
    print("Adding unique document (should be added)...")
    res = requests.post(
        f"{BASE_URL}/collections/dedup_test/add_batch", 
        params={"deduplicate": "true"},
        json={
            "ids": ["doc4"],
            "documents": ["Python is a programming language"],
            "metadatas": [{"ver": 4}]
        }
    ).json()
    
    print(f"Result: {res}")
    assert res["count"] == 1, "Expected 1 added"
    
    # Cleanup
    requests.delete(f"{BASE_URL}/collections/dedup_test")
    print("✅ Deduplication tests passed!")

if __name__ == "__main__":
    test_deduplication()
