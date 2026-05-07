# How To Use KSdb

This guide gets you from a clean checkout to a working local vector database, then shows how to ingest real public data and query it.

## 1. Install

KSdb targets Python 3.11 or 3.12. Use a virtual environment so ML dependencies do not collide with your system Python.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[server]"
```

If `python3.11` is not available, install Python 3.11 or 3.12 first. Some ML packages may lag behind newer Python releases.

For the Streamlit RAG demo, install the demo extras too:

```bash
python -m pip install -e ".[server,demo]"
```

## 2. Run The Server

```bash
ksdb run --path .ksdb --port 8000
```

Open the API docs at `http://127.0.0.1:8000/docs`.

Local data is stored under `.ksdb/` by default:

- `.ksdb/metadata.db` stores collections, documents, metadata, graph triples, and the SQLite FTS index.
- `.ksdb/indices/` stores HNSW vector index files.

## 3. Add And Query Documents

```python
from ksdb import Client

client = Client("http://127.0.0.1:8000")
collection = client.get_or_create_collection("docs")

collection.add(
    ids=["doc1", "doc2", "doc3"],
    documents=[
        "KSdb supports hybrid vector and keyword search.",
        "Metadata filters help scope retrieval to the right tenant or topic.",
        "Graph extraction can add entity relationships for graph RAG.",
    ],
    metadatas=[
        {"topic": "search", "priority": 2},
        {"topic": "filters", "priority": 1},
        {"topic": "graph", "priority": 3},
    ],
)

results = collection.query(
    query_texts=["hybrid retrieval with filters"],
    n_results=3,
    where={"priority": {"$lte": 2}},
)

print(results["ids"][0])
```

## 4. Explain A Query

When search quality looks surprising, use `explain_query()` to see whether a result came from vector search, keyword search, or both.

```python
explain = collection.explain_query(
    query_texts=["hybrid retrieval with filters"],
    n_results=3,
    where={"priority": {"$lte": 2}},
)

print(explain["profile"])
for result in explain["results"]:
    print(
        result["id"],
        result["matched_by"],
        result.get("vector_rank"),
        result.get("keyword_rank"),
        result["rrf_score"],
    )
```

The profile includes candidate counts and timings for embedding, metadata filtering, vector search, keyword search, and fusion. Use it when tuning filters, FTS behavior, HNSW settings, or future reranking.

## 5. Ingest Real Current Data

The repository includes an API-key-free Hacker News ingestion example:

```bash
python examples/ingest_hacker_news.py \
  --query "RAG vector database" \
  --limit 25 \
  --collection live_hacker_news
```

Then query it:

```python
from ksdb import Client

client = Client("http://127.0.0.1:8000")
collection = client.get_collection("live_hacker_news")

results = collection.query(
    query_texts=["what are developers discussing about hybrid search"],
    n_results=5,
    where={"source": "hacker_news"},
)

for title, url in zip(
    [m["title"] for m in results["metadatas"][0]],
    [m["url"] for m in results["metadatas"][0]],
):
    print(title, url)
```

## 6. Use The Knowledge Graph

Graph extraction is useful for graph RAG and entity exploration, but it is slower than plain ingestion.

```python
collection.add(
    ids=["company1"],
    documents=["OpenAI works with Microsoft on AI infrastructure."],
    extract_graph=True,
)

graph = collection.query_graph(["OpenAI"])
print(graph)
```

For high-throughput ingestion, keep `extract_graph=False` and add graph extraction as a background job later.

## 7. Common Issues

- `ModuleNotFoundError`: activate your virtual environment and run `python -m pip install -e ".[server]"`.
- First query is slow: the embedding model is lazy-loaded on first use.
- Keyword matches like `X-99` fail in older builds: update to the latest code; FTS queries now tokenize and quote terms safely.
- Filtered queries return too few results in older builds: update to the latest code; filters now preselect matching document IDs before ranking.
