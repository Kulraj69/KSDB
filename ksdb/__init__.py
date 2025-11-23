"""
KSdb - A production-ready vector database for AI applications

Drop-in replacement for ChromaDB with cloud storage built-in.

Usage:
    import ksdb
    
    client = ksdb.Client()
    collection = client.get_or_create_collection("my_docs")
    
    collection.add(
        ids=["doc1", "doc2"],
        documents=["Python is great", "KSdb is fast"],
        metadatas=[{"lang": "python"}, {"type": "db"}]
    )
    
    results = collection.query(
        query_texts=["programming"],
        n_results=5
    )
"""

__version__ = "0.1.0"

from ksdb.client import Client, Collection

__all__ = ["Client", "Collection"]
