import os
import json
import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy import create_engine, Column, String, BigInteger, Text, ForeignKey, select, delete
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
from sqlalchemy.exc import IntegrityError

Base = declarative_base()

class CollectionModel(Base):
    __tablename__ = "collections"
    id = Column(String, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    metadata_json = Column("metadata", Text)

    @property
    def meta(self):
        return json.loads(self.metadata_json) if self.metadata_json else {}

class DocumentModel(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True) # Composite PK part 1
    collection_id = Column(String, ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True) # Composite PK part 2
    int_id = Column(BigInteger, index=True) # For HNSW mapping
    text = Column(Text)
    metadata_json = Column("metadata", Text)

    @property
    def meta(self):
        return json.loads(self.metadata_json) if self.metadata_json else {}

class MetadataDB:
    def __init__(self):
        # Default to sqlite if no env var provided
        self.db_url = os.getenv("DATABASE_URL", "sqlite:///metadata.db")
        
        connect_args = {}
        engine_args = {}
        
        if "sqlite" in self.db_url:
            connect_args["check_same_thread"] = False
        else:
            # Postgres Production Config
            engine_args["pool_size"] = 20
            engine_args["max_overflow"] = 10
            engine_args["pool_pre_ping"] = True # Auto-reconnect on stale connections
            
        self.engine = create_engine(
            self.db_url, 
            connect_args=connect_args,
            **engine_args
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self._init_db()

    def _init_db(self):
        Base.metadata.create_all(bind=self.engine)

    def _get_session(self) -> Session:
        return self.SessionLocal()

    # --- Collection Management ---

    def create_collection(self, name: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        session = self._get_session()
        try:
            collection_id = str(uuid.uuid4())
            meta_json = json.dumps(metadata or {})
            new_collection = CollectionModel(id=collection_id, name=name, metadata_json=meta_json)
            session.add(new_collection)
            session.commit()
            return {"id": collection_id, "name": name, "metadata": metadata}
        except IntegrityError:
            session.rollback()
            return self.get_collection(name)
        finally:
            session.close()

    def get_collection(self, name: str) -> Optional[Dict[str, Any]]:
        session = self._get_session()
        try:
            stmt = select(CollectionModel).where(CollectionModel.name == name)
            collection = session.execute(stmt).scalar_one_or_none()
            if collection:
                return {
                    "id": collection.id,
                    "name": collection.name,
                    "metadata": collection.meta
                }
            return None
        finally:
            session.close()
    
    def list_collections(self) -> List[Dict[str, Any]]:
        session = self._get_session()
        try:
            stmt = select(CollectionModel)
            collections = session.execute(stmt).scalars().all()
            return [
                {"id": c.id, "name": c.name, "metadata": c.meta}
                for c in collections
            ]
        finally:
            session.close()

    def delete_collection(self, name: str):
        session = self._get_session()
        try:
            stmt = delete(CollectionModel).where(CollectionModel.name == name)
            session.execute(stmt)
            session.commit()
        finally:
            session.close()

    # --- Document Management ---

    def insert(self, collection_id: str, doc_id: str, int_id: int, text: str, metadata: Dict[str, Any] = {}):
        session = self._get_session()
        try:
            meta_json = json.dumps(metadata)
            # Merge handles insert or update based on PK
            doc = DocumentModel(
                id=doc_id, 
                collection_id=collection_id, 
                int_id=int_id, 
                text=text, 
                metadata_json=meta_json
            )
            session.merge(doc)
            session.commit()
        finally:
            session.close()
    
    def insert_batch(
        self, 
        collection_id: str, 
        doc_ids: List[str], 
        int_ids: List[int], 
        texts: List[str], 
        metadatas: List[Dict[str, Any]]
    ):
        """Batch insert - much faster than individual inserts"""
        session = self._get_session()
        try:
            docs = []
            for doc_id, int_id, text, metadata in zip(doc_ids, int_ids, texts, metadatas):
                meta_json = json.dumps(metadata)
                doc = DocumentModel(
                    id=doc_id,
                    collection_id=collection_id,
                    int_id=int_id,
                    text=text,
                    metadata_json=meta_json
                )
                docs.append(doc)
            
            # Bulk merge operation
            for doc in docs:
                session.merge(doc)
            
            session.commit()
        finally:
            session.close()

    def get(self, collection_id: str, doc_id: str) -> Optional[Dict[str, Any]]:
        session = self._get_session()
        try:
            stmt = select(DocumentModel).where(
                DocumentModel.collection_id == collection_id,
                DocumentModel.id == doc_id
            )
            doc = session.execute(stmt).scalar_one_or_none()
            if doc:
                return {
                    "id": doc.id,
                    "text": doc.text,
                    "metadata": doc.meta
                }
            return None
        finally:
            session.close()

    def get_by_int_ids(self, collection_id: str, int_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        if not int_ids:
            return {}
        
        session = self._get_session()
        try:
            stmt = select(DocumentModel).where(
                DocumentModel.collection_id == collection_id,
                DocumentModel.int_id.in_(int_ids)
            )
            docs = session.execute(stmt).scalars().all()
            
            results = {}
            for doc in docs:
                results[doc.int_id] = {
                    "id": doc.id,
                    "text": doc.text,
                    "metadata": doc.meta
                }
            return results
        finally:
            session.close()

    def delete(self, collection_id: str, doc_id: str):
        session = self._get_session()
        try:
            stmt = delete(DocumentModel).where(
                DocumentModel.collection_id == collection_id,
                DocumentModel.id == doc_id
            )
            session.execute(stmt)
            session.commit()
        finally:
            session.close()
        
    def query(self, collection_id: str, where: Dict[str, Any] = None) -> List[str]:
        """
        Returns a list of document IDs that match the filter.
        """
        if not where:
            return None 
            
        # Naive implementation: Fetch all metadata and filter in Python
        # (Same as before, but using ORM)
        session = self._get_session()
        try:
            stmt = select(DocumentModel).where(DocumentModel.collection_id == collection_id)
            docs = session.execute(stmt).scalars().all()
            
            matching_ids = []
            for doc in docs:
                doc_meta = doc.meta
                match = True
                for k, v in where.items():
                    if doc_meta.get(k) != v:
                        match = False
                        break
                if match:
                    matching_ids.append(doc.id)
            return matching_ids
        finally:
            session.close()

    def close(self):
        # SQLAlchemy engine connection pooling handles closing usually
        pass
