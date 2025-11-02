#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Search Model - MVC Model for search functionality
Extracted from core_search.py
"""

import os
import re
import sys
import sqlite3
import appdirs
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Import settings with error handling
try:
    # Add parent directory to path to find settings package
    parent_dir = os.path.dirname(os.path.dirname(__file__))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    from settings.core_settings import (
        MAX_RESULTS_PER_LIBRARY,
        MAX_TOTAL_RESULTS,
        GENRE_KEYWORDS,
        ELASTICSEARCH_ENABLED,
        ELASTICSEARCH_MAX_RESULTS,
    )

    # Try to import logger, but don't fail if it's not initialized yet
    try:
        from utils.logger import info, debug, warning, error, critical

        info("✅ Successfully imported settings from settings.core_settings")
    except RuntimeError:
        # Logger not initialized yet, use print instead
        info("✅ Successfully imported settings from settings.core_settings")

except ImportError as e:
    # Try to use logger, but fall back to print if not available
    try:
        from utils.logger import critical, error

        critical("❌ CRITICAL ERROR: Cannot import settings.core_settings")
        error("🔍 Error details: {}".format(e))
        error("🔍 Current working directory: {}".format(os.getcwd()))
        error("🔍 File location: {}".format(__file__))
        error(
            "🔍 Expected settings file: {}".format(
                os.path.join(parent_dir, "settings", "core_settings.py")
            )
        )
        error("")
        error("❌ Application cannot start without settings.core_settings")
        error("❌ Please ensure settings/core_settings.py exists and is accessible")
    except RuntimeError:
        error("❌ CRITICAL ERROR: Cannot import settings.core_settings")
        error("🔍 Error details: {}".format(e))
        error("🔍 Current working directory: {}".format(os.getcwd()))
        error("🔍 File location: {}".format(__file__))
        error(
            "🔍 Expected settings file: {}".format(
                os.path.join(parent_dir, "settings", "core_settings.py")
            )
        )
        error("")
        critical("❌ Application cannot start without settings.core_settings")
        critical("❌ Please ensure settings/core_settings.py exists and is accessible")
    raise ImportError("Failed to import settings.core_settings: {}".format(e))


class SearchModel:
    """Model for search functionality - handles all search logic"""

    def __init__(self, user_settings_model=None):
        self.last_results = []
        self.search_folders = []
        # Use user settings if provided, otherwise fall back to defaults
        if user_settings_model:
            self.selected_extensions = user_settings_model.get_setting("extensions", [])
            self.user_settings = user_settings_model
        else:
            # Fallback to core settings defaults
            from settings.core_settings import DEFAULT_EXTENSIONS

            self.selected_extensions = DEFAULT_EXTENSIONS
            self.user_settings = None

        # Database path for index search - use app data folder
        self.db_path = self._get_database_path()

        # ES client initialization
        self._es_client = None
        self._es_enabled = bool(ELASTICSEARCH_ENABLED)
        self._init_es_if_available()

        # FTS5 initialization
        self._fts5_available = False
        self._init_fts5_if_available()

        # Search engine priority: FTS5 -> ES -> Native SQLite
        self.search_engine_priority = self._get_search_engine_priority()

    def _get_search_engine_priority(self):
        """Determine search engine priority based on configuration"""
        priority = []

        if getattr(self, "_fts5_available", False) and getattr(
            __import__("settings.core_settings"), "FTS5_SQLITE_ENABLED", False
        ):
            priority.append("fts5")

        if self._es_enabled:
            priority.append("elasticsearch")

        # Native SQLite is always available as fallback
        priority.append("native_sqlite")

        debug(f"🔍 Search engine priority: {priority}")
        return priority

    def _init_fts5_if_available(self):
        """Initialize FTS5 virtual tables if available and enabled"""
        try:
            # Check if FTS5 is available in SQLite
            conn = sqlite3.connect(":memory:")
            cursor = conn.cursor()
            cursor.execute("SELECT fts5(?);", ("test",))
            conn.close()

            # FTS5 is available
            self._fts5_available = True
            info("✅ FTS5 is available in SQLite")

            # Create FTS5 virtual tables if they don't exist
            self._create_fts5_tables()

        except sqlite3.OperationalError:
            warning(
                "⚠️ FTS5 not available in SQLite - falling back to other search engines"
            )
            self._fts5_available = False
        except Exception as e:
            warning(f"⚠️ Error checking FTS5 availability: {e}")
            self._fts5_available = False

    def _create_fts5_tables(self):
        """Create FTS5 virtual tables for full-text search"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check if FTS5 table already exists
            cursor.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='files_fts'
            """
            )

            if not cursor.fetchone():
                info("🔧 Creating FTS5 virtual table...")

                # Create FTS5 virtual table with the same columns as main table
                cursor.execute(
                    """
                    CREATE VIRTUAL TABLE files_fts USING fts5(
                        path,
                        name,
                        vendor,
                        library,
                        instrument,
                        genre,
                        tags,
                        keywords,
                        file_type,
                        tokenize = 'porter unicode61'
                    )
                """
                )

                # Populate FTS5 table with existing data
                cursor.execute(
                    """
                    INSERT INTO files_fts 
                    SELECT path, name, vendor, library, instrument, genre, tags, keywords, file_type
                    FROM files
                """
                )

                info("✅ FTS5 virtual table created and populated")

            conn.commit()
            conn.close()

        except Exception as e:
            error(f"❌ Error creating FTS5 tables: {e}")

    def _init_es_if_available(self):
        if not self._es_enabled:
            return
        try:
            from utils.search.es_client import ESClient

            es = ESClient()
            if es.is_enabled() and es.ping():
                es.ensure_index()
                self._es_client = es
                info(
                    "🔌 Elasticsearch is available; SearchModel will use ES for search"
                )
            else:
                warning("⚠️ Elasticsearch not reachable; falling back to SQLite search")
                self._es_enabled = False
                self._es_client = None
        except Exception as e:
            warning(f"⚠️ Elasticsearch init failed: {e}")
            self._es_enabled = False
            self._es_client = None

    def _get_database_path(self) -> str:
        """Get the database path using the same method as other settings files"""
        # Use the same app identity as user_settings_model.py
        from settings.core_settings import APP_NAME, APP_AUTHOR

        # Use appdirs to get the config directory (same as user_settings_model.py)
        config_dir = appdirs.user_config_dir(APP_NAME, APP_AUTHOR)
        os.makedirs(config_dir, exist_ok=True)

        # Return the full path to the database file in the config directory
        return os.path.join(config_dir, "patchio_index.db")

    def setup_default_folders(self) -> None:
        """Setup default folders from user settings"""
        try:
            if self.user_settings:
                # Use user settings for search folders
                search_folders = self.user_settings.get_setting("search_folders", [])
                existing_folders = [f for f in search_folders if os.path.exists(f)]
                self.set_search_folders(existing_folders)
                info("📁 User search folders: {}".format(existing_folders))
            else:
                # Fallback to core settings
                from settings.core_settings import DEFAULT_SEARCH_FOLDERS

                existing_folders = [
                    f for f in DEFAULT_SEARCH_FOLDERS if os.path.exists(f)
                ]
                self.set_search_folders(existing_folders)
                info("📁 Default search folders: {}".format(existing_folders))

            # Test if we can find any files at all
            try:
                self.test_search_setup()
            except Exception as e:
                warning("⚠️ Test search setup failed: {}".format(e))
                warning("⚠️ Continuing without test search setup")

        except Exception as e:
            warning("⚠️ Setup default folders failed: {}".format(e))
            self.search_folders = []
            warning("⚠️ Using empty search folders as fallback")

    def set_search_folders(self, folders: List[str]) -> None:
        """Set the folders to search in"""
        self.search_folders = [Path(f) for f in folders if os.path.exists(f)]
        debug(f"🔧 Search folders configured: {[str(f) for f in self.search_folders]}")

    def test_search_setup(self) -> None:
        """Test if search setup is working by counting files"""
        try:
            debug("🧪 Testing search setup...")
            total_files = 0

            for folder in self.search_folders:
                folder_files = 0
                try:
                    for item in folder.iterdir():
                        if item.is_file():
                            folder_files += 1
                            total_files += 1
                        if folder_files >= 5:  # Just sample a few files
                            break
                    debug("  📂 {}: Found {} files".format(folder, folder_files))
                except (PermissionError, OSError) as e:
                    warning("  ⚠️ Cannot access {}: {}".format(folder, e))

            debug(
                "🧪 Test complete: Found {} files across all folders".format(
                    total_files
                )
            )
            if total_files == 0:
                warning("⚠️ WARNING: No files found in any search folder!")

        except Exception as e:
            warning("⚠️ Test search setup failed: {}".format(e))
            warning("⚠️ Continuing without test results")

    # --------------------
    # Public search APIs
    # --------------------

    def simple_search(self, query: str) -> List[Dict[str, Any]]:
        """Perform simple filename search"""
        info(f"📁 Simple Search: {query}")
        debug(f"🔍 Searching in folders: {[str(f) for f in self.search_folders]}")

        if not self.search_folders:
            warning("⚠️ No search folders configured!")
            return []

        if not query.strip():
            warning("⚠️ Empty search query!")
            return []

        # Parse search terms exactly like patchio.py
        try:
            simple_raw = query.strip().lower()
            or_terms, or_quoted = self._parse_terms(simple_raw)
            debug(f"🔍 Parsed OR terms: {list(zip(or_terms, or_quoted))}")
        except Exception as e:
            error(f"⚠️ Error parsing search terms: {e}")
            return []

        if not or_terms:
            warning("⚠️ No valid search terms found!")
            return []

        results = []
        excluded_folders = []  # Using dummy empty list as requested

        for folder in self.search_folders:
            if not folder.exists():
                warning(f"⚠️ Folder doesn't exist: {folder}")
                continue
            debug(f"📂 Searching in: {folder}")
            try:
                for file_path in self._recursive_scan(
                    str(folder), self.selected_extensions, excluded_folders
                ):
                    full_path = file_path.lower()

                    # Classic search mode logic: OR matching (exact from patchio.py line 2321)
                    if any(
                        self._matches_term(term, full_path, quoted)
                        for term, quoted in zip(or_terms, or_quoted)
                    ):
                        results.append(
                            {
                                "name": os.path.basename(file_path),
                                "path": file_path,
                                "type": f"Simple Match in {folder.name}",
                                "is_audio": True,  # All results are audio files due to extension filtering
                            }
                        )
                        debug(f"  ✅ Found match: {os.path.basename(file_path)}")
            except Exception as e:
                warning(f"  ⚠️ Cannot search in {folder}: {e}")
                continue

        info(f"📊 Simple search found {len(results)} matching files")
        if len(results) == 0:
            info(f"💡 No files found matching '{query}'. Try different search terms.")
        return results

    def database_search(self, query: str) -> List[Dict[str, Any]]:
        """
        Enhanced database search with configurable engine priority:
        FTS5 -> Elasticsearch -> Native SQLite
        """
        # Try search engines in priority order
        for engine in self.search_engine_priority:
            try:
                if engine == "fts5" and self._fts5_available:
                    results = self.fts5_sqlite_search(query)
                    if results:
                        info(f"🔍 FTS5 search found {len(results)} results")
                        return results

                elif engine == "elasticsearch" and self._es_client:
                    results = self.elasticsearch_search(query)
                    if results:
                        info(f"🔍 Elasticsearch found {len(results)} results")
                        return results

                elif engine == "native_sqlite":
                    results = self.native_sqlite_search(query)
                    if results:
                        info(f"🔍 Native SQLite found {len(results)} results")
                        return results

            except Exception as e:
                warning(f"⚠️ {engine} search failed: {e}")
                continue

        warning("⚠️ All search engines failed")
        return []

    # --------------------
    # fts5_sqlite search
    # --------------------
    def fts5_sqlite_search(self, query: str) -> List[Dict[str, Any]]:
        """Perform high-performance search using SQLite FTS5"""
        info(f"🚀 FTS5 Search: {query}")

        if not query or not query.strip():
            warning("⚠️ Empty search query!")
            return []

        if not self._fts5_available:
            warning("⚠️ FTS5 not available")
            return []

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Parse query for FTS5 syntax
            fts5_query = self._build_fts5_query(query)

            # build query
            sql_query = """
                SELECT 
                    f.path, f.name, f.vendor, f.library, f.instrument, 
                    f.genre, f.tags, f.keywords, f.file_type
                FROM files_fts
                JOIN files f ON files_fts.path = f.path
                WHERE files_fts MATCH ?
                ORDER BY f.name ASC
                LIMIT ?
            """

            limit = getattr(
                __import__("settings.core_settings"), "FTS5_MAX_RESULTS", 1000
            )

            debug(f"🔍 Executing FTS5 query: {fts5_query}")
            cursor.execute(sql_query, (fts5_query, limit))
            rows = cursor.fetchall()

            results = []
            for row in rows:
                results.append(
                    {
                        "path": row[0],
                        "name": row[1],
                        "vendor": row[2] or "Unknown Vendor",
                        "library": row[3] or "Unknown Library",
                        "instrument": row[4] or "",
                        "genre": row[5] or "",
                        "tags": row[6] or "",
                        "keywords": row[7] or "",
                        "file_type": row[8] or "File",
                        "type": "FTS5 Match",
                        "is_audio": True,
                    }
                )

            conn.close()
            info(f"📊 FTS5 search found {len(results)} matching files")
            return results

        except Exception as e:
            error(f"❌ FTS5 search error: {e}")
            return []

    def _build_fts5_query(self, query: str) -> str:
        """Convert user query to FTS5 syntax with advanced features"""
        # Parse the bubble query to understand structure
        or_terms, and_terms, not_terms, or_quoted, and_quoted, not_quoted = (
            self._parse_bubble_query(query.strip())
        )

        fts5_parts = []

        # Handle OR terms (default)
        if or_terms:
            or_query = " OR ".join(
                f'"{term}"' if quoted else term
                for term, quoted in zip(or_terms, or_quoted)
            )
            fts5_parts.append(f"({or_query})")

        # Handle AND terms (must appear)
        if and_terms:
            and_query = " ".join(
                f'"{term}"' if quoted else f"+{term}"
                for term, quoted in zip(and_terms, and_quoted)
            )
            fts5_parts.append(f"({and_query})")

        # Handle NOT terms (exclude)
        if not_terms:
            not_query = " ".join(
                f'"{term}"' if quoted else f"-{term}"
                for term, quoted in zip(not_terms, not_quoted)
            )
            fts5_parts.append(f"({not_query})")

        # Combine all parts
        if fts5_parts:
            final_query = " ".join(fts5_parts)
        else:
            # Fallback to simple query
            final_query = query

        debug(f"🔍 FTS5 query transformation: '{query}' -> '{final_query}'")
        return final_query

    def native_sqlite_search(self, query: str) -> List[Dict[str, Any]]:
        """Native SQLite search (existing functionality, now as separate method)"""
        # This is essentially the existing sqlite_database_search method
        # renamed and refactored for clarity
        info(f"🗄️ Native SQLite Search: {query}")
        # ... existing sqlite_database_search implementation ...
        return self.sqlite_database_search(query)

    # --------------------
    # Elasticsearch search
    # --------------------
    def _build_es_bool_query(self, query_text: str) -> Dict[str, Any]:
        """
        Convert the bubble query into ES bool query format.
        Fixed to handle partial matches and standard analyzer properly.
        """
        or_terms, and_terms, not_terms, or_quoted, and_quoted, not_quoted = (
            self._parse_bubble_query(query_text.strip())
        )

        def term_to_query(term: str, quoted: bool):
            # For quoted: phrase match; else: multi_match with fuzziness
            if quoted:
                return {
                    "multi_match": {
                        "query": term,
                        "type": "phrase",
                        "fields": [
                            "name^5",
                            "library^4",
                            "vendor^4",
                            "fulltext^2",
                            "path",
                            "genre",
                            "instrument",
                            "tags",
                        ],
                        "slop": 2,
                    }
                }
            else:
                # For unquoted terms: use multiple approaches for better matching
                # 1. Standard multi_match with cross_fields for better token matching
                standard_match = {
                    "multi_match": {
                        "query": term,
                        "type": "cross_fields",  # Better for matching across multiple fields
                        "fields": [
                            "name^5",
                            "name.ac^3",  # Include autocomplete field
                            "library^4",
                            "vendor^4",
                            "fulltext^2",
                            "path",
                            "genre",
                            "instrument",
                            "tags",
                        ],
                        "operator": "or",  # Match any term in multi-term queries
                    }
                }

                # 2. Wildcard query for partial matches in key fields
                wildcard_queries = [
                    {"wildcard": {"name": f"*{term}*"}},
                    {"wildcard": {"path": f"*{term}*"}},
                    {"wildcard": {"vendor": f"*{term}*"}},
                    {"wildcard": {"library": f"*{term}*"}},
                ]

                # 3. Prefix query for beginning-of-word matches
                prefix_queries = [
                    {"prefix": {"name.ac": term.lower()}},
                ]

                # Combine all approaches - any of them matching is sufficient
            return {
                "bool": {
                    "should": [standard_match, *wildcard_queries, *prefix_queries],
                    "minimum_should_match": 1,
                }
            }

        must = []
        should = []
        must_not = []

        # Process AND terms (must match all)
        for term, quoted in zip(and_terms, and_quoted):
            must.append(term_to_query(term, quoted))

        # Process OR terms (should match any)
        for term, quoted in zip(or_terms, or_quoted):
            should.append(term_to_query(term, quoted))

        # Process NOT terms (must not match any)
        for term, quoted in zip(not_terms, not_quoted):
            must_not.append(term_to_query(term, quoted))

        # Build the final bool query
        bool_query = {}

        if must:
            bool_query["must"] = must
        if should:
            bool_query["should"] = should
        if must_not:
            bool_query["must_not"] = must_not

        # If we only have OR terms, we need at least one to match
        if should and not must:
            bool_query["minimum_should_match"] = 1

        return {"bool": bool_query}

    def elasticsearch_search(self, query_text: str) -> List[Dict[str, Any]]:
        """
        Perform ES search and map results to the format expected by controller.
        """
        if not query_text or not query_text.strip():
            warning("⚠️ Empty search query!")
            return []

        if not self._es_client:
            return []

        debug(f"🧠 ES building query for: {query_text}")
        q = self._build_es_bool_query(query_text)

        size = min(ELASTICSEARCH_MAX_RESULTS, MAX_TOTAL_RESULTS)
        sort = [{"_score": "desc"}, {"name.raw": "asc"}]  # Stable within score
        res = self._es_client.search({"query": q, "sort": sort}, size=size)
        debug(f"🧠 ES query result: {res}")

        hits = res.get("hits", {}).get("hits", [])
        results = []
        for h in hits:
            src = h.get("_source", {})
            results.append(
                {
                    "id": src.get("path", ""),
                    "name": src.get("name", "")
                    or os.path.basename(src.get("path", "")),
                    "path": src.get("path", ""),
                    "vendor": src.get("vendor", "Unknown Vendor") or "Unknown Vendor",
                    "library": src.get("library", "Unknown Library")
                    or "Unknown Library",
                    "instrument": ", ".join(src.get("instrument", [])),
                    "genre": ", ".join(src.get("genre", [])),
                    "tags": " • ".join(src.get("tags", [])),
                    "file_type": src.get("file_type", "File") or "File",
                    "type": "Elasticsearch Match",
                    "is_audio": True,
                }
            )

        info(f"📊 ES search found {len(results)} matching files")
        return results

    # --------------------
    # SQLite fallback search (unchanged logic)
    # --------------------
    def sqlite_database_search(self, query: str) -> List[Dict[str, Any]]:
        info(f"🗄️ Database Search (SQLite): {query}")

        if not os.path.exists(self.db_path):
            warning(f"⚠️ Database not found: {self.db_path}")
            return []

        if not query.strip():
            warning("⚠️ Empty search query!")
            return []

        # Parse search terms
        try:
            or_terms, and_terms, not_terms, or_quoted, and_quoted, not_quoted = (
                self._parse_bubble_query(query.strip())
            )
            debug(f"🔍 Parsed OR terms: {list(zip(or_terms, or_quoted))}")
            debug(f"🔍 Parsed AND terms: {list(zip(and_terms, and_quoted))}")
            debug(f"🔍 Parsed NOT terms: {list(zip(not_terms, not_quoted))}")
        except Exception as e:
            error(f"⚠️ Error parsing search terms: {e}")
            return []

        if not or_terms and not and_terms:
            warning("⚠️ No valid search terms found!")
            return []

        results = []

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Build SQL query for searching across all columns
            search_conditions = []
            params = []

            # OR conditions
            if or_terms:
                or_conditions = []
                for term, quoted in zip(or_terms, or_quoted):
                    or_conditions.append(
                        """
                        (LOWER(path) LIKE ? OR 
                        LOWER(name) LIKE ? OR 
                        LOWER(vendor) LIKE ? OR 
                        LOWER(library) LIKE ? OR 
                        LOWER(instrument) LIKE ? OR 
                        LOWER(genre) LIKE ? OR 
                        LOWER(tags) LIKE ?)
                        """
                    )
                    search_param = f"%{term.lower()}%"
                    params.extend([search_param] * 7)
                if or_conditions:
                    search_conditions.append(f"({' OR '.join(or_conditions)})")

            # AND conditions
            if and_terms:
                and_conditions = []
                for term, quoted in zip(and_terms, and_quoted):
                    and_conditions.append(
                        """
                        (LOWER(path) LIKE ? OR 
                        LOWER(name) LIKE ? OR 
                        LOWER(vendor) LIKE ? OR 
                        LOWER(library) LIKE ? OR 
                        LOWER(instrument) LIKE ? OR 
                        LOWER(genre) LIKE ? OR 
                        LOWER(tags) LIKE ?)
                        """
                    )
                    search_param = f"%{term.lower()}%"
                    params.extend([search_param] * 7)
                if and_conditions:
                    search_conditions.append(f"({' AND '.join(and_conditions)})")

            # NOT conditions
            if not_terms:
                not_conditions = []
                for term, quoted in zip(not_terms, not_quoted):
                    not_conditions.append(
                        """
                        NOT (LOWER(path) LIKE ? OR 
                            LOWER(name) LIKE ? OR 
                            LOWER(vendor) LIKE ? OR 
                            LOWER(library) LIKE ? OR 
                            LOWER(instrument) LIKE ? OR 
                            LOWER(genre) LIKE ? OR 
                            LOWER(tags) LIKE ?)
                        """
                    )
                    search_param = f"%{term.lower()}%"
                    params.extend([search_param] * 7)
                if not_conditions:
                    search_conditions.append(f"({' AND '.join(not_conditions)})")

            # Build final query
            if search_conditions:
                where_clause = " AND ".join(search_conditions)
                sql_query = f"""
                    SELECT id, path, name, vendor, library, instrument, genre, tags, file_type
                    FROM files 
                    WHERE {where_clause}
                    ORDER BY name
                    LIMIT ?
                """
            else:
                sql_query = """
                    SELECT id, path, name, vendor, library, instrument, genre, tags, file_type
                    FROM files 
                    ORDER BY name
                    LIMIT ?
                """

            # Limit to keep UI responsive
            params.append(min(MAX_TOTAL_RESULTS, 1000))
            debug(f"🔍 Executing SQL: {sql_query}")
            debug(f"🔍 Parameters: {params}")

            cursor.execute(sql_query, params)
            rows = cursor.fetchall()

            for row in rows:
                (
                    file_id,
                    path,
                    name,
                    vendor,
                    library,
                    instrument,
                    genre,
                    tags,
                    file_type,
                ) = row

                file_name = os.path.basename(path) if path else name

                results.append(
                    {
                        "id": file_id,
                        "name": file_name,
                        "path": path or "",
                        "vendor": vendor or "Unknown Vendor",
                        "library": library or "Unknown Library",
                        "instrument": instrument or "",
                        "genre": genre or "",
                        "tags": tags or "",
                        "file_type": file_type or "File",
                        "type": "Database Match",
                        "is_audio": True,
                    }
                )

            conn.close()

        except Exception as e:
            error(f"⚠️ Database search error: {e}")
            return []

        info(f"📊 Database search found {len(results)} matching files")

        if len(results) == 0:
            info(
                f"💡 No files found matching '{query}' in database. Try different search terms."
            )

        return results

    def ai_search(self, query: str) -> List[Dict[str, Any]]:
        """AI-powered search (placeholder for now)"""
        info(f"🤖 AI Search: {query}")

        # TODO: Later integrate with patchio.py AI functions
        # For now, return mock results to test UI
        return [
            {
                "name": f"AI: Epic Drums for '{query}'",
                "path": "/path/to/epic_drums.wav",
                "type": "AI Result",
            },
            {
                "name": f"AI: Cinematic Strings matching '{query}'",
                "path": "/path/to/strings.wav",
                "type": "AI Result",
            },
            {
                "name": f"AI: Dark Bass inspired by '{query}'",
                "path": "/path/to/bass.wav",
                "type": "AI Result",
            },
        ]

    def advanced_search(self, query: str) -> List[Dict[str, Any]]:
        """Advanced search with filters"""
        info(f"⚙️ Advanced Search: {query}")

        # TODO: Later integrate with patchio.py advanced search
        # For now, return mock results to test UI
        return [
            {
                "name": f"Advanced: Complex Pattern for '{query}'",
                "path": "/path/to/pattern.wav",
                "type": "Advanced Result",
            },
            {
                "name": f"Advanced: Filtered Sound matching '{query}'",
                "path": "/path/to/filtered.wav",
                "type": "Advanced Result",
            },
        ]

    def get_matched_keywords(self, file_path: str, search_terms: str) -> List[str]:
        """Get the search terms that matched this specific file"""
        if not search_terms:
            return []

        # Parse the search terms with operators
        or_terms, and_terms, not_terms, or_quoted, and_quoted, not_quoted = (
            self._parse_bubble_query(search_terms)
        )
        matched_terms = []

        # Get the file name and path for matching
        file_name = os.path.basename(file_path).lower()
        file_path_lower = file_path.lower()

        # Check which OR terms matched this file
        for term, quoted in zip(or_terms, or_quoted):
            if self._matches_term(term, file_name, quoted) or self._matches_term(
                term, file_path_lower, quoted
            ):
                matched_terms.append(term.lower())

        # Check which AND terms matched this file
        for term, quoted in zip(and_terms, and_quoted):
            if self._matches_term(term, file_name, quoted) or self._matches_term(
                term, file_path_lower, quoted
            ):
                matched_terms.append(term.lower())

        # Note: NOT terms are not included in matched keywords since they exclude files

        return matched_terms

    def get_genre_keywords(self, file_path: str) -> List[str]:
        """Extract genre keywords from file path using settings"""
        file_name = os.path.basename(file_path).lower()
        path_lower = file_path.lower()
        combined_text = (file_name + " " + path_lower).lower()

        genre_keywords = []

        # Use settings for genre keywords
        for category, keywords in GENRE_KEYWORDS.items():
            if any(word in combined_text for word in keywords):
                genre_keywords.append(category)

        return genre_keywords

    def _parse_terms(self, input_str: str) -> Tuple[List[str], List[bool]]:
        """
        Parse the input string into terms and detect which were quoted.
        Returns a tuple (terms, quoted_flags)
        """
        pattern = r'"([^"]+)"|(\S+)'
        matches = re.findall(pattern, input_str)
        terms = []
        quoted_flags = []
        for quoted, unquoted in matches:
            if quoted:
                terms.append(quoted)
                quoted_flags.append(True)
            else:
                terms.append(unquoted)
                quoted_flags.append(False)
        return terms, quoted_flags

    def _parse_bubble_query(
        self, input_str: str
    ) -> Tuple[List[str], List[str], List[str], List[bool], List[bool], List[bool]]:
        """
        Parse bubble query text into OR/AND/NOT terms with quoted flags.
        Returns (or_terms, and_terms, not_terms, or_quoted, and_quoted, not_quoted)
        """
        or_terms = []
        and_terms = []
        not_terms = []
        or_quoted = []
        and_quoted = []
        not_quoted = []

        # Split the query into parts (bubbles and operators)
        pattern = r'"([^"]+)"|(\S+)'
        matches = re.findall(pattern, input_str)

        current_operator = "OR"  # Default operator
        current_terms = or_terms
        current_quoted = or_quoted

        for quoted, unquoted in matches:
            term = quoted if quoted else unquoted
            is_quoted = bool(quoted)

            # Check if this is an operator
            if term.upper() in ["OR", "AND", "NOT"]:
                current_operator = term.upper()
                # Switch to appropriate list based on operator
                if current_operator == "OR":
                    current_terms = or_terms
                    current_quoted = or_quoted
                elif current_operator == "AND":
                    current_terms = and_terms
                    current_quoted = and_quoted
                elif current_operator == "NOT":
                    current_terms = not_terms
                    current_quoted = not_quoted
            else:
                # This is a search term, add it to current operator's list
                current_terms.append(term)
                current_quoted.append(is_quoted)

        return or_terms, and_terms, not_terms, or_quoted, and_quoted, not_quoted

    def _matches_term(self, term: str, text: str, quoted: bool) -> bool:
        """
        Check if term matches text, handling quoted vs unquoted matching
        """
        term = term.lower()
        text = text.lower()

        if quoted:
            if " " in term:
                return term in text
            else:
                # Match whole word or surrounded by non-alphanumeric characters
                pattern = (
                    r"(?:^|[^a-zA-Z0-9])" + re.escape(term) + r"(?:[^a-zA-Z0-9]|$)"
                )
                return re.search(pattern, text) is not None
        else:
            return term in text

    def _recursive_scan(
        self,
        folder: str,
        selected_extensions: List[str],
        excluded_folders: List[str] = None,
    ) -> List[str]:
        """
        Recursively scan folder for files with selected extensions
        """
        if excluded_folders is None:
            excluded_folders = []

        selected_extensions_lower = tuple(ext.lower() for ext in selected_extensions)

        try:
            for entry in os.scandir(folder):
                entry_path = os.path.normcase(os.path.abspath(entry.path))

                if entry.is_dir(follow_symlinks=False):
                    # Skip excluded folders
                    if any(
                        entry_path == ex or entry_path.startswith(ex + os.sep)
                        for ex in excluded_folders
                    ):
                        continue

                    yield from self._recursive_scan(
                        entry.path, selected_extensions, excluded_folders
                    )

                elif entry.is_file(follow_symlinks=False):
                    if entry.name.lower().endswith(selected_extensions_lower):
                        yield entry.path

        except PermissionError as e:
            error(f"PermissionError accessing '{folder}': {e}")
        except Exception as e:
            error(f"Unexpected error accessing '{folder}': {e}")
