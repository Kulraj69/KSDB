import requests
from typing import Dict, Any, List, Optional

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

