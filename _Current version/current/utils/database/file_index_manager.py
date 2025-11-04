#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File Index Manager for PatchIO handle_file_event
Comprehensive system for keeping file index in sync with filesystem
Handles startup sync, real-time monitoring, and efficient change detection 1270
"""

import os
import sys
import sqlite3
import time
import hashlib
import threading
import re
from pathlib import Path
from typing import Set, Dict, List, Optional, Tuple, Callable
from collections import defaultdict

# Add parent directory to path for imports
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from utils.logger import info, warning, error, debug
from settings.core_settings import DEFAULT_EXTENSIONS
from utils.search.es_sync import ESSync


class FileIndexManager:
    """Comprehensive file index management system"""

    def __init__(self, db_path: str, indexed_folders: Set[str]):
        self.db_path = db_path
        self.indexed_folders = indexed_folders
        self.supported_extensions = set(DEFAULT_EXTENSIONS)
        self.file_watcher = None
        self.is_monitoring = False
        self._lock = threading.Lock()

        # ES sync (single source of truth = SQLite)
        self.es_sync = ESSync(self.db_path)

        self._compiled_extensions = self._compile_extension_patterns()
        self._system_file_patterns = self._compile_system_patterns()
        self.batch_size = 1000
        self.progress_callback = None

        # Statistics
        self.stats = {
            "files_scanned": 0,
            "files_added": 0,
            "files_removed": 0,
            "files_updated": 0,
            "files_renamed": 0,
            "sync_time": 0.0,
        }

        # Initialize database
        self._initialize_database()

        # FTS5 maintenance
        self._ensure_fts5_tables()

        info(f"📁 File Index Manager initialized for {len(indexed_folders)} folders")
        info(
            f"🚀 Professional optimizations enabled: {len(self._compiled_extensions)} extensions, batch size {self.batch_size}"
        )

    def _apply_sqlite_tuning(self, cursor, mode: str = "safe"):
        # Always-on
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.execute("PRAGMA mmap_size=268435456")
        cursor.execute("PRAGMA cache_size=-200000")  # ~200MB
        # You likely don’t use FKs on the index DB
        cursor.execute("PRAGMA foreign_keys=OFF")

        if mode == "safe":
            cursor.execute("PRAGMA synchronous=NORMAL")
            # Avoid EXCLUSIVE so other connections (readers) can work
            cursor.execute("PRAGMA locking_mode=NORMAL")
        elif mode == "turbo":
            cursor.execute("PRAGMA synchronous=OFF")
            cursor.execute("PRAGMA locking_mode=EXCLUSIVE")
            cursor.execute("PRAGMA cache_size=-500000")  # ~500MB
        else:
            raise ValueError("mode must be 'safe' or 'turbo'")

    def _ensure_fts5_tables(self):
        """Ensure FTS5 virtual tables exist and are maintained"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check if FTS5 extension is available
            cursor.execute("PRAGMA compile_options;")
            compile_options = [row[0] for row in cursor.fetchall()]

            if "ENABLE_FTS5" not in compile_options:
                warning("⚠️ FTS5 not compiled in SQLite - FTS5 search will be disabled")
                conn.close()
                return

            # Create FTS5 table if it doesn't exist
            cursor.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='files_fts'
            """
            )

            if not cursor.fetchone():
                info("🔧 Creating FTS5 virtual table for full-text search...")
                cursor.execute(
                    """
                    CREATE VIRTUAL TABLE files_fts USING fts5(
                        path UNINDEXED,
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

                # Populate initial data
                cursor.execute(
                    """
                    INSERT INTO files_fts 
                    SELECT path, name, vendor, library, instrument, genre, tags, keywords, file_type
                    FROM files
                """
                )

                info("✅ FTS5 virtual table created")

            conn.commit()
            conn.close()

        except Exception as e:
            warning(f"⚠️ FTS5 setup failed: {e}")

    def _initialize_database(self):
        """Initialize database with required tables and indexes"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            self._apply_sqlite_tuning(cursor, mode="safe")
            # Create files table with comprehensive schema
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    extension TEXT,
                    file_type TEXT,
                    parent_folder TEXT,
                    modified_time REAL,
                    file_size INTEGER,
                    file_hash TEXT,
                    bpm TEXT,
                    key TEXT,
                    vendor TEXT,
                    library TEXT,
                    keywords TEXT,
                    tags TEXT,
                    instrument TEXT,
                    genre TEXT,
                    mood TEXT,
                    format TEXT,
                    created_at REAL DEFAULT (strftime('%s', 'now')),
                    updated_at REAL DEFAULT (strftime('%s', 'now'))
                )
            """
            )

            # Create file_hashes table for efficient change detection
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS file_hashes (
                    path TEXT PRIMARY KEY,
                    file_hash TEXT NOT NULL,
                    modified_time REAL NOT NULL,
                    file_size INTEGER NOT NULL
                )
            """
            )

            # Create last_sync table for intelligent sync
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS last_sync (
                    id INTEGER PRIMARY KEY,
                    last_sync_time REAL,
                    indexed_folders TEXT,
                    sync_type TEXT
                )
            """
            )

            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_path ON files(path)")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_files_vendor ON files(vendor)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_files_library ON files(library)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_files_modified_time ON files(modified_time)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_files_hash ON files(file_hash)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_file_hashes_path ON file_hashes(path)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_file_hashes_hash ON file_hashes(file_hash)"
            )

            conn.commit()
            conn.close()
            info(f"🚀 Indexed Manager am done accessing db!")
            info(f"🚀 Indexed Manager am done accessing db!")
            info(f"🚀 Indexed Manager am done accessing db!")
            info(f"🚀 Indexed Manager am done accessing db!")
            info(f"🚀 Indexed Manager am done accessing db!")
            info(f"🚀 Indexed Manager am done accessing db!")

        except Exception as e:
            error(f"❌ Error initializing database: {e}")
            raise

    # meilisearch
    def _sync_to_meilisearch(self, file_paths: List[str], operation: str = "upsert"):
        """
        🚀 Sync files to MeiliSearch via SearchModel _apply_changes
        """
        try:
            # Import and initialize SearchModel
            from models.search_model import SearchModel

            # Create SearchModel instance
            search_model = SearchModel()

            if operation == "upsert":
                search_model.bulk_sync_to_meilisearch(file_paths, "upsert")
            elif operation == "delete":
                search_model.bulk_sync_to_meilisearch(file_paths, "delete")

        except Exception as e:
            warning(f"⚠️ MeiliSearch sync failed: {e}")

    def sync_index_with_filesystem(
        self,
        force_full_sync: bool = False,
        progress_callback: Optional[Callable] = None,
    ) -> Dict:
        """
        🚀 PROFESSIONAL file index synchronization with streaming and progress reporting

        Args:
            force_full_sync: If True, performs full rescan regardless of timestamps
            progress_callback: Optional callback for progress updates (rate, ETA, etc.)

        Returns:
            Dictionary with sync statistics
        """
        start_time = time.time()
        self.progress_callback = progress_callback

        info("🔄 Starting PROFESSIONAL file index synchronization...")
        info(
            "🚀 Optimizations: Ultra-fast filtering, batch operations, streaming processing"
        )

        with self._lock:
            try:
                # Reset statistics
                self.stats = {
                    "files_scanned": 0,
                    "files_added": 0,
                    "files_removed": 0,
                    "files_updated": 0,
                    "files_renamed": 0,
                    "sync_time": 0.0,
                    "scan_rate": 0.0,
                    "processing_rate": 0.0,
                }

                # Check if we can skip sync
                if not force_full_sync and self._can_skip_sync():
                    info("⚡ Skipping sync - no significant changes detected")
                    self.stats["sync_time"] = time.time() - start_time
                    # Note: We still return the stats, but the background worker will handle completion
                    return self.stats

                # 🚀 STREAMING PROCESSING - Handle unlimited file counts efficiently
                if force_full_sync:
                    # For large collections, use streaming approach
                    info("🌊 Using streaming processing for large file collection...")
                    self._streaming_sync()
                else:
                    # For incremental sync, use traditional approach
                    info("📊 Using incremental sync approach...")

                    # Get current database state
                    db_files = self._get_database_files()
                    info(f"📊 Database contains {len(db_files)} files")

                    # Scan filesystem
                    fs_files = self._scan_filesystem()
                    info(f"📁 Filesystem contains {len(fs_files)} relevant files")

                    # Find and apply changes
                    changes = self._find_changes(db_files, fs_files)
                    self._apply_changes(changes)

                # Update sync timestamp
                self._update_last_sync_time("full_sync")

                # Calculate sync time and rates
                self.stats["sync_time"] = time.time() - start_time
                if self.stats["sync_time"] > 0:
                    self.stats["scan_rate"] = (
                        self.stats["files_scanned"] / self.stats["sync_time"]
                    )
                    total_processed = (
                        self.stats["files_added"]
                        + self.stats["files_removed"]
                        + self.stats["files_updated"]
                        + self.stats["files_renamed"]
                    )
                    self.stats["processing_rate"] = (
                        total_processed / self.stats["sync_time"]
                    )

                # Log results
                self._log_sync_results()

                return self.stats

            except Exception as e:
                error(f"❌ File index sync failed: {e}")
                raise

    def _can_skip_sync(self) -> bool:
        """Check if we can skip sync based on folder modification times"""
        try:
            # Always run sync on startup to detect deleted files
            # (Folder modification times don't change when files are deleted)
            print("🔍 DEBUG: Always running sync on startup to detect deleted files")
            return False
        except Exception as e:
            error(f"❌ Error checking sync skip condition: {e}")
            return False  # On error, do full sync

    def _compile_extension_patterns(self) -> Set[str]:
        """Pre-compile extension patterns for ultra-fast filtering"""
        # Convert extensions to lowercase and add dots
        compiled = set()
        for ext in self.supported_extensions:
            if not ext.startswith("."):
                ext = "." + ext
            compiled.add(ext.lower())
        return compiled

    def _compile_system_patterns(self) -> Dict[str, bool]:
        """Pre-compile system file patterns for fast filtering"""
        patterns = {
            # Hidden files
            "hidden_start": re.compile(r"^\."),
            # System files
            "system_files": {
                ".DS_Store",
                "Thumbs.db",
                "desktop.ini",
                ".Spotlight-V100",
                ".Trashes",
                ".fseventsd",
                ".TemporaryItems",
                ".VolumeIcon.icns",
                ".apdisk",
                ".localized",
                ".metadata_never_index",
                ".parentlock",
            },
            # Temporary file endings
            "temp_endings": (".tmp", ".temp", ".swp", ".lock", ".bak", ".backup"),
            # Database file endings
            "db_endings": (
                ".db",
                ".db-journal",
                ".db-wal",
                ".db-shm",
                ".sqlite",
                ".sqlite3",
            ),
            # Log file endings
            "log_endings": (".log", ".logs"),
            # Cache file endings
            "cache_endings": (".cache", ".cached"),
            # Partial file endings
            "partial_endings": (".part", ".partial"),
        }
        return patterns

    def _get_database_files(self) -> Dict[str, Dict]:
        """Get all files currently in database with their metadata"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT path, name, vendor, library, file_type, modified_time, 
                   file_size, file_hash, tags, keywords, instrument, genre, mood
            FROM files
        """
        )

        db_files = {}
        for row in cursor.fetchall():
            (
                path,
                name,
                vendor,
                library,
                file_type,
                modified_time,
                file_size,
                file_hash,
                tags,
                keywords,
                instrument,
                genre,
                mood,
            ) = row
            db_files[path] = {
                "name": name,
                "vendor": vendor,
                "library": library,
                "file_type": file_type,
                "modified_time": modified_time,
                "file_size": file_size,
                "file_hash": file_hash,
                "tags": tags,
                "keywords": keywords,
                "instrument": instrument,
                "genre": genre,
                "mood": mood,
            }

        conn.close()
        return db_files

    def _scan_filesystem(self) -> Dict[str, Dict]:
        """🚀 PROFESSIONAL filesystem scanning with streaming and progress reporting"""
        fs_files = {}
        total_files_scanned = 0
        relevant_files_found = 0
        start_time = time.time()

        # Progress tracking
        last_progress_time = start_time
        last_progress_count = 0

        for folder in self.indexed_folders:
            if not os.path.exists(folder):
                warning(f"⚠️ Indexed folder does not exist: {folder}")
                continue

            info(f"🔍 Scanning folder: {folder}")

            # Walk through folder recursively
            for root, dirs, files in os.walk(folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    total_files_scanned += 1

                    # 🚀 ULTRA-FAST filtering - most files filtered out here
                    if not self._should_process_file(file_path):
                        continue

                    relevant_files_found += 1

                    try:
                        # Get file info
                        stat = os.stat(file_path)
                        file_name = os.path.basename(file_path)

                        # 🚀 FAST extension extraction - avoid Path() overhead
                        last_dot = file_name.rfind(".")
                        file_type = (
                            file_name[last_dot:].lower() if last_dot != -1 else ""
                        )

                        # Skip hash calculation during initial scan for speed
                        file_hash = ""  # Empty hash for now

                        # 🚀 SIMPLIFIED vendor extraction for speed
                        vendor, library = self._fast_extract_vendor_library(file_path)

                        fs_files[file_path] = {
                            "name": file_name,
                            "vendor": vendor,
                            "library": library,
                            "file_type": file_type,
                            "modified_time": stat.st_mtime,
                            "file_size": stat.st_size,
                            "file_hash": file_hash,
                        }

                        self.stats["files_scanned"] += 1

                        # 🚀 PROFESSIONAL progress reporting with rate and ETA
                        current_time = time.time()
                        if current_time - last_progress_time >= 2.0:
                            rate = (total_files_scanned - last_progress_count) / max(
                                0.001, (current_time - last_progress_time)
                            )

                            # Estimate remaining files (rough approximation)
                            if rate > 0:
                                # Assume we're scanning about 10% of total files
                                estimated_total = total_files_scanned * 10
                                remaining = max(
                                    0, estimated_total - total_files_scanned
                                )
                                eta_seconds = remaining / rate if rate > 0 else 0
                                eta_minutes = eta_seconds / 60

                                print(
                                    f"🔍 Scanned {total_files_scanned:,} files, found {relevant_files_found:,} relevant files..."
                                )
                                print(
                                    f"   Rate: {rate:.0f} files/sec, ETA: {eta_minutes:.1f} minutes"
                                )

                            last_progress_time = current_time
                            last_progress_count = total_files_scanned

                    except (OSError, IOError) as e:
                        warning(f"⚠️ Cannot access file {file_path}: {e}")
                        continue

        total_time = time.time() - start_time
        rate = total_files_scanned / total_time if total_time > 0 else 0

        print(
            f"🔍 Filesystem scan complete: {total_files_scanned:,} total files, {relevant_files_found:,} relevant files"
        )
        print(
            f"   Scan rate: {rate:.0f} files/sec, Total time: {total_time:.1f} seconds"
        )

        return fs_files

    def _should_process_file(self, file_path: str) -> bool:
        """🚀 ULTRA-FAST file filtering - optimized for 1.2M+ files"""
        try:
            # Get filename and extension in one go
            filename = os.path.basename(file_path)
            if filename and filename[0] == ".":
                return False

            # Skip system files - use pre-compiled set
            if filename in self._system_file_patterns["system_files"]:
                return False

            # Skip temporary files - use pre-compiled tuple
            if filename.endswith(self._system_file_patterns["temp_endings"]):
                return False

            # Skip database files
            if filename.endswith(self._system_file_patterns["db_endings"]):
                return False

            # Skip log files
            if filename.endswith(self._system_file_patterns["log_endings"]):
                return False

            # Skip cache files
            if filename.endswith(self._system_file_patterns["cache_endings"]):
                return False

            # Skip partial files
            if filename.endswith(self._system_file_patterns["partial_endings"]):
                return False

            # 🚀 ULTRA-FAST extension check - find last dot and check against pre-compiled set
            last_dot = filename.rfind(".")
            if last_dot == -1:
                return False  # No extension

            ext = filename[last_dot:].lower()
            return ext in self._compiled_extensions

        except:
            return False  # Skip if we can't determine

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate MD5 hash of file for change detection"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                # Read file in chunks to handle large files
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except:
            return ""  # Return empty string if hash calculation fails

    def _extract_vendor_library_from_path(self, file_path: str) -> Tuple[str, str]:
        """Extract vendor and library from file path"""
        try:
            from utils.database.knowledge_database import KnowledgeDatabase
            import appdirs
            from settings.core_settings import APP_NAME, APP_AUTHOR

            # Get knowledge database path
            config_dir = appdirs.user_config_dir(APP_NAME, APP_AUTHOR)
            knowledge_db_path = os.path.join(config_dir, "patchio_knowledge.db")

            if os.path.exists(knowledge_db_path):
                knowledge_db = KnowledgeDatabase(knowledge_db_path)
                return knowledge_db.extract_vendor_library(file_path)
            else:
                return self._simple_extract_vendor_library(file_path)

        except Exception as e:
            return self._simple_extract_vendor_library(file_path)

    def _fast_extract_vendor_library(self, file_path: str) -> Tuple[str, str]:
        """🚀 ULTRA-FAST vendor/library extraction - optimized for speed"""
        # Use string operations instead of Path() for speed
        path_lower = file_path.lower()

        # Pre-compiled vendor patterns for speed
        vendor_patterns = {
            "native instruments": "Native Instruments",
            "spitfire": "Spitfire Audio",
            "heavyocity": "Heavyocity",
            "eastwest": "EastWest",
            "cinesamples": "Cinesamples",
            "synthogy": "Synthogy",
            "apple": "Apple",
            "steinberg": "Steinberg",
            "image-line": "Image-Line",
            "avid": "Avid",
            "cockos": "Cockos",
            "bitwig": "Bitwig",
            "reason studios": "Reason Studios",
        }

        # Find vendor in path
        vendor = "Unknown Vendor"
        library = "Unknown Library"

        for pattern, vendor_name in vendor_patterns.items():
            if pattern in path_lower:
                vendor = vendor_name
                # Extract library name (folder after vendor)
                parts = file_path.split(os.sep)
                for i, part in enumerate(parts):
                    if pattern in part.lower():
                        # Look for library in next few folders
                        for j in range(i + 1, min(i + 4, len(parts))):
                            next_part = parts[j]
                            if (
                                len(next_part) > 2
                                and len(next_part) <= 30
                                and next_part.lower()
                                not in {"samples", "patches", "instruments", "presets"}
                            ):
                                library = next_part
                                break
                        break
                break

        return vendor, library

    def _streaming_sync(self):
        """🚀 STREAMING SYNC - Memory-efficient processing for unlimited file counts"""
        info("🌊 Starting streaming sync for large file collection...")

        # Phase 1: Clear existing database for fresh start
        info("🗑️ Clearing existing database for fresh sync...")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        self._apply_sqlite_tuning(cursor, mode="safe")
        cursor.execute("DELETE FROM files")
        cursor.execute("DELETE FROM file_hashes")
        conn.commit()
        conn.close()

        # Phase 2: Stream filesystem scan with batch processing
        info("📁 Streaming filesystem scan with batch processing...")

        batch_buffer = []
        inserted_paths = []  # for ES upsert
        total_files_scanned = 0
        relevant_files_found = 0
        start_time = time.time()
        last_progress_time = start_time

        for folder in self.indexed_folders:
            if not os.path.exists(folder):
                warning(f"⚠️ Indexed folder does not exist: {folder}")
                continue

            info(f"🔍 Streaming folder: {folder}")

            # Walk through folder recursively
            for root, dirs, files in os.walk(folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    total_files_scanned += 1

                    # 🚀 ULTRA-FAST filtering
                    if not self._should_process_file(file_path):
                        continue

                    relevant_files_found += 1

                    try:
                        # Get file info
                        stat = os.stat(file_path)
                        file_name = os.path.basename(file_path)

                        # 🚀 FAST extension extraction
                        last_dot = file_name.rfind(".")
                        file_type = (
                            file_name[last_dot:].lower() if last_dot != -1 else ""
                        )
                        extension = file_type
                        parent_folder = os.path.dirname(file_path)

                        # 🚀 FAST vendor extraction
                        vendor, library = self._fast_extract_vendor_library(file_path)

                        # Add to batch buffer
                        batch_buffer.append(
                            (
                                file_path,
                                file_name,
                                extension,
                                file_type,
                                parent_folder,
                                stat.st_mtime,
                                stat.st_size,
                                "",  # hash deferred
                                vendor,
                                library,
                            )
                        )
                        inserted_paths.append(file_path)

                        self.stats["files_scanned"] += 1

                        # 🚀 BATCH PROCESSING - Process in chunks to avoid memory issues
                        if len(batch_buffer) >= self.batch_size:
                            self._process_batch(batch_buffer, inserted_paths)
                            batch_buffer = []
                            inserted_paths = []

                        # 🚀 PROFESSIONAL progress reporting
                        current_time = time.time()
                        if current_time - last_progress_time >= 3.0:
                            rate = relevant_files_found / max(
                                0.001, (current_time - last_progress_time)
                            )
                            estimated_total = total_files_scanned * 1.2
                            remaining = max(0, estimated_total - total_files_scanned)
                            eta_seconds = remaining / rate if rate > 0 else 0
                            eta_minutes = eta_seconds / 60

                            print(
                                f"🌊 Streaming: {total_files_scanned:,} scanned, {relevant_files_found:,} relevant, {self.stats['files_added']:,} added"
                            )
                            print(
                                f"   Rate: {rate:.0f} files/sec, ETA: {eta_minutes:.1f} minutes"
                            )

                            # Call progress callback if provided
                            if self.progress_callback:
                                self.progress_callback(
                                    {
                                        "phase": "streaming_scan",
                                        "scanned": total_files_scanned,
                                        "relevant": relevant_files_found,
                                        "added": self.stats["files_added"],
                                        "rate": rate,
                                        "eta_minutes": eta_minutes,
                                    }
                                )

                            last_progress_time = current_time

                    except (OSError, IOError) as e:
                        warning(f"⚠️ Cannot access file {file_path}: {e}")
                        continue

        # Process remaining batch
        if batch_buffer:
            self._process_batch(batch_buffer, inserted_paths)

        total_time = time.time() - start_time
        rate = total_files_scanned / total_time if total_time > 0 else 0

        info(
            f"🌊 Streaming sync complete: {total_files_scanned:,} scanned, {relevant_files_found:,} relevant, {self.stats['files_added']:,} added"
        )
        info(
            f"   Final rate: {rate:.0f} files/sec, Total time: {total_time:.1f} seconds"
        )

    def _process_batch(self, batch_data: List[Tuple], inserted_paths: List[str]):
        """Process batch with FTS5 maintenance"""
        if not batch_data:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        self._apply_sqlite_tuning(cursor, mode="safe")
        try:
            # 🚀 BATCH INSERT with INSERT OR IGNORE to handle duplicates
            insert_sql = """
                INSERT OR IGNORE INTO files 
                (path, name, extension, file_type, parent_folder, 
                modified_time, file_size, file_hash, vendor, library,
                                        created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%s', 'now'), strftime('%s', 'now'))
            """

            cursor.executemany(insert_sql, batch_data)
            added = (
                cursor.rowcount
                if cursor.rowcount and cursor.rowcount > 0
                else len(batch_data)
            )
            self.stats["files_added"] += added

            # After main batch processing, update FTS5 table
            self._update_fts5_for_batch(inserted_paths, cursor)

            conn.commit()

        except Exception as e:
            conn.rollback()
            error(f"❌ Batch processing failed: {e}")
            raise
        finally:
            conn.close()

        # Real-time ES bulk upsert for this batch (optional but fast)
        try:
            if self.es_sync and self.es_sync.is_enabled():
                self.es_sync.bulk_upsert_paths(inserted_paths)
        except Exception as e:
            warning(f"⚠️ ES bulk upsert (batch) failed: {e}")

    def _update_fts5_for_batch(self, paths: List[str], cursor):
        """Update FTS5 table for a batch of changed files"""
        if not paths:
            return

        try:
            # Delete existing FTS5 entries for these paths
            placeholders = ",".join(["?"] * len(paths))
            delete_sql = f"DELETE FROM files_fts WHERE path IN ({placeholders})"
            cursor.execute(delete_sql, paths)

            # Insert updated entries - USE SIMPLE INSERT, NOT REPLACE
            insert_sql = """
                INSERT INTO files_fts 
                SELECT path, name, vendor, library, instrument, genre, tags, keywords, file_type
                FROM files 
                WHERE path IN ({})
            """.format(
                placeholders
            )

            cursor.execute(insert_sql, paths)

            debug(f"🔄 Updated FTS5 for {len(paths)} files")

        except Exception as e:
            warning(f"⚠️ FTS5 batch update failed: {e}")
        # 🚀 MeiliSearch bulk sync for this batch
        try:
            self._sync_to_meilisearch(inserted_paths, "upsert")
        except Exception as e:
            warning(f"⚠️ MeiliSearch bulk sync (batch) failed: {e}")

    def _simple_extract_vendor_library(self, file_path: str) -> Tuple[str, str]:
        """Simple fallback vendor/library extraction"""
        return self._fast_extract_vendor_library(file_path)

    def _find_changes(self, db_files: Dict, fs_files: Dict) -> Dict:
        """Find differences between database and filesystem"""
        changes = {"to_add": [], "to_remove": [], "to_update": [], "to_rename": []}

        # Find files to add (in FS but not in DB)
        for path, file_info in fs_files.items():
            if path not in db_files:
                changes["to_add"].append((path, file_info))

        # Find files to remove (in DB but not in FS)
        for path, file_info in db_files.items():
            if path not in fs_files:
                changes["to_remove"].append((path, file_info))

        # Find files to update or rename
        for path, fs_info in fs_files.items():
            if path in db_files:
                db_info = db_files[path]

                # Check if file was modified (skip hash check for speed during initial scan)
                if (
                    abs(fs_info["modified_time"] - db_info["modified_time"]) > 1.0
                    or fs_info["file_size"] != db_info["file_size"]
                ):
                    changes["to_update"].append((path, fs_info))

        # Skip rename detection during initial scan for speed (relies on file hashes)
        # self._find_potential_renames(db_files, fs_files, changes)

        return changes

    def _find_potential_renames(self, db_files: Dict, fs_files: Dict, changes: Dict):
        pass  # unchanged (optional)

    def _apply_changes(self, changes: Dict):
        """🚀 PROFESSIONAL batch database operations with MeiliSearch sync"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        self._apply_sqlite_tuning(cursor, mode="safe")
        add_paths = []
        update_paths = []
        remove_paths = []
        rename_old_paths = []
        rename_new_paths = []

        try:
            # 🚀 BATCH INSERT - Add new files in batches to avoid UNIQUE constraint errors
            if changes["to_add"]:
                info(
                    f"📝 Adding {len(changes['to_add'])} files in batches of {self.batch_size}..."
                )

                # Prepare batch insert statement
                insert_sql = """
                    INSERT OR IGNORE INTO files 
                    (path, name, extension, file_type, modified_time, 
                    file_size, file_hash, vendor, library, parent_folder,
                    created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%s', 'now'), strftime('%s', 'now'))
                """

                # Process in batches
                for i in range(0, len(changes["to_add"]), self.batch_size):
                    batch = changes["to_add"][i : i + self.batch_size]
                    batch_data = []

                    for path, file_info in batch:
                        name = os.path.basename(path)
                        extension = file_info["file_type"]
                        parent_folder = os.path.dirname(path)
                        batch_data.append(
                            (
                                path,
                                name,
                                extension,
                                file_info["file_type"],
                                file_info["modified_time"],
                                file_info["file_size"],
                                file_info["file_hash"],
                                file_info["vendor"],
                                file_info["library"],
                                parent_folder,
                            )
                        )
                        add_paths.append(path)

                    cursor.executemany(insert_sql, batch_data)
                    self.stats["files_added"] += len(batch_data)

                info(f"✅ Added {self.stats['files_added']} files successfully")

            # 🚀 BATCH DELETE - Remove deleted files in batches
            if changes["to_remove"]:
                info(f"🗑️ Removing {len(changes['to_remove'])} files in batches...")

                delete_sql = "DELETE FROM files WHERE path = ?"

                for i in range(0, len(changes["to_remove"]), self.batch_size):
                    batch = changes["to_remove"][i : i + self.batch_size]
                    batch_paths = [(path,) for path, file_info in batch]

                    cursor.executemany(delete_sql, batch_paths)
                    self.stats["files_removed"] += len(batch_paths)
                    remove_paths.extend([p for p, _ in batch])

                info(f"✅ Removed {self.stats['files_removed']} files successfully")

            # 🚀 BATCH UPDATE - Update modified files in batches
            if changes["to_update"]:
                info(f"📝 Updating {len(changes['to_update'])} files in batches...")

                update_sql = """
                    UPDATE files 
                    SET modified_time = ?, file_size = ?, file_hash = ?, 
                        vendor = ?, library = ?, extension = ?, parent_folder = ?, 
                        updated_at = strftime('%s', 'now')
                    WHERE path = ?
                """

                for i in range(0, len(changes["to_update"]), self.batch_size):
                    batch = changes["to_update"][i : i + self.batch_size]
                    batch_data = []

                    for path, file_info in batch:
                        extension = file_info["file_type"]
                        parent_folder = os.path.dirname(path)
                        batch_data.append(
                            (
                                file_info["modified_time"],
                                file_info["file_size"],
                                file_info["file_hash"],
                                file_info["vendor"],
                                file_info["library"],
                                extension,
                                parent_folder,
                                path,
                            )
                        )
                        update_paths.append(path)

                    cursor.executemany(update_sql, batch_data)
                    self.stats["files_updated"] += len(batch_data)

                info(f"✅ Updated {self.stats['files_updated']} files successfully")

            # 🚀 BATCH RENAME - Handle renames in batches
            if changes["to_rename"]:
                info(f"🔄 Renaming {len(changes['to_rename'])} files in batches...")

                rename_sql = """
                    UPDATE files 
                    SET path = ?, name = ?, modified_time = ?, file_size = ?, 
                        file_hash = ?, extension = ?, parent_folder = ?, 
                        updated_at = strftime('%s', 'now')
                    WHERE path = ?
                """

                for i in range(0, len(changes["to_rename"]), self.batch_size):
                    batch = changes["to_rename"][i : i + self.batch_size]
                    batch_data = []

                    for old_path, new_path, file_info in batch:
                        name = os.path.basename(new_path)
                        extension = file_info["file_type"]
                        parent_folder = os.path.dirname(new_path)
                        batch_data.append(
                            (
                                new_path,
                                name,
                                file_info["modified_time"],
                                file_info["file_size"],
                                file_info["file_hash"],
                                extension,
                                parent_folder,
                                old_path,
                            )
                        )
                        rename_old_paths.append(old_path)
                        rename_new_paths.append(new_path)

                    cursor.executemany(rename_sql, batch_data)
                    self.stats["files_renamed"] += len(batch_data)

                info(f"✅ Renamed {self.stats['files_renamed']} files successfully")

            conn.commit()

        except Exception as e:
            conn.rollback()
            error(f"❌ Batch database operations failed: {e}")
            raise
        finally:
            conn.close()

        # ES sync for applied changes
        try:
            if self.es_sync and self.es_sync.is_enabled():
                if add_paths or update_paths:
                    self.es_sync.bulk_upsert_paths(list(set(add_paths + update_paths)))
                if remove_paths or rename_old_paths:
                    self.es_sync.bulk_delete_paths(
                        list(set(remove_paths + rename_old_paths))
                    )
                if rename_new_paths:
                    self.es_sync.bulk_upsert_paths(list(set(rename_new_paths)))
        except Exception as e:
            warning(f"⚠️ ES sync for applied changes failed: {e}")

        # 🚀 MeiliSearch sync for applied changes
        try:
            if add_paths or update_paths or rename_new_paths:
                all_upsert_paths = list(
                    set(add_paths + update_paths + rename_new_paths)
                )
                self._sync_to_meilisearch(all_upsert_paths, "upsert")

            if remove_paths or rename_old_paths:
                all_delete_paths = list(set(remove_paths + rename_old_paths))
                self._sync_to_meilisearch(all_delete_paths, "delete")
        except Exception as e:
            warning(f"⚠️ MeiliSearch sync for applied changes failed: {e}")

    def _update_last_sync_time(self, sync_type: str):
        """Update the last sync timestamp"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            self._apply_sqlite_tuning(cursor, mode="safe")
            current_time = time.time()
            indexed_folders_json = str(list(self.indexed_folders))

            cursor.execute(
                """
                INSERT INTO last_sync (last_sync_time, indexed_folders, sync_type)
                VALUES (?, ?, ?)
            """,
                (current_time, indexed_folders_json, sync_type),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            error(f"❌ Error updating last sync time: {e}")

    def _log_sync_results(self):
        """🚀 PROFESSIONAL sync results logging with performance metrics"""
        info("📊 PROFESSIONAL FILE INDEX SYNC RESULTS")
        info("=" * 50)
        info(f"Folders scanned: {len(self.indexed_folders)}")
        info(f"Files scanned: {self.stats['files_scanned']:,}")
        info(f"Files added: {self.stats['files_added']:,}")
        info(f"Files removed: {self.stats['files_removed']:,}")
        info(f"Files updated: {self.stats['files_updated']:,}")
        info(f"Files renamed: {self.stats['files_renamed']:,}")
        info(f"Sync time: {self.stats['sync_time']:.2f} seconds")

        # 🚀 Performance metrics
        if self.stats["scan_rate"] > 0:
            info(f"Scan rate: {self.stats['scan_rate']:.0f} files/second")
        if self.stats["processing_rate"] > 0:
            info(
                f"Processing rate: {self.stats['processing_rate']:.0f} operations/second"
            )

        # Efficiency metrics
        if self.stats["files_scanned"] > 0:
            efficiency = (
                (
                    self.stats["files_added"]
                    + self.stats["files_removed"]
                    + self.stats["files_updated"]
                    + self.stats["files_renamed"]
                )
                / self.stats["files_scanned"]
                * 100
            )
            info(
                f"Processing efficiency: {efficiency:.1f}% of scanned files required changes"
            )

        if (
            self.stats["files_added"] > 0
            or self.stats["files_removed"] > 0
            or self.stats["files_updated"] > 0
            or self.stats["files_renamed"] > 0
        ):
            info("✅ File index synchronized with filesystem changes")
        else:
            info("✅ File index already up to date")

        info(
            "🚀 Professional optimizations: Ultra-fast filtering, batch operations, streaming processing"
        )

    def start_real_time_monitoring(self, callback: Optional[Callable] = None) -> None:
        """Start real-time file system monitoring (idempotent & thread-safe)."""
        with getattr(self, "_monitor_lock", threading.Lock()):
            # If already monitoring, don't start again
            if getattr(self, "is_monitoring", False):
                warning("🛡️ Real-time monitoring already active; skipping start")
                return

            # Normalize & filter folders once
            folders = set()
            for p in self.indexed_folders or []:
                try:
                    # absolute path; Windows-safe normalization
                    ap = os.path.abspath(p)
                    if os.path.isdir(ap):
                        folders.add(ap)
                    else:
                        warning(f"⚠️ Indexed folder does not exist (skipping): {p}")
                except Exception as e:
                    warning(f"⚠️ Skipping invalid folder {p}: {e}")

            if not folders:
                warning("⚠️ No valid folders to watch; monitoring not started")
                return

            try:
                from utils.database.file_watcher import create_file_watcher, FileEvent

                # Reuse watcher if present and running
                watcher = getattr(self, "file_watcher", None)
                if watcher and getattr(watcher, "is_running", False):
                    info("🛡️ File watcher already running; marking monitoring active")
                    self.is_monitoring = True
                    return

                # Create (or replace) watcher
                self.file_watcher = create_file_watcher(self.db_path)

                def handle_file_event(event: "FileEvent") -> None:
                    try:
                        self._handle_real_time_event(event)
                    except Exception as e:
                        error(f"❌ Error handling file event {event}: {e}")
                    finally:
                        # optional fan-out
                        if callback:
                            try:
                                callback(event)
                            except Exception as ce:
                                warning(f"⚠️ External callback failed: {ce}")

                # Start monitoring; only mark active after success
                self.file_watcher.start(frozenset(folders), handle_file_event)
                self.is_monitoring = True
                info(f"✅ Real-time monitoring started for {len(folders)} folder(s)")

            except Exception as e:
                # Ensure we don't leave a half-initialized state
                self.is_monitoring = False
                # Try best-effort stop if watcher partially started
                try:
                    if getattr(self, "file_watcher", None):
                        self.file_watcher.stop()
                except Exception:
                    pass
                error(f"❌ Failed to start real-time monitoring: {e}")
                raise

    def stop_real_time_monitoring(self) -> None:
        """Stop real-time monitoring safely with proper resource cleanup."""
        info("🛑 Stopping real-time monitoring file index manager line 1183")
        
        # Ensure lock exists
        if not hasattr(self, "_monitor_lock"):
            self._monitor_lock = threading.Lock()
        
        with self._monitor_lock:
            # Early return if already stopped
            if not self.is_monitoring:
                info("ℹ️ Real-time monitoring already stopped")
                return
            
            watcher = getattr(self, "file_watcher", None)
            if not watcher:
                info("ℹ️ No file watcher instance found")
                self.is_monitoring = False
                return
            
            try:
                # Stop the watcher
                if getattr(watcher, "is_running", False):
                    
                    info("inside here 1")
                    try:
                        watcher.stop()
                    except Exception as e:
                        print(f"error: {e}")
                    info("inside here 2")
                    
                    # Wait for completion if supported
                    if hasattr(watcher, 'join'):
                        watcher.join(timeout=10.0)
                    
                    info("✅ Real-time monitoring stopped successfully")
                else:
                    info("ℹ️ File watcher was not running")
                    
            except Exception as e:
                info(f"⚠️ Error stopping file watcher: {e}")
            finally:
                # Always clean up state
                self.is_monitoring = False
                # Consider cleaning up the watcher object
                # self.file_watcher = None


    def _handle_real_time_event(self, event):
        """DB commit first, then ES and MeiliSearch real-time sync"""
        print(f"event: {event.event_type}")
        print(f"event: {event.event_type}")
        print(f"event: {event.event_type}")
        print(f"event: {event.event_type}")
        print(f"event: {event.event_type}")
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            self._apply_sqlite_tuning(cursor, mode="safe")
            if event.event_type == "created":
                self._handle_file_created(cursor, event.path)
                self._sync_to_meilisearch([event.path], "upsert")

            elif event.event_type == "deleted":
                self._handle_file_deleted(cursor, event.path)
                self._sync_to_meilisearch([event.path], "delete")

            elif event.event_type == "moved":
                self._handle_file_moved(cursor, event.path, event.dest_path)

                if event.dest_path:
                    self._sync_to_meilisearch([event.path], "delete")
                    self._sync_to_meilisearch([event.dest_path], "upsert")
                else:
                    self._sync_to_meilisearch([event.path], "delete")

            elif event.event_type == "modified":
                self._handle_file_modified(cursor, event.path)
                self._sync_to_meilisearch([event.path], "upsert")

            conn.commit()
            conn.close()

        except Exception as e:
            error(f"❌ Error handling real-time event: {e}")
            return

        # After DB commit, perform real-time ES sync (your existing code)
        try:
            if self.es_sync and self.es_sync.is_enabled():
                if event.event_type == "created":
                    self.es_sync.upsert_path(event.path)
                elif event.event_type == "deleted":
                    self.es_sync.delete_path(event.path)
                elif event.event_type == "modified":
                    self.es_sync.upsert_path(event.path)
                elif event.event_type == "moved":
                    if event.dest_path:
                        self.es_sync.delete_path(event.path)
                        self.es_sync.upsert_path(event.dest_path)
                    else:
                        self.es_sync.delete_path(event.path)
        except Exception as e:
            warning(f"⚠️ Real-time ES sync failed: {e}")

    def _update_fts5_for_file(self, cursor, file_path: str):
        """Safely update FTS5 for a single file"""
        try:
            # First delete any existing entries for this path
            cursor.execute("DELETE FROM files_fts WHERE path = ?", (file_path,))

            # Then insert the current data (no REPLACE, just INSERT)
            cursor.execute(
                """
                INSERT INTO files_fts 
                SELECT path, name, vendor, library, instrument, genre, tags, keywords, file_type
                FROM files 
                WHERE path = ?
            """,
                (file_path,),
            )

        except Exception as e:
            warning(f"⚠️ FTS5 update failed for {file_path}: {e}")

    def _handle_file_created(self, cursor, file_path: str):
        """Handle file creation with FTS5 update"""
        if not self._should_process_file(file_path):
            return

        try:
            stat = os.stat(file_path)
            file_name = os.path.basename(file_path)

            # 🚀 FAST extension extraction
            last_dot = file_name.rfind(".")
            file_type = file_name[last_dot:].lower() if last_dot != -1 else ""
            extension = file_type
            parent_folder = os.path.dirname(file_path)

            file_hash = self._calculate_file_hash(file_path)
            vendor, library = self._fast_extract_vendor_library(file_path)

            cursor.execute(
                """
                INSERT OR IGNORE INTO files 
                (path, name, extension, file_type, parent_folder, 
                modified_time, file_size, file_hash, vendor, library,
                                           created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%s', 'now'), strftime('%s', 'now'))
            """,
                (
                    file_path,
                    file_name,
                    extension,
                    file_type,
                    parent_folder,
                    stat.st_mtime,
                    stat.st_size,
                    file_hash,
                    vendor,
                    library,
                ),
            )

            # Update FTS5 table - USE THE CORRECTED METHOD
            self._update_fts5_for_file(cursor, file_path)

            info(f"➕ Added file: {file_name}")

        except Exception as e:
            error(f"❌ Error adding file {file_path}: {e}")

    def _handle_file_deleted(self, cursor, file_path: str):
        """Handle file deletion with FTS5 update"""
        cursor.execute("DELETE FROM files WHERE path = ?", (file_path,))
        if cursor.rowcount > 0:
            info(f"➖ Removed file: {os.path.basename(file_path)}")

        # Update FTS5 table
        try:
            cursor.execute("DELETE FROM files_fts WHERE path = ?", (file_path,))
        except Exception as e:
            warning(f"⚠️ FTS5 delete failed for {file_path}: {e}")

    def _handle_file_moved(self, cursor, old_path: str, new_path: str):
        """Handle file move/rename event with optimized processing and FTS5 update"""
        # Check if moved to Trash (macOS deletion)
        if ".Trashes" in new_path or "Trash" in new_path:
            cursor.execute("DELETE FROM files WHERE path = ?", (old_path,))
            if cursor.rowcount > 0:
                info(f"➖ Removed file (moved to Trash): {os.path.basename(old_path)}")
            return

        # Check if moved from Trash (macOS restore)
        if ".Trashes" in old_path or "Trash" in old_path:
            if self._should_process_file(new_path):
                self._handle_file_created(cursor, new_path)
                info(f"♻️ Restored file from Trash: {os.path.basename(new_path)}")
            return

        # Regular move/rename - update path, preserve metadata
        if self._should_process_file(new_path):
            try:
                stat = os.stat(new_path)
                file_name = os.path.basename(new_path)

                # 🚀 FAST extension extraction
                last_dot = file_name.rfind(".")
                file_type = file_name[last_dot:].lower() if last_dot != -1 else ""
                extension = file_type
                parent_folder = os.path.dirname(new_path)

                file_hash = self._calculate_file_hash(new_path)
                vendor, library = self._fast_extract_vendor_library(new_path)

                # First, check if old_path exists in database
                cursor.execute("SELECT COUNT(*) FROM files WHERE path = ?", (old_path,))
                old_file_exists = cursor.fetchone()[0] > 0

                if old_file_exists:
                    # Update existing record
                    cursor.execute(
                        """
                        UPDATE files 
                        SET path = ?, name = ?, modified_time = ?, file_size = ?, 
                            file_hash = ?, vendor = ?, library = ?, extension = ?, parent_folder = ?, 
                            updated_at = strftime('%s', 'now')
                        WHERE path = ?
                    """,
                        (
                            new_path,
                            file_name,
                            stat.st_mtime,
                            stat.st_size,
                            file_hash,
                            vendor,
                            library,
                            extension,
                            parent_folder,
                            old_path,
                        ),
                    )

                    if cursor.rowcount > 0:
                        info(
                            f"🔄 Renamed file: {os.path.basename(old_path)} -> {file_name}"
                        )
                    else:
                        # Update failed, delete old and create new
                        cursor.execute("DELETE FROM files WHERE path = ?", (old_path,))
                        self._handle_file_created(cursor, new_path)
                        info(
                            f"🔄 Renamed file (fallback): {os.path.basename(old_path)} -> {file_name}"
                        )
                else:
                    # Old file not in database, just create the new one
                    self._handle_file_created(cursor, new_path)
                    info(f"➕ Added renamed file: {file_name}")

                # Update FTS5 table - DELETE OLD, INSERT NEW
                try:
                    cursor.execute("DELETE FROM files_fts WHERE path = ?", (old_path,))
                    self._update_fts5_for_file(cursor, new_path)
                except Exception as e:
                    warning(f"⚠️ FTS5 move update failed: {e}")

            except Exception as e:
                error(f"❌ Error moving file {old_path}: {e}")
                # Fallback: ensure old file is removed and new one is added
                try:
                    cursor.execute("DELETE FROM files WHERE path = ?", (old_path,))
                    self._handle_file_created(cursor, new_path)
                except Exception as fallback_error:
                    error(f"❌ Fallback rename also failed: {fallback_error}")
        else:
            # File moved outside indexed area, remove the old one
            cursor.execute("DELETE FROM files WHERE path = ?", (old_path,))
            if cursor.rowcount > 0:
                info(
                    f"➖ Moved file outside indexed area: {os.path.basename(old_path)}"
                )

    def _handle_file_modified(self, cursor, file_path: str):
        """Handle file modification event with optimized processing and FTS5 update"""
        if not self._should_process_file(file_path):
            return

        try:
            stat = os.stat(file_path)
            file_hash = self._calculate_file_hash(file_path)
            vendor, library = self._fast_extract_vendor_library(file_path)
            parent_folder = os.path.dirname(file_path)
            last_dot = os.path.basename(file_path).rfind(".")
            extension = (
                os.path.basename(file_path)[last_dot:].lower() if last_dot != -1 else ""
            )

            cursor.execute(
                """
                UPDATE files 
                SET modified_time = ?, file_size = ?, file_hash = ?, 
                    vendor = ?, library = ?, extension = ?, parent_folder = ?, 
                    updated_at = strftime('%s', 'now')
                WHERE path = ?
            """,
                (
                    stat.st_mtime,
                    stat.st_size,
                    file_hash,
                    vendor,
                    library,
                    extension,
                    parent_folder,
                    file_path,
                ),
            )

            if cursor.rowcount > 0:
                info(f"📝 Updated file: {os.path.basename(file_path)}")

            # Update FTS5 table
            self._update_fts5_for_file(cursor, file_path)

        except Exception as e:
            error(f"❌ Error updating file {file_path}: {e}")

    def get_file_metadata(self, file_path: str) -> Optional[Dict]:
        """Get metadata for a specific file"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT path, name, vendor, library, file_type, modified_time, 
                       file_size, file_hash, tags, keywords, instrument, genre, mood
                FROM files WHERE path = ?
            """,
                (file_path,),
            )

            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    "path": row[0],
                    "name": row[1],
                    "vendor": row[2],
                    "library": row[3],
                    "file_type": row[4],
                    "modified_time": row[5],
                    "file_size": row[6],
                    "file_hash": row[7],
                    "tags": row[8],
                    "keywords": row[9],
                    "instrument": row[10],
                    "genre": row[11],
                    "mood": row[12],
                }

            return None

        except Exception as e:
            error(f"❌ Error getting file metadata: {e}")
            return None

    def update_file_metadata(self, file_path: str, metadata: Dict):
        """Update metadata for a specific file and sync to search engines"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            self._apply_sqlite_tuning(cursor, mode="safe")
            cursor.execute(
                """
                UPDATE files 
                SET tags = ?, keywords = ?, instrument = ?, genre = ?, mood = ?,
                    updated_at = strftime('%s', 'now')
                WHERE path = ?
            """,
                (
                    metadata.get("tags"),
                    metadata.get("keywords"),
                    metadata.get("instrument"),
                    metadata.get("genre"),
                    metadata.get("mood"),
                    file_path,
                ),
            )

            conn.commit()
            conn.close()

            if cursor.rowcount > 0:
                info(f"📝 Updated metadata for: {os.path.basename(file_path)}")

            # Sync to both search engines
            try:
                # ES sync
                if self.es_sync and self.es_sync.is_enabled():
                    self.es_sync.upsert_path(file_path)
            except Exception as e:
                warning(f"⚠️ ES upsert after metadata update failed: {e}")

            # MeiliSearch sync
            try:
                self._sync_to_meilisearch([file_path], "upsert")
            except Exception as e:
                warning(f"⚠️ MeiliSearch sync after metadata update failed: {e}")

        except Exception as e:
            error(f"❌ Error updating file metadata: {e}")

        def search_files(self, query: str, limit: int = 100) -> List[Dict]:
            """Search for files in the index"""
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # Simple search across name, vendor, library, tags, keywords
                cursor.execute(
                    """
                    SELECT path, name, vendor, library, file_type, tags, keywords, instrument, genre, mood
                    FROM files 
                    WHERE name LIKE ? OR vendor LIKE ? OR library LIKE ? OR tags LIKE ? OR keywords LIKE ?
                    ORDER BY name
                    LIMIT ?
                """,
                    (
                        f"%{query}%",
                        f"%{query}%",
                        f"%{query}%",
                        f"%{query}%",
                        f"%{query}%",
                        limit,
                    ),
                )

                results = []
                for row in cursor.fetchall():
                    results.append(
                        {
                            "path": row[0],
                            "name": row[1],
                            "vendor": row[2],
                            "library": row[3],
                            "file_type": row[4],
                            "tags": row[5],
                            "keywords": row[6],
                            "instrument": row[7],
                            "genre": row[8],
                            "mood": row[9],
                        }
                    )

                conn.close()
                return results

            except Exception as e:
                error(f"❌ Error searching files: {e}")
                return []

        def get_statistics(self) -> Dict:
            """Get database statistics"""
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # Get total file count
                cursor.execute("SELECT COUNT(*) FROM files")
                total_files = cursor.fetchone()[0]

                # Get vendor distribution
                cursor.execute(
                    """
                    SELECT vendor, COUNT(*) as count 
                    FROM files 
                    WHERE vendor IS NOT NULL AND vendor != 'Unknown Vendor'
                    GROUP BY vendor 
                    ORDER BY count DESC 
                    LIMIT 10
                """
                )
                vendor_stats = dict(cursor.fetchall())

                # Get file type distribution
                cursor.execute(
                    """
                    SELECT file_type, COUNT(*) as count 
                    FROM files 
                    WHERE file_type IS NOT NULL
                    GROUP BY file_type 
                    ORDER BY count DESC
                """
                )
                file_type_stats = dict(cursor.fetchall())

                conn.close()

                return {
                    "total_files": total_files,
                    "vendor_distribution": vendor_stats,
                    "file_type_distribution": file_type_stats,
                    "indexed_folders": len(self.indexed_folders),
                    "is_monitoring": self.is_monitoring,
                }

            except Exception as e:
                error(f"❌ Error getting statistics: {e}")
                return {}


# Convenience function for easy integration
def sync_index_with_filesystem(
    db_path: str,
    indexed_folders: Set[str],
    force_full_sync: bool = False,
    progress_callback: Optional[Callable] = None,
) -> Dict:
    """
    🚀 PROFESSIONAL convenience function to sync file index with filesystem

    Args:
        db_path: Path to SQLite database
        indexed_folders: Set of folders to index
        force_full_sync: If True, performs full rescan with streaming processing
        progress_callback: Optional callback for progress updates (rate, ETA, etc.)

    Returns:
        Dictionary with sync statistics including performance metrics
    """
    manager = FileIndexManager(db_path, indexed_folders)
    return manager.sync_index_with_filesystem(force_full_sync, progress_callback)


# Test function
def test_file_index_manager():
    """Test the file index manager"""
    print("🧪 Testing File Index Manager")

    import tempfile
    import shutil

    # Create test environment
    test_dir = tempfile.mkdtemp(prefix="patchio_test_")
    test_db = os.path.join(test_dir, "test_index.db")

    try:
        # Create test files
        test_files = [
            "test_patch.nki",
            "another_sound.wav",
            "hidden_file.nki",  # Should be ignored
        ]

        for filename in test_files:
            file_path = os.path.join(test_dir, filename)
            with open(file_path, "w") as f:
                f.write("test content")

        # Create hidden file
        hidden_file = os.path.join(test_dir, ".hidden_file.nki")
        with open(hidden_file, "w") as f:
            f.write("hidden content")

        print(f"Created test directory: {test_dir}")

        # Test file index manager
        manager = FileIndexManager(test_db, {test_dir})

        # Test sync
        results = manager.sync_index_with_filesystem(force_full_sync=True)
        print(f"Sync results: {results}")

        # Test search
        search_results = manager.search_files("test")
        print(f"Search results: {len(search_results)} files found")

        # Test statistics
        stats = manager.get_statistics()
        print(f"Statistics: {stats}")

        print("✅ File Index Manager test completed successfully")

    finally:
        # Cleanup
        shutil.rmtree(test_dir)


if __name__ == "__main__":
    test_file_index_manager()
