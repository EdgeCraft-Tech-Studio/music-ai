import os
import json
import sqlite3
import time
from typing import Dict, Any, List, Optional, Iterable, Tuple

import appdirs

# === Project Imports ===
from settings.core_settings import (
    APP_NAME,
    APP_AUTHOR,
    ELASTICSEARCH_ENABLED,
    ELASTICSEARCH_INDEX,
    ELASTICSEARCH_BULK_SIZE,
    ELASTICSEARCH_MAX_RESULTS,
)
from utils.logger import info, debug, warning, error
from utils.search.es_client import ESClient


# === Helper Functions ===


def parse_json_array(val: Optional[str]) -> List[str]:
    """
    Parse a string that may contain a JSON array, a delimited list, or a single value.
    Returns a list of strings.
    """
    if not val:
        return []

    try:
        obj = json.loads(val)
        if isinstance(obj, list):
            return [str(x) for x in obj if x]
        return [str(obj)]
    except Exception:
        # Handle delimited or plain strings
        s = str(val)
        if "•" in s:
            return [p.strip() for p in s.split("•") if p.strip()]
        return [s] if s else []


def to_es_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a SQLite row/dict into an Elasticsearch document.
    Expects keys defined in database_indexer.py schema.
    """

    # Base document structure
    doc = {
        "path": row.get("path", ""),
        "name": row.get("name", ""),
        "vendor": row.get("vendor") or "",
        "library": row.get("library") or "",
        "instrument": parse_json_array(row.get("instrument")),
        "genre": parse_json_array(row.get("genre")),
        "tags": parse_json_array(row.get("tags")),
        "file_type": row.get("file_type") or "",
        "extension": row.get("extension") or "",
        "parent_folder": row.get("parent_folder") or "",
        "bpm": row.get("bpm") or "",
        "key": row.get("key") or "",
        "modified_time": int(row.get("modified_time") or 0),
        "created_at": int(row.get("created_at") or 0),
    }

    # Build aggregated fulltext field for better recall/ranking
    ft_parts = [
        doc["name"],
        doc["path"],
        doc["vendor"],
        doc["library"],
        " ".join(doc["instrument"]),
        " ".join(doc["genre"]),
        " ".join(doc["tags"]),
        doc["file_type"],
        doc["extension"],
        doc["parent_folder"],
        doc["bpm"],
        doc["key"],
    ]

    doc["fulltext"] = " ".join([p for p in ft_parts if p])

    return doc


# === Main Functions ===
class ESSync:
    """
    Service responsible for syncing from SQLite -> Elasticsearch.
    Can:
    - full/bulk sync from the entire SQLite table
    - incremental sync based on created_at/modified_time
    - single upsert/delete by path
    """

    def __init__(self, sqlite_path: str):
        self.sqlite_path = sqlite_path
        self.es = ESClient()
        self.enabled = bool(
            ELASTICSEARCH_ENABLED and self.es.is_enabled() and self.es.ping()
        )
        if self.enabled:
            self.es.ensure_index()

    def is_enabled(self) -> bool:
        return self.enabled

    def _connect_sqlite(self):
        return sqlite3.connect(self.sqlite_path)

    def _select_fields(self) -> str:
        # Keep in sync with files table schema
        return (
            "path, name, extension, file_type, parent_folder, "
            "modified_time, bpm, key, vendor, library, keywords, tags, "
            "instrument, genre, mood, format, created_at"
        )

    def _fetch_rows_in_batches(
        self, where_clause: str = "", params: tuple = (), batch_size: int = 5000
    ) -> Iterable[List[Dict[str, Any]]]:
        fields = self._select_fields()
        sql = f"SELECT {fields} FROM files"
        if where_clause:
            sql += f" WHERE {where_clause}"
        sql += " ORDER BY rowid"

        conn = self._connect_sqlite()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        cols = [d[0] for d in cursor.description]

        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break
            yield [dict(zip(cols, r)) for r in rows]

        conn.close()

    def _fetch_rows_by_paths(self, paths: List[str]) -> List[Dict[str, Any]]:
        if not paths:
            return []
        fields = self._select_fields()
        placeholders = ",".join(["?"] * len(paths))
        sql = f"SELECT {fields} FROM files WHERE path IN ({placeholders})"
        conn = self._connect_sqlite()
        cursor = conn.cursor()
        cursor.execute(sql, tuple(paths))
        cols = [d[0] for d in cursor.description]
        rows = [dict(zip(cols, r)) for r in cursor.fetchall()]
        conn.close()
        return rows

    def _fetch_row_by_path(self, path: str) -> Optional[Dict[str, Any]]:
        rows = self._fetch_rows_by_paths([path])
        return rows[0] if rows else None

    def bulk_full_sync(self, bulk_size: int = None) -> int:
        """
        Full reindex of the files table into Elasticsearch.
        Returns number of documents indexed.
        """
        if not self.enabled:
            return 0

        bulk_sz = bulk_size or ELASTICSEARCH_BULK_SIZE
        total = 0
        for batch in self._fetch_rows_in_batches():
            actions = []
            for row in batch:
                doc = to_es_doc(row)
                doc_id = doc["path"]  # path as unique id
                actions.append({"_op_type": "index", "_id": doc_id, "_source": doc})
                if len(actions) >= bulk_sz:
                    self.es.bulk(actions)
                    total += len(actions)
                    actions.clear()
            if actions:
                self.es.bulk(actions)
                total += len(actions)
                actions.clear()
            debug(f"⚡ ES bulk synced (running total={total})")
        info(f"✅ ES full sync completed: {total} documents")
        return total

    def upsert_path(self, path: str) -> bool:
        if not self.enabled:
            return False
        row = self._fetch_row_by_path(path)
        if not row:
            # If the row is not found, ensure it's deleted from ES
            self.delete_path(path)
            return False
        doc = to_es_doc(row)
        return self.es.index_doc(doc_id=path, source=doc)

    def delete_path(self, path: str) -> bool:
        if not self.enabled:
            return False
        return self.es.delete_doc(path)

    def bulk_upsert_paths(self, paths: List[str], bulk_size: int = None) -> int:
        if not self.enabled or not paths:
            return 0
        bulk_sz = bulk_size or ELASTICSEARCH_BULK_SIZE
        rows = self._fetch_rows_by_paths(paths)
        total = 0
        actions = []
        for row in rows:
            doc = to_es_doc(row)
            actions.append({"_op_type": "index", "_id": doc["path"], "_source": doc})
            if len(actions) >= bulk_sz:
                self.es.bulk(actions)
                total += len(actions)
                actions.clear()
        if actions:
            self.es.bulk(actions)
            total += len(actions)
        return total

    def bulk_delete_paths(self, paths: List[str]) -> int:
        if not self.enabled or not paths:
            return 0
        actions = [{"_op_type": "delete", "_id": p} for p in paths]
        if not actions:
            return 0
        ok = self.es.bulk(actions)
        return len(paths) if ok else 0
