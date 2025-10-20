#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PatchIO Knowledge Database
Consolidated database for all tagging rules, vendor/library mappings, and knowledge.
This is the single source of truth for all PatchIO tagging and library knowledge.
"""

import sqlite3
import os
import json
import threading
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from utils.logger import debug, info, warning, error, critical

class KnowledgeDatabase:
    """Consolidated knowledge database for PatchIO tagging and library rules"""
    
    _instances = {}  # Class-level cache for singleton instances (per thread)
    _lock = threading.Lock()  # Thread lock for instance creation
    
    @staticmethod
    def get_default_db_path() -> str:
        """
        Get the default knowledge database path (AppDirs location).
        This is the SINGLE SOURCE OF TRUTH for where the knowledge DB should be.
        
        Returns:
            str: Full path to patchio_knowledge.db in AppDirs
        """
        try:
            import appdirs
            from settings.core_settings import APP_NAME, APP_AUTHOR
            
            config_dir = appdirs.user_config_dir(APP_NAME, APP_AUTHOR)
            os.makedirs(config_dir, exist_ok=True)  # Ensure directory exists
            return os.path.join(config_dir, 'patchio_knowledge.db')
        except Exception as e:
            # Fallback to current directory if AppDirs fails
            warning(f"⚠️  Could not determine AppDirs path: {e}")
            debug(f"   Using current directory as fallback")
            return "patchio_knowledge.db"
    
    def __new__(cls, db_path: str = None):
        """
        Thread-safe singleton pattern.
        Each thread gets its own instance (with its own SQLite connection).
        """
        # Use default path if none provided
        if db_path is None:
            db_path = cls.get_default_db_path()
        
        # Create unique key: (db_path, thread_id)
        thread_id = threading.get_ident()
        instance_key = (db_path, thread_id)
        
        with cls._lock:
            if instance_key not in cls._instances:
                instance = super(KnowledgeDatabase, cls).__new__(cls)
                cls._instances[instance_key] = instance
            return cls._instances[instance_key]
    
    def __init__(self, db_path: str = None):
        # Use default path if none provided
        if db_path is None:
            db_path = self.get_default_db_path()
        
        # Only initialize if not already initialized
        if not hasattr(self, 'db_path') or self.db_path != db_path:
            self.db_path = db_path
            self.conn = None
            self.cursor = None
            self._initialize_database()
    
    def _is_new_database(self) -> bool:
        """Check if this is a new database (no tables exist yet)"""
        try:
            self.cursor.execute("""
                SELECT COUNT(*) FROM sqlite_master 
                WHERE type='table' AND name='vendor_profiles'
            """)
            count = self.cursor.fetchone()[0]
            return count == 0
        except:
            return True
    
    def _migrate_add_aliases_column(self):
        """Migration: Add aliases column to vendor_profiles if it doesn't exist"""
        try:
            # Check if vendor_profiles table exists
            self.cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='vendor_profiles'
            """)
            
            if self.cursor.fetchone():
                # Check if aliases column exists
                self.cursor.execute("PRAGMA table_info(vendor_profiles)")
                columns = [row[1] for row in self.cursor.fetchall()]
                
                if 'aliases' not in columns:
                    # Add aliases column
                    self.cursor.execute("""
                        ALTER TABLE vendor_profiles 
                        ADD COLUMN aliases TEXT
                    """)
                    self.conn.commit()
                    debug("✅ Added 'aliases' column to vendor_profiles table")
        except Exception as e:
            # Silently ignore if table doesn't exist yet (will be created)
            pass
    
    def _initialize_database(self):
        """Initialize the knowledge database with all required tables"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            
            # Enable foreign keys
            self.cursor.execute('PRAGMA foreign_keys = ON')
            
            # Migration: Add aliases column if it doesn't exist
            self._migrate_add_aliases_column()
            
            # Track if this is a new database
            is_new_database = self._is_new_database()
            
            # Create vendor profiles table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS vendor_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vendor_name TEXT UNIQUE NOT NULL,
                    display_name TEXT,
                    aliases TEXT,  -- JSON array of vendor name variations
                    website TEXT,
                    description TEXT,
                    default_genre TEXT,
                    default_mood TEXT,
                    default_character TEXT
                )
            ''')
            
            # Create library profiles table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS library_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    library_name TEXT UNIQUE NOT NULL,
                    vendor_id INTEGER,
                    display_name TEXT,
                    description TEXT,
                    genre_tags TEXT,  -- JSON array
                    mood_tags TEXT,   -- JSON array
                    character_tags TEXT, -- JSON array
                    format_tags TEXT, -- JSON array
                    FOREIGN KEY (vendor_id) REFERENCES vendor_profiles (id)
                )
            ''')
            
            # Create vendor library mappings table (from vendor_library.db)
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS vendor_library_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path_pattern TEXT NOT NULL,
                    vendor_name TEXT NOT NULL,
                    library_name TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    is_regex BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # Create tag mappings table (simplified structure with separate columns for each tag type)
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS tag_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern TEXT NOT NULL,
                    instrument TEXT,     -- Instrument tag value
                    genre TEXT,          -- Genre tag value
                    mood TEXT,           -- Mood tag value
                    format TEXT,         -- Format tag value
                    confidence REAL DEFAULT 1.0,
                    is_regex BOOLEAN DEFAULT FALSE,
                    library_id INTEGER,  -- Optional: library-specific rule
                    FOREIGN KEY (library_id) REFERENCES library_profiles (id)
                )
            ''')
            
            # Create vendor specific words table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS vendor_specific_words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT UNIQUE NOT NULL,
                    vendor_name TEXT NOT NULL,
                    min_length INTEGER DEFAULT 3,
                    match_position TEXT DEFAULT 'start',  -- 'start', 'any', 'end'
                    FOREIGN KEY (vendor_name) REFERENCES vendor_profiles (vendor_name)
                )
            ''')
            
            # Create indexes for performance
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_vendor_library_path ON vendor_library_mappings(path_pattern)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_vendor_library_vendor ON vendor_library_mappings(vendor_name)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_vendor_library_library ON vendor_library_mappings(library_name)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_tag_mappings_pattern ON tag_mappings(pattern)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_tag_mappings_library ON tag_mappings(library_id)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_library_profiles_name ON library_profiles(library_name)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_vendor_profiles_name ON vendor_profiles(vendor_name)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_vendor_specific_words_word ON vendor_specific_words(word)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_vendor_specific_words_vendor ON vendor_specific_words(vendor_name)')
            
            self.conn.commit()
            
            # Auto-sync vendors from knowledge_initial.json if this is a new DB
            # or if vendor_profiles is empty
            if is_new_database or self._should_sync_vendors():
                self._auto_sync_vendors_from_json()
            
            # Only print initialization message once per session
            if not hasattr(KnowledgeDatabase, '_initialized_dbs'):
                KnowledgeDatabase._initialized_dbs = set()
            
            if self.db_path not in KnowledgeDatabase._initialized_dbs:
                debug(f"✅ Knowledge database initialized: {self.db_path}")
                KnowledgeDatabase._initialized_dbs.add(self.db_path)
            
        except Exception as e:
            error(f"❌ Error initializing knowledge database: {e}")
            raise
    
    def _should_sync_vendors(self) -> bool:
        """Check if vendors should be synced (if vendor_profiles is empty)"""
        try:
            self.cursor.execute("SELECT COUNT(*) FROM vendor_profiles")
            count = self.cursor.fetchone()[0]
            return count == 0
        except:
            return True
    
    def _auto_sync_vendors_from_json(self):
        """Automatically sync vendors from knowledge_initial.json on DB initialization"""
        try:
            # Load vendors from knowledge_initial.json
            json_path = Path(__file__).parent / "knowledge_initial.json"
            
            if not json_path.exists():
                # Silent - not an error, just no initial data
                return
            
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                vendors = data.get('vendors', {})
            
            if not vendors:
                return
            
            # Sync vendors to database
            for canonical_name, aliases in vendors.items():
                self.cursor.execute(
                    'SELECT id FROM vendor_profiles WHERE vendor_name = ?',
                    (canonical_name,)
                )
                existing = self.cursor.fetchone()
                
                if not existing:
                    # Add new vendor
                    self.cursor.execute('''
                        INSERT INTO vendor_profiles (vendor_name, display_name, aliases)
                        VALUES (?, ?, ?)
                    ''', (canonical_name, canonical_name, json.dumps(aliases)))
            
            self.conn.commit()
            
            # Check count
            self.cursor.execute("SELECT COUNT(*) FROM vendor_profiles")
            count = self.cursor.fetchone()[0]
            
            if count > 0:
                debug(f"✅ Auto-synced {count} vendors from knowledge_initial.json")
                
        except Exception as e:
            # Silent failure - not critical
            pass
    
    def migrate_from_existing_databases(self):
        """Migrate data from existing vendor_library.db and tag_mappings.db"""
        info("🔄 Migrating data from existing databases...")
        
        # Migrate vendor_library.db
        vendor_library_path = "vendor_library.db"
        if os.path.exists(vendor_library_path):
            debug(f"📦 Migrating vendor_library.db...")
            self._migrate_vendor_library_db(vendor_library_path)
        
        # Migrate tag_mappings.db
        tag_mappings_path = "tag_mappings.db"
        if os.path.exists(tag_mappings_path):
            debug(f"🏷️ Migrating tag_mappings.db...")
            self._migrate_tag_mappings_db(tag_mappings_path)
        
        # Migrate hardcoded vendor specific words
        debug(f"🔤 Migrating hardcoded vendor specific words...")
        self._migrate_hardcoded_vendor_words()
        
        # Migrate tag mappings to new structure
        debug(f"🏷️ Migrating tag mappings to new structure...")
        self._migrate_tag_mappings_to_new_structure()
        
        info("✅ Migration completed!")
    
    def _migrate_vendor_library_db(self, source_path: str):
        """Migrate data from vendor_library.db"""
        try:
            source_conn = sqlite3.connect(source_path)
            source_cursor = source_conn.cursor()
            
            # Check if the old structure exists (vendor_library_mappings table)
            source_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vendor_library_mappings'")
            if source_cursor.fetchone():
                # Old structure with vendor_library_mappings table
                source_cursor.execute('SELECT path_pattern, vendor_name, library_name, confidence FROM vendor_library_mappings')
                mappings = source_cursor.fetchall()
                
                # Insert into knowledge database
                self.cursor.executemany('''
                    INSERT OR REPLACE INTO vendor_library_mappings 
                    (path_pattern, vendor_name, library_name, confidence)
                    VALUES (?, ?, ?, ?)
                ''', mappings)
                
                # Create vendor profiles
                vendors = set(mapping[1] for mapping in mappings)
                for vendor in vendors:
                    self.cursor.execute('''
                        INSERT OR IGNORE INTO vendor_profiles (vendor_name, display_name)
                        VALUES (?, ?)
                    ''', (vendor, vendor))
                
                # Create library profiles
                libraries = set((mapping[1], mapping[2]) for mapping in mappings)
                for vendor, library in libraries:
                    # Get vendor ID
                    self.cursor.execute('SELECT id FROM vendor_profiles WHERE vendor_name = ?', (vendor,))
                    vendor_id = self.cursor.fetchone()
                    if vendor_id:
                        self.cursor.execute('''
                            INSERT OR IGNORE INTO library_profiles (library_name, vendor_id, display_name)
                            VALUES (?, ?, ?)
                        ''', (library, vendor_id[0], library))
                
                debug(f"✅ Migrated {len(mappings)} vendor/library mappings")
            
            else:
                # New structure with separate vendors and libraries tables
                # Migrate vendors
                source_cursor.execute('SELECT name, aliases FROM vendors')
                vendors = source_cursor.fetchall()
                
                for vendor_name, aliases in vendors:
                    self.cursor.execute('''
                        INSERT OR IGNORE INTO vendor_profiles (vendor_name, display_name)
                        VALUES (?, ?)
                    ''', (vendor_name, vendor_name))
                
                # Migrate libraries
                source_cursor.execute('SELECT name, vendor_id FROM libraries')
                libraries = source_cursor.fetchall()
                
                for library_name, vendor_id in libraries:
                    # Get vendor name
                    source_cursor.execute('SELECT name FROM vendors WHERE id = ?', (vendor_id,))
                    vendor_result = source_cursor.fetchone()
                    if vendor_result:
                        vendor_name = vendor_result[0]
                        
                        # Get vendor ID in knowledge database
                        self.cursor.execute('SELECT id FROM vendor_profiles WHERE vendor_name = ?', (vendor_name,))
                        knowledge_vendor_id = self.cursor.fetchone()
                        if knowledge_vendor_id:
                            self.cursor.execute('''
                                INSERT OR IGNORE INTO library_profiles (library_name, vendor_id, display_name)
                                VALUES (?, ?, ?)
                            ''', (library_name, knowledge_vendor_id[0], library_name))
                
                debug(f"✅ Migrated {len(vendors)} vendors and {len(libraries)} libraries")
            
            source_conn.close()
            self.conn.commit()
            
        except Exception as e:
            error(f"❌ Error migrating vendor_library.db: {e}")
    
    def _migrate_tag_mappings_db(self, source_path: str):
        """Migrate data from tag_mappings.db"""
        try:
            source_conn = sqlite3.connect(source_path)
            source_cursor = source_conn.cursor()
            
            # Get all mappings from source
            source_cursor.execute('SELECT pattern, tag_type, tag_value, confidence, is_regex FROM tag_mappings')
            mappings = source_cursor.fetchall()
            
            # Insert into knowledge database
            self.cursor.executemany('''
                INSERT OR REPLACE INTO tag_mappings 
                (pattern, tag_type, tag_value, confidence, is_regex)
                VALUES (?, ?, ?, ?, ?)
            ''', mappings)
            
            source_conn.close()
            self.conn.commit()
            debug(f"✅ Migrated {len(mappings)} tag mappings")
            
        except Exception as e:
            error(f"❌ Error migrating tag_mappings.db: {e}")
    
    def _migrate_hardcoded_vendor_words(self):
        """Migrate hardcoded vendor specific words from database_vendor_extractor.py"""
        try:
            # Hardcoded vendor specific words from database_vendor_extractor.py
            vendor_specific_words = {
                'spitfire': 'Spitfire Audio',
                'eastwest': 'EastWest',
                'cinesamples': 'Cinesamples',
                'heavyocity': 'Heavyocity',
                'synthogy': 'Synthogy'
            }
            
            # Ensure vendors exist in vendor_profiles first
            for word, vendor_name in vendor_specific_words.items():
                self.cursor.execute('''
                    INSERT OR IGNORE INTO vendor_profiles (vendor_name, display_name)
                    VALUES (?, ?)
                ''', (vendor_name, vendor_name))
            
            # Add vendor specific words
            for word, vendor_name in vendor_specific_words.items():
                self.cursor.execute('''
                    INSERT OR REPLACE INTO vendor_specific_words
                    (word, vendor_name, min_length, match_position)
                    VALUES (?, ?, ?, ?)
                ''', (word, vendor_name, 3, 'start'))
            
            self.conn.commit()
            debug(f"✅ Migrated {len(vendor_specific_words)} vendor specific words")
            
        except Exception as e:
            error(f"❌ Error migrating hardcoded vendor words: {e}")
    
    def _migrate_tag_mappings_to_new_structure(self):
        """Migrate existing tag mappings from old structure to new simplified structure"""
        try:
            # Check if we have old structure data in backup
            backup_path = "patchio_knowledge_backup.db"
            if os.path.exists(backup_path):
                debug(f"📦 Migrating from backup database: {backup_path}")
                
                # Connect to backup database
                backup_conn = sqlite3.connect(backup_path)
                backup_cursor = backup_conn.cursor()
                
                # Get all old tag mappings
                backup_cursor.execute('''
                    SELECT pattern, tag_type, tag_value, confidence, is_regex, library_id
                    FROM tag_mappings
                ''')
                old_mappings = backup_cursor.fetchall()
                backup_conn.close()
                
                # Group mappings by pattern to combine multiple tag types for the same pattern
                pattern_groups = {}
                for pattern, tag_type, tag_value, confidence, is_regex, library_id in old_mappings:
                    if pattern not in pattern_groups:
                        pattern_groups[pattern] = {
                        'pattern': pattern,
                        'instrument': None,
                        'genre': None,
                        'mood': None,
                        'format': None,
                        'confidence': confidence,
                        'is_regex': is_regex,
                        'library_id': library_id
                        }
                    
                    # Set the appropriate column based on tag_type
                    if tag_type in ['instrument', 'genre', 'mood', 'format']:
                        pattern_groups[pattern][tag_type] = tag_value
                
                # Insert the combined mappings
                for pattern_data in pattern_groups.values():
                    self.cursor.execute('''
                        INSERT INTO tag_mappings 
                        (pattern, instrument, genre, mood, format, confidence, is_regex, library_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        pattern_data['pattern'],
                        pattern_data['instrument'],
                        pattern_data['genre'],
                        pattern_data['mood'],
                        pattern_data['format'],
                        pattern_data['confidence'],
                        pattern_data['is_regex'],
                        pattern_data['library_id']
                    ))
                
                self.conn.commit()
                debug(f"✅ Migrated {len(pattern_groups)} tag mappings to new structure")
            else:
                warning("ℹ️ No backup database found, skipping tag mappings migration")
            
        except Exception as e:
            error(f"❌ Error migrating tag mappings to new structure: {e}")
    
    def get_vendor_library_mapping(self, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """Get vendor and library for a file path"""
        try:
            # Try exact matches first
            self.cursor.execute('''
                SELECT vendor_name, library_name, confidence
                FROM vendor_library_mappings
                WHERE path_pattern = ?
                ORDER BY confidence DESC
                LIMIT 1
            ''', (file_path,))
            
            result = self.cursor.fetchone()
            if result:
                return result[0], result[1]
            
            # Try pattern matches
            self.cursor.execute('''
                SELECT vendor_name, library_name, confidence
                FROM vendor_library_mappings
                WHERE ? LIKE path_pattern
                ORDER BY confidence DESC, LENGTH(path_pattern) DESC
                LIMIT 1
            ''', (file_path,))
            
            result = self.cursor.fetchone()
            if result:
                return result[0], result[1]
            
            return None, None
            
        except Exception as e:
            error(f"❌ Error getting vendor/library mapping: {e}")
            return None, None
    
    def get_tag_mappings(self, tag_type: str = None) -> List[Tuple[str, str, str, str, str, float, bool]]:
        """Get all tag mappings, optionally filtered by type"""
        try:
            if tag_type and tag_type in ['instrument', 'genre', 'mood', 'format']:
                # Filter by specific tag type (only return rows where that column has a value)
                self.cursor.execute(f'''
                    SELECT pattern, instrument, genre, mood, format, confidence, is_regex
                    FROM tag_mappings
                    WHERE {tag_type} IS NOT NULL
                    ORDER BY confidence DESC, pattern
                ''')
            else:
                self.cursor.execute('''
                    SELECT pattern, instrument, genre, mood, format, confidence, is_regex
                    FROM tag_mappings
                    ORDER BY confidence DESC, pattern
                ''')
            
            return self.cursor.fetchall()
            
        except Exception as e:
            error(f"❌ Error getting tag mappings: {e}")
            return []
    
    def get_library_profile(self, library_name: str) -> Optional[Dict[str, Any]]:
        """Get library profile with all metadata"""
        try:
            self.cursor.execute('''
                SELECT lp.*, vp.vendor_name, vp.display_name as vendor_display_name
                FROM library_profiles lp
                LEFT JOIN vendor_profiles vp ON lp.vendor_id = vp.id
                WHERE lp.library_name = ?
            ''', (library_name,))
            
            row = self.cursor.fetchone()
            if not row:
                return None
            
            # Convert to dictionary
            columns = [desc[0] for desc in self.cursor.description]
            profile = dict(zip(columns, row))
            
            # Parse JSON fields
            for field in ['genre_tags', 'mood_tags', 'character_tags', 'format_tags']:
                if profile[field]:
                    try:
                        profile[field] = json.loads(profile[field])
                    except json.JSONDecodeError:
                        profile[field] = []
                else:
                    profile[field] = []
            
            return profile
            
        except Exception as e:
            error(f"❌ Error getting library profile: {e}")
            return None
    
    def add_tag_mapping(self, pattern: str, instrument = None, genre = None, 
                       mood = None, format = None,
                       confidence: float = 1.0, is_regex: bool = False, 
                       library_id: Optional[int] = None):
        """Add a new tag mapping with the new simplified structure. 
        Values can be strings or lists of strings for multiple values."""
        try:
            # Convert lists to JSON strings
            instrument_json = json.dumps(instrument) if isinstance(instrument, list) else instrument
            genre_json = json.dumps(genre) if isinstance(genre, list) else genre
            mood_json = json.dumps(mood) if isinstance(mood, list) else mood
            format_json = json.dumps(format) if isinstance(format, list) else format
            
            # Check if pattern already exists
            self.cursor.execute('SELECT id FROM tag_mappings WHERE pattern = ?', (pattern,))
            existing = self.cursor.fetchone()
            
            if existing:
                # Update existing mapping
                self.cursor.execute('''
                    UPDATE tag_mappings SET
                        instrument = COALESCE(?, instrument),
                        genre = COALESCE(?, genre),
                        mood = COALESCE(?, mood),
                        format = COALESCE(?, format),
                        confidence = ?,
                        is_regex = ?,
                        library_id = COALESCE(?, library_id)
                    WHERE pattern = ?
                ''', (instrument_json, genre_json, mood_json, format_json, confidence, is_regex, library_id, pattern))
            else:
                # Insert new mapping
                self.cursor.execute('''
                    INSERT INTO tag_mappings
                    (pattern, instrument, genre, mood, format, confidence, is_regex, library_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (pattern, instrument_json, genre_json, mood_json, format_json, confidence, is_regex, library_id))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            error(f"❌ Error adding tag mapping: {e}")
            return False
    
    def _parse_tag_value(self, value):
        """Parse a tag value from database (could be JSON string or regular string)"""
        if not value:
            return None
        try:
            # Try to parse as JSON first
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else [parsed]
        except (json.JSONDecodeError, TypeError):
            # If not JSON, return as single-item list
            return [value] if value else None
    
    def add_vendor_library_mapping(self, path_pattern: str, vendor_name: str, 
                                 library_name: str, confidence: float = 1.0):
        """Add a new vendor/library mapping"""
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO vendor_library_mappings
                (path_pattern, vendor_name, library_name, confidence)
                VALUES (?, ?, ?, ?)
            ''', (path_pattern, vendor_name, library_name, confidence))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            error(f"❌ Error adding vendor/library mapping: {e}")
            return False
    
    def add_vendor_specific_word(self, word: str, vendor_name: str, 
                               min_length: int = 3, match_position: str = 'start'):
        """Add a vendor specific word"""
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO vendor_specific_words
                (word, vendor_name, min_length, match_position)
                VALUES (?, ?, ?, ?)
            ''', (word, vendor_name, min_length, match_position))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            error(f"❌ Error adding vendor specific word: {e}")
            return False
    
    def get_vendor_specific_words(self) -> List[Tuple[str, str, int, str]]:
        """Get all vendor specific words"""
        try:
            self.cursor.execute('''
                SELECT word, vendor_name, min_length, match_position
                FROM vendor_specific_words
                ORDER BY LENGTH(word) DESC, word
            ''')
            return self.cursor.fetchall()
            
        except Exception as e:
            error(f"❌ Error getting vendor specific words: {e}")
            return []
    
    def find_vendor_by_specific_word(self, library_name: str) -> Optional[str]:
        """Find vendor by matching vendor specific words in library name"""
        try:
            library_lower = library_name.lower()
            
            # Get all vendor specific words sorted by length (longest first)
            self.cursor.execute('''
                SELECT word, vendor_name, min_length, match_position
                FROM vendor_specific_words
                ORDER BY LENGTH(word) DESC
            ''')
            
            for word, vendor_name, min_length, match_position in self.cursor.fetchall():
                if len(word) >= min_length:
                    if match_position == 'start':
                        if (library_lower.startswith(word + ' ') or 
                            library_lower.startswith(word + '-') or
                            library_lower == word):
                            return vendor_name
                    elif match_position == 'end':
                        if (library_lower.endswith(' ' + word) or 
                            library_lower.endswith('-' + word) or
                            library_lower == word):
                            return vendor_name
                    elif match_position == 'any':
                        if word in library_lower:
                            return vendor_name
            
            return None
            
        except Exception as e:
            error(f"❌ Error finding vendor by specific word: {e}")
            return None
    
    def export_to_json(self, output_path: str):
        """Export all knowledge to JSON for backup/editing"""
        try:
            knowledge = {
                'vendor_profiles': [],
                'library_profiles': [],
                'vendor_library_mappings': [],
                'tag_mappings': [],
                'vendor_specific_words': []
            }
            
            # Export vendor profiles
            self.cursor.execute('SELECT * FROM vendor_profiles')
            for row in self.cursor.fetchall():
                columns = [desc[0] for desc in self.cursor.description]
                knowledge['vendor_profiles'].append(dict(zip(columns, row)))
            
            # Export library profiles
            self.cursor.execute('SELECT * FROM library_profiles')
            for row in self.cursor.fetchall():
                columns = [desc[0] for desc in self.cursor.description]
                knowledge['library_profiles'].append(dict(zip(columns, row)))
            
            # Export vendor/library mappings
            self.cursor.execute('SELECT * FROM vendor_library_mappings')
            for row in self.cursor.fetchall():
                columns = [desc[0] for desc in self.cursor.description]
                knowledge['vendor_library_mappings'].append(dict(zip(columns, row)))
            
            # Export tag mappings
            self.cursor.execute('SELECT * FROM tag_mappings')
            for row in self.cursor.fetchall():
                columns = [desc[0] for desc in self.cursor.description]
                knowledge['tag_mappings'].append(dict(zip(columns, row)))
            
            # Export vendor specific words
            self.cursor.execute('SELECT * FROM vendor_specific_words')
            for row in self.cursor.fetchall():
                columns = [desc[0] for desc in self.cursor.description]
                knowledge['vendor_specific_words'].append(dict(zip(columns, row)))
            
            # Write to JSON file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(knowledge, f, indent=2, ensure_ascii=False)
            
            debug(f"✅ Exported knowledge to {output_path}")
            return True
            
        except Exception as e:
            error(f"❌ Error exporting knowledge: {e}")
            return False
    
    def import_from_json(self, json_path: str):
        """Import knowledge from JSON configuration file"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            debug(f"✅ Loaded configuration from: {json_path}")
            
            # Temporarily disable foreign key constraints for import
            self.cursor.execute('PRAGMA foreign_keys = OFF')
            
            # Import vendor profiles first
            if 'vendor_profiles' in config:
                for vendor in config['vendor_profiles']:
                    self.cursor.execute('''
                        INSERT OR REPLACE INTO vendor_profiles 
                        (vendor_name, display_name, website, description, default_genre, default_mood, default_character)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        vendor['vendor_name'],
                        vendor.get('display_name', vendor['vendor_name']),
                        vendor.get('website', ''),
                        vendor.get('description', ''),
                        vendor.get('default_genre', ''),
                        vendor.get('default_mood', ''),
                        vendor.get('default_character', '')
                    ))
                debug(f"✅ Imported {len(config['vendor_profiles'])} vendor profiles")
            
            # Import library profiles
            if 'library_profiles' in config:
                for library in config['library_profiles']:
                    # Get vendor ID
                    self.cursor.execute('SELECT id FROM vendor_profiles WHERE vendor_name = ?', (library['vendor_name'],))
                    vendor_result = self.cursor.fetchone()
                    
                    if not vendor_result:
                        warning(f"⚠️ Warning: Vendor '{library['vendor_name']}' not found for library '{library['library_name']}'")
                        continue
                    
                    vendor_id = vendor_result[0]
                    
                    # Convert tag arrays to JSON strings
                    genre_tags = json.dumps(library.get('genre_tags', []))
                    mood_tags = json.dumps(library.get('mood_tags', []))
                    character_tags = json.dumps(library.get('character_tags', []))
                    format_tags = json.dumps(library.get('format_tags', []))
                    
                    self.cursor.execute('''
                        INSERT OR REPLACE INTO library_profiles 
                        (library_name, vendor_id, display_name, description, genre_tags, mood_tags, character_tags, format_tags)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        library['library_name'],
                        vendor_id,
                        library.get('display_name', library['library_name']),
                        library.get('description', ''),
                        genre_tags,
                        mood_tags,
                        character_tags,
                        format_tags
                    ))
                debug(f"✅ Imported {len(config['library_profiles'])} library profiles")
            
            # Import tag mappings
            if 'tag_mappings' in config:
                for mapping in config['tag_mappings']:
                    # Get library ID if specified
                    library_id = None
                    if mapping.get('library_name'):
                        self.cursor.execute('SELECT id FROM library_profiles WHERE library_name = ?', (mapping['library_name'],))
                        library_result = self.cursor.fetchone()
                        if library_result:
                            library_id = library_result[0]
                    
                    # Convert tag values to JSON if they are lists
                    instrument = json.dumps(mapping['instrument']) if isinstance(mapping.get('instrument'), list) else mapping.get('instrument')
                    genre = json.dumps(mapping['genre']) if isinstance(mapping.get('genre'), list) else mapping.get('genre')
                    mood = json.dumps(mapping['mood']) if isinstance(mapping.get('mood'), list) else mapping.get('mood')
                    format_tag = json.dumps(mapping['format']) if isinstance(mapping.get('format'), list) else mapping.get('format')
                    
                    self.cursor.execute('''
                        INSERT OR REPLACE INTO tag_mappings 
                        (pattern, instrument, genre, mood, format, confidence, is_regex, library_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        mapping['pattern'],
                        instrument,
                        genre,
                        mood,
                        format_tag,
                        mapping.get('confidence', 1.0),
                        mapping.get('is_regex', False),
                        library_id
                    ))
                debug(f"✅ Imported {len(config['tag_mappings'])} tag mappings")
            
            # Import vendor specific words
            if 'vendor_specific_words' in config:
                for word_data in config['vendor_specific_words']:
                    # Check if vendor exists before inserting
                    self.cursor.execute('SELECT vendor_name FROM vendor_profiles WHERE vendor_name = ?', (word_data['vendor_name'],))
                    if not self.cursor.fetchone():
                        warning(f"⚠️ Warning: Vendor '{word_data['vendor_name']}' not found for word '{word_data['word']}', skipping")
                        continue
                    
                    self.cursor.execute('''
                        INSERT OR REPLACE INTO vendor_specific_words 
                        (word, vendor_name, min_length, match_position)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        word_data['word'],
                        word_data['vendor_name'],
                        word_data.get('min_length', 3),
                        word_data.get('match_position', 'start')
                    ))
                debug(f"✅ Imported {len(config['vendor_specific_words'])} vendor specific words")
            
            # Re-enable foreign key constraints
            self.cursor.execute('PRAGMA foreign_keys = ON')
            
            self.conn.commit()
            info("✅ Configuration import completed successfully!")
            return True
            
        except Exception as e:
            error(f"❌ Error importing configuration: {e}")
            # Re-enable foreign key constraints even if there's an error
            try:
                self.cursor.execute('PRAGMA foreign_keys = ON')
            except:
                pass
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge database"""
        try:
            stats = {}
            
            # Count records in each table
            tables = ['vendor_profiles', 'library_profiles', 'vendor_library_mappings', 'tag_mappings', 'vendor_specific_words']
            for table in tables:
                self.cursor.execute(f'SELECT COUNT(*) FROM {table}')
                stats[f'{table}_count'] = self.cursor.fetchone()[0]
            
            # Count by tag type (new structure)
            tag_types = ['instrument', 'genre', 'mood', 'format']
            stats['tag_mappings_by_type'] = {}
            for tag_type in tag_types:
                self.cursor.execute(f'SELECT COUNT(*) FROM tag_mappings WHERE {tag_type} IS NOT NULL')
                count = self.cursor.fetchone()[0]
                if count > 0:
                    stats['tag_mappings_by_type'][tag_type] = count
            
            # Database size
            stats['database_size_mb'] = os.path.getsize(self.db_path) / (1024 * 1024)
            
            return stats
            
        except Exception as e:
            error(f"❌ Error getting database stats: {e}")
            return {}
    
    # Vendor/Library Extraction Methods (merged from database_vendor_extractor.py)
    
    def get_all_vendors(self) -> List[str]:
        """Get all vendors from the database"""
        try:
            self.cursor.execute('SELECT vendor_name FROM vendor_profiles ORDER BY vendor_name')
            return [row[0] for row in self.cursor.fetchall()]
        except Exception as e:
            error(f"❌ Error getting vendors: {e}")
            return []
    
    def find_library_mapping(self, path: str) -> Optional[Tuple[str, str]]:
        """Find vendor/library mapping by searching for library names in the path"""
        path_lower = path.lower()
        
        # Get all libraries sorted by length (longest first) to avoid partial matches
        self.cursor.execute('''
            SELECT lp.library_name, vp.vendor_name 
            FROM library_profiles lp 
            JOIN vendor_profiles vp ON lp.vendor_id = vp.id 
            ORDER BY LENGTH(lp.library_name) DESC
        ''')
        
        for library_name, vendor_name in self.cursor.fetchall():
            if library_name.lower() in path_lower:
                # Skip generic terms like "Kontakt" if we can find a better vendor match
                if library_name.lower() == "kontakt":
                    # Check if there's a known vendor in the path that should take priority
                    vendors = self.get_all_vendors()
                    for vendor in vendors:
                        if vendor.lower() in path_lower and vendor.lower() != "native instruments":
                            # Found a better vendor match, skip the generic "Kontakt" match
                            break
                    else:
                        # No better vendor found, use the Kontakt match
                        return vendor_name, library_name
                else:
                    return vendor_name, library_name
        
        return None
    
    def find_vendor_in_path(self, path: str) -> Optional[Tuple[str, str]]:
        """Find vendor in path using exact matching only"""
        path_obj = Path(path)
        path_parts = [part for part in path_obj.parts]
        
        # Get all vendors
        vendors = self.get_all_vendors()
        
        # Store all exact matches with their scores for prioritization
        matches = []
        
        for vendor in vendors:
            vendor_lower = vendor.lower()
            
            # Check each path part for exact vendor name match
            for i, part in enumerate(path_parts):
                part_lower = part.lower()
                
                # Only exact matches - no partial matching
                if part_lower == vendor_lower:
                    # Try to extract library name from surrounding context
                    library_name = self.extract_library_from_vendor_context(path_parts, vendor, part)
                    # Score: earlier in path gets higher priority
                    score = 1000 - i  # Higher score for earlier path positions
                    matches.append((score, vendor, library_name, 'exact'))
        
        # Return the match with the highest score (earliest in path)
        if matches:
            matches.sort(key=lambda x: x[0], reverse=True)
            best_match = matches[0]
            return best_match[1], best_match[2]  # Return vendor, library_name
        
        return None
    
    def extract_library_from_vendor_context(self, path_parts: list, vendor: str, vendor_part: str) -> Optional[str]:
        """Extract library name from the context around a vendor match"""
        vendor_index = None
        for i, part in enumerate(path_parts):
            if part.lower() == vendor_part.lower():
                vendor_index = i
                break
        
        if vendor_index is None:
            return None
        
        # First, check for Kontakt library files (.nicnt) in the directory tree
        # This is the highest priority for Kontakt libraries
        nicnt_library_name = self._find_kontakt_library_name(path_parts)
        if nicnt_library_name:
            return nicnt_library_name
        
        # Look for library name in nearby path parts
        # Check the part after the vendor
        if vendor_index + 1 < len(path_parts):
            next_part = path_parts[vendor_index + 1]
            if len(next_part) > 2 and not next_part.lower() in ['library', 'libraries', 'samples', 'sample']:
                # Remove file extension if present
                return os.path.splitext(next_part)[0]
        
        # Check the part before the vendor
        if vendor_index - 1 >= 0:
            prev_part = path_parts[vendor_index - 1]
            if len(prev_part) > 2 and not prev_part.lower() in ['library', 'libraries', 'samples', 'sample']:
                # Remove file extension if present
                return os.path.splitext(prev_part)[0]
        
        # If no clear library name found, return the vendor part itself
        return vendor_part
    
    def _find_kontakt_library_name(self, path_parts: list) -> Optional[str]:
        """Find Kontakt library name by looking for .nicnt files in the directory tree"""
        try:
            # Start from the file's directory and walk up the tree
            current_path = os.sep.join(path_parts)
            
            # Walk up the directory tree to find .nicnt files
            while current_path and current_path != os.path.dirname(current_path):  # Stop at root
                try:
                    # Look for .nicnt files in this directory
                    for file in os.listdir(current_path):
                        if file.lower().endswith('.nicnt'):
                            # Found a .nicnt file - use its name (without extension) as the library name
                            library_name = os.path.splitext(file)[0]
                            return library_name
                except (OSError, PermissionError):
                    # Skip if we can't access the directory
                    pass
                
                # Move up one level
                current_path = os.path.dirname(current_path)
            
            return None
            
        except Exception as e:
            # If anything goes wrong, return None to fall back to other methods
            return None
    
    
    def extract_vendor_library(self, path: str) -> Tuple[str, str]:
        """Extract vendor and library from file path using database knowledge"""
        # First try to find library mapping (highest priority - most accurate)
        library_mapping = self.find_library_mapping(path)
        if library_mapping:
            return library_mapping
        
        # Then try to find vendor in path (database knowledge)
        vendor_mapping = self.find_vendor_in_path(path)
        if vendor_mapping:
            return vendor_mapping
        
        # Check for Kontakt library files (.nicnt) even if no vendor match found
        # This handles cases like GROTH where the vendor isn't in the database
        from pathlib import Path
        path_parts = [part for part in Path(path).parts]
        nicnt_library_name = self._find_kontakt_library_name(path_parts)
        if nicnt_library_name:
            # Try to extract vendor from the library name or path
            vendor = self.extract_vendor_from_library_name(nicnt_library_name, path_parts)
            return vendor, nicnt_library_name
        
        # Fallback: use original PatchIO vendor extraction logic
        vendor = self._extract_vendor_original_patchio_logic(path)
        library = self._extract_library_original_patchio_logic(path)
        return vendor, library
    
    def extract_vendor_from_library_name(self, library_name: str, path_parts: list) -> str:
        """Extract vendor from library name using vendor-specific words"""
        # Get vendor-specific words
        vendor_words = self.get_vendor_specific_words()
        
        # Check each path part against vendor-specific words
        for part in path_parts:
            part_lower = part.lower()
            
            for word, vendor, confidence, _ in vendor_words:
                if word.lower() in part_lower:
                    return vendor
        
        return "Unknown Vendor"
    
    def _extract_vendor_original_patchio_logic(self, path: str) -> str:
        """Extract vendor using knowledge database as source of truth"""
        try:
            # Use knowledge database instead of JSON config
            # This is a fallback method, so we'll use simple extraction
            
            # Check for vendor-specific words in the path
            vendor_words = self.get_vendor_specific_words()
            path_lower = path.lower()
            
            for word, vendor, confidence, _ in vendor_words:
                if word.lower() in path_lower:
                    return vendor
            
            # Simple fallback: look for common vendor names in path using knowledge database
            fallback_vendors = self.get_all_vendors()
            
            for vendor in fallback_vendors:
                if vendor.lower() in path_lower:
                    return vendor
            
            return "Unknown Vendor"
            
        except Exception as e:
            error(f"⚠️ Error in original vendor extraction: {e}")
            return "Unknown Vendor"
    
    def _extract_library_original_patchio_logic(self, path: str) -> str:
        """Extract library using FileModel as single source of truth"""
        try:
            # Import file model for library extraction
            from models.file_model import FileModel
            from models.user_settings_model import UserSettingsModel
            
            # Create file model instance
            settings_model = UserSettingsModel()
            file_model = FileModel(settings_model)
            
            # Use FileModel as single source of truth
            library = file_model.extract_library_info(path)
            return library if library else "Unknown Library"
            
        except Exception as e:
            error(f"⚠️ Error in library extraction: {e}")
            return "Unknown Library"
    
    def add_vendor(self, vendor_name: str, aliases: List[str] = None) -> bool:
        """Add a new vendor to the database"""
        try:
            self.cursor.execute('''
                INSERT OR IGNORE INTO vendor_profiles (vendor_name) 
                VALUES (?)
            ''', (vendor_name,))
            self.conn.commit()
            return True
        except Exception as e:
            error(f"❌ Error adding vendor {vendor_name}: {e}")
            return False
    
    def add_library(self, library_name: str, vendor_name: str, aliases: List[str] = None) -> bool:
        """Add a new library to the database"""
        try:
            # Get vendor ID
            self.cursor.execute('SELECT id FROM vendor_profiles WHERE vendor_name = ?', (vendor_name,))
            vendor_result = self.cursor.fetchone()
            
            if not vendor_result:
                # Vendor doesn't exist, create it
                self.add_vendor(vendor_name)
                self.cursor.execute('SELECT id FROM vendor_profiles WHERE vendor_name = ?', (vendor_name,))
                vendor_result = self.cursor.fetchone()
            
            vendor_id = vendor_result[0]
            
            # Add library
            self.cursor.execute('''
                INSERT OR IGNORE INTO library_profiles (library_name, vendor_id) 
                VALUES (?, ?)
            ''', (library_name, vendor_id))
            self.conn.commit()
            return True
        except Exception as e:
            error(f"❌ Error adding library {library_name}: {e}")
            return False

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

def main():
    """Main function for testing and management"""
    import sys
    
    if len(sys.argv) < 2:
        debug("Usage: python3 knowledge_database.py [init|migrate|stats|export|import]")
        debug("  init     - Initialize database schema")
        debug("  migrate  - Migrate from existing databases")
        debug("  stats    - Show database statistics")
        debug("  export   - Export database to JSON")
        debug("  import   - Import database from JSON")
        return
    
    command = sys.argv[1]
    knowledge_db = KnowledgeDatabase()
    
    try:
        if command == "init":
            debug("✅ Knowledge database initialized")
        elif command == "migrate":
            knowledge_db.migrate_from_existing_databases()
        elif command == "stats":
            stats = knowledge_db.get_database_stats()
            debug("📊 Knowledge Database Statistics:")
            for key, value in stats.items():
                debug(f"  {key}: {value}")
        elif command == "export":
            output_path = sys.argv[2] if len(sys.argv) > 2 else "utils/database/database_config.json"
            knowledge_db.export_to_json(output_path)
        elif command == "import":
            json_path = sys.argv[2] if len(sys.argv) > 2 else "utils/database/database_config.json"
            knowledge_db.import_from_json(json_path)
        else:
            debug(f"Unknown command: {command}")
    
    finally:
        knowledge_db.close()

if __name__ == "__main__":
    main()
