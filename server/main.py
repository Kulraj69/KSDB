from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
import uvicorn

from vector_index import VectorIndex
from db import MetadataDB

app = FastAPI(title="KSdb", description="Custom Vector Database")

# Configuration
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
VECTOR_DIM = 384
MAX_ELEMENTS = 10000

# Initialize components
print("Loading embedding model...")
model = SentenceTransformer(EMBEDDING_MODEL)
print("Loading vector index...")
vector_index = VectorIndex(dim=VECTOR_DIM, max_elements=MAX_ELEMENTS)
print("Loading metadata DB...")
meta_db = MetadataDB()

class Document(BaseModel):
    id: int
    text: str
    metadata: Dict[str, Any] = {}

class SearchQuery(BaseModel):
    query: str
    k: int = 5

class SearchResult(BaseModel):
    id: int
    score: float
    text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@app.post("/upsert")
async def upsert(doc: Document):
    try:
        # 1. Generate embedding
        embedding = model.encode(doc.text)
        
        # 2. Store in Vector Index
        vector_index.add_items(np.array([embedding]), np.array([doc.id]))
        
        # 3. Store in Metadata DB
        meta_db.insert(doc.id, doc.text, doc.metadata)
        
        return {"status": "success", "id": doc.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search", response_model=List[SearchResult])
async def search(q: SearchQuery):
    try:
        # 1. Generate query embedding
        query_emb = model.encode(q.query)
        
        # 2. Search vector index
        ids, distances = vector_index.search(np.array([query_emb]), k=q.k)
        
        results = []
        for doc_id, dist in zip(ids, distances):
            # 3. Fetch metadata
            meta = meta_db.get(int(doc_id))
            if meta:
                results.append(SearchResult(
                    id=doc_id,
                    score=float(dist), # L2 distance (lower is better)
                    text=meta["text"],
                    metadata=meta["metadata"]
                ))
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/delete/{doc_id}")
async def delete(doc_id: int):
    # Note: HNSWlib delete is limited, we only remove metadata for now
    meta_db.delete(doc_id)
    vector_index.delete_item(doc_id)
    return {"status": "deleted", "id": doc_id, "note": "Vector remains in index but metadata removed"}

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
