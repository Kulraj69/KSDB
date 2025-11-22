import requests
from typing import Dict, Any, List

class KSdbClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    def upsert(self, doc_id: int, text: str, metadata: Dict[str, Any] = {}):
        url = f"{self.base_url}/upsert"
        payload = {
            "id": doc_id,
            "text": text,
            "metadata": metadata
        }
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/search"
        payload = {
            "query": query,
            "k": k
        }
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def delete(self, doc_id: int):
        url = f"{self.base_url}/delete/{doc_id}"
        response = requests.delete(url)
        response.raise_for_status()
        return response.json()

    def health(self):
        return requests.get(f"{self.base_url}/health").json()
