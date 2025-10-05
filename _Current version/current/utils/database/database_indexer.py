#!/usr/bin/env python3
"""
Database Indexer - Standalone SQLite indexing module for PatchIO
Recursively indexes files and folders, storing metadata in SQLite database.
"""

import os
import sqlite3
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# Import existing models and settings
from models.file_model import FileModel
from models.user_settings_model import UserSettingsModel
from settings.core_settings import FILE_TYPE_MAPPINGS

class DatabaseIndexer:
    """Standalone SQLite database indexer for PatchIO file system"""
    
    def __init__(self, db_path: str = "patchio_index.db", batch_size: int = 1000):
        """Initialize the database indexer"""
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.batch_size = batch_size
        
        # Initialize models
        self.settings_model = UserSettingsModel()
        self.file_model = FileModel(self.settings_model)
        
        # Cache for folder-level vendor/library extraction (major performance optimization)
        self.folder_cache = {}  # folder_path -> (vendor, library)
        
        # Get allowed extensions from settings (faster lookup with set)
        self.allowed_extensions = set(self.settings_model.get_setting('extensions', []))
        if not self.allowed_extensions:
            # Fallback to default extensions from core_settings
            from settings.core_settings import DEFAULT_EXTENSIONS
            self.allowed_extensions = set(DEFAULT_EXTENSIONS)
        
        print(f"📁 Indexing files with extensions: {sorted(self.allowed_extensions)}")
        print(f"📦 Batch size: {self.batch_size} files per batch")
        
        # Initialize automatic tagger (single instance for performance)
        self.automatic_tagger = None
        try:
            from utils.database.automatic_tagger import AutomaticTagger
            self.automatic_tagger = AutomaticTagger()
            print("✅ Automatic tagger initialized")
        except ImportError:
            print("⚠️ Automatic tagger not available - skipping automatic tagging")
        
        # Initialize knowledge database for vendor extraction (single instance for performance)
        self.knowledge_db = None
        try:
            from utils.database.knowledge_database import KnowledgeDatabase
            self.knowledge_db = KnowledgeDatabase("patchio_knowledge.db")
            print("✅ Knowledge database initialized for vendor extraction")
        except ImportError:
            print("⚠️ Knowledge database not available - using fallback method")
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with required tables"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            
            # Optimize SQLite for bulk operations and maximum performance
            self.cursor.execute('PRAGMA journal_mode=WAL')
            self.cursor.execute('PRAGMA synchronous=OFF')  # Faster for bulk operations
            self.cursor.execute('PRAGMA cache_size=50000')  # Larger cache
            self.cursor.execute('PRAGMA temp_store=MEMORY')
            self.cursor.execute('PRAGMA mmap_size=268435456')  # 256MB memory mapping
            self.cursor.execute('PRAGMA page_size=4096')  # Larger page size
            self.cursor.execute('PRAGMA locking_mode=EXCLUSIVE')  # Exclusive locking for bulk operations
            
            # Create files table
            self.cursor.execute('''
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
            ''')
            
            # Add new columns to existing databases if they don't exist
            new_columns = [
                ('vendor', 'TEXT'),
                ('instrument', 'TEXT'),
                ('genre', 'TEXT'),
                ('mood', 'TEXT'),
                ('format', 'TEXT')
            ]
            
            for column_name, column_type in new_columns:
                try:
                    self.cursor.execute(f'ALTER TABLE files ADD COLUMN {column_name} {column_type}')
                    print(f"✅ Added {column_name} column to existing database")
                except sqlite3.OperationalError as e:
                    if 'duplicate column name' not in str(e):
                        print(f"⚠️ Warning: Could not add {column_name} column: {e}")
            
            # Create indexes for better performance
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_path ON files(path)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_file_type ON files(file_type)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_vendor ON files(vendor)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_library ON files(library)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_extension ON files(extension)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_instrument ON files(instrument)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_genre ON files(genre)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_mood ON files(mood)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_format ON files(format)')
            
            self.conn.commit()
            print(f"✅ Database initialized: {self.db_path}")
            
        except Exception as e:
            print(f"❌ Error initializing database: {e}")
            raise
    
    def _get_file_type(self, file_path: str) -> str:
        """Get file type using FILE_TYPE_MAPPINGS"""
        _, ext = os.path.splitext(file_path.lower())
        return FILE_TYPE_MAPPINGS.get(ext, "File")
    
    def _get_library_folder(self, file_path: str) -> str:
        """Get the library folder path for caching purposes"""
        parts = os.path.normpath(file_path).split(os.sep)
        
        # Look for common library organization patterns
        # Skip common organization folders
        organization_folders = {
            'volumes', 'users', 'applications', 'desktop', 'documents', 'downloads',
            'libraries', 'kontakt libraries', 'player libraries', 'non player libraries',
            'best service engine libraries', 'service engine libraries',
            'sample libraries', 'vst', 'plugins', 'cubase projects', 'logic'
        }
        
        # Find the library folder (usually 2-3 levels up from the file)
        # Look for folders that contain "Instruments", "Samples", "Presets", etc.
        content_folders = {'instruments', 'samples', 'presets', 'patches', 'articulations', 'custom'}
        
        for i, part in enumerate(parts):
            part_lower = part.lower()
            
            # If we find a content folder, the library folder is the parent
            if part_lower in content_folders and i > 0:
                # Return the parent of the content folder (this is the library folder)
                return os.sep.join(parts[:i])
        
        # If no content folder found, look for the actual library folder
        # This handles cases where the structure is different
        for i, part in enumerate(parts):
            part_lower = part.lower()
            
            # Skip organization folders and look for library-like folders
            if (part_lower not in organization_folders and 
                len(part) > 3 and 
                not part.startswith('.') and
                i > 2):  # Skip drive/volume names
                
                # Check if this looks like a library folder (contains vendor name or library name)
                # Look for patterns like "Vendor - Library Name" or just "Library Name"
                if (' - ' in part or 
                    any(word in part_lower for word in ['library', 'collection', 'bundle', 'pack', 'suite']) or
                    len(part.split()) >= 2):  # Multi-word names are often library names
                    return os.sep.join(parts[:i+1])
        
        # Fallback: return the folder 2 levels up from the file
        if len(parts) >= 3:
            return os.sep.join(parts[:-2])
        elif len(parts) >= 2:
            return os.sep.join(parts[:-1])
        else:
            return os.path.dirname(file_path)
    
    def _get_file_metadata(self, file_path: str, file_name: str) -> Dict[str, Any]:
        """Extract metadata from file using enhanced vendor/library extraction and automatic tagging"""
        try:
            # Get musical metadata (BPM, key)
            musical_metadata = self.file_model.extract_musical_metadata(file_name, file_path)
            
            # Get library folder for caching vendor/library extraction
            # Use the library folder (2-3 levels up from file) instead of immediate parent
            library_folder = self._get_library_folder(file_path)
            
            # Check folder cache first (major performance optimization)
            if library_folder in self.folder_cache:
                vendor, library = self.folder_cache[library_folder]
            else:
                # Extract vendor and library information (expensive operation)
                if self.knowledge_db:
                    try:
                        vendor, library = self.knowledge_db.extract_vendor_library(file_path)
                    except Exception as e:
                        print(f"⚠️ Error extracting vendor/library for {file_path}: {e}")
                        library = self.file_model.extract_library_info(file_path)
                        vendor = "Unknown Vendor"
                else:
                    # Fallback to original method if knowledge database not available
                    library = self.file_model.extract_library_info(file_path)
                    vendor = "Unknown Vendor"
                
                # Cache the result for this library folder (all files in same library will reuse this)
                self.folder_cache[library_folder] = (vendor, library)
            
            # Get automatic tags using the tagging system
            if self.automatic_tagger:
                try:
                    tag_result = self.automatic_tagger.tag_file(file_path, library, vendor)
                except Exception as e:
                    print(f"⚠️ Error tagging file {file_path}: {e}")
                    tag_result = type('TagResult', (), {
                        'instrument': [], 'genre': [], 'mood': [], 'format': [], 'confidence': 0.0
                    })()
            else:
                # Fallback if tagging system not available
                tag_result = type('TagResult', (), {
                    'instrument': [], 'genre': [], 'mood': [], 'format': [], 'confidence': 0.0
                })()
            
            return {
                'bpm': musical_metadata.get('bpm', ''),
                'key': musical_metadata.get('key', ''),
                'vendor': vendor,
                'library': library,
                'keywords': '',  # Placeholder for future keyword extraction
                'tags': '',      # Placeholder for future tag extraction
                'instrument': json.dumps(tag_result.instrument) if tag_result.instrument else '',
                'genre': json.dumps(tag_result.genre) if tag_result.genre else '',
                'mood': json.dumps(tag_result.mood) if tag_result.mood else '',
                'format': json.dumps(tag_result.format) if tag_result.format else ''
            }
        except Exception as e:
            print(f"⚠️ Error extracting metadata for {file_path}: {e}")
            return {
                'bpm': '',
                'key': '',
                'vendor': 'Unknown Vendor',
                'library': 'Unknown Library',
                'keywords': '',
                'tags': '',
                'instrument': '',
                'genre': '',
                'mood': '',
                'format': ''
            }
    
    def _remove_folder_entries(self, folder_path: str):
        """Remove all entries for a folder and its subfolders from files table"""
        try:
            # Remove files in this folder and subfolders
            self.cursor.execute('''
                DELETE FROM files 
                WHERE path LIKE ? || '%'
            ''', (folder_path,))
            
            self.conn.commit()
            print(f"🗑️ Removed existing entries for: {folder_path}")
            
        except Exception as e:
            print(f"❌ Error removing folder entries: {e}")
            raise
    
    def _scan_folder_recursive(self, folder_path: str, callback=None) -> int:
        """Recursively scan folder and process files in batches"""
        total_files_processed = 0
        current_batch = []
        
        try:
            for root, dirs, files in os.walk(folder_path):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for file_name in files:
                    # Skip hidden files
                    if file_name.startswith('.'):
                        continue
                    
                    # Fast extension check - only process allowed extensions
                    _, ext = os.path.splitext(file_name.lower())
                    if ext not in self.allowed_extensions:
                        continue
                    
                    file_path = os.path.join(root, file_name)
                    file_path_normalized = os.path.normpath(file_path)
                    
                    try:
                        # Get file info
                        file_type = self._get_file_type(file_name)
                        parent_folder = os.path.dirname(file_path_normalized)
                        
                        # Get file modification time
                        modified_time = os.path.getmtime(file_path)
                        
                        # Get metadata
                        metadata = self._get_file_metadata(file_path_normalized, file_name)
                        
                        # Create file record
                        file_record = {
                            'path': file_path_normalized,
                            'name': file_name,
                            'extension': ext,
                            'file_type': file_type,
                            'parent_folder': parent_folder,
                            'modified_time': modified_time,
                            'bpm': metadata['bpm'],
                            'key': metadata['key'],
                            'vendor': metadata['vendor'],
                            'library': metadata['library'],
                            'keywords': metadata['keywords'],
                            'tags': metadata['tags'],
                            'instrument': metadata['instrument'],
                            'genre': metadata['genre'],
                            'mood': metadata['mood'],
                            'format': metadata['format']
                        }
                        
                        current_batch.append(file_record)
                        
                        # Process batch when it reaches the batch size
                        if len(current_batch) >= self.batch_size:
                            if callback:
                                callback(current_batch)
                            current_batch = []
                            total_files_processed += self.batch_size
                            
                            # Show progress
                            print(f"📦 Processed {total_files_processed} files...")
                        
                    except (OSError, PermissionError) as e:
                        print(f"⚠️ Skipping file {file_path}: {e}")
                        continue
                
        except Exception as e:
            print(f"❌ Error scanning folder {folder_path}: {e}")
            raise
        
        # Process remaining files in the last batch
        if current_batch:
            if callback:
                callback(current_batch)
            total_files_processed += len(current_batch)
        
        return total_files_processed
    
    def _insert_files(self, files_data: List[Dict[str, Any]]):
        """Insert file records into database using batch operations for speed"""
        try:
            if not files_data:
                return
                
            # Prepare batch data
            batch_data = []
            for file_record in files_data:
                batch_data.append((
                    file_record['path'],
                    file_record['name'],
                    file_record['extension'],
                    file_record['file_type'],
                    file_record['parent_folder'],
                    file_record['modified_time'],
                    file_record['bpm'],
                    file_record['key'],
                    file_record['vendor'],
                    file_record['library'],
                    file_record['keywords'],
                    file_record['tags'],
                    file_record['instrument'],
                    file_record['genre'],
                    file_record['mood'],
                    file_record['format']
                ))
            
            # Use executemany for batch insertion (much faster)
            self.cursor.executemany('''
                INSERT OR REPLACE INTO files 
                (path, name, extension, file_type, parent_folder, 
                 modified_time, bpm, key, vendor, library, keywords, tags,
                 instrument, genre, mood, format)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', batch_data)
            
            self.conn.commit()
            print(f"✅ Inserted {len(files_data)} file records")
            
        except Exception as e:
            print(f"❌ Error inserting files: {e}")
            raise
    
    
    def index_folder_to_db(self, root_folder_path: str, show_progress: bool = True) -> Dict[str, Any]:
        """
        Index a folder and all its subfolders into the database using batch processing
        
        Args:
            root_folder_path: Path to the root folder to index
            show_progress: Whether to show progress updates
            
        Returns:
            Dictionary with indexing statistics
        """
        start_time = time.time()
        
        try:
            print(f"🔍 Starting indexing of: {root_folder_path}")
            print(f"📁 Allowed extensions: {len(self.allowed_extensions)} types")
            print(f"📦 Processing in batches of {self.batch_size} files")
            
            # Clear folder cache for fresh start
            self.folder_cache.clear()
            print(f"🗂️ Folder cache cleared for fresh indexing")
            
            # Remove existing entries for this folder
            self._remove_folder_entries(root_folder_path)
            
            # Track statistics
            total_files_processed = 0
            
            # Define batch processing callback
            def process_batch(files_batch):
                nonlocal total_files_processed
                self._insert_files(files_batch)
                total_files_processed += len(files_batch)
                if show_progress:
                    print(f"💾 Inserted batch of {len(files_batch)} files (Total: {total_files_processed})")
            
            # Scan folder recursively with batch processing
            if show_progress:
                print("📁 Scanning and processing files in batches...")
            
            files_processed = self._scan_folder_recursive(root_folder_path, process_batch)
            
            # Calculate statistics
            total_time = time.time() - start_time
            files_per_second = files_processed / total_time if total_time > 0 else 0
            
            # Calculate cache efficiency
            unique_folders = len(self.folder_cache)
            cache_efficiency = ((files_processed - unique_folders) / files_processed * 100) if files_processed > 0 else 0
            
            stats = {
                'root_folder': root_folder_path,
                'files_indexed': files_processed,
                'indexing_time_seconds': total_time,
                'files_per_second': files_per_second,
                'allowed_extensions_count': len(self.allowed_extensions),
                'database_path': self.db_path,
                'batch_size': self.batch_size,
                'unique_folders': unique_folders,
                'cache_efficiency_percent': cache_efficiency
            }
            
            print(f"✅ Indexing completed in {total_time:.2f} seconds")
            print(f"📊 Statistics: {stats['files_indexed']} files indexed")
            print(f"⚡ Speed: {files_per_second:.1f} files/second")
            print(f"📦 Processed in batches of {self.batch_size}")
            print(f"🗂️ Folder cache: {unique_folders} unique folders, {cache_efficiency:.1f}% calculations saved")
            
            return stats
            
        except Exception as e:
            print(f"❌ Error during indexing: {e}")
            raise
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get current database statistics"""
        try:
            # Count files by type
            self.cursor.execute('''
                SELECT file_type, COUNT(*) as count 
                FROM files 
                GROUP BY file_type
            ''')
            files_by_type = dict(self.cursor.fetchall())
            
            # Count total files
            self.cursor.execute('SELECT COUNT(*) FROM files')
            total_files = self.cursor.fetchone()[0]
            
            # Get database file size
            db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            
            return {
                'total_files': total_files,
                'files_by_type': files_by_type,
                'database_size_bytes': db_size,
                'database_path': self.db_path
            }
            
        except Exception as e:
            print(f"❌ Error getting database stats: {e}")
            return {}
    
    def _restore_safe_settings(self):
        """Restore safe SQLite settings after bulk operations"""
        try:
            self.cursor.execute('PRAGMA synchronous=NORMAL')  # Restore safe sync mode
            self.cursor.execute('PRAGMA locking_mode=NORMAL')  # Restore normal locking
            self.conn.commit()
        except Exception as e:
            print(f"⚠️ Warning: Could not restore safe settings: {e}")
    
    def close(self):
        """Close database connection and optimize database"""
        # Close automatic tagger first
        if self.automatic_tagger:
            try:
                self.automatic_tagger.close()
                print("🔒 Automatic tagger closed")
            except Exception as e:
                print(f"⚠️ Warning: Could not close automatic tagger: {e}")
        
        # Close knowledge database
        if self.knowledge_db:
            try:
                self.knowledge_db.close()
                print("🔒 Knowledge database closed")
            except Exception as e:
                print(f"⚠️ Warning: Could not close knowledge database: {e}")
        
        # Close database connection
        if self.conn:
            try:
                # Restore safe settings before final operations
                self._restore_safe_settings()
                
                # Optimize database after bulk operations
                self.cursor.execute('VACUUM')
                self.cursor.execute('ANALYZE')
                self.conn.commit()
                print("🔧 Database optimized (VACUUM + ANALYZE)")
            except Exception as e:
                print(f"⚠️ Warning: Could not optimize database: {e}")
            finally:
                self.conn.close()
                print("🔒 Database connection closed")


def index_folder_to_db(root_folder_path: str, db_path: str = "patchio_index.db", batch_size: int = 1000) -> Dict[str, Any]:
    """
    Standalone function to index a folder into SQLite database
    
    Args:
        root_folder_path: Path to the root folder to index
        db_path: Path to the SQLite database file
        batch_size: Number of files to process in each batch (default: 1000)
        
    Returns:
        Dictionary with indexing statistics
    """
    indexer = DatabaseIndexer(db_path, batch_size)
    try:
        return indexer.index_folder_to_db(root_folder_path)
    finally:
        indexer.close()


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python database_indexer.py <folder_path> [database_path] [batch_size]")
        print("  folder_path: Path to folder to index")
        print("  database_path: Path to SQLite database (default: patchio_index.db)")
        print("  batch_size: Files per batch (default: 1000, recommended: 500-2000)")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    db_path = sys.argv[2] if len(sys.argv) > 2 else "patchio_index.db"
    batch_size = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
    
    if not os.path.exists(folder_path):
        print(f"❌ Folder does not exist: {folder_path}")
        sys.exit(1)
    
    try:
        print(f"🚀 Starting optimized indexing with batch size: {batch_size}")
        stats = index_folder_to_db(folder_path, db_path, batch_size)
        print(f"\n📊 Final Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    except Exception as e:
        print(f"❌ Indexing failed: {e}")
        sys.exit(1) 