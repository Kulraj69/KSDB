import requests
import time
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_graph():
    print("🚀 Testing Knowledge Graph...")
    
    # 1. Setup
    requests.delete(f"{BASE_URL}/collections/graph_test")
    requests.post(f"{BASE_URL}/collections", json={"name": "graph_test"})
    
    # 2. Add Triples
    print("Adding triples...")
    triples = [
        {"subject": "Elon Musk", "predicate": "founded", "object": "SpaceX"},
        {"subject": "Elon Musk", "predicate": "CEO of", "object": "Tesla"},
        {"subject": "SpaceX", "predicate": "builds", "object": "Starship"},
        {"subject": "Tesla", "predicate": "makes", "object": "Model Y"}
    ]
    
    res = requests.post(f"{BASE_URL}/collections/graph_test/triples/add", json={"triples": triples}).json()
    assert res["count"] == 4, f"Expected 4 triples, got {res['count']}"
    
    # 3. Query Graph (1-hop)
    print("Querying graph for 'Elon Musk'...")
    res = requests.post(f"{BASE_URL}/collections/graph_test/triples/query", json={"entities": ["Elon Musk"]}).json()
    
    print(f"Results: {res}")
    assert len(res) == 2, f"Expected 2 connections for Elon, got {len(res)}"
    
    # 4. Query Graph (Multi-hop / Expansion)
    # In a real app, we would query "Elon Musk", get "SpaceX", then query "SpaceX"
    print("Querying graph for 'SpaceX'...")
    res = requests.post(f"{BASE_URL}/collections/graph_test/triples/query", json={"entities": ["SpaceX"]}).json()
    print(f"Results: {res}")
    assert len(res) == 2, f"Expected 2 connections for SpaceX (founded by Elon, builds Starship), got {len(res)}"
    
    # Cleanup
    requests.delete(f"{BASE_URL}/collections/graph_test")
    print("✅ Graph tests passed!")

if __name__ == "__main__":
    test_graph()
