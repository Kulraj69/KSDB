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

# LLM Configuration (Qwen)
HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    raise ValueError("Please set HF_TOKEN environment variable")
MODEL_NAME = "Qwen/Qwen2.5-72B-Instruct"

llm_client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_TOKEN,
)

# Sample Data (500 facts about Space)
FACTS = [
    f"Fact {i}: The planet Mars has a thin atmosphere composed primarily of carbon dioxide. It is known as the Red Planet due to iron oxide on its surface. (Batch {i})"
    for i in range(500)
]
IDS = [str(uuid.uuid4()) for _ in range(500)]

def benchmark_ksdb_pure_vector():
    """KSdb with PURE VECTOR SEARCH (no hybrid, no graph)"""
    print("\n--- 🚀 KSdb: Pure Vector Search (Fair Comparison) ---")
    client = KSdbClient(url="http://127.0.0.1:8000")
    col_name = f"bench_vector_{int(time.time())}"
    
    # 1. Ingestion (NO graph extraction)
    start = time.time()
    col = client.create_collection(col_name)
    col.add(ids=IDS, documents=FACTS, extract_graph=False, deduplicate=False)
    ingest_time = time.time() - start
    print(f"📥 Ingestion (500 docs): {ingest_time:.4f}s")
    
    # 2. Retrieval (Pure Vector)
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

def benchmark_chroma_vector():
    """ChromaDB with PURE VECTOR SEARCH (default behavior)"""
    print("\n--- 🌈 ChromaDB: Pure Vector Search (Default) ---")
    try:
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
    # Test 1: KSdb Pure Vector
    k_ingest, k_ret, k_gen = benchmark_ksdb_pure_vector()
    
    # Test 2: ChromaDB Pure Vector
    c_ingest, c_ret, c_gen = benchmark_chroma_vector()
    
    # Results
    print("\n" + "="*70)
    print("=== 🏆 FINAL RESULTS: Pure Vector Search Comparison ===")
    print("="*70)
    print(f"{'Metric':<25} | {'KSdb':<15} | {'ChromaDB':<15} | {'Winner':<15}")
    print("-" * 70)
    
    if c_ingest:
        # Ingestion
        if k_ingest < c_ingest:
            winner1 = f"KSdb ({c_ingest/k_ingest:.1f}x)"
        else:
            winner1 = f"Chroma ({k_ingest/c_ingest:.1f}x)"
        print(f"{'Ingestion (500 docs)':<25} | {k_ingest:<15.4f} | {c_ingest:<15.4f} | {winner1}")
        
        # Retrieval
        if k_ret < c_ret:
            winner2 = f"KSdb ({c_ret/k_ret:.1f}x)"
        else:
            winner2 = f"Chroma ({k_ret/c_ret:.1f}x)"
        print(f"{'Retrieval Latency':<25} | {k_ret:<15.4f} | {c_ret:<15.4f} | {winner2}")
        
        # Generation
        if k_gen < c_gen:
            winner3 = f"KSdb ({c_gen/k_gen:.1f}x)"
        else:
            winner3 = f"Chroma ({k_gen/c_gen:.1f}x)"
        print(f"{'RAG Generation':<25} | {k_gen:<15.4f} | {c_gen:<15.4f} | {winner3}")
        
        # Total
        k_total = k_ret + k_gen
        c_total = c_ret + c_gen
        if k_total < c_total:
            winner_total = f"KSdb ({c_total/k_total:.1f}x)"
        else:
            winner_total = f"Chroma ({k_total/c_total:.1f}x)"
        print(f"{'Total RAG Latency':<25} | {k_total:<15.4f} | {c_total:<15.4f} | {winner_total}")
        
        print("\n" + "="*70)
        print("🎯 **KEY INSIGHTS**:")
        print("="*70)
        print("✓ Both systems tested with PURE VECTOR SEARCH only")
        print("✓ No graph extraction, no hybrid search, no extra features")
        print("✓ This is a fair apples-to-apples comparison")
        print("\n💡 Note: KSdb supports Hybrid Search (vector+keyword) which")
        print("   ChromaDB doesn't offer. This gives better accuracy for many queries!")
    else:
        print("Could not compare due to ChromaDB failure.")
