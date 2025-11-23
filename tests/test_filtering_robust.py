import requests
import time
import sys
import json

BASE_URL = "http://127.0.0.1:8000"

def run_test(name, query, where, expected_count, expected_ids=None):
    print(f"Testing {name}...", end=" ")
    try:
        res = requests.post(f"{BASE_URL}/collections/robust_test/query", json={
            "query": query, "k": 100, "where": where
        }).json()
        
        if len(res) != expected_count:
            print(f"❌ Failed! Expected {expected_count}, got {len(res)}")
            print(f"Query: {json.dumps(where, indent=2)}")
            print(f"Results: {[r['id'] for r in res]}")
            return False
            
        if expected_ids:
            got_ids = set(r['id'] for r in res)
            if got_ids != set(expected_ids):
                print(f"❌ Failed! Expected IDs {expected_ids}, got {got_ids}")
                return False
                
        print("✅ Passed")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_robust_filtering():
    print("🚀 Starting Robust Filtering Tests...")
    
    # 1. Setup
    requests.delete(f"{BASE_URL}/collections/robust_test")
    requests.post(f"{BASE_URL}/collections", json={"name": "robust_test"})
    
    docs = [
        {"id": "laptop_pro", "text": "Pro Laptop", "metadata": {"type": "electronics", "price": 2000, "brand": "Apple", "in_stock": True}},
        {"id": "laptop_air", "text": "Air Laptop", "metadata": {"type": "electronics", "price": 1000, "brand": "Apple", "in_stock": False}},
        {"id": "pixel_phone", "text": "Pixel Phone", "metadata": {"type": "electronics", "price": 800, "brand": "Google", "in_stock": True}},
        {"id": "galaxy_phone", "text": "Galaxy Phone", "metadata": {"type": "electronics", "price": 900, "brand": "Samsung", "in_stock": True}},
        {"id": "tshirt", "text": "T-Shirt", "metadata": {"type": "clothing", "price": 20, "brand": "Nike", "sizes": ["S", "M", "L"]}},
        {"id": "jeans", "text": "Jeans", "metadata": {"type": "clothing", "price": 50, "brand": "Levi", "sizes": ["M", "L", "XL"]}},
        {"id": "book", "text": "Python Book", "metadata": {"type": "book", "price": 45, "author": "Guido"}}, # Missing 'brand'
    ]
    
    print(f"Adding {len(docs)} documents...")
    # Use batch insert for speed
    requests.post(f"{BASE_URL}/collections/robust_test/add_batch", json={
        "ids": [d["id"] for d in docs],
        "documents": [d["text"] for d in docs],
        "metadatas": [d["metadata"] for d in docs]
    })
    
    time.sleep(2) # Wait for indexing
    
    failures = 0
    
    # Test Cases
    
    # 1. Simple Equality
    if not run_test("Simple Eq", "laptop", {"brand": "Apple"}, 2, ["laptop_pro", "laptop_air"]): failures += 1
    
    # 2. Greater Than
    if not run_test("Price > 900", "item", {"price": {"$gt": 900}}, 2, ["laptop_pro", "laptop_air"]): failures += 1
    
    # 3. In List
    if not run_test("Brand In [Apple, Google]", "tech", {"brand": {"$in": ["Apple", "Google"]}}, 3, ["laptop_pro", "laptop_air", "pixel_phone"]): failures += 1
    
    # 4. Logical AND
    if not run_test("Electronics AND Price < 1000", "tech", {
        "$and": [
            {"type": {"$eq": "electronics"}},
            {"price": {"$lt": 1000}}
        ]
    }, 2, ["pixel_phone", "galaxy_phone"]): failures += 1
    
    # 5. Logical OR
    if not run_test("Apple OR Samsung", "phone", {
        "$or": [
            {"brand": {"$eq": "Apple"}},
            {"brand": {"$eq": "Samsung"}}
        ]
    }, 3, ["laptop_pro", "laptop_air", "galaxy_phone"]): failures += 1
    
    # 6. Nested Logic (AND inside OR) - Complex
    # (Apple AND > 1500) OR (Google)
    if not run_test("Complex Nested", "tech", {
        "$or": [
            {
                "$and": [
                    {"brand": {"$eq": "Apple"}},
                    {"price": {"$gt": 1500}}
                ]
            },
            {"brand": {"$eq": "Google"}}
        ]
    }, 2, ["laptop_pro", "pixel_phone"]): failures += 1
    
    # 7. Missing Field (should not match)
    if not run_test("Missing Field", "item", {"brand": "Nike"}, 1, ["tshirt"]): failures += 1
    
    # 8. Boolean Field
    if not run_test("Boolean True", "item", {"in_stock": True}, 3, ["laptop_pro", "pixel_phone", "galaxy_phone"]): failures += 1
    
    # 9. Not Equal
    if not run_test("Not Electronics", "item", {"type": {"$ne": "electronics"}}, 3, ["tshirt", "jeans", "book"]): failures += 1
    
    # Cleanup
    requests.delete(f"{BASE_URL}/collections/robust_test")
    
    if failures == 0:
        print("\n🎉 ALL ROBUST TESTS PASSED!")
        sys.exit(0)
    else:
        print(f"\n❌ {failures} TESTS FAILED")
        sys.exit(1)

if __name__ == "__main__":
    test_robust_filtering()
