import requests
import time
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_filtering():
    print("Testing Advanced Filtering...")
    
    # 1. Create collection
    print("Creating collection...")
    requests.post(f"{BASE_URL}/collections", json={"name": "filter_test"})
    
    # 2. Add documents with diverse metadata
    print("Adding documents...")
    docs = [
        {"id": "doc1", "text": "Apple", "metadata": {"category": "fruit", "price": 1.5, "count": 10}},
        {"id": "doc2", "text": "Banana", "metadata": {"category": "fruit", "price": 0.5, "count": 20}},
        {"id": "doc3", "text": "Carrot", "metadata": {"category": "vegetable", "price": 0.8, "count": 15}},
        {"id": "doc4", "text": "Laptop", "metadata": {"category": "electronics", "price": 1000, "count": 5}},
        {"id": "doc5", "text": "Phone", "metadata": {"category": "electronics", "price": 500, "count": 8}},
    ]
    
    for d in docs:
        requests.post(f"{BASE_URL}/collections/filter_test/add", json=d)
        
    time.sleep(1) # Wait for indexing
    
    # 3. Test Operators
    
    # $eq
    print("Testing $eq...")
    res = requests.post(f"{BASE_URL}/collections/filter_test/query", json={
        "query": "food", "k": 10, "where": {"category": {"$eq": "fruit"}}
    }).json()
    if len(res) != 2:
        print(f"❌ Expected 2 fruits, got {len(res)}")
        for r in res:
            print(f" - {r['id']}: {r['metadata']}")
    assert len(res) == 2, f"Expected 2 fruits, got {len(res)}"
    
    # $gt
    print("Testing $gt...")
    res = requests.post(f"{BASE_URL}/collections/filter_test/query", json={
        "query": "item", "k": 10, "where": {"price": {"$gt": 100}}
    }).json()
    assert len(res) == 2, f"Expected 2 expensive items, got {len(res)}"
    
    # $lte
    print("Testing $lte...")
    res = requests.post(f"{BASE_URL}/collections/filter_test/query", json={
        "query": "item", "k": 10, "where": {"count": {"$lte": 10}}
    }).json()
    assert len(res) == 3, f"Expected 3 items with low count, got {len(res)}" # doc1(10), doc4(5), doc5(8)
    
    # $in
    print("Testing $in...")
    res = requests.post(f"{BASE_URL}/collections/filter_test/query", json={
        "query": "item", "k": 10, "where": {"category": {"$in": ["fruit", "vegetable"]}}
    }).json()
    assert len(res) == 3, f"Expected 3 produce items, got {len(res)}"
    
    # $and
    print("Testing $and...")
    res = requests.post(f"{BASE_URL}/collections/filter_test/query", json={
        "query": "item", "k": 10, "where": {
            "$and": [
                {"category": {"$eq": "electronics"}},
                {"price": {"$lt": 800}}
            ]
        }
    }).json()
    assert len(res) == 1, f"Expected 1 cheap electronic, got {len(res)}" # Phone
    assert res[0]["id"] == "doc5"
    
    # Cleanup
    print("Cleaning up...")
    requests.delete(f"{BASE_URL}/collections/filter_test")
    
    print("✅ All filtering tests passed!")

if __name__ == "__main__":
    try:
        test_filtering()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
