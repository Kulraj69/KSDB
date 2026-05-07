import hnswlib
import numpy as np
import os
from typing import Dict, Tuple

class VectorIndex:
    def __init__(self, dim: int, max_elements: int = 10000, persistence_dir: str = None):
        self.dim = dim
        self.max_elements = max_elements
        data_path = os.getenv("KSDB_DATA_PATH", ".ksdb")
        self.persistence_dir = persistence_dir or os.getenv("INDEX_PATH") or os.path.join(data_path, "indices")
        self.indices: Dict[str, hnswlib.Index] = {}
        
        # S3 Configuration
        self.s3_bucket = os.getenv("S3_BUCKET_NAME")
        self.s3_client = None
        if self.s3_bucket:
            import boto3

            self.s3_client = boto3.client("s3")
        
        if not os.path.exists(self.persistence_dir):
            os.makedirs(self.persistence_dir)
            
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
        needed_capacity = index.element_count + len(ids)
        try:
            current_capacity = index.get_max_elements()
        except AttributeError:
            current_capacity = self.max_elements

        if needed_capacity > current_capacity:
            new_capacity = max(needed_capacity, int(current_capacity * 1.5), current_capacity + 1000)
            index.resize_index(new_capacity)
            self.max_elements = max(self.max_elements, new_capacity)

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
        if len(labels) == 1:
            return labels[0], distances[0]
        return labels, distances

    def count(self, collection_id: str) -> int:
        return self._load_or_create_index(collection_id).element_count

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
        index = self._load_or_create_index(collection_id)
        try:
            index.mark_deleted(id)
            self.save(collection_id)
            return True
        except RuntimeError:
            return False

    def save(self, collection_id: str):
        if collection_id in self.indices:
            self.indices[collection_id].save_index(self._get_index_path(collection_id))
            self._upload_to_s3(collection_id)
