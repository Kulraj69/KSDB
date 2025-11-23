import hnswlib
import numpy as np
import os
import pickle
import boto3
from typing import Dict, Tuple, Optional

class VectorIndex:
    def __init__(self, dim: int, max_elements: int = 10000, persistence_dir: str = "indices"):
        self.dim = dim
        self.max_elements = max_elements
        self.persistence_dir = persistence_dir
        self.indices: Dict[str, hnswlib.Index] = {}
        
        # S3 Configuration
        self.s3_bucket = os.getenv("S3_BUCKET_NAME")
        self.s3_client = boto3.client("s3") if self.s3_bucket else None
        
        if not os.path.exists(persistence_dir):
            os.makedirs(persistence_dir)
            
        if self.s3_client:
            print(f"S3 Persistence Enabled. Bucket: {self.s3_bucket}")
            # Lazy Loading: We do NOT download all indices at startup anymore.
        else:
            print("S3 Persistence Disabled (Local Mode)")

    def _get_index_path(self, collection_id: str) -> str:
        return os.path.join(self.persistence_dir, f"{collection_id}.bin")

    def _download_from_s3(self, collection_id: str) -> bool:
        """Download specific index file from S3. Returns True if found."""
        if not self.s3_client:
            return False
            
        key = f"{collection_id}.bin"
        local_path = self._get_index_path(collection_id)
        try:
            # Check if exists in S3 first (optional, but good for avoiding 404 logs)
            self.s3_client.head_object(Bucket=self.s3_bucket, Key=key)
            print(f"Downloading {key} from S3...")
            self.s3_client.download_file(self.s3_bucket, key, local_path)
            return True
        except Exception:
            # Not found in S3 or error
            return False

    def _upload_to_s3(self, collection_id: str):
        """Upload specific index file to S3"""
        if not self.s3_client:
            return
            
        local_path = self._get_index_path(collection_id)
        key = f"{collection_id}.bin"
        try:
            # print(f"Uploading {key} to S3...") # Verbose logging
            self.s3_client.upload_file(local_path, self.s3_bucket, key)
        except Exception as e:
            print(f"Error uploading to S3: {e}")

    def _load_or_create_index(self, collection_id: str) -> hnswlib.Index:
        if collection_id in self.indices:
            return self.indices[collection_id]

        path = self._get_index_path(collection_id)
        index = hnswlib.Index(space='l2', dim=self.dim)

        # 1. Try to load from local disk
        if os.path.exists(path):
            # print(f"Loading index for collection {collection_id} from disk")
            index.load_index(path, max_elements=self.max_elements)
        
        # 2. If not local, try to download from S3 (Lazy Load)
        elif self._download_from_s3(collection_id):
            # print(f"Loading index for collection {collection_id} from S3")
            index.load_index(path, max_elements=self.max_elements)
            
        # 3. If neither, initialize new
        else:
            # print(f"Initializing new index for collection {collection_id}")
            index.init_index(max_elements=self.max_elements, ef_construction=200, M=16)
            index.set_ef(50)

        self.indices[collection_id] = index
        return index

    def add_items(self, collection_id: str, vectors: np.ndarray, ids: np.ndarray):
        index = self._load_or_create_index(collection_id)
        index.add_items(vectors, ids)
        self.save(collection_id)

    def search(self, collection_id: str, query_vector: np.ndarray, k: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        index = self._load_or_create_index(collection_id)
        # Check if index is empty
        if index.element_count == 0:
            return np.array([]), np.array([])
            
        # Adjust k if index has fewer elements
        current_k = min(k, index.element_count)
        
        labels, distances = index.knn_query(query_vector, k=current_k)
        return labels[0], distances[0]

    def delete_collection(self, collection_id: str):
        if collection_id in self.indices:
            del self.indices[collection_id]
        
        path = self._get_index_path(collection_id)
        if os.path.exists(path):
            os.remove(path)
            
        if self.s3_client:
            try:
                self.s3_client.delete_object(Bucket=self.s3_bucket, Key=f"{collection_id}.bin")
            except Exception as e:
                print(f"Error deleting from S3: {e}")

    def delete_item(self, collection_id: str, id: int):
        # Still limited support in HNSWlib
        print(f"Warning: Delete item not fully supported in raw HNSWlib without rebuild.")
        pass

    def save(self, collection_id: str):
        if collection_id in self.indices:
            self.indices[collection_id].save_index(self._get_index_path(collection_id))
            self._upload_to_s3(collection_id)
