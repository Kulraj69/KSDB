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

Configure the server with environment variables, then connect with the normal client:

```bash
export DATABASE_URL="postgresql://user:pass@host:5432/db"
export S3_BUCKET_NAME="my-vectors"
export AWS_REGION="us-east-1"
ksdb run --path .ksdb
```

```python
import ksdb

client = ksdb.Client("http://127.0.0.1:8000")
```

For a fuller walkthrough, see [docs/HOW_TO_USE.md](docs/HOW_TO_USE.md).
