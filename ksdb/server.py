from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import numpy as np
import os
import uvicorn
import uuid

from .vector_index import VectorIndex
from .db import MetadataDB
from .extractors import GraphExtractor

app = FastAPI(title="KSdb", description="Custom Vector Database with Collections")

import torch

# Initialize components
# Lazy load model to prevent startup timeout on cloud
class LazyModel:
    def __init__(self):
        self._model = None
        self.device = "cpu"
        if torch.cuda.is_available():
            self.device = "cuda"
            print("🚀 Hardware Acceleration: CUDA (NVIDIA GPU) Enabled")
        elif torch.backends.mps.is_available():
            self.device = "mps"
            print("🚀 Hardware Acceleration: MPS (Mac GPU) Enabled")
        else:
            print("⚠️ Hardware Acceleration: Disabled (CPU Mode)")

    def encode(self, *args, **kwargs):
        if self._model is None:
            print("Loading embedding model (lazy)...")
            model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
            self._model = SentenceTransformer(model_name, device=self.device)
        return self._model.encode(*args, **kwargs)

model = LazyModel()
print("Loading vector index...")
vector_index = VectorIndex(dim=int(os.getenv("VECTOR_DIM", "384")))
print("Loading metadata DB...")
meta_db = MetadataDB()
print("Loading graph extractor...")
extractor = GraphExtractor()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "KSdb Vector Database is running"}

# --- Pydantic Models ---

class CreateCollectionRequest(BaseModel):
    name: str
    metadata: Dict[str, Any] = {}

class CollectionResponse(BaseModel):
    id: str
    name: str
    metadata: Dict[str, Any]

class Document(BaseModel):
    id: str # Changed to string to support UUIDs
    text: str
    metadata: Dict[str, Any] = {}

class SearchQuery(BaseModel):
    query: str
    k: int = 5
    where: Optional[Dict[str, Any]] = None # Metadata filter

class SearchResult(BaseModel):
    id: str
    score: float
    text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

# --- Helpers ---

def get_collection_or_404(name: str):
    collection = meta_db.get_collection(name)
    if not collection:
        raise HTTPException(status_code=404, detail=f"Collection '{name}' not found")
    return collection

def _matches_filter(metadata: Dict[str, Any], filter_dict: Dict[str, Any]) -> bool:
    """
    Check if metadata matches the filter dictionary.
    Supports ChromaDB-style operators: $eq, $ne, $gt, $gte, $lt, $lte, $in, $nin
    And logical operators: $and, $or
    """
    for key, value in filter_dict.items():
        # Handle logical operators
        if key == "$and":
            if not isinstance(value, list):
                return False
            if not all(_matches_filter(metadata, sub_filter) for sub_filter in value):
                return False
            continue
        if key == "$or":
            if not isinstance(value, list):
                return False
            if not any(_matches_filter(metadata, sub_filter) for sub_filter in value):
                return False
            continue
            
        # Handle field filters
        doc_val = metadata.get(key)
        
        # Direct equality check (e.g. {"category": "tech"})
        if not isinstance(value, dict):
            if doc_val != value:
                return False
            continue
            
        # Operator checks (e.g. {"price": {"$gt": 10}})
        for op, op_val in value.items():
            if op == "$eq":
                if doc_val != op_val: return False
            elif op == "$ne":
                if doc_val == op_val: return False
            elif op == "$gt":
                if not (isinstance(doc_val, (int, float)) and isinstance(op_val, (int, float))): return False
                if not doc_val > op_val: return False
            elif op == "$gte":
                if not (isinstance(doc_val, (int, float)) and isinstance(op_val, (int, float))): return False
                if not doc_val >= op_val: return False
            elif op == "$lt":
                if not (isinstance(doc_val, (int, float)) and isinstance(op_val, (int, float))): return False
                if not doc_val < op_val: return False
            elif op == "$lte":
                if not (isinstance(doc_val, (int, float)) and isinstance(op_val, (int, float))): return False
                if not doc_val <= op_val: return False
            elif op == "$in":
                if not isinstance(op_val, list): return False
                if doc_val not in op_val: return False
            elif op == "$nin":
                if not isinstance(op_val, list): return False
                if doc_val in op_val: return False
            else:
                # Unknown operator or nested dict, treat as inequality if not dict
                return False
                
    return True

# --- Collection Endpoints ---

@app.post("/collections", response_model=CollectionResponse)
async def create_collection(req: CreateCollectionRequest):
    try:
        return meta_db.create_collection(req.name, req.metadata)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/collections", response_model=List[CollectionResponse])
async def list_collections():
    return meta_db.list_collections()

@app.get("/collections/{name}", response_model=CollectionResponse)
async def get_collection(name: str):
    return get_collection_or_404(name)

@app.delete("/collections/{name}")
async def delete_collection(name: str):
    collection = get_collection_or_404(name)
    try:
        # 1. Delete from Metadata DB
        meta_db.delete_collection(name)
        # 2. Delete Index
        vector_index.delete_collection(collection["id"])
        return {"status": "deleted", "name": name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Document Endpoints ---

@app.post("/collections/{name}/add")
async def upsert(name: str, doc: Document):
    collection = get_collection_or_404(name)
    try:
        # 1. Generate embedding
        embedding = model.encode(doc.text)
        
        # 2. Generate HNSW ID (int) from UUID (str)
        hnsw_id = int(uuid.uuid5(uuid.NAMESPACE_DNS, doc.id).int >> 64)
        hnsw_id = hnsw_id & ((1 << 63) - 1)

        # 3. Store in Vector Index
        vector_index.add_items(collection["id"], np.array([embedding]), np.array([hnsw_id]))
        
        # 4. Store in Metadata DB
        meta_db.insert(collection["id"], doc.id, hnsw_id, doc.text, doc.metadata)
        
        return {"status": "success", "id": doc.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class BatchDocument(BaseModel):
    ids: List[str]
    documents: List[str]
    metadatas: Optional[List[Dict[str, Any]]] = None


@app.post("/collections/{name}/add_batch")
async def upsert_batch(
    name: str, 
    batch: BatchDocument, 
    deduplicate: bool = False, 
    similarity_threshold: float = 0.1,
    extract_graph: bool = False
):
    """
    Batch insert with optional smart deduplication and auto-graph extraction.
    """
    collection = get_collection_or_404(name)
    try:
        # Default metadatas if not provided
        if batch.metadatas is None:
            batch.metadatas = [{} for _ in batch.ids]
        
        # 1. Generate all embeddings at once
        embeddings = model.encode(batch.documents)
        
        # 2. Deduplication Logic
        to_add_indices = []
        skipped_count = 0
        
        if deduplicate:
            # Search for nearest neighbor for each new vector
            # k=1 is enough to find the closest match
            # We need to handle the case where index is empty
            if vector_index.indices.get(collection["id"]) and vector_index.indices[collection["id"]].element_count > 0:
                ids, distances = vector_index.search(collection["id"], embeddings, k=1)
                
                for i, dist in enumerate(distances):
                    # HNSWlib returns L2 squared distance. 
                    # Handle both array and scalar returns
                    d_val = dist[0] if isinstance(dist, (list, np.ndarray)) else dist
                    
                    if d_val > similarity_threshold:
                        to_add_indices.append(i)
                    else:
                        skipped_count += 1
            else:
                # Index empty, add all
                to_add_indices = list(range(len(batch.ids)))
        else:
            to_add_indices = list(range(len(batch.ids)))
            
        if not to_add_indices:
            return {"status": "success", "count": 0, "skipped": len(batch.ids), "message": "All documents were duplicates"}

        # Filter data to add
        final_ids = [batch.ids[i] for i in to_add_indices]
        final_docs = [batch.documents[i] for i in to_add_indices]
        final_metas = [batch.metadatas[i] for i in to_add_indices]
        final_embeddings = embeddings[to_add_indices]
        
        # 3. Auto-Graph Extraction
        extracted_triples_count = 0
        if extract_graph:
            try:
                all_triples = []
                for doc_id, text in zip(final_ids, final_docs):
                    # Skip extraction for very long texts to avoid OOM/Timeout
                    if len(text) > 50000: 
                        print(f"⚠️ Skipping graph extraction for doc {doc_id} (length {len(text)})")
                        continue
                        
                    triples = extractor.extract(text)
                    for t in triples:
                        t["doc_id"] = doc_id # Link triple to document
                    all_triples.extend(triples)
                
                if all_triples:
                    meta_db.insert_triples(collection["id"], all_triples)
                    extracted_triples_count = len(all_triples)
            except Exception as e:
                print(f"❌ Graph Extraction Failed: {e}")
                import traceback
                traceback.print_exc()
                # Continue without graph extraction
        
        # 4. Generate HNSW IDs
        hnsw_ids = []
        for doc_id in final_ids:
            hnsw_id = int(uuid.uuid5(uuid.NAMESPACE_DNS, doc_id).int >> 64)
            hnsw_id = hnsw_id & ((1 << 63) - 1)
            hnsw_ids.append(hnsw_id)
        
        hnsw_ids_array = np.array(hnsw_ids)
        
        # 5. Batch insert into vector index
        vector_index.add_items(collection["id"], final_embeddings, hnsw_ids_array)
        
        # 6. Batch insert into metadata DB
        meta_db.insert_batch(
            collection["id"],
            final_ids,
            hnsw_ids,
            final_docs,
            final_metas
        )
        
        # 7. Index in FTS
        meta_db.insert_fts_batch(collection["id"], final_ids, final_docs)
        
        return {
            "status": "success", 
            "count": len(final_ids), 
            "skipped": skipped_count,
            "triples_extracted": extracted_triples_count
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/collections/{name}/query", response_model=List[SearchResult])
async def search(name: str, q: SearchQuery):
    collection = get_collection_or_404(name)
    try:
        # 1. Generate query embedding
        query_emb = model.encode(q.query)
        
        # 2. Hybrid Search Logic
        # A. Vector Search
        search_k = q.k * 2 if q.where else q.k
        hnsw_ids, distances = vector_index.search(collection["id"], np.array([query_emb]), k=search_k)
        
        vector_results = []
        hnsw_ids_list = [int(id) for id in hnsw_ids]
        
        # Map HNSW IDs back to String IDs
        # We need a way to get String IDs from HNSW IDs efficiently. 
        # For now, we fetch the docs and get IDs.
        docs_map = meta_db.get_by_int_ids(collection["id"], hnsw_ids_list)
        
        for i, hnsw_id in enumerate(hnsw_ids_list):
            doc = docs_map.get(hnsw_id)
            if doc:
                vector_results.append({"id": doc["id"], "score": float(distances[i]), "doc": doc})

        # B. Keyword Search (FTS)
        keyword_results = []
        fts_ids = meta_db.search_fts(collection["id"], q.query, limit=q.k * 2)
        
        # We need to fetch docs for FTS results too if they aren't in vector results
        missing_fts_ids = [fid for fid in fts_ids if fid not in [r["id"] for r in vector_results]]
        # This part is tricky without a "get_by_ids" method in db.py that takes string IDs.
        # For MVP, we might skip fetching full docs for FTS-only results or add a method.
        # Let's add a simple fetch for now.
        
        # C. Reciprocal Rank Fusion (RRF)
        # RRF Score = 1 / (k + rank)
        rrf_k = 60
        scores = {}
        
        # Score Vector Results
        for rank, res in enumerate(vector_results):
            if res["id"] not in scores: scores[res["id"]] = 0
            scores[res["id"]] += 1 / (rrf_k + rank + 1)
            
        # Score Keyword Results
        for rank, doc_id in enumerate(fts_ids):
            if doc_id not in scores: scores[doc_id] = 0
            scores[doc_id] += 1 / (rrf_k + rank + 1)
            
        # Sort by RRF Score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:q.k]
        
        # Fetch final documents
        # We need to fetch any docs we don't have yet.
        # Re-using docs_map from vector search is good, but we might need more.
        # Let's just fetch the final set to be safe and clean.
        # We need a get_by_ids method in MetadataDB. Let's assume we add it or use get() in loop.
        
        results = []
        for doc_id in sorted_ids:
            # Check if we already have it
            found_doc = None
            for res in vector_results:
                if res["id"] == doc_id:
                    found_doc = res["doc"]
                    break
            
            if not found_doc:
                # Fetch from DB
                found_doc = meta_db.get(collection["id"], doc_id)
                
            if found_doc:
                # Apply Filter
                if q.where:
                    if not _matches_filter(found_doc["metadata"], q.where):
                        continue
                        
                results.append(SearchResult(
                    id=found_doc["id"],
                    score=scores[doc_id], # RRF Score
                    text=found_doc["text"],
                    metadata=found_doc["metadata"]
                ))
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Knowledge Graph Endpoints ---

class Triple(BaseModel):
    subject: str
    predicate: str
    object: str
    doc_id: Optional[str] = None
    weight: Optional[float] = 1.0

class TripleBatch(BaseModel):
    triples: List[Triple]

@app.post("/collections/{name}/triples/add")
async def add_triples(name: str, batch: TripleBatch):
    collection = get_collection_or_404(name)
    try:
        triples_data = [t.dict() for t in batch.triples]
        meta_db.insert_triples(collection["id"], triples_data)
        return {"status": "success", "count": len(triples_data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class GraphQuery(BaseModel):
    entities: List[str]

@app.post("/collections/{name}/triples/query")
async def query_graph(name: str, q: GraphQuery):
    collection = get_collection_or_404(name)
    try:
        results = meta_db.get_triples(collection["id"], q.entities)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
