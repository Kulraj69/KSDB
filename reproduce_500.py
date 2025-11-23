import requests
import uuid

url = "http://127.0.0.1:8000/collections/rag_demo/add_batch"
params = {"deduplicate": True, "extract_graph": True}

# Test Case 1: Normal text
print("Test 1: Normal text")
payload = {
    "ids": [str(uuid.uuid4())],
    "documents": ["The keto diet is a low-carb diet."],
    "metadatas": [{"source": "test"}]
}
try:
    res = requests.post(url, params=params, json=payload)
    print(f"Status: {res.status_code}")
    if res.status_code != 200:
        print(res.text)
except Exception as e:
    print(e)

# Test Case 2: Empty text (might crash GLiNER)
print("\nTest 2: Empty text")
payload = {
    "ids": [str(uuid.uuid4())],
    "documents": [""],
    "metadatas": [{"source": "test"}]
}
try:
    res = requests.post(url, params=params, json=payload)
    print(f"Status: {res.status_code}")
    if res.status_code != 200:
        print(res.text)
except Exception as e:
    print(e)

# Test Case 3: Large text (10k chars)
print("\nTest 3: Large text")
large_text = "The keto diet is a low-carb diet. " * 500
payload = {
    "ids": [str(uuid.uuid4())],
    "documents": [large_text],
    "metadatas": [{"source": "test"}]
}
try:
    res = requests.post(url, params=params, json=payload)
    print(f"Status: {res.status_code}")
    if res.status_code != 200:
        print(res.text)
except Exception as e:
    print(e)
