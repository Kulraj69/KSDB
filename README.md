# KSdb - Custom Vector Database

A production-ready, high-performance vector database built from scratch.

## 🏗 Architecture

| Component | Technology | Description |
|-----------|------------|-------------|
| **API Layer** | **FastAPI** (Python) | High-performance async REST API |
| **Vector Index** | **HNSWlib** | State-of-the-art Approximate Nearest Neighbor search |
| **Metadata** | **SQLite** | Lightweight, serverless SQL database (upgradable to Postgres) |
| **Embeddings** | **Sentence-Transformers** | Local inference for text-to-vector conversion |
| **Deployment** | **Docker** | Containerized for easy deployment |

## 🚀 Features

- **Upsert**: Add or update documents with vector embeddings.
- **Search**: Semantic search with HNSW index.
- **Filtering**: (Planned) Metadata filtering using SQL.
- **Persistence**: Automatic saving of index and metadata.
- **Dockerized**: Run anywhere with a single command.

## 📂 Structure

```
KSdb/
 ├── server/            # FastAPI Server
 │   ├── main.py        # API Endpoints
 │   ├── db.py          # Metadata storage (SQLite)
 │   ├── vector_index.py# HNSWlib wrapper
 │   └── Dockerfile     # Server container
 ├── client/            # Python SDK
 │   └── sdk.py         # Client library
 └── README.md
```

## 🛠 Getting Started

### Prerequisites
- Python 3.9+
- Docker (optional)

### Running Locally
```bash
cd server
pip install -r requirements.txt
python main.py
```
