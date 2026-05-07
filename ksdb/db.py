import os
import json
import uuid
import re
from typing import Optional, Dict, Any, List
from sqlalchemy import create_engine, Column, String, BigInteger, Text, ForeignKey, select, delete, Float, or_, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
from sqlalchemy.exc import IntegrityError

Base = declarative_base()


def _metadata_matches_filter(metadata: Dict[str, Any], filter_dict: Dict[str, Any]) -> bool:
    """
    Check whether a metadata payload matches a Chroma-style filter.
    Supports $eq, $ne, $gt, $gte, $lt, $lte, $in, $nin, $and, and $or.
    """
    if not filter_dict:
        return True

    for key, value in filter_dict.items():
        if key == "$and":
            if not isinstance(value, list):
                return False
            if not all(_metadata_matches_filter(metadata, sub_filter) for sub_filter in value):
                return False
            continue

        if key == "$or":
            if not isinstance(value, list):
                return False
            if not any(_metadata_matches_filter(metadata, sub_filter) for sub_filter in value):
                return False
            continue

        doc_val = metadata.get(key)

        if not isinstance(value, dict):
            if doc_val != value:
                return False
            continue

        for op, op_val in value.items():
            if op == "$eq":
                if doc_val != op_val:
                    return False
            elif op == "$ne":
                if doc_val == op_val:
                    return False
            elif op == "$gt":
                if not isinstance(doc_val, (int, float)) or not isinstance(op_val, (int, float)):
                    return False
                if not doc_val > op_val:
                    return False
            elif op == "$gte":
                if not isinstance(doc_val, (int, float)) or not isinstance(op_val, (int, float)):
                    return False
                if not doc_val >= op_val:
                    return False
            elif op == "$lt":
                if not isinstance(doc_val, (int, float)) or not isinstance(op_val, (int, float)):
                    return False
                if not doc_val < op_val:
                    return False
            elif op == "$lte":
                if not isinstance(doc_val, (int, float)) or not isinstance(op_val, (int, float)):
                    return False
                if not doc_val <= op_val:
                    return False
            elif op == "$in":
                if not isinstance(op_val, list):
                    return False
                if isinstance(doc_val, list):
                    if not any(item in op_val for item in doc_val):
                        return False
                elif doc_val not in op_val:
                    return False
            elif op == "$nin":
                if not isinstance(op_val, list):
                    return False
                if isinstance(doc_val, list):
                    if any(item in op_val for item in doc_val):
                        return False
                elif doc_val in op_val:
                    return False
            else:
                return False

    return True

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
        # Default to a self-contained local data directory unless DATABASE_URL is provided.
        self.db_url = os.getenv("DATABASE_URL") or self._default_sqlite_url()
        self._ensure_sqlite_parent_dir(self.db_url)
        
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

    @staticmethod
    def _default_sqlite_url() -> str:
        data_path = os.path.abspath(os.getenv("KSDB_DATA_PATH", ".ksdb"))
        os.makedirs(data_path, exist_ok=True)
        return f"sqlite:///{os.path.join(data_path, 'metadata.db')}"

    @staticmethod
    def _ensure_sqlite_parent_dir(db_url: str):
        if not db_url.startswith("sqlite:///"):
            return

        path = db_url.replace("sqlite:///", "", 1)
        if not path or path == ":memory:":
            return

        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

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

        if not ids:
            return
            
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

    def delete_fts_batch(self, collection_id: str, ids: List[str]):
        """Remove documents from the SQLite FTS index."""
        if "sqlite" not in self.db_url or not ids:
            return

        with self.engine.connect() as conn:
            values = [{"id": doc_id, "col_id": collection_id} for doc_id in ids]
            conn.execute(
                text("DELETE FROM documents_fts WHERE id = :id AND collection_id = :col_id"),
                values,
            )
            conn.commit()

    @staticmethod
    def _format_fts_query(query: str) -> str:
        tokens = re.findall(r"[\w]+", query, flags=re.UNICODE)
        quoted_tokens = [f'"{token.replace(chr(34), chr(34) * 2)}"' for token in tokens]
        return " OR ".join(quoted_tokens)

    def search_fts(self, collection_id: str, query: str, limit: int = 20) -> List[str]:
        """Full Text Search using FTS5"""
        if "sqlite" not in self.db_url:
            return []

        match_query = self._format_fts_query(query)
        if not match_query:
            return []
            
        with self.engine.connect() as conn:
            stmt = text("SELECT id FROM documents_fts WHERE collection_id = :col_id AND documents_fts MATCH :query ORDER BY rank LIMIT :limit")
            try:
                result = conn.execute(stmt, {"col_id": collection_id, "query": match_query, "limit": limit})
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
        collection_id = None
        try:
            collection = session.execute(select(CollectionModel).where(CollectionModel.name == name)).scalar_one_or_none()
            if collection:
                collection_id = collection.id

            if collection_id:
                session.execute(delete(DocumentModel).where(DocumentModel.collection_id == collection_id))
                session.execute(delete(TripleModel).where(TripleModel.collection_id == collection_id))

            stmt = delete(CollectionModel).where(CollectionModel.name == name)
            session.execute(stmt)
            session.commit()
        finally:
            session.close()

        if collection_id and "sqlite" in self.db_url:
            with self.engine.connect() as conn:
                conn.execute(text("DELETE FROM documents_fts WHERE collection_id = :col_id"), {"col_id": collection_id})
                conn.commit()

    # --- Document Management ---

    def insert(self, collection_id: str, doc_id: str, int_id: int, text: str, metadata: Dict[str, Any] = None):
        session = self._get_session()
        try:
            meta_json = json.dumps(metadata or {})
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

    def get_by_ids(self, collection_id: str, doc_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        if not doc_ids:
            return {}

        session = self._get_session()
        try:
            stmt = select(DocumentModel).where(
                DocumentModel.collection_id == collection_id,
                DocumentModel.id.in_(doc_ids)
            )
            docs = session.execute(stmt).scalars().all()

            return {
                doc.id: {
                    "id": doc.id,
                    "text": doc.text,
                    "metadata": doc.meta
                }
                for doc in docs
            }
        finally:
            session.close()

    def delete(self, collection_id: str, doc_id: str):
        session = self._get_session()
        deleted = 0
        try:
            stmt = delete(DocumentModel).where(
                DocumentModel.collection_id == collection_id,
                DocumentModel.id == doc_id
            )
            result = session.execute(stmt)
            deleted = result.rowcount or 0
            session.commit()
        finally:
            session.close()

        if deleted:
            self.delete_fts_batch(collection_id, [doc_id])

        return deleted > 0
        
    def query(self, collection_id: str, where: Dict[str, Any] = None) -> List[str]:
        """
        Returns a list of document IDs that match the filter.
        """
        if not where:
            return None 
            
        # SQLite/Postgres JSON pushdown can come later; this keeps filter semantics
        # correct across both backends while the storage layer is still small.
        session = self._get_session()
        try:
            stmt = select(DocumentModel).where(DocumentModel.collection_id == collection_id)
            docs = session.execute(stmt).scalars().all()
            
            matching_ids = []
            for doc in docs:
                if _metadata_matches_filter(doc.meta, where):
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
