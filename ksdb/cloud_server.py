"""
KSdb Cloud Server - Production version with authentication
"""
import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import uvicorn

# Import existing components
from ksdb.auth import get_current_tenant, auth_manager
from ksdb.server import (
    app as base_app,
    model,
    vector_index,
    meta_db,
    extractor,
    BatchDocument,
    SearchQuery,
    SearchResult,
    CollectionCreate
)

# Create FastAPI app
app = FastAPI(
    title="KSdb Cloud API",
    description="High-performance vector database as a service",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check (no auth required)
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ksdb-cloud"}

# Authentication endpoints
class CreateKeyRequest(BaseModel):
    name: Optional[str] = None

@app.post("/auth/keys")
async def create_api_key(request: CreateKeyRequest, tenant_id: str = Depends(get_current_tenant)):
    """Create a new API key (requires existing API key)"""
    new_key = auth_manager.generate_api_key(tenant_id, request.name)
    return {"api_key": new_key, "tenant_id": tenant_id}

@app.get("/auth/keys")
async def list_api_keys(tenant_id: str = Depends(get_current_tenant)):
    """List all API keys for current tenant"""
    keys = auth_manager.list_keys(tenant_id)
    return {"keys": keys}

@app.delete("/auth/keys/{key}")
async def revoke_api_key(key: str, tenant_id: str = Depends(get_current_tenant)):
    """Revoke an API key"""
    auth_manager.revoke_api_key(key)
    return {"status": "revoked"}

# Protected Collection Endpoints
@app.post("/collections")
async def create_collection(
    request: CollectionCreate,
    tenant_id: str = Depends(get_current_tenant)
):
    """Create a collection (tenant-isolated)"""
    # Prefix collection name with tenant_id for isolation
    collection_name = f"{tenant_id}_{request.name}"
    
    existing = meta_db.get_collection(collection_name)
    if existing:
        raise HTTPException(status_code=400, detail="Collection already exists")
    
    collection = meta_db.create_collection(collection_name, request.metadata or {})
    vector_index.create_collection(collection["id"])
    
    return {
        "name": request.name,  # Return original name
        "id": collection["id"],
        "metadata": collection["metadata"]
    }

@app.get("/collections")
async def list_collections(tenant_id: str = Depends(get_current_tenant)):
    """List all collections for current tenant"""
    all_collections = meta_db.list_collections()
    # Filter by tenant prefix
    tenant_collections = [
        {
            "name": c["name"].replace(f"{tenant_id}_", ""),  # Remove tenant prefix
            "id": c["id"],
            "metadata": c["metadata"]
        }
        for c in all_collections
        if c["name"].startswith(f"{tenant_id}_")
    ]
    return {"collections": tenant_collections}

@app.get("/collections/{name}")
async def get_collection(name: str, tenant_id: str = Depends(get_current_tenant)):
    """Get collection info"""
    collection_name = f"{tenant_id}_{name}"
    collection = meta_db.get_collection(collection_name)
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    return {
        "name": name,
        "id": collection["id"],
        "metadata": collection["metadata"]
    }

@app.delete("/collections/{name}")
async def delete_collection(name: str, tenant_id: str = Depends(get_current_tenant)):
    """Delete a collection"""
    collection_name = f"{tenant_id}_{name}"
    collection = meta_db.get_collection(collection_name)
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    vector_index.delete_collection(collection["id"])
    meta_db.delete_collection(collection_name)
    
    return {"status": "deleted"}

@app.post("/collections/{name}/add")
async def add_documents(
    name: str,
    batch: BatchDocument,
    deduplicate: bool = False,
    similarity_threshold: float = 0.1,
    extract_graph: bool = False,
    tenant_id: str = Depends(get_current_tenant)
):
    """Add documents to collection (tenant-isolated)"""
    collection_name = f"{tenant_id}_{name}"
    collection = meta_db.get_collection(collection_name)
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    # Use existing upsert_batch logic
    # Import the function from server.py
    from ksdb.server import upsert_batch
    
    # Create a mock request with tenant-prefixed name
    class MockRequest:
        def __init__(self):
            self.path_params = {"name": collection_name}
    
    # Call existing logic (this reuses all the dedup, graph extraction, etc.)
    result = await upsert_batch(
        name=collection_name,
        batch=batch,
        deduplicate=deduplicate,
        similarity_threshold=similarity_threshold,
        extract_graph=extract_graph
    )
    
    return result

@app.post("/collections/{name}/query")
async def query_collection(
    name: str,
    query: SearchQuery,
    tenant_id: str = Depends(get_current_tenant)
):
    """Query collection (tenant-isolated)"""
    collection_name = f"{tenant_id}_{name}"
    collection = meta_db.get_collection(collection_name)
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    # Use existing search logic
    from ksdb.server import search
    
    results = await search(name=collection_name, q=query)
    return results

@app.get("/collections/{name}/graph")
async def get_graph(
    name: str,
    subjects: List[str],
    tenant_id: str = Depends(get_current_tenant)
):
    """Get knowledge graph (tenant-isolated)"""
    collection_name = f"{tenant_id}_{name}"
    collection = meta_db.get_collection(collection_name)
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    triples = meta_db.get_triples(collection["id"], subjects)
    return {"triples": triples}

# Admin endpoint (for initial setup)
@app.post("/admin/create-tenant")
async def create_tenant(tenant_name: str, admin_key: str):
    """Create initial tenant and API key (admin only)"""
    # Verify admin key
    if admin_key != os.getenv("ADMIN_KEY", "change_me_in_production"):
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    # Generate tenant ID
    import uuid
    tenant_id = str(uuid.uuid4())
    
    # Create first API key
    api_key = auth_manager.generate_api_key(tenant_id, f"{tenant_name}_master")
    
    return {
        "tenant_id": tenant_id,
        "api_key": api_key,
        "message": "Save this API key securely. It cannot be retrieved later."
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
