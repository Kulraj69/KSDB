"""
KSdb Client - ChromaDB-compatible API

Usage (exactly like ChromaDB):
    import ksdb
    
    client = ksdb.Client()
    collection = client.get_or_create_collection("my_docs")
    
    collection.add(
        ids=["id1", "id2"],
        documents=["doc1", "doc2"],
        metadatas=[{"key": "value"}, {"key": "value"}]
    )
    
    results = collection.query(
        query_texts=["search query"],
        n_results=5
    )
"""
import requests
from typing import List, Dict, Any, Optional


class Collection:
    """Collection object - matches ChromaDB API"""
    
    def __init__(self, name: str, client_url: str):
        self.name = name
        self.client_url = client_url
    
    def add(
        self,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ):
        """Add documents to collection - automatically uses batch API for speed"""
        if metadatas is None:
            metadatas = [{} for _ in ids]
        
        # Use batch endpoint for better performance
        response = requests.post(
            f"{self.client_url}/collections/{self.name}/add_batch",
            json={
                "ids": ids,
                "documents": documents,
                "metadatas": metadatas
            }
        )
        response.raise_for_status()
    
    def query(
        self,
        query_texts: List[str],
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Query the collection"""
        response = requests.post(
            f"{self.client_url}/collections/{self.name}/query",
            json={
                "query": query_texts[0],
                "k": n_results,
                "where": where
            }
        )
        response.raise_for_status()
        data = response.json()
        
        # Format response to match ChromaDB
        return {
            "ids": [[r["id"] for r in data]],
            "documents": [[r["text"] for r in data]],
            "metadatas": [[r["metadata"] for r in data]],
            "distances": [[r["score"] for r in data]]
        }
    
    def delete(self, ids: Optional[List[str]] = None):
        """Delete documents from collection"""
        if ids:
            for doc_id in ids:
                requests.delete(f"{self.client_url}/collections/{self.name}/delete/{doc_id}")


class Client:
    """
    KSdb Client - Drop-in replacement for ChromaDB
    
    Your data is automatically stored in the cloud - no configuration needed!
    """
    
    def __init__(self, url: str = "http://localhost:8000"):
        """
        Initialize KSdb client
        
        Args:
            url: Server URL (default: http://localhost:8000)
        """
        self.url = url.rstrip("/")
    
    def create_collection(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> Collection:
        """Create a new collection"""
        response = requests.post(
            f"{self.url}/collections",
            json={"name": name, "metadata": metadata or {}}
        )
        response.raise_for_status()
        return Collection(name, self.url)
    
    def get_collection(self, name: str) -> Collection:
        """Get an existing collection"""
        response = requests.get(f"{self.url}/collections/{name}")
        if response.status_code == 404:
            raise ValueError(f"Collection '{name}' does not exist")
        response.raise_for_status()
        return Collection(name, self.url)
    
    def get_or_create_collection(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> Collection:
        """Get or create a collection"""
        try:
            return self.get_collection(name)
        except ValueError:
            return self.create_collection(name, metadata)
    
    def delete_collection(self, name: str):
        """Delete a collection"""
        response = requests.delete(f"{self.url}/collections/{name}")
        response.raise_for_status()
    
    def list_collections(self) -> List[Dict[str, Any]]:
        """List all collections"""
        response = requests.get(f"{self.url}/collections")
        response.raise_for_status()
        return response.json()


# Backwards compatibility
KSdbClient = Client

class Collection:
    def __init__(self, client, name: str):
        self.client = client
        self.name = name

    def add(self, ids: List[str], documents: List[str], metadatas: Optional[List[Dict[str, Any]]] = None):
        if metadatas is None:
            metadatas = [{} for _ in documents]
            
        if len(ids) != len(documents) or len(ids) != len(metadatas):
            raise ValueError("ids, documents, and metadatas must have the same length")

        url = f"{self.client.base_url}/collections/{self.name}/add"
        results = []
        for id, doc, meta in zip(ids, documents, metadatas):
            payload = {
                "id": id,
                "text": doc,
                "metadata": meta
            }
            response = requests.post(url, json=payload)
            response.raise_for_status()
            results.append(response.json())
        return results

    def query(self, query_texts: List[str], n_results: int = 5, where: Optional[Dict[str, Any]] = None):
        # Currently API only supports single query string, so we loop
        url = f"{self.client.base_url}/collections/{self.name}/query"
        all_results = []
        
        for q in query_texts:
            payload = {
                "query": q,
                "k": n_results,
                "where": where
            }
            response = requests.post(url, json=payload)
            response.raise_for_status()
            all_results.append(response.json())
            
        return all_results

    def delete(self):
        url = f"{self.client.base_url}/collections/{self.name}"
        response = requests.delete(url)
        response.raise_for_status()
        return response.json()

class KSdbClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    def heartbeat(self):
        return requests.get(f"{self.base_url}/health").json()

    def create_collection(self, name: str, metadata: Dict[str, Any] = None) -> Collection:
        url = f"{self.base_url}/collections"
        payload = {"name": name, "metadata": metadata or {}}
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return Collection(self, name)

    def get_collection(self, name: str) -> Collection:
        url = f"{self.base_url}/collections/{name}"
        response = requests.get(url)
        response.raise_for_status()
        return Collection(self, name)

    def get_or_create_collection(self, name: str, metadata: Dict[str, Any] = None) -> Collection:
        try:
            return self.get_collection(name)
        except requests.exceptions.HTTPError:
            return self.create_collection(name, metadata)

    def list_collections(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/collections"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    def delete_collection(self, name: str):
        url = f"{self.base_url}/collections/{name}"
        response = requests.delete(url)
        response.raise_for_status()

