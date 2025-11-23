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
        metadatas: Optional[List[Dict[str, Any]]] = None,
        deduplicate: bool = False,
        extract_graph: bool = False
    ):
        """
        Add documents to collection.
        
        Args:
            ids: List of unique IDs
            documents: List of text documents
            metadatas: List of metadata dicts
            deduplicate: If True, skips documents that are semantically identical to existing ones
            extract_graph: If True, automatically extracts entities and builds a knowledge graph
        """
        if metadatas is None:
            metadatas = [{} for _ in ids]
        
        # Use batch endpoint for better performance
        response = requests.post(
            f"{self.client_url}/collections/{self.name}/add_batch",
            params={"deduplicate": deduplicate, "extract_graph": extract_graph},
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

    def add_triples(self, triples: List[Dict[str, Any]]):
        """
        Add triples to the knowledge graph.
        Format: [{"subject": "S", "predicate": "P", "object": "O"}]
        """
        response = requests.post(
            f"{self.client_url}/collections/{self.name}/triples/add",
            json={"triples": triples}
        )
        response.raise_for_status()
        return response.json()
        
    def query_graph(self, entities: List[str]) -> List[Dict[str, Any]]:
        """
        Query the knowledge graph for connections to these entities.
        """
        response = requests.post(
            f"{self.client_url}/collections/{self.name}/triples/query",
            json={"entities": entities}
        )
        response.raise_for_status()
        return response.json()


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

