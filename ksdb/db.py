import os
import json
import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy import create_engine, Column, String, BigInteger, Text, ForeignKey, select, delete, Float, or_, text
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

class TripleModel(Base):
    __tablename__ = "triples"
    id = Column(String, primary_key=True)
    collection_id = Column(String, ForeignKey("collections.id", ondelete="CASCADE"), nullable=False)
    subject = Column(String, index=True, nullable=False)
    predicate = Column(String, nullable=False)
    object = Column(String, index=True, nullable=False)
    document_id = Column(String, nullable=True)
    weight = Column(Float, default=1.0)

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
        # Initialize FTS5 virtual table for Hybrid Search (SQLite only for now)
        if "sqlite" in self.db_url:
            with self.engine.connect() as conn:
                conn.execute(text("CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(id UNINDEXED, text, collection_id UNINDEXED)"))
                conn.commit()

    def _get_session(self) -> Session:
        return self.SessionLocal()

    # --- FTS / Hybrid Search ---

    def insert_fts_batch(self, collection_id: str, ids: List[str], texts: List[str]):
        """Insert text into FTS index"""
        if "sqlite" not in self.db_url:
            return # Skip for non-sqlite for now (Postgres uses tsvector)
            
        with self.engine.connect() as conn:
            # Delete existing entries to avoid duplicates (naive update)
            # In FTS5 we can't easily "upsert", so we delete and insert
            for doc_id in ids:
                conn.execute(text("DELETE FROM documents_fts WHERE id = :id AND collection_id = :col_id"), 
                           {"id": doc_id, "col_id": collection_id})
            
            # Insert new
            values = [{"id": i, "text": t, "col_id": collection_id} for i, t in zip(ids, texts)]
            conn.execute(text("INSERT INTO documents_fts (id, text, collection_id) VALUES (:id, :text, :col_id)"), values)
            conn.commit()

    def search_fts(self, collection_id: str, query: str, limit: int = 20) -> List[str]:
        """Full Text Search using FTS5"""
        if "sqlite" not in self.db_url:
            return []
            
        with self.engine.connect() as conn:
            # Simple FTS query
            # We sanitize the query slightly to prevent syntax errors
            safe_query = query.replace('"', '""')
            stmt = text(f"SELECT id FROM documents_fts WHERE collection_id = :col_id AND documents_fts MATCH :query ORDER BY rank LIMIT :limit")
            try:
                result = conn.execute(stmt, {"col_id": collection_id, "query": safe_query, "limit": limit})
                return [row[0] for row in result]
            except Exception as e:
                print(f"FTS Error: {e}")
                return []

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

    # --- Knowledge Graph Management ---

    def insert_triples(self, collection_id: str, triples: List[Dict[str, Any]]):
        """
        Insert triples into the graph.
        triples format: [{"subject": "S", "predicate": "P", "object": "O", "doc_id": "opt"}]
        """
        session = self._get_session()
        try:
            triple_objs = []
            for t in triples:
                triple_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{collection_id}:{t['subject']}:{t['predicate']}:{t['object']}"))
                obj = TripleModel(
                    id=triple_id,
                    collection_id=collection_id,
                    subject=t['subject'],
                    predicate=t['predicate'],
                    object=t['object'],
                    document_id=t.get('doc_id'),
                    weight=t.get('weight', 1.0)
                )
                triple_objs.append(obj)
            
            for obj in triple_objs:
                session.merge(obj)
            session.commit()
        finally:
            session.close()

    def get_triples(self, collection_id: str, subjects: List[str]) -> List[Dict[str, Any]]:
        """
        Get triples where subject OR object matches the list of entities.
        This allows for 1-hop traversal.
        """
        session = self._get_session()
        try:
            stmt = select(TripleModel).where(
                TripleModel.collection_id == collection_id,
                or_(
                    TripleModel.subject.in_(subjects),
                    TripleModel.object.in_(subjects)
                )
            )
            triples = session.execute(stmt).scalars().all()
            return [
                {
                    "subject": t.subject,
                    "predicate": t.predicate,
                    "object": t.object,
                    "weight": t.weight
                }
                for t in triples
            ]
        finally:
            session.close()
