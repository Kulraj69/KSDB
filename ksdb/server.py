from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import numpy as np
import os
import uvicorn
import uuid
import time

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
    metadata: Dict[str, Any] = Field(default_factory=dict)

class CollectionResponse(BaseModel):
    id: str
    name: str
    metadata: Dict[str, Any]

class Document(BaseModel):
    id: str # Changed to string to support UUIDs
    text: str = Field(min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SearchQuery(BaseModel):
    query: str = Field(min_length=1)
    k: int = Field(default=5, gt=0, le=1000)
    where: Optional[Dict[str, Any]] = None # Metadata filter

class SearchResult(BaseModel):
    id: str
    score: float
    text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class SearchExplainResult(SearchResult):
    rrf_score: float
    vector_rank: Optional[int] = None
    vector_distance: Optional[float] = None
    keyword_rank: Optional[int] = None
    matched_by: List[str] = Field(default_factory=list)

class SearchProfile(BaseModel):
    collection_id: str
    requested_k: int
    total_indexed_vectors: int
    metadata_filter_applied: bool
    metadata_filter_matches: Optional[int] = None
    vector_candidates: int
    keyword_candidates: int
    fused_candidates: int
    timings_ms: Dict[str, float]

class SearchExplainResponse(BaseModel):
    results: List[SearchExplainResult]
    profile: SearchProfile

# --- Helpers ---

def get_collection_or_404(name: str):
    collection = meta_db.get_collection(name)
    if not collection:
        raise HTTPException(status_code=404, detail=f"Collection '{name}' not found")
    return collection

def _hnsw_id_for_document(doc_id: str) -> int:
    hnsw_id = int(uuid.uuid5(uuid.NAMESPACE_DNS, doc_id).int >> 64)
    return hnsw_id & ((1 << 63) - 1)

def _elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 3)

def _ranked_lookup(ids: List[str]) -> Dict[str, int]:
    return {doc_id: rank + 1 for rank, doc_id in enumerate(ids)}

def _run_hybrid_search(name: str, q: SearchQuery, include_profile: bool = False):
    collection = get_collection_or_404(name)
    timings = {}

    start = time.perf_counter()
    query_emb = model.encode(q.query)
    timings["embedding"] = _elapsed_ms(start)

    start = time.perf_counter()
    total_indexed_vectors = vector_index.count(collection["id"])
    allowed_ids = None
    if q.where:
        allowed_ids = set(meta_db.query(collection["id"], q.where) or [])
        if not allowed_ids:
            profile = SearchProfile(
                collection_id=collection["id"],
                requested_k=q.k,
                total_indexed_vectors=total_indexed_vectors,
                metadata_filter_applied=True,
                metadata_filter_matches=0,
                vector_candidates=0,
                keyword_candidates=0,
                fused_candidates=0,
                timings_ms={**timings, "metadata_filter": _elapsed_ms(start)},
            )
            return [], profile
    timings["metadata_filter"] = _elapsed_ms(start)

    start = time.perf_counter()
    search_k = total_indexed_vectors if q.where else q.k
    hnsw_ids, distances = vector_index.search(collection["id"], np.array([query_emb]), k=search_k)
    hnsw_ids_list = [int(id) for id in hnsw_ids]
    docs_map = meta_db.get_by_int_ids(collection["id"], hnsw_ids_list)

    vector_results = []
    for i, hnsw_id in enumerate(hnsw_ids_list):
        doc = docs_map.get(hnsw_id)
        if not doc:
            continue
        if allowed_ids is not None and doc["id"] not in allowed_ids:
            continue
        vector_results.append({"id": doc["id"], "distance": float(distances[i]), "doc": doc})
    timings["vector_search"] = _elapsed_ms(start)

    start = time.perf_counter()
    fts_limit = max(q.k * 4, len(allowed_ids) if allowed_ids is not None else q.k * 2)
    fts_ids = meta_db.search_fts(collection["id"], q.query, limit=fts_limit)
    if allowed_ids is not None:
        fts_ids = [doc_id for doc_id in fts_ids if doc_id in allowed_ids]
    timings["keyword_search"] = _elapsed_ms(start)

    start = time.perf_counter()
    rrf_k = 60
    scores = {}
    vector_ids = [res["id"] for res in vector_results]
    vector_ranks = _ranked_lookup(vector_ids)
    keyword_ranks = _ranked_lookup(fts_ids)
    vector_distances = {res["id"]: res["distance"] for res in vector_results}

    for rank, doc_id in enumerate(vector_ids):
        scores.setdefault(doc_id, 0)
        scores[doc_id] += 1 / (rrf_k + rank + 1)

    for rank, doc_id in enumerate(fts_ids):
        scores.setdefault(doc_id, 0)
        scores[doc_id] += 1 / (rrf_k + rank + 1)

    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:q.k]
    docs_by_id = meta_db.get_by_ids(collection["id"], sorted_ids)
    vector_docs_by_id = {res["id"]: res["doc"] for res in vector_results}

    results = []
    for doc_id in sorted_ids:
        found_doc = vector_docs_by_id.get(doc_id) or docs_by_id.get(doc_id)
        if not found_doc:
            continue

        matched_by = []
        if doc_id in vector_ranks:
            matched_by.append("vector")
        if doc_id in keyword_ranks:
            matched_by.append("keyword")

        if include_profile:
            results.append(SearchExplainResult(
                id=found_doc["id"],
                score=scores[doc_id],
                rrf_score=scores[doc_id],
                vector_rank=vector_ranks.get(doc_id),
                vector_distance=vector_distances.get(doc_id),
                keyword_rank=keyword_ranks.get(doc_id),
                matched_by=matched_by,
                text=found_doc["text"],
                metadata=found_doc["metadata"],
            ))
        else:
            results.append(SearchResult(
                id=found_doc["id"],
                score=scores[doc_id],
                text=found_doc["text"],
                metadata=found_doc["metadata"],
            ))

    timings["fusion"] = _elapsed_ms(start)
    profile = SearchProfile(
        collection_id=collection["id"],
        requested_k=q.k,
        total_indexed_vectors=total_indexed_vectors,
        metadata_filter_applied=q.where is not None,
        metadata_filter_matches=len(allowed_ids) if allowed_ids is not None else None,
        vector_candidates=len(vector_results),
        keyword_candidates=len(fts_ids),
        fused_candidates=len(scores),
        timings_ms=timings,
    )
    return results, profile

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
        hnsw_id = _hnsw_id_for_document(doc.id)

        # 3. Store in Vector Index
        vector_index.add_items(collection["id"], np.array([embedding]), np.array([hnsw_id]))
        
        # 4. Store in Metadata DB
        meta_db.insert(collection["id"], doc.id, hnsw_id, doc.text, doc.metadata)

        # 5. Store in keyword index for hybrid search
        meta_db.insert_fts_batch(collection["id"], [doc.id], [doc.text])
        
        return {"status": "success", "id": doc.id}
    except HTTPException:
        raise
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

    if not batch.ids:
        raise HTTPException(status_code=400, detail="ids must contain at least one document")
    if len(batch.ids) != len(batch.documents):
        raise HTTPException(status_code=400, detail="ids and documents must have the same length")
    if any(not document for document in batch.documents):
        raise HTTPException(status_code=400, detail="documents must not contain empty strings")
    if batch.metadatas is not None and len(batch.metadatas) != len(batch.ids):
        raise HTTPException(status_code=400, detail="metadatas must have the same length as ids")

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
            if vector_index.count(collection["id"]) > 0:
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
            hnsw_ids.append(_hnsw_id_for_document(doc_id))
        
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
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/collections/{name}/delete/{doc_id}")
async def delete_document(name: str, doc_id: str):
    collection = get_collection_or_404(name)
    try:
        hnsw_id = _hnsw_id_for_document(doc_id)
        vector_index.delete_item(collection["id"], hnsw_id)
        deleted = meta_db.delete(collection["id"], doc_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")
        return {"status": "deleted", "id": doc_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/collections/{name}/query", response_model=List[SearchResult])
async def search(name: str, q: SearchQuery):
    try:
        results, _ = _run_hybrid_search(name, q)
        return results
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/collections/{name}/query/explain", response_model=SearchExplainResponse)
async def explain_search(name: str, q: SearchQuery):
    try:
        results, profile = _run_hybrid_search(name, q, include_profile=True)
        return SearchExplainResponse(results=results, profile=profile)
    except HTTPException:
        raise
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

@app.get("/collections/{name}/graph")
async def get_graph(name: str, subjects: List[str]):
    collection = get_collection_or_404(name)
    try:
        return meta_db.get_triples(collection["id"], subjects)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
