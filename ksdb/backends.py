"""
Storage backends for KSdb - abstracts away infrastructure details
"""
import os
from typing import Optional


class StorageBackend:
    """Base class for storage backends"""
    
    def __init__(self, **kwargs):
        pass
    
    def get_database_url(self) -> str:
        raise NotImplementedError
    
    def get_vector_storage_config(self) -> dict:
        raise NotImplementedError


class LocalBackend(StorageBackend):
    """Local storage using SQLite and local files (default)"""
    
    def __init__(self, data_path: str = ".ksdb"):
        self.data_path = os.path.abspath(data_path)
        os.makedirs(self.data_path, exist_ok=True)
        os.makedirs(os.path.join(self.data_path, "indices"), exist_ok=True)
    
    def get_database_url(self) -> str:
        db_path = os.path.join(self.data_path, "metadata.db")
        return f"sqlite:///{db_path}"
    
    def get_vector_storage_config(self) -> dict:
        return {
            "type": "local",
            "path": os.path.join(self.data_path, "indices")
        }


class PostgresBackend(StorageBackend):
    """PostgreSQL storage backend"""
    
    def __init__(self, connection_string: str, vector_path: str = ".ksdb/indices"):
        self.connection_string = connection_string
        self.vector_path = vector_path
        os.makedirs(vector_path, exist_ok=True)
    
    def get_database_url(self) -> str:
        return self.connection_string
    
    def get_vector_storage_config(self) -> dict:
        return {
            "type": "local",
            "path": self.vector_path
        }


class S3Backend(StorageBackend):
    """AWS S3 storage backend"""
    
    def __init__(self, 
                 database_url: str,
                 bucket_name: str,
                 region: str = "us-east-1",
                 access_key: Optional[str] = None,
                 secret_key: Optional[str] = None):
        self.database_url = database_url
        self.bucket_name = bucket_name
        self.region = region
        
        # Set AWS credentials if provided
        if access_key:
            os.environ["AWS_ACCESS_KEY_ID"] = access_key
        if secret_key:
            os.environ["AWS_SECRET_ACCESS_KEY"] = secret_key
        os.environ["AWS_REGION"] = region
    
    def get_database_url(self) -> str:
        return self.database_url
    
    def get_vector_storage_config(self) -> dict:
        return {
            "type": "s3",
            "bucket": self.bucket_name,
            "region": self.region
        }


def get_backend(backend_type: str = "local", **kwargs) -> StorageBackend:
    """Factory function to get storage backend"""
    
    backends = {
        "local": LocalBackend,
        "postgres": PostgresBackend,
        "s3": S3Backend
    }
    
    if backend_type not in backends:
        raise ValueError(f"Unknown backend: {backend_type}. Choose from: {list(backends.keys())}")
    
    return backends[backend_type](**kwargs)
