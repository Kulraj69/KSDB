# KSdb - Production-Ready Vector Database

A scalable, cloud-native vector database built with Python, PostgreSQL, and AWS S3. Designed to compete with ChromaDB for semantic search and AI applications.

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
