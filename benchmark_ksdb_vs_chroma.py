import time
import uuid
import os
import sys
import chromadb
from openai import OpenAI
from typing import List

# Force local import of ksdb
sys.path.insert(0, os.path.abspath("."))
from ksdb.client import Client as KSdbClient

# --- Configuration ---
CHROMA_API_KEY = 'ck-7oe4qjzvxj7HCWHR9iDRAfo9FPjfuGchYXjQqAAo6hj1'
CHROMA_TENANT = 'b242b559-3888-407b-9141-402da34cf4c0'
CHROMA_DATABASE = 'AI Engineer'

# LLM Configuration (Qwen)
HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    raise ValueError("Please set HF_TOKEN environment variable")
MODEL_NAME = "Qwen/Qwen2.5-72B-Instruct"

llm_client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_TOKEN,
)

# Sample Data (500 facts about Space - Larger Load)
FACTS = [
    f"Fact {i}: The planet Mars has a thin atmosphere composed primarily of carbon dioxide. It is known as the Red Planet due to iron oxide on its surface. (Batch {i})"
    for i in range(500)
]
IDS = [str(uuid.uuid4()) for _ in range(500)]

def benchmark_ksdb():
    print("\n--- 🚀 Benchmarking KSdb (Local) ---")
    client = KSdbClient(url="http://127.0.0.1:8000")
    col_name = f"bench_ksdb_{int(time.time())}"
    
    # 1. Ingestion
    start = time.time()
    col = client.create_collection(col_name)
    col.add(ids=IDS, documents=FACTS)
    ingest_time = time.time() - start
    print(f"📥 Ingestion (500 docs): {ingest_time:.4f}s")
    
    # 2. Retrieval
    query = "What is Mars atmosphere made of?"
    start = time.time()
    results = col.query(query_texts=[query], n_results=3)
    retrieve_time = time.time() - start
    print(f"🔍 Retrieval Latency: {retrieve_time:.4f}s")
    
    # 3. RAG Generation
    context = "\n".join(results["documents"][0])
    start = time.time()
    completion = llm_client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "Answer based on context."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
        ],
    )
    gen_time = time.time() - start
    print(f"🤖 Generation Time: {gen_time:.4f}s")
    print(f"📝 Answer: {completion.choices[0].message.content}")
    
    return ingest_time, retrieve_time, gen_time

def benchmark_chroma():
    print("\n--- 🌈 Benchmarking ChromaDB (Local Persistence) ---")
    try:
        # Use Local Persistent Client for fair comparison (No Network Latency)
        client = chromadb.PersistentClient(path="./chroma_benchmark_db")
        col_name = f"bench_chroma_{int(time.time())}"
        
        # 1. Ingestion
        start = time.time()
        col = client.create_collection(col_name)
        col.add(ids=IDS, documents=FACTS)
        ingest_time = time.time() - start
        print(f"📥 Ingestion (500 docs): {ingest_time:.4f}s")
        
        # 2. Retrieval
        query = "What is Mars atmosphere made of?"
        start = time.time()
        results = col.query(query_texts=[query], n_results=3)
        retrieve_time = time.time() - start
        print(f"🔍 Retrieval Latency: {retrieve_time:.4f}s")
        
        # 3. RAG Generation
        context = "\n".join(results["documents"][0])
        start = time.time()
        completion = llm_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "Answer based on context."},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
            ],
        )
        gen_time = time.time() - start
        print(f"🤖 Generation Time: {gen_time:.4f}s")
        print(f"📝 Answer: {completion.choices[0].message.content}")
        
        # Cleanup
        client.delete_collection(col_name)
        
        return ingest_time, retrieve_time, gen_time
    except Exception as e:
        print(f"❌ ChromaDB Failed: {e}")
        return None, None, None

if __name__ == "__main__":
    k_ingest, k_ret, k_gen = benchmark_ksdb()
    c_ingest, c_ret, c_gen = benchmark_chroma()
    
    print("\n--- 🏆 Final Results ---")
    print(f"{'Metric':<20} | {'KSdb (Local)':<15} | {'ChromaDB (Local)':<15}")
    print("-" * 60)
    
    if c_ingest:
        print(f"{'Ingestion (500 docs)':<20} | {k_ingest:.4f}s        | {c_ingest:.4f}s")
        print(f"{'Retrieval Latency':<20} | {k_ret:.4f}s        | {c_ret:.4f}s")
        print(f"{'RAG Generation':<20} | {k_gen:.4f}s        | {c_gen:.4f}s")
        
        k_total = k_ret + k_gen
        c_total = c_ret + c_gen
        print(f"{'Total RAG Latency':<20} | {k_total:.4f}s        | {c_total:.4f}s")
        
        if k_total < c_total:
            print(f"\n🚀 KSdb is {c_total/k_total:.1f}x faster overall!")
        else:
            print(f"\n☁️ ChromaDB is {k_total/c_total:.1f}x faster overall!")
    else:
        print("Could not compare due to ChromaDB failure.")
