import os
from typing import Optional, Dict, Any, List

from settings.core_settings import (
    ELASTICSEARCH_ENABLED,
    ELASTICSEARCH_HOSTS,
    ELASTICSEARCH_USERNAME,
    ELASTICSEARCH_PASSWORD,
    ELASTICSEARCH_SSL_VERIFY,
    ELASTICSEARCH_INDEX,
)

try:
    from elasticsearch import Elasticsearch, TransportError, NotFoundError
    from elasticsearch.helpers import bulk
except Exception:
    Elasticsearch = None
    TransportError = Exception
    NotFoundError = Exception
    bulk = None

from utils.logger import info, warning, error, debug


class ESClient:
    def __init__(self):
        self.enabled = bool(ELASTICSEARCH_ENABLED and Elasticsearch is not None)
        self._client = None
        self._index = ELASTICSEARCH_INDEX

    def is_enabled(self) -> bool:
        return self.enabled

    def client(self) -> Optional[Elasticsearch]:
        if not self.enabled:
            return None
        if self._client is None:
            try:
                http_auth = (
                    (ELASTICSEARCH_USERNAME, ELASTICSEARCH_PASSWORD)
                    if ELASTICSEARCH_USERNAME and ELASTICSEARCH_PASSWORD
                    else None
                )
                self._client = Elasticsearch(
                    ELASTICSEARCH_HOSTS,
                    basic_auth=http_auth,
                    verify_certs=bool(ELASTICSEARCH_SSL_VERIFY),
                    request_timeout=30,
                    retry_on_timeout=True,
                    max_retries=3,
                )
                debug("✅ Elasticsearch client created")
            except Exception as e:
                error(f"❌ Failed to create Elasticsearch client: {e}")
                self.enabled = False
                self._client = None
        return self._client

    def ping(self) -> bool:
        c = self.client()
        if not c:
            return False
        try:
            return bool(c.ping())
        except Exception as e:
            warning(f"⚠️ Elasticsearch ping failed: {e}")
            return False

    def index_name(self) -> str:
        return self._index

    def ensure_index(self) -> bool:
        """
        Ensure the index exists with settings/mappings for:
        - full-text fields (analyzed)
        - keyword fields
        - edge_ngram for autocomplete on name/vendor/library
        """
        c = self.client()
        if not c:
            return False
        try:
            if c.indices.exists(index=self._index):
                debug(f"ℹ️ ES index already exists: {self._index}")
                return True
        except Exception:
            # ES 8 returns bool; older clients may raise NotFoundError
            pass

        settings = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "analysis": {
                    "filter": {
                        "edge_ngram_filter": {
                            "type": "edge_ngram",
                            "min_gram": 1,
                            "max_gram": 20,
                        }
                    },
                    "analyzer": {
                        "autocomplete_analyzer": {
                            "tokenizer": "standard",
                            "filter": ["lowercase", "edge_ngram_filter"],
                        },
                        "autocomplete_search_analyzer": {
                            "tokenizer": "standard",
                            "filter": ["lowercase"],
                        },
                    },
                },
            },
            "mappings": {
                "properties": {
                    "path": {"type": "keyword"},
                    "name": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "raw": {"type": "keyword"},
                            "ac": {
                                "type": "text",
                                "analyzer": "autocomplete_analyzer",
                                "search_analyzer": "autocomplete_search_analyzer",
                            },
                        },
                    },
                    "vendor": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "raw": {"type": "keyword"},
                            "ac": {
                                "type": "text",
                                "analyzer": "autocomplete_analyzer",
                                "search_analyzer": "autocomplete_search_analyzer",
                            },
                        },
                    },
                    "library": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "raw": {"type": "keyword"},
                            "ac": {
                                "type": "text",
                                "analyzer": "autocomplete_analyzer",
                                "search_analyzer": "autocomplete_search_analyzer",
                            },
                        },
                    },
                    "instrument": {"type": "keyword"},  # stored as array of keywords
                    "genre": {"type": "keyword"},  # stored as array of keywords
                    "tags": {"type": "keyword"},  # stored as array or keywords
                    "file_type": {"type": "keyword"},
                    "extension": {"type": "keyword"},
                    "parent_folder": {"type": "keyword"},
                    "bpm": {"type": "keyword"},
                    "key": {"type": "keyword"},
                    "modified_time": {"type": "date", "format": "epoch_second"},
                    "created_at": {"type": "date", "format": "epoch_second"},
                    # Aggregated catch-all for boosting recall
                    "fulltext": {"type": "text", "analyzer": "standard"},
                }
            },
        }

        try:
            c.indices.create(index=self._index, **settings)
            info(f"✅ Created ES index: {self._index}")
            return True
        except Exception as e:
            error(f"❌ Failed to create ES index {self._index}: {e}")
            return False

    def bulk(self, actions: List[Dict[str, Any]]) -> bool:
        c = self.client()
        if not c or bulk is None:
            return False
        try:
            success, _ = bulk(c, actions, index=self._index, refresh=False)
            debug(f"📦 ES bulk indexed: {success} docs")
            return True
        except Exception as e:
            error(f"❌ ES bulk failed: {e}")
            return False

    def index_doc(self, doc_id: str, source: Dict[str, Any]) -> bool:
        c = self.client()
        if not c:
            return False
        try:
            c.index(index=self._index, id=doc_id, document=source, refresh=False)
            return True
        except Exception as e:
            error(f"❌ ES index failed for {doc_id}: {e}")
            return False

    def delete_doc(self, doc_id: str) -> bool:
        c = self.client()
        if not c:
            return False
        try:
            c.delete(index=self._index, id=doc_id, refresh=False)
            return True
        except NotFoundError:
            return True
        except Exception as e:
            error(f"❌ ES delete failed for {doc_id}: {e}")
            return False

    def search(self, body: Dict[str, Any], size: int = 50) -> Dict[str, Any]:
        c = self.client()
        if not c:
            return {"hits": {"hits": []}}
        try:
            return c.search(
                index=self._index,
                query=body.get("query"),
                size=size,
                sort=body.get("sort"),
                _source=True,
            )
        except Exception as e:
            error(f"❌ ES search failed: {e}")
            return {"hits": {"hits": []}}

    def suggest(self, body: Dict[str, Any]) -> Dict[str, Any]:
        c = self.client()
        if not c:
            return {}
        try:
            return c.search(index=self._index, **body)
        except Exception as e:
            error(f"❌ ES suggest failed: {e}")
            return {}
