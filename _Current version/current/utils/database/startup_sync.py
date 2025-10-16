#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Startup Database Synchronization for PatchIO
Scans indexed folders on app startup to sync database with file system changes
"""

import os
import sys
import sqlite3
import time
import json
from pathlib import Path
from typing import Set, Dict, List, Tuple
from collections import defaultdict

# Add parent directory to path for imports
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from utils.logger import info, warning, error, debug
from settings.core_settings import DEFAULT_EXTENSIONS


class StartupSync:
    """Handles database synchronization on app startup"""

    def __init__(self, db_path: str, indexed_folders: Set[str]):
        self.db_path = db_path
        self.indexed_folders = indexed_folders
        self.supported_extensions = set(DEFAULT_EXTENSIONS)

        # Statistics
        self.stats = {
            "files_scanned": 0,
            "files_added": 0,
            "files_removed": 0,
            "files_updated": 0,
            "folders_scanned": 0,
            "sync_time": 0.0,
        }

        info("🔄 Startup sync initialized for {} folders".format(len(indexed_folders)))

    def _initialize_database(self):
        """Initialize database with required tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create files table
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
                    created_at REAL DEFAULT (strftime('%s', 'now'))
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

            # Create last_sync table for intelligent sync
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS last_sync (
                    id INTEGER PRIMARY KEY,
                    last_sync_time REAL,
                    indexed_folders TEXT
                )
            """
            )

            conn.commit()
            conn.close()

        except Exception as e:
            error(f"❌ Error initializing database: {e}")
            raise

    def sync_database(self, force_full_sync: bool = False) -> Dict:
        """Perform intelligent database synchronization"""
        start_time = time.time()
        info("🚀 Starting database synchronization...")

        try:
            # Initialize database if needed
            self._initialize_database()

            # Check if we can skip sync (quick check)
            if not force_full_sync and self._can_skip_sync():
                info("⚡ Skipping sync - no significant changes detected")
                self.stats["sync_time"] = time.time() - start_time
                return self.stats

            # Get current database state
            db_files = self._get_database_files()
            info("📊 Database contains {} files".format(len(db_files)))

            # Scan file system
            fs_files = self._scan_file_system()
            info("📁 File system contains {} relevant files".format(len(fs_files)))

            # Find differences
            changes = self._find_changes(db_files, fs_files)

            # Apply changes to database
            self._apply_changes(changes)

            # Update last sync timestamp
            self._update_last_sync_time()

            # Calculate sync time
            self.stats["sync_time"] = time.time() - start_time

            # Log results
            self._log_sync_results()

            return self.stats

        except Exception as e:
            error("❌ Startup sync failed: {}".format(e))
            raise

    def _get_database_files(self) -> Dict[str, Dict]:
        """Get all files currently in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT path, name, vendor, library, file_type, modified_time
            FROM files
        """
        )

        db_files = {}
        for row in cursor.fetchall():
            path, name, vendor, library, file_type, modified_time = row
            db_files[path] = {
                "name": name,
                "vendor": vendor,
                "library": library,
                "file_type": file_type,
                "modified_time": modified_time,
            }

        conn.close()
        return db_files

    def _can_skip_sync(self) -> bool:
        """Check if we can skip the sync based on last sync time and folder modification times"""
        try:
            # Check if database has a last_sync table
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create last_sync table if it doesn't exist
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS last_sync (
                    id INTEGER PRIMARY KEY,
                    last_sync_time REAL,
                    indexed_folders TEXT
                )
            """
            )

            # Get last sync time
            cursor.execute(
                "SELECT last_sync_time FROM last_sync ORDER BY id DESC LIMIT 1"
            )
            result = cursor.fetchone()

            if not result:
                conn.close()
                return False  # No previous sync, need to do full sync

            last_sync_time = result[0]
            conn.close()

            # Check if any indexed folder has been modified since last sync
            for folder in self.indexed_folders:
                if os.path.exists(folder):
                    folder_mtime = os.path.getmtime(folder)
                    if folder_mtime > last_sync_time:
                        return False  # Folder modified, need to sync

            return True  # No changes detected, can skip sync

        except Exception as e:
            error("❌ Error checking sync skip condition: {}".format(e))
            return False  # On error, do full sync

    def _update_last_sync_time(self):
        """Update the last sync timestamp"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Insert new sync timestamp
            current_time = time.time()
            indexed_folders_json = json.dumps(list(self.indexed_folders))

            cursor.execute(
                """
                INSERT INTO last_sync (last_sync_time, indexed_folders)
                VALUES (?, ?)
            """,
                (current_time, indexed_folders_json),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            error("❌ Error updating last sync time: {}".format(e))

    def _scan_file_system(self) -> Dict[str, Dict]:
        """Scan indexed folders for relevant files"""
        fs_files = {}

        for folder in self.indexed_folders:
            if not os.path.exists(folder):
                warning("⚠️ Indexed folder does not exist: {}".format(folder))
                continue

            self.stats["folders_scanned"] += 1
            info("🔍 Scanning folder: {}".format(folder))

            # Walk through folder recursively
            for root, dirs, files in os.walk(folder):
                for file in files:
                    file_path = os.path.join(root, file)

                    # Check if file has supported extension
                    if not self._is_supported_file(file_path):
                        continue

                    try:
                        # Get file info
                        stat = os.stat(file_path)
                        file_name = os.path.basename(file_path)
                        file_type = Path(file_path).suffix.lower()

                        # Extract vendor and library info using knowledge database
                        vendor, library = self._extract_vendor_library_from_path(
                            file_path
                        )

                        fs_files[file_path] = {
                            "name": file_name,
                            "vendor": vendor,
                            "library": library,
                            "file_type": file_type,
                            "modified_time": stat.st_mtime,
                        }

                        self.stats["files_scanned"] += 1

                    except (OSError, IOError) as e:
                        warning("⚠️ Cannot access file {}: {}".format(file_path, e))
                        continue

        return fs_files

    def _find_changes(self, db_files: Dict, fs_files: Dict) -> Dict:
        """Find differences between database and file system"""
        changes = {"to_add": [], "to_remove": [], "to_update": []}

        # Find files to add (in FS but not in DB)
        for path, info in fs_files.items():
            if path not in db_files:
                changes["to_add"].append((path, info))

        # Find files to remove (in DB but not in FS)
        for path, info in db_files.items():
            if path not in fs_files:
                changes["to_remove"].append((path, info))

        # Find files to update (different modification time)
        for path, fs_info in fs_files.items():
            if path in db_files:
                db_info = db_files[path]
                if (
                    abs(fs_info["modified_time"] - db_info["modified_time"]) > 1.0
                ):  # 1 second tolerance
                    changes["to_update"].append((path, fs_info))

        return changes

    def _apply_changes(self, changes: Dict):
        """Apply changes to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Add new files
            for path, info in changes["to_add"]:
                cursor.execute(
                    """
                    INSERT INTO files (path, name, vendor, library, file_type, modified_time)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        path,
                        info["name"],
                        info["vendor"],
                        info["library"],
                        info["file_type"],
                        info["modified_time"],
                    ),
                )
                self.stats["files_added"] += 1

            # Remove deleted files
            for path, info in changes["to_remove"]:
                cursor.execute("DELETE FROM files WHERE path = ?", (path,))
                if cursor.rowcount > 0:
                    self.stats["files_removed"] += 1

            # Update modified files
            for path, info in changes["to_update"]:
                cursor.execute(
                    """
                    UPDATE files 
                    SET modified_time = ?, vendor = ?, library = ?
                    WHERE path = ?
                """,
                    (info["modified_time"], info["vendor"], info["library"], path),
                )
                if cursor.rowcount > 0:
                    self.stats["files_updated"] += 1

            conn.commit()

        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _should_ignore_file(self, file_path: str) -> bool:
        """Check if file should be ignored (hidden, system files, etc.)"""
        try:
            filename = os.path.basename(file_path)

            # Skip hidden files (starting with .) - this is the most common case
            if filename.startswith("."):
                return True

            # Skip system files
            system_files = {
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
            }
            if filename in system_files:
                return True

            # Skip temporary files
            if filename.endswith((".tmp", ".temp", ".swp", ".lock", ".bak", ".backup")):
                return True

            # Skip database files (we don't want to index our own database)
            if filename.endswith(
                (".db", ".db-journal", ".db-wal", ".db-shm", ".sqlite", ".sqlite3")
            ):
                return True

            # Skip log files
            if filename.endswith((".log", ".logs")):
                return True

            # Skip cache files
            if filename.endswith((".cache", ".cached")):
                return True

            # Skip archive files that might be temporary
            if filename.endswith((".part", ".partial")):
                return True

            return False
        except:
            return True  # Skip if we can't determine

    def _is_supported_file(self, file_path: str) -> bool:
        """Check if file has a supported extension"""
        if not file_path:
            return False

        # First check if file should be ignored
        if self._should_ignore_file(file_path):
            return False

        ext = Path(file_path).suffix.lower()
        return ext in self.supported_extensions

    def _extract_vendor_library_from_path(self, file_path: str) -> tuple:
        """Extract vendor and library from file path using knowledge database"""
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
                # Fallback to simple extraction if knowledge database not available
                return self._simple_extract_vendor_library(file_path)

        except Exception as e:
            # Fallback to simple extraction on error
            return self._simple_extract_vendor_library(file_path)

    def _simple_extract_vendor_library(self, file_path: str) -> tuple:
        """Simple fallback vendor/library extraction"""
        path_parts = Path(file_path).parts

        # Skip volume names and common system folders
        skip_parts = {
            "volumes",
            "users",
            "applications",
            "desktop",
            "documents",
            "downloads",
            "samples",
            "patches",
            "instruments",
            "presets",
        }

        # Look for common vendor names in path
        vendor_keywords = [
            "native instruments",
            "spitfire",
            "heavyocity",
            "eastwest",
            "cinesamples",
            "synthogy",
            "apple",
            "steinberg",
            "image-line",
            "avid",
            "cockos",
            "bitwig",
            "reason studios",
        ]

        vendor = "Unknown Vendor"
        library = "Unknown Library"

        for i, part in enumerate(path_parts):
            part_lower = part.lower()
            if part_lower in skip_parts or len(part) > 20:
                continue
            for vendor_keyword in vendor_keywords:
                if vendor_keyword in part_lower:
                    vendor = vendor_keyword.title()
                    # Library is usually the next folder after vendor
                    if i + 1 < len(path_parts):
                        next_part = path_parts[i + 1]
                        if next_part.lower() not in skip_parts and len(next_part) <= 30:
                            library = next_part
                    break

        return vendor, library

    def _log_sync_results(self):
        """Log synchronization results"""
        info("📊 STARTUP SYNC RESULTS")
        info("=" * 40)
        info("Folders scanned: {}".format(self.stats["folders_scanned"]))
        info("Files scanned: {}".format(self.stats["files_scanned"]))
        info("Files added: {}".format(self.stats["files_added"]))
        info("Files removed: {}".format(self.stats["files_removed"]))
        info("Files updated: {}".format(self.stats["files_updated"]))
        info("Sync time: {:.2f} seconds".format(self.stats["sync_time"]))

        if (
            self.stats["files_added"] > 0
            or self.stats["files_removed"] > 0
            or self.stats["files_updated"] > 0
        ):
            info("✅ Database synchronized with file system changes")
        else:
            info("✅ Database already up to date")


# Test function
def test_startup_sync():
    """Test the startup synchronization"""
    print("🧪 Testing Startup Synchronization")

    # Get database path
    import appdirs
    from settings.core_settings import APP_NAME, APP_AUTHOR

    config_dir = appdirs.user_config_dir(APP_NAME, APP_AUTHOR)
    db_path = os.path.join(config_dir, "patchio_index.db")

    # Test folders (use current directory for testing)
    test_folders = {os.getcwd()}

    # Create sync instance
    sync = StartupSync(db_path, test_folders)

    try:
        # Perform sync
        results = sync.sync_database()
        print("✅ Startup sync completed successfully")
        print("Results:", results)

    except Exception as e:
        print("❌ Startup sync failed: {}".format(e))
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_startup_sync()
