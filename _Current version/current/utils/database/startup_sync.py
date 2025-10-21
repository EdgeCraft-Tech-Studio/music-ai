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
        
        # 🚀 OPTIMIZATION: Initialize shared knowledge database
        self._knowledge_db = self._get_shared_knowledge_database()
        
        # Sync vendors from knowledge_initial.json to knowledge DB
        self._sync_vendors_on_startup()
        
        info("🔄 Startup sync initialized for {} folders".format(len(indexed_folders)))
    
    def _get_shared_knowledge_database(self):
        """
        Get shared knowledge database instance for the entire sync process.
        Uses centralized AppDirs path (single source of truth).
        """
        try:
            from utils.database.knowledge_database import KnowledgeDatabase
            
            # KnowledgeDatabase() automatically uses AppDirs location
            # Will create DB if doesn't exist
            return KnowledgeDatabase()
        except Exception as e:
            warning(f"❌ Error getting shared knowledge database: {e}")
            return None
    
    def _sync_vendors_on_startup(self):
        """Sync vendors from knowledge_initial.json to knowledge database on startup"""
        if not self._knowledge_db:
            return
        
        try:
            from utils.database.library_extractor_v3 import LibraryExtractorV3
            
            # Load vendors from JSON
            vendors_from_json = LibraryExtractorV3.get_default_vendors()
            
            if not vendors_from_json:
                debug("⚠️  No vendors found in knowledge_initial.json")
                return
            
            # Check how many vendors are currently in DB
            self._knowledge_db.cursor.execute("SELECT COUNT(*) FROM vendor_profiles")
            current_count = self._knowledge_db.cursor.fetchone()[0]
            
            # Sync vendors to knowledge DB
            for canonical_name, aliases in vendors_from_json.items():
                self._knowledge_db.cursor.execute(
                    'SELECT id FROM vendor_profiles WHERE vendor_name = ?',
                    (canonical_name,)
                )
                existing = self._knowledge_db.cursor.fetchone()
                
                if not existing:
                    # Add new vendor
                    self._knowledge_db.cursor.execute('''
                        INSERT INTO vendor_profiles (vendor_name, display_name, aliases)
                        VALUES (?, ?, ?)
                    ''', (canonical_name, canonical_name, json.dumps(aliases)))
            
            self._knowledge_db.conn.commit()
            
            # Check new count
            self._knowledge_db.cursor.execute("SELECT COUNT(*) FROM vendor_profiles")
            new_count = self._knowledge_db.cursor.fetchone()[0]
            
            if new_count > current_count:
                added = new_count - current_count
                info(f"✅ Synced {added} new vendors to knowledge database")
            elif current_count == 0:
                info(f"✅ Initialized knowledge database with {new_count} vendors")
            else:
                debug(f"✓ Knowledge database already has {new_count} vendors")
                
        except Exception as e:
            warning(f"⚠️  Could not sync vendors on startup: {e}")
    
    def _prescan_projects(self) -> Dict[str, str]:
        """
        🚀 Pre-scan all indexed folders for DAW projects.
        Returns a map of {folder_path: project_name} for instant lookup.
        
        This is MUCH faster than checking during file indexing because:
        - Only scans each folder once
        - No repeated os.listdir() calls
        - Typical scan: 39,000+ folders/second
        """
        info("🎵 Pre-scanning folders for DAW projects...")
        
        PROJECT_EXTENSIONS = {'.cpr', '.logicx', '.als', '.flp', '.ptx', '.song', '.rpp'}
        project_map = {}
        total_folders = 0
        projects_found = 0
        start_time = time.time()
        
        for folder in self.indexed_folders:
            if not os.path.exists(folder):
                continue
            
            for root, dirs, files in os.walk(folder):
                total_folders += 1
                
                # Check if this folder has a project file OR project folder (Logic .logicx)
                found_project = False
                
                # Check files (.cpr, .als, .flp, .ptx, .song, .rpp)
                for file in files:
                    if any(file.lower().endswith(ext) for ext in PROJECT_EXTENSIONS):
                        project_name = os.path.basename(root)
                        project_map[root] = project_name
                        projects_found += 1
                        found_project = True
                        break
                
                # Also check directories for Logic projects (.logicx)
                if not found_project:
                    for dir_name in dirs:
                        if dir_name.lower().endswith('.logicx'):
                            project_name = os.path.basename(root)
                            project_map[root] = project_name
                            projects_found += 1
                            break
        
        elapsed = time.time() - start_time
        rate = total_folders / elapsed if elapsed > 0 else 0
        
        info(f"✅ Project pre-scan complete: {projects_found} projects found in {total_folders:,} folders ({rate:.0f} folders/sec, {elapsed:.2f}s)")
        
        return project_map
    
    def _update_projects_in_database(self):
        """
        🚀 Update project column for audio files in project folders.
        Uses the pre-scanned project_map for instant lookup.
        """
        if not hasattr(self, '_project_map') or not self._project_map:
            return
        
        info("🎵 Updating project information for audio files...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get all audio files (only these can be in projects)
            cursor.execute("""
                SELECT path FROM files 
                WHERE name LIKE '%.wav' OR name LIKE '%.aiff' OR name LIKE '%.mp3' 
                   OR name LIKE '%.flac' OR name LIKE '%.ogg'
            """)
            audio_files = cursor.fetchall()
            
            if not audio_files:
                conn.close()
                return
            
            # For each audio file, check if it's in a project folder
            updates = []
            for (file_path,) in audio_files:
                project_name = None
                parts = Path(file_path).parts
                
                # 🚀 PRIORITY: Check if .logicx is IN the path (file inside package)
                for part in parts:
                    if part.lower().endswith('.logicx'):
                        project_name = part[:-7]  # Remove .logicx extension
                        break
                
                # If not inside .logicx package, check project_map
                if not project_name:
                    for i in range(len(parts) - 1, max(0, len(parts) - 6), -1):
                        folder = os.path.join('/', *parts[:i+1])
                        if folder in self._project_map:
                            project_name = self._project_map[folder]
                            break
                
                if project_name:
                    updates.append((project_name, file_path))
            
            # Batch update all files in projects
            if updates:
                cursor.executemany("""
                    UPDATE files 
                    SET vendor = 'User', library = NULL, project = ?
                    WHERE path = ?
                """, updates)
                
                conn.commit()
                info(f"✅ Updated {len(updates)} audio files with project information")
            
        except Exception as e:
            warning(f"⚠️  Error updating projects: {e}")
        finally:
            conn.close()
    
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
                    project TEXT,
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
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_path ON files(path)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_vendor ON files(vendor)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_library ON files(library)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_project ON files(project)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_modified_time ON files(modified_time)')
            
            # Migrate existing databases (add project column if it doesn't exist)
            cursor.execute("PRAGMA table_info(files)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'project' not in columns:
                cursor.execute('ALTER TABLE files ADD COLUMN project TEXT')
                info("✅ Added 'project' column to existing database")
            
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
            
            # 🚀 PRE-SCAN: Find all DAW projects before indexing (ultra-fast)
            self._project_map = self._prescan_projects()
            
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
            
            # 🚀 POST-PROCESS: Update project column for files in project folders
            if self._project_map:
                self._update_projects_in_database()
            
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
        """Scan indexed folders for relevant files with optimized batch processing"""
        fs_files = {}

        for folder in self.indexed_folders:
            if not os.path.exists(folder):
                warning("⚠️ Indexed folder does not exist: {}".format(folder))
                continue

            self.stats["folders_scanned"] += 1
            info("🔍 Scanning folder: {}".format(folder))
            
            # Collect all files first, then process by folder batches
            folder_files = {}  # folder_path -> list of files
            
            # Walk through folder recursively
            for root, dirs, files in os.walk(folder):
                folder_path = root
                folder_files[folder_path] = []
                
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
                        
                        folder_files[folder_path].append({
                            'path': file_path,
                            'name': file_name,
                            'type': file_type,
                            'mtime': stat.st_mtime
                        })
                        
                    except (OSError, IOError) as e:
                        warning("⚠️ Cannot access file {}: {}".format(file_path, e))
                        continue
            
            # Process files by folder batches for better performance
            total_folders = len([f for f in folder_files.values() if f])
            processed_folders = 0
            
            for folder_path, files in folder_files.items():
                if not files:
                    continue
                
                processed_folders += 1
                
                # 🚀 OPTIMIZED vendor/library extraction + project detection
                vendor, library, project = self._extract_vendor_library_from_path(files[0]['path'])
                
                # Log progress for this folder with batch info (reduced frequency for speed)
                if processed_folders % 200 == 0 or len(files) > 100:  # Log every 200 folders or large folders
                    if len(files) > 1:
                        info("🔍 Optimized extraction for {} files in folder ({}/{}): {} - {}".format(
                            len(files), processed_folders, total_folders, vendor, library))
                    else:
                        info("🔍 Optimized extraction for {} ({}/{}): {} - {}".format(
                            files[0]['name'], processed_folders, total_folders, vendor, library))
                
                # Add all files from this folder with the same vendor/library/project
                for file_info in files:
                    fs_files[file_info['path']] = {
                        'name': file_info['name'],
                        'vendor': vendor,
                        'library': library,
                        'project': project,
                        'file_type': file_info['type'],
                        'modified_time': file_info['mtime']
                    }
                    
                    self.stats['files_scanned'] += 1
        
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
            for path, info in changes['to_add']:
                cursor.execute("""
                    INSERT INTO files (path, name, vendor, library, project, file_type, modified_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (path, info['name'], info['vendor'], info['library'], info.get('project'),
                     info['file_type'], info['modified_time']))
                self.stats['files_added'] += 1
            
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
        """🚀 OPTIMIZED vendor/library/project extraction using V3 with project detection"""
        try:
            # 🚀 Use V3 extractor with project detection
            from utils.database.library_extractor_v3 import LibraryExtractorV3
            if not hasattr(self, '_v3_extractor'):
                self._v3_extractor = LibraryExtractorV3(use_knowledge_db=True)
            
            # Get project map (if available from pre-scan)
            project_map = getattr(self, '_project_map', None)
            
            return self._v3_extractor.extract_vendor_library(file_path, project_map=project_map)
                
        except Exception as e:
            # Fallback to simple extraction on error
            return self._simple_extract_vendor_library(file_path)
    
    def _extract_vendor_library_hierarchy(self, file_path: str, knowledge_db) -> tuple:
        """Extract vendor/library using folder hierarchy with improved caching"""
        # Get folder path for caching
        folder_path = str(Path(file_path).parent)
        
        # Initialize folder cache if not exists
        if not hasattr(self, '_folder_cache'):
            self._folder_cache = {}
        
        # Check if we already processed this folder
        if folder_path in self._folder_cache:
            # DISABLED for performance - too much I/O overhead
            # debug(f"🚀 Using cached result for folder: {folder_path}")
            return self._folder_cache[folder_path]
        
        # DISABLED for performance - too much I/O overhead
        # debug(f"🔍 Processing new folder: {folder_path}")
        # 🚀 NEW: Use V3 extractor (fast pattern-based)
        from utils.database.library_extractor_v3 import LibraryExtractorV3
        if not hasattr(self, '_v3_extractor'):
            self._v3_extractor = LibraryExtractorV3(use_knowledge_db=True)
        
        # Get project map (if available from pre-scan)
        project_map = getattr(self, '_project_map', None)
        
        vendor, library, project = self._v3_extractor.extract_vendor_library(file_path, project_map=project_map)
        
        # Cache result for this folder and all parent folders to avoid re-processing
        self._folder_cache[folder_path] = (vendor, library, project)
        
        # Also cache for parent folders to speed up future processing
        parent_path = str(Path(folder_path).parent)
        if parent_path != folder_path and parent_path not in self._folder_cache:
            self._folder_cache[parent_path] = (vendor, library, project)
        
        return vendor, library, project
    
    def _simple_extract_vendor_library(self, file_path: str) -> tuple:
        """
        Simple fallback vendor/library extraction.
        🚀 NEW: Uses V3 extractor for accurate extraction.
        """
        from utils.database.library_extractor_v3 import LibraryExtractorV3
        if not hasattr(self, '_v3_extractor'):
            self._v3_extractor = LibraryExtractorV3(use_knowledge_db=True)
        return self._v3_extractor.extract_vendor_library(file_path)
    
    def _extract_vendor_library_ultra_fast(self, file_path: str):
        """🚀 ULTRA-FAST vendor/library extraction - no database calls, just pattern matching"""
        try:
            # Use string operations for maximum speed
            path_lower = file_path.lower()
            
            # 🚀 ULTRA-FAST pattern matching (pre-compiled)
            vendor_patterns = {
                'native instruments': 'Native Instruments',
                'kontakt': 'Native Instruments',
                'spitfire': 'Spitfire Audio',
                'spitfire audio': 'Spitfire Audio',
                'heavyocity': 'Heavyocity',
                'eastwest': 'EastWest',
                'east west': 'EastWest',
                'composer cloud': 'EastWest',
                'hollywood': 'EastWest',
                'cinesamples': 'Cinesamples',
                'synthogy': 'Synthogy',
                'apple': 'Apple',
                'steinberg': 'Steinberg',
                'image-line': 'Image-Line',
                'avid': 'Avid',
                'cockos': 'Cockos',
                'bitwig': 'Bitwig',
                'reason studios': 'Reason Studios',
                'output': 'Output',
                '8dio': '8DIO',
                'orchestral tools': 'Orchestral Tools',
                'audio imperia': 'Audio Imperia',
                'keep forest': 'Keep Forest',
                'sonokinetic': 'Sonokinetic',
                'project sam': 'Project SAM',
                'omnisphere': 'Spectrasonics',
                'spectrasonics': 'Spectrasonics',
                'arturia': 'Arturia',
                'u-he': 'u-he',
                'fabfilter': 'FabFilter',
                'izotope': 'iZotope',
                'waves': 'Waves',
                'plugin alliance': 'Plugin Alliance',
                'softube': 'Softube',
                'valhalla': 'Valhalla DSP',
                'soundtoys': 'Soundtoys',
                'splice': 'Splice',
                'loopmasters': 'Loopmasters',
                'black octopus': 'Black Octopus',
                'ghost syndicate': 'Ghost Syndicate',
                'vengeance': 'Vengeance',
                'prime loops': 'Prime Loops',
                'sample magic': 'Sample Magic',
                'big fish audio': 'Big Fish Audio',
                'zero-g': 'Zero-G',
                'best service': 'Best Service',
                'engine': 'Best Service'
            }
            
            # Find vendor using ultra-fast pattern matching
            vendor = 'Unknown Vendor'
            library = 'Unknown Library'
            
            for pattern, vendor_name in vendor_patterns.items():
                if pattern in path_lower:
                    vendor = vendor_name
                    # Fast library extraction
                    library = self._extract_library_ultra_fast(file_path, pattern)
                    break
            
            return vendor, library
            
        except Exception as e:
            warning(f"❌ Error in ultra-fast extraction: {e}")
            return 'Unknown Vendor', 'Unknown Library'
    
    def _extract_library_ultra_fast(self, file_path: str, vendor_pattern: str):
        """🚀 ULTRA-FAST library name extraction"""
        try:
            parts = file_path.split(os.sep)
            
            for i, part in enumerate(parts):
                if vendor_pattern in part.lower():
                    # Look for library in next few folders (optimized)
                    for j in range(i + 1, min(i + 3, len(parts))):  # Only check next 2 folders
                        next_part = parts[j]
                        if (len(next_part) > 2 and len(next_part) <= 30 and 
                            next_part.lower() not in {'samples', 'patches', 'instruments', 'presets', 'content', 'data', 'library', 'libraries'}):
                            return next_part
                    break
            
            return 'Unknown Library'
            
        except Exception:
            return 'Unknown Library'
    
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
    debug("🧪 Testing Startup Synchronization")
    
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
        info("✅ Startup sync completed successfully")
        debug("Results:", results)
        
    except Exception as e:
        error("❌ Startup sync failed: {}".format(e))
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_startup_sync()
