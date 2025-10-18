import os
import json
import sqlite3
import time
from typing import Dict, Any, List, Optional, Iterable

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

    def _fetch_rows_in_batches(
        self, where_clause: str = "", params: tuple = (), batch_size: int = 5000
    ) -> Iterable[List[Dict[str, Any]]]:
        fields = (
            "path, name, extension, file_type, parent_folder, "
            "modified_time, bpm, key, vendor, library, keywords, tags, "
            "instrument, genre, mood, format, created_at"
        )
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
            if actions:
                self.es.bulk(actions)
                total += len(actions)
                debug(f"⚡ ES bulk synced {len(actions)} documents (total={total})")
        info(f"✅ ES full sync completed: {total} documents")
        return total

    def upsert_one_by_path(self, path: str) -> bool:
        """
        Fetch a single record from SQLite by path and upsert into ES.
        """
        if not self.enabled:
            return False
        conn = self._connect_sqlite()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT path, name, extension, file_type, parent_folder, 
                  modified_time, bpm, key, vendor, library, keywords, tags,
                  instrument, genre, mood, format, created_at
            FROM files
            WHERE path = ?
            """,
            (path,),
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            # if not found in DB, delete from ES
            return self.es.delete_doc(path)

        cols = [
            "path",
            "name",
            "extension",
            "file_type",
            "parent_folder",
            "modified_time",
            "bpm",
            "key",
            "vendor",
            "library",
            "keywords",
            "tags",
            "instrument",
            "genre",
            "mood",
            "format",
            "created_at",
        ]
        data = dict(zip(cols, row))
        doc = to_es_doc(data)
        return self.es.index_doc(path, doc)

    def delete_by_path(self, path: str) -> bool:
        if not self.enabled:
            return False
        return self.es.delete_doc(path)

    def incremental_sync_since(
        self, since_epoch_seconds: int, bulk_size: int = None
    ) -> int:
        """
        Upsert rows where created_at or modified_time >= since_epoch_seconds
        """
        if not self.enabled:
            return 0
        bulk_sz = bulk_size or ELASTICSEARCH_BULK_SIZE
        total = 0

        where_clause = "(created_at >= ? OR modified_time >= ?)"
        params = (since_epoch_seconds, since_epoch_seconds)
        for batch in self._fetch_rows_in_batches(where_clause, params):
            actions = []
            for row in batch:
                doc = to_es_doc(row)
                doc_id = doc["path"]
                actions.append({"_op_type": "index", "_id": doc_id, "_source": doc})
                if len(actions) >= bulk_sz:
                    self.es.bulk(actions)
                    total += len(actions)
                    actions.clear()
            if actions:
                self.es.bulk(actions)
                total += len(actions)
        if total:
            info(f"🔄 ES incremental sync: {total} documents upserted")
        return total


class ESBackgroundSync:
    """
    Tiny background synchronizer that:
    - Performs an initial bulk sync on first run (if ES empty)
    - Then performs incremental sync every N seconds based on last sync timestamp
    Stores last sync state in a small JSON file in PatchIO config dir.
    """

    def __init__(self, sqlite_path: str, interval_seconds: int = 15):
        self.sqlite_path = sqlite_path
        self.interval = interval_seconds
        self.sync = ESSync(sqlite_path)
        self.state_path = self._state_file_path()
        self._running = False

    def _state_file_path(self) -> str:
        config_dir = appdirs.user_config_dir(APP_NAME, APP_AUTHOR)
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, "es_sync_state.json")

    def _load_state(self) -> Dict[str, Any]:
        try:
            if os.path.exists(self.state_path):
                with open(self.state_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {"last_sync_ts": 0}

    def _save_state(self, state: Dict[str, Any]):
        try:
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(state, f)
        except Exception as e:
            warning(f"⚠️ Could not persist ES sync state: {e}")

    def start(self):
        if not self.sync.is_enabled():
            info("ℹ️ ES background sync disabled/not available")
            return
        import threading

        self._running = True
        t = threading.Thread(target=self._run_loop, daemon=True)
        t.start()
        info("🚀 ES background incremental sync started")

    def stop(self):
        self._running = False

    def _run_loop(self):
        state = self._load_state()
        last_ts = int(state.get("last_sync_ts", 0))

        # Initial sync on first run (if needed)
        try:
            if last_ts == 0:
                info("🔁 Performing initial ES full sync...")
                self.sync.bulk_full_sync()
                last_ts = int(time.time())
                state["last_sync_ts"] = last_ts
                self._save_state(state)
        except Exception as e:
            error(f"❌ Initial ES full sync failed: {e}")

        while self._running:
            try:
                # Incremental sync based on last timestamp
                upserted = self.sync.incremental_sync_since(last_ts)
                last_ts = int(time.time())
                state["last_sync_ts"] = last_ts
                self._save_state(state)
            except Exception as e:
                error(f"❌ ES incremental sync failed: {e}")
            time.sleep(self.interval)
