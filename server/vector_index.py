import hnswlib
import numpy as np
import os
import pickle

class VectorIndex:
    def __init__(self, dim: int, max_elements: int = 10000, persistence_path: str = "index.bin"):
        self.dim = dim
        self.max_elements = max_elements
        self.persistence_path = persistence_path
        self.index = hnswlib.Index(space='l2', dim=dim)
        
        if os.path.exists(persistence_path):
            print(f"Loading index from {persistence_path}")
            self.index.load_index(persistence_path, max_elements=max_elements)
        else:
            print("Initializing new HNSW index")
            self.index.init_index(max_elements=max_elements, ef_construction=200, M=16)
            self.index.set_ef(50)  # ef_search

    def add_items(self, vectors: np.ndarray, ids: np.ndarray):
        """
        vectors: shape (N, dim)
        ids: shape (N,)
        """
        self.index.add_items(vectors, ids)
        self.save()

    def search(self, query_vector: np.ndarray, k: int = 5):
        """
        query_vector: shape (dim,) or (1, dim)
        Returns: (labels, distances)
        """
        labels, distances = self.index.knn_query(query_vector, k=k)
        return labels[0], distances[0]

    def delete_item(self, id: int):
        # HNSWlib doesn't support direct deletion easily in the basic interface 
        # without marking as deleted. For this MVP, we'll skip true deletion 
        # or implement a soft delete if needed. 
        # Re-building index is often required for true deletion in simple HNSW implementations.
        # For now, we will just log a warning.
        print(f"Warning: Delete not fully supported in raw HNSWlib without rebuild. ID {id} remains in index.")
        pass

    def save(self):
        self.index.save_index(self.persistence_path)
