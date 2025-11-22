import time
import numpy as np
from sdk import KSdbClient

def benchmark_ksdb():
    client = KSdbClient()
    collection = client.get_or_create_collection("benchmark")
    
    # Test 1: Insert Speed
    print("=" * 50)
    print("BENCHMARK: KSdb Performance")
    print("=" * 50)
    
    # Insert 1000 documents
    print("\n📝 Test 1: Insert 1000 documents")
    ids = [f"doc_{i}" for i in range(1000)]
    texts = [f"This is document number {i} with some random text for testing" for i in range(1000)]
    metadatas = [{"category": f"cat_{i % 10}", "index": i} for i in range(1000)]
    
    start = time.time()
    collection.add(ids=ids, documents=texts, metadatas=metadatas)
    insert_time = time.time() - start
    print(f"✅ Inserted 1000 docs in {insert_time:.2f}s")
    print(f"   Speed: {1000/insert_time:.0f} docs/sec")
    
    # Test 2: Search Speed (Cold)
    print("\n🔍 Test 2: Search Speed (Cold - first search)")
    start = time.time()
    results = collection.query(query_texts=["random text"], n_results=10)
    cold_search_time = time.time() - start
    print(f"✅ Search completed in {cold_search_time*1000:.0f}ms")
    
    # Test 3: Search Speed (Warm)
    print("\n🔍 Test 3: Search Speed (Warm - cached)")
    times = []
    for _ in range(10):
        start = time.time()
        results = collection.query(query_texts=["document testing"], n_results=10)
        times.append(time.time() - start)
    
    avg_search_time = np.mean(times) * 1000
    print(f"✅ Average search time: {avg_search_time:.0f}ms (over 10 queries)")
    print(f"   Throughput: {1000/avg_search_time:.0f} queries/sec")
    
    # Test 4: Search with Filter
    print("\n🔍 Test 4: Search with Metadata Filter")
    start = time.time()
    results = collection.query(
        query_texts=["document"], 
        n_results=10,
        where={"category": "cat_5"}
    )
    filter_time = time.time() - start
    print(f"✅ Filtered search completed in {filter_time*1000:.0f}ms")
    
    # Cleanup
    print("\n🧹 Cleaning up...")
    client.delete_collection("benchmark")
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Insert Speed:        {1000/insert_time:.0f} docs/sec")
    print(f"Search Speed (warm): {avg_search_time:.0f}ms")
    print(f"Search Throughput:   {1000/avg_search_time:.0f} queries/sec")
    print(f"Filtered Search:     {filter_time*1000:.0f}ms")
    print("=" * 50)

if __name__ == "__main__":
    benchmark_ksdb()
