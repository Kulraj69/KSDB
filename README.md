<div align="center">

# 🚀 KSdb

**A Production-Ready Vector Database for AI Applications**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

[Features](#-features) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [Deployment](#-deployment) • [Contributing](#-contributing)

</div>

---

## 🎯 What is KSdb?

KSdb is a **cloud-native vector database** built from scratch to compete with ChromaDB and Pinecone. It's designed for developers who need:

- ⚡ **Fast semantic search** for AI applications
- 🔍 **Metadata filtering** for precise queries
- ☁️ **Cloud-ready architecture** (AWS RDS + S3)
- 🐍 **Simple Python SDK** (ChromaDB-compatible API)
- 🌐 **REST API** for any programming language

Perfect for **RAG systems**, **semantic search**, **recommendation engines**, and **AI agents**.

---

## ✨ Features

| Feature | Status | Description |
|---------|--------|-------------|
| **Vector Search (HNSW)** | ✅ | Fast approximate nearest neighbor search |
| **Collections** | ✅ | Multi-tenant data isolation |
| **Metadata Filtering** | ✅ | Search with metadata constraints |
| **PostgreSQL Support** | ✅ | Scalable metadata storage |
| **S3 Integration** | ✅ | Cloud-native vector persistence |
| **REST API** | ✅ | Language-agnostic interface |
| **Python SDK** | ✅ | ChromaDB-like developer experience |
| **Docker Ready** | ✅ | One-command deployment |
| **AWS Deployment** | ✅ | Production-ready on App Runner/Fargate |

---

## 🚀 Quick Start

### Installation

```bash
pip install requests sentence-transformers
```

### Start the Server

```bash
# Clone the repo
git clone https://github.com/Kulraj69/KSDB.git
cd KSdb

# Run with Docker
docker-compose up

# OR run locally
cd server
pip install -r requirements.txt
python main.py
```

### Use the Python SDK

```python
from sdk import KSdbClient

# Connect to KSdb
client = KSdbClient("http://localhost:8000")

# Create a collection
collection = client.get_or_create_collection("my_documents")

# Add documents
collection.add(
    ids=["doc1", "doc2", "doc3"],
    documents=[
        "KSdb is a vector database for AI",
        "It supports semantic search",
        "Built with Python and FastAPI"
    ],
    metadatas=[
        {"category": "intro"},
        {"category": "features"},
        {"category": "tech"}
    ]
)

# Search
results = collection.query(
    query_texts=["What is KSdb?"],
    n_results=2
)

print(results)
```

---

## 📊 How It Works

```
┌──────────────────────────────────────────────┐
│              Your Application                │
└────────────────┬─────────────────────────────┘
                 │ REST API / Python SDK
                 ▼
┌──────────────────────────────────────────────┐
│           KSdb Server (FastAPI)              │
│  ┌────────────────┐  ┌──────────────────┐   │
│  │  Embeddings    │  │  HNSW Index      │   │
│  │  (Transformers)│  │  (Vector Search) │   │
│  └────────────────┘  └──────────────────┘   │
└────────────┬──────────────────┬──────────────┘
             │                  │
    ┌────────▼────────┐  ┌─────▼──────┐
    │   PostgreSQL    │  │    S3      │
    │   (Metadata)    │  │  (Vectors) │
    └─────────────────┘  └────────────┘
```

1. **Text → Embeddings**: Sentence Transformers convert text to vectors
2. **Vector Search**: HNSW algorithm finds similar vectors (10-50ms)
3. **Metadata Storage**: PostgreSQL stores text and metadata
4. **Cloud Persistence**: S3 stores vector indices for scalability

---

## 📈 Performance

| Metric | KSdb | ChromaDB | Pinecone |
|--------|------|----------|----------|
| **Search Latency** | ~10-50ms | ~10-50ms | ~50-100ms |
| **Insert Speed** | 10-20ms/doc | 5-10ms/doc | 20-50ms/doc |
| **Scalability** | Millions | Millions | Billions |
| **Cost** | **Free** (self-hosted) | **Free** (self-hosted) | **$$$** (cloud) |

---

## 🆚 Why KSdb?

### vs ChromaDB
- ✅ **Cloud-native** from day 1 (RDS + S3)
- ✅ **REST API** in addition to Python SDK
- ✅ **Transparent** - you own the infrastructure

### vs Pinecone
- ✅ **Free** - no usage limits
- ✅ **Self-hosted** - complete control
- ✅ **Open source** - customize as needed

### vs Weaviate/Qdrant
- ✅ **Simpler** - easier to understand and deploy
- ✅ **Lightweight** - no complex dependencies
- ✅ **Python-first** - built for data scientists

---

## ☁️ Deployment

### Local (SQLite)
```bash
python server/main.py
```

### Docker (PostgreSQL)
```bash
docker-compose up
```

### AWS (Production)
See [`deployment.md`](deployment.md) for step-by-step guide.

**One-command deploy:**
```bash
./push_to_ecr.sh  # Push to AWS ECR
# Then deploy to App Runner via AWS Console
```

---

## 📚 Documentation

- [**Walkthrough**](walkthrough.md) - Feature tour with examples
- [**Deployment Guide**](deployment.md) - AWS setup instructions
- [**API Reference**](http://localhost:8000/docs) - Interactive API docs (FastAPI)
- [**Contributing**](CONTRIBUTING.md) - How to contribute

---

## 🛣️ Roadmap

- [ ] **Batch Insert API** - 10x faster bulk inserts
- [ ] **Authentication** - API key support
- [ ] **Advanced Filtering** - `$gt`, `$lt`, `$in` operators
- [ ] **Cosine Similarity** - Additional distance metric
- [ ] **Update Operation** - Modify existing documents
- [ ] **Web Dashboard** - Visual interface for KSdb
- [ ] **LangChain Integration** - Official integration
- [ ] **Horizontal Scaling** - Multi-node deployment

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Areas we need help:**
- 🚀 Performance optimization
- 🔐 Authentication & security
- 📊 Advanced query features
- 🎨 Web dashboard
- 📚 Documentation & tutorials

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [HNSWlib](https://github.com/nmslib/hnswlib) - Fast vector search
- [Sentence Transformers](https://www.sbert.net/) - Text embeddings
- [PostgreSQL](https://www.postgresql.org/) - Reliable database
- [AWS S3](https://aws.amazon.com/s3/) - Scalable storage

---

## 💬 Community

- **GitHub Issues**: [Report bugs](https://github.com/Kulraj69/KSDB/issues)
- **Discussions**: [Ask questions](https://github.com/Kulraj69/KSDB/discussions)
- **Twitter**: [@Kulraj69](https://twitter.com/Kulraj69)

---

<div align="center">

**⭐ Star this repo if you find it useful!**

Made with ❤️ by [Kulraj Singh](https://github.com/Kulraj69)

</div>

## 🚀 Features

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
