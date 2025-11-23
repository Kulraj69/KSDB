# Quick Start Example - KSdb

```python
# Install
pip install ksdb

# Use it!
import ksdb

# Create client (uses local SQLite by default - no setup needed!)
client = ksdb.Client()

# Create a collection
collection = client.get_or_create_collection("my_docs")

# Add documents
collection.add(
    ids=["doc1", "doc2"],
    documents=["Python is great", "KSdb is fast"],
    metadatas=[{"lang": "python"}, {"type": "db"}]
)

# Search
results = collection.query(
    query_texts=["programming"],
    n_results=2
)

print(results)
```

## Run the server

```bash
# Start server (stores data in .ksdb/ folder)
ksdb run

# Custom data path
ksdb run --path /my/data/path

# Custom port
ksdb run --port 9000
```

## Advanced: Use with PostgreSQL + S3

```python
import ksdb

client = ksdb.Client(
    backend="s3",
    database_url="postgresql://user:pass@host:5432/db",
    bucket_name="my-vectors",
    region="us-east-1"
)
```

**No AWS knowledge needed for basic use!** 🎉
