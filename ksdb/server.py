from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import numpy as np
import os
import uvicorn
import uuid

from vector_index import VectorIndex
from db import MetadataDB

app = FastAPI(title="KSdb", description="Custom Vector Database with Collections")

# Initialize components
print("Loading embedding model...")
model = SentenceTransformer(os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"))
print("Loading vector index...")
vector_index = VectorIndex(dim=int(os.getenv("VECTOR_DIM", "384")))
print("Loading metadata DB...")
meta_db = MetadataDB()

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
async def upsert_batch(name: str, batch: BatchDocument):
    """Batch insert - 10-20x faster than individual inserts"""
    collection = get_collection_or_404(name)
    try:
        # Default metadatas if not provided
        if batch.metadatas is None:
            batch.metadatas = [{} for _ in batch.ids]
        
        # 1. Generate all embeddings at once (vectorized operation)
        embeddings = model.encode(batch.documents)
        
        # 2. Generate all HNSW IDs
        hnsw_ids = []
        for doc_id in batch.ids:
            hnsw_id = int(uuid.uuid5(uuid.NAMESPACE_DNS, doc_id).int >> 64)
            hnsw_id = hnsw_id & ((1 << 63) - 1)
            hnsw_ids.append(hnsw_id)
        
        hnsw_ids_array = np.array(hnsw_ids)
        
        # 3. Batch insert into vector index
        vector_index.add_items(collection["id"], embeddings, hnsw_ids_array)
        
        # 4. Batch insert into metadata DB
        meta_db.insert_batch(
            collection["id"],
            batch.ids,
            hnsw_ids,
            batch.documents,
            batch.metadatas
        )
        
        return {"status": "success", "count": len(batch.ids)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/collections/{name}/query", response_model=List[SearchResult])
async def search(name: str, q: SearchQuery):
    collection = get_collection_or_404(name)
    try:
        # 1. Generate query embedding
        query_emb = model.encode(q.query)
        
        # 2. Search vector index
        # We ask for more candidates (k*2) to allow for filtering
        search_k = q.k * 2 if q.where else q.k
        hnsw_ids, distances = vector_index.search(collection["id"], np.array([query_emb]), k=search_k)
        
        if len(hnsw_ids) == 0:
            return []

        # 3. Fetch metadata for all candidates
        # Convert numpy ints to python ints
        hnsw_ids_list = [int(id) for id in hnsw_ids]
        docs_map = meta_db.get_by_int_ids(collection["id"], hnsw_ids_list)
        
        results = []
        count = 0
        
        for hnsw_id, dist in zip(hnsw_ids_list, distances):
            if count >= q.k:
                break
            
            doc = docs_map.get(hnsw_id)
            if not doc:
                continue # Should not happen unless DB and Index are out of sync
            
            # 4. Apply Metadata Filter (Python-side)
            if q.where:
                match = True
                for k, v in q.where.items():
                    if doc["metadata"].get(k) != v:
                        match = False
                        break
                if not match:
                    continue
            
            results.append(SearchResult(
                id=doc["id"],
                score=float(dist),
                text=doc["text"],
                metadata=doc["metadata"]
            ))
            count += 1
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
