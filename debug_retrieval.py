import sys
import os
sys.path.insert(0, os.path.abspath("."))
from ksdb.client import Client

print("--- Debugging RAG Retrieval ---")
client = Client(url="http://127.0.0.1:8000")

try:
    col = client.get_collection("rag_demo")
    print("✅ Found collection 'rag_demo'")
    
    # 1. Check Count (using internal API for now as client doesn't have count)
    # We'll just list some docs
    print("\n--- querying 'keto' ---")
    results = col.query(query_texts=["keto diet"], n_results=5)
    
    docs = results["documents"][0]
    metas = results["metadatas"][0]
    dists = results["distances"][0]
    
    if not docs:
        print("❌ No documents found for query 'keto diet'")
        print("This means either:")
        print("1. The document wasn't ingested correctly.")
        print("2. The embeddings are way off.")
    else:
        print(f"✅ Found {len(docs)} chunks:")
        for i, (d, m, s) in enumerate(zip(docs, metas, dists)):
            print(f"[{i+1}] Score: {s:.4f} | Source: {m.get('source')} | Preview: {d[:50]}...")

except Exception as e:
    print(f"❌ Error: {e}")
