import requests
import time
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_auto_extraction():
    print("🚀 Testing Auto-Graph Extraction...")
    
    # 1. Setup
    requests.delete(f"{BASE_URL}/collections/auto_graph_test")
    requests.post(f"{BASE_URL}/collections", json={"name": "auto_graph_test"})
    
    # 2. Add Document with Auto-Extraction
    text = "Bill Gates founded Microsoft in Albuquerque. He later stepped down as CEO."
    print(f"Adding document: '{text}'")
    
    res = requests.post(
        f"{BASE_URL}/collections/auto_graph_test/add_batch", 
        params={"extract_graph": "true"},
        json={
            "ids": ["doc1"],
            "documents": [text],
            "metadatas": [{"source": "wiki"}]
        }
    ).json()
    
    print(f"Insert Result: {res}")
    assert res["triples_extracted"] > 0, "Expected triples to be extracted"
    
    # 3. Query Graph to verify
    print("Querying graph for 'Bill Gates'...")
    res = requests.post(f"{BASE_URL}/collections/auto_graph_test/triples/query", json={"entities": ["Bill Gates"]}).json()
    
    print(f"Graph Results: {res}")
    
    # Check if we found connections
    found_microsoft = False
    for t in res:
        if "Microsoft" in t["subject"] or "Microsoft" in t["object"]:
            found_microsoft = True
            break
            
    assert found_microsoft, "Expected connection between Bill Gates and Microsoft"
    
    # Cleanup
    requests.delete(f"{BASE_URL}/collections/auto_graph_test")
    print("✅ Auto-Extraction tests passed!")

if __name__ == "__main__":
    test_auto_extraction()
