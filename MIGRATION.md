# KSdb - Drop-in ChromaDB Replacement

## Install

```bash
pip install ksdb
```

## Usage (Exactly like ChromaDB!)

```python
import ksdb

# Create client
client = ksdb.Client()

# Create collection
collection = client.get_or_create_collection("my_documents")

# Add documents
collection.add(
    ids=["doc1", "doc2", "doc3"],
    documents=[
        "This is a document about Python",
        "This is a document about JavaScript", 
        "This is a document about databases"
    ],
    metadatas=[
        {"category": "programming", "language": "python"},
        {"category": "programming", "language": "javascript"},
        {"category": "data", "type": "database"}
    ]
)

# Search
results = collection.query(
    query_texts=["programming languages"],
    n_results=2
)

print(results)
# {
#   'ids': [['doc1', 'doc2']],
#   'documents': [['This is a document about Python', ...]],
#   'metadatas': [[{'category': 'programming', ...}]],
#   'distances': [[0.5, 0.7]]
# }

# Search with filter
results = collection.query(
    query_texts=["programming"],
    n_results=5,
    where={"category": "programming"}
)

# Delete collection
client.delete_collection("my_documents")
```

## Migrating from ChromaDB

**Just change the import!**

```python
# Before
import chromadb
client = chromadb.Client()

# After
import ksdb
client = ksdb.Client()

# Everything else stays the same!
```

## Your Data is Safe

- ✅ Automatically stored in the cloud
- ✅ No configuration needed
- ✅ Scales automatically
- ✅ You don't need to know about AWS, S3, or databases

**Just use it like ChromaDB - we handle the rest!** 🚀

## Run Your Own Server

```bash
# Start server
ksdb run

# Your client connects to it
client = ksdb.Client("http://localhost:8000")
```

## API Compatibility

| ChromaDB Method | KSdb | Status |
|----------------|------|--------|
| `Client()` | ✅ | Identical |
| `create_collection()` | ✅ | Identical |
| `get_collection()` | ✅ | Identical |
| `get_or_create_collection()` | ✅ | Identical |
| `delete_collection()` | ✅ | Identical |
| `collection.add()` | ✅ | Identical |
| `collection.query()` | ✅ | Identical |
| `collection.delete()` | ✅ | Identical |

**100% API compatible with ChromaDB!**
