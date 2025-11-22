# KSdb Evolution: Collections & Filtering

We have successfully evolved KSdb into a multi-tenant vector database with an architecture similar to ChromaDB.

## 🚀 New Features

### 1. Collections
You can now organize data into separate **Collections**. Each collection has its own isolated vector index and metadata.
- **Isolation**: Searching in one collection never returns results from another.
- **Management**: Create, list, and delete collections dynamically.

### 2. Metadata Filtering
You can now filter search results based on metadata fields.
- **Syntax**: `where={"category": "tech"}`
- **Behavior**: Filters are applied *after* vector search (for now), ensuring you get the most relevant results that match your criteria.

## 🛠 How to Use

### Python SDK

The SDK has been completely refactored to use the `Collection` pattern.

```python
from sdk import KSdbClient

client = KSdbClient()

# 1. Get or Create a Collection
collection = client.get_or_create_collection("my_docs")

# 2. Add Data
collection.add(
    ids=["doc1", "doc2"],
    documents=["Hello world", "Vector databases are cool"],
    metadatas=[{"source": "demo"}, {"source": "demo"}]
)

# 3. Search
results = collection.query(
    query_texts=["database"],
    n_results=2
)

# 4. Search with Filter
results = collection.query(
    query_texts=["database"],
    n_results=2,
    where={"source": "demo"}
)
```

## ✅ Verification Results

We ran `client/test_chroma_flow.py` to verify the changes.

### Test 1: Collection Isolation
> **Goal**: Ensure searching for "cat" in `documents` collection does NOT find the "cat" image stored in `images` collection.
> **Result**: ✅ PASS. Only text documents were returned.

### Test 2: Metadata Filtering
> **Goal**: Search for "language" but only return documents where `category="tech"`.
> **Result**: ✅ PASS. Non-tech documents were filtered out.

## 🏗 Architecture Changes

| Component | Old | New |
|-----------|-----|-----|
| **MetadataDB** | Single `documents` table | `collections` table + `documents` table with `collection_id` |
| **VectorIndex** | Single `index.bin` | Multiple `indices/{uuid}.bin` files |
| **API** | `/upsert`, `/search` | `/collections/{name}/add`, `/collections/{name}/query` |
