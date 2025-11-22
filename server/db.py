import sqlite3
import json
from typing import Optional, Dict, Any

class MetadataDB:
    def __init__(self, db_path: str = "metadata.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY,
                text TEXT,
                metadata TEXT
            )
        """)
        self.conn.commit()

    def insert(self, doc_id: int, text: str, metadata: Dict[str, Any] = {}):
        meta_json = json.dumps(metadata)
        self.conn.execute(
            "INSERT OR REPLACE INTO documents (id, text, metadata) VALUES (?, ?, ?)",
            (doc_id, text, meta_json)
        )
        self.conn.commit()

    def get(self, doc_id: int) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT id, text, metadata FROM documents WHERE id = ?", (doc_id,))
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "text": row[1],
                "metadata": json.loads(row[2])
            }
        return None

    def delete(self, doc_id: int):
        self.conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        self.conn.commit()

    def close(self):
        self.conn.close()
