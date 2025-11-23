"""
KSdb Cloud Client - For connecting to KSdb Cloud API
"""
import requests
from typing import List, Dict, Any, Optional

class CloudClient:
    """
    Client for KSdb Cloud API with authentication
    
    Usage:
        client = CloudClient(
            api_key="ks_live_abc123...",
            url="https://api.ksdb.dev"
        )
        
        collection = client.get_or_create_collection("my_docs")
        collection.add(ids=[...], documents=[...])
    """
    
    def __init__(self, api_key: str, url: str = "https://api.ksdb.dev"):
        self.api_key = api_key
        self.url = url.rstrip("/")
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
    
    def create_collection(self, name: str, metadata: Dict[str, Any] = None):
        """Create a new collection"""
        response = requests.post(
            f"{self.url}/collections",
            headers=self.headers,
            json={"name": name, "metadata": metadata or {}}
        )
        response.raise_for_status()
        return CloudCollection(self, name, response.json())
    
    def get_collection(self, name: str):
        """Get existing collection"""
        response = requests.get(
            f"{self.url}/collections/{name}",
            headers=self.headers
        )
        response.raise_for_status()
        return CloudCollection(self, name, response.json())
    
    def get_or_create_collection(self, name: str, metadata: Dict[str, Any] = None):
        """Get collection or create if it doesn't exist"""
        try:
            return self.get_collection(name)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return self.create_collection(name, metadata)
            raise
    
    def list_collections(self):
        """List all collections"""
        response = requests.get(
            f"{self.url}/collections",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()["collections"]
    
    def delete_collection(self, name: str):
        """Delete a collection"""
        response = requests.delete(
            f"{self.url}/collections/{name}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

class CloudCollection:
    """Collection in KSdb Cloud"""
    
    def __init__(self, client: CloudClient, name: str, info: Dict[str, Any]):
        self.client = client
        self.name = name
        self.id = info["id"]
        self.metadata = info.get("metadata", {})
    
    def add(
        self,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        deduplicate: bool = False,
        extract_graph: bool = False
    ):
        """Add documents to collection"""
        response = requests.post(
            f"{self.client.url}/collections/{self.name}/add",
            headers=self.client.headers,
            params={
                "deduplicate": deduplicate,
                "extract_graph": extract_graph
            },
            json={
                "ids": ids,
                "documents": documents,
                "metadatas": metadatas
            }
        )
        response.raise_for_status()
        return response.json()
    
    def query(
        self,
        query_texts: List[str],
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ):
        """Query collection"""
        response = requests.post(
            f"{self.client.url}/collections/{self.name}/query",
            headers=self.client.headers,
            json={
                "query_texts": query_texts,
                "k": n_results,
                "filter": where,
                "where_document": where_document
            }
        )
        response.raise_for_status()
        
        results = response.json()
        
        # Transform to ChromaDB-compatible format
        return {
            "ids": [[r["id"] for r in results]],
            "documents": [[r["text"] for r in results]],
            "metadatas": [[r["metadata"] for r in results]],
            "distances": [[r["distance"] for r in results]]
        }
    
    def get_graph(self, subjects: List[str]):
        """Get knowledge graph"""
        response = requests.get(
            f"{self.client.url}/collections/{self.name}/graph",
            headers=self.client.headers,
            params={"subjects": subjects}
        )
        response.raise_for_status()
        return response.json()["triples"]
