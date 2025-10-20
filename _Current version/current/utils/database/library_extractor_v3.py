#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Library Extractor V3 - Simple & Universal
Based on user specification: Analyze from end to start

RULE:
1. If .nki/.nkm is inside "Instruments", "Instrument", "Instruments *", or "Multis" folder
   → Library = parent of that folder
2. Otherwise
   → Library = immediate parent folder of the .nki file
"""

import os
import json
import threading
from pathlib import Path
from typing import Tuple, Optional, Dict, List
import re
from utils.logger import debug, info, warning, error, critical


class LibraryExtractorV3:
    """
    Simple, universal library extractor based on folder structure.
    No learning, no complexity - just follows the rule!
    """
    
    # Path to initial vendor knowledge JSON file (same directory as this file)
    KNOWLEDGE_JSON_PATH = "knowledge_initial.json"
    
    # DAW project file extensions
    PROJECT_EXTENSIONS = {'.cpr', '.logicx', '.als', '.flp', '.ptx', '.song', '.rpp'}
    
    # 🚀 Shared vendor cache (loaded once from knowledge DB, shared across all threads)
    # Thread-safe: Python dicts/sets are thread-safe for reads
    _shared_vendors_cache = None
    _cache_lock = threading.Lock()
    
    @classmethod
    def _load_vendors_from_json(cls) -> Dict[str, List[str]]:
        """
        Load vendor database from knowledge_initial.json.
        
        Returns:
            Dictionary of canonical_name → [aliases]
        """
        try:
            # Get the directory of this file
            script_dir = Path(__file__).parent
            
            # JSON file is in the same directory
            json_path = script_dir / cls.KNOWLEDGE_JSON_PATH
            
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    vendors = data.get('vendors', {})
                    if vendors:
                        return vendors
            
            # JSON file not found - return empty dict
            error(f"❌ ERROR: knowledge_initial.json not found!")
            debug(f"   Expected location: {json_path}")
            debug(f"   Please ensure the file exists in the database directory.")
            return {}
            
        except Exception as e:
            error(f"❌ ERROR loading knowledge_initial.json: {e}")
            debug(f"   Please check the JSON file format.")
            return {}
    
    @classmethod
    def get_default_vendors(cls) -> Dict[str, List[str]]:
        """
        Get the default vendor database from knowledge_initial.json.
        
        Returns:
            Dictionary of canonical_name → [aliases]
            Empty dict if JSON file not found
        """
        return cls._load_vendors_from_json()
    
    def __init__(self, use_knowledge_db: bool = True):
        """
        Initialize the library extractor.
        
        🚀 Thread-safe: Uses shared vendor cache (loaded once from knowledge DB).
        
        Args:
            use_knowledge_db: If True, load vendors from knowledge database (cached).
                             If False, load from knowledge_initial.json.
        """
        self.knowledge_db = None  # No DB connection stored (thread-safe!)
        self._project_cache = {}  # Cache project detection results per folder
        
        if use_knowledge_db:
            # 🚀 Use shared vendor cache (loaded once from knowledge DB, thread-safe)
            self.known_vendors, self.vendor_aliases_map = self._get_or_load_shared_vendors()
        else:
            # Load from JSON file only
            self.known_vendors, self.vendor_aliases_map = self._build_default_vendor_set()
    
    @classmethod
    def _get_or_load_shared_vendors(cls):
        """
        Get vendors from shared cache (loads once from knowledge DB if needed).
        
        🚀 Thread-safe: Only loads from DB once, then all threads share the cache.
        Knowledge DB is the single source of truth.
        
        Returns:
            (known_vendors set, alias_map dict) - Shared across all instances/threads
        """
        # Check if cache is already populated
        if cls._shared_vendors_cache is not None:
            return cls._shared_vendors_cache
        
        # Load from knowledge DB (only happens once)
        with cls._cache_lock:
            # Double-check after acquiring lock
            if cls._shared_vendors_cache is not None:
                return cls._shared_vendors_cache
            
            try:
                # Import here to avoid circular dependencies
                try:
                    from .knowledge_database import KnowledgeDatabase
                except ImportError:
                    from knowledge_database import KnowledgeDatabase
                
                # Create temporary DB connection to load vendors
                kb = KnowledgeDatabase()
                
                # Load vendor aliases from knowledge DB
                known_vendors = set()
                alias_map = {}
                
                kb.cursor.execute('SELECT vendor_name, aliases FROM vendor_profiles')
                
                for canonical_name, aliases_json in kb.cursor.fetchall():
                    try:
                        aliases = json.loads(aliases_json) if aliases_json else []
                        for alias in aliases:
                            alias_lower = alias.lower()
                            known_vendors.add(alias_lower)
                            alias_map[alias_lower] = canonical_name
                    except:
                        # If parsing fails, use canonical name as alias
                        alias_lower = canonical_name.lower()
                        known_vendors.add(alias_lower)
                        alias_map[alias_lower] = canonical_name
                
                # Close DB connection (we only needed it to load vendors)
                kb.close()
                
                # Cache the results (shared across all threads)
                cls._shared_vendors_cache = (known_vendors, alias_map)
                
                return cls._shared_vendors_cache
                
            except Exception as e:
                warning(f"⚠️  Could not load from knowledge DB: {e}")
                # Fallback to JSON
                known_vendors, alias_map = cls._build_default_vendor_set_static()
                cls._shared_vendors_cache = (known_vendors, alias_map)
                return cls._shared_vendors_cache
    
    @classmethod
    def _build_default_vendor_set_static(cls):
        """Static version of _build_default_vendor_set for class-level use"""
        known_vendors = set()
        alias_map = {}
        
        default_vendors = cls.get_default_vendors()
        
        for canonical_name, aliases in default_vendors.items():
            for alias in aliases:
                alias_lower = alias.lower()
                known_vendors.add(alias_lower)
                alias_map[alias_lower] = canonical_name
        
        return known_vendors, alias_map
    
    def _build_default_vendor_set(self):
        """
        Build vendor set and alias map from knowledge_initial.json.
        
        Returns:
            (known_vendors set, alias_map dict)
        """
        known_vendors = set()
        alias_map = {}
        
        default_vendors = self.get_default_vendors()
        
        for canonical_name, aliases in default_vendors.items():
            for alias in aliases:
                alias_lower = alias.lower()
                known_vendors.add(alias_lower)
                alias_map[alias_lower] = canonical_name
        
        return known_vendors, alias_map
    
    def _sync_vendors_to_knowledge_db(self):
        """Sync vendors from knowledge_initial.json to knowledge database"""
        if not self.knowledge_db:
            return
        
        try:
            import json
            
            default_vendors = self.get_default_vendors()
            
            for canonical_name, aliases in default_vendors.items():
                # Check if vendor already exists
                self.knowledge_db.cursor.execute(
                    'SELECT id FROM vendor_profiles WHERE vendor_name = ?',
                    (canonical_name,)
                )
                existing = self.knowledge_db.cursor.fetchone()
                
                if not existing:
                    # Add new vendor
                    self.knowledge_db.cursor.execute('''
                        INSERT INTO vendor_profiles (vendor_name, display_name, aliases)
                        VALUES (?, ?, ?)
                    ''', (canonical_name, canonical_name, json.dumps(aliases)))
                else:
                    # Update aliases if needed
                    self.knowledge_db.cursor.execute('''
                        UPDATE vendor_profiles
                        SET aliases = ?
                        WHERE vendor_name = ?
                    ''', (json.dumps(aliases), canonical_name))
            
            self.knowledge_db.conn.commit()
            
        except Exception as e:
            warning(f"⚠️  Could not sync vendors to knowledge database: {e}")
    
    def _load_vendors_from_knowledge_db(self):
        """
        Load vendor aliases from knowledge database.
        
        Returns:
            (known_vendors set, alias_map dict)
        """
        if not self.knowledge_db:
            return set(), {}
        
        try:
            import json
            
            known_vendors = set()
            alias_map = {}
            
            # Load all vendor profiles
            self.knowledge_db.cursor.execute('''
                SELECT vendor_name, aliases
                FROM vendor_profiles
            ''')
            
            for canonical_name, aliases_json in self.knowledge_db.cursor.fetchall():
                try:
                    # Parse aliases from aliases field
                    aliases = json.loads(aliases_json) if aliases_json else []
                    
                    for alias in aliases:
                        alias_lower = alias.lower()
                        known_vendors.add(alias_lower)
                        alias_map[alias_lower] = canonical_name
                        
                except json.JSONDecodeError:
                    # If not JSON, treat as single alias
                    alias_lower = canonical_name.lower()
                    known_vendors.add(alias_lower)
                    alias_map[alias_lower] = canonical_name
            
            return known_vendors, alias_map
            
        except Exception as e:
            warning(f"⚠️  Could not load vendors from knowledge database: {e}")
            return set(), {}
    
    def detect_project(self, file_path: str, project_map: dict = None) -> Optional[str]:
        """
        Detect if audio file is part of a DAW project.
        
        🚀 FAST: If project_map provided (from pre-scan), uses instant lookup.
        Otherwise, searches up to 5 levels backwards for project files.
        
        Args:
            file_path: Path to audio file
            project_map: Optional pre-scanned map of {folder_path: project_name}
            
        Returns:
            Project name (folder name) or None if not in a project
        """
        # Only process audio files
        if not file_path.lower().endswith(('.wav', '.aiff', '.mp3', '.flac', '.ogg')):
            return None
        
        parts = Path(file_path).parts
        
        # 🚀 SPECIAL: Check if audio file is INSIDE a .logicx package
        # If so, use the .logicx folder name (without extension) as project name
        for i, part in enumerate(parts):
            if part.lower().endswith('.logicx'):
                # Remove .logicx extension (7 chars) to get clean project name
                project_name = part[:-7]
                return project_name
        
        # 🚀 FAST PATH: Use pre-scanned project map (instant lookup, no I/O)
        if project_map:
            # Check parent folders up to 5 levels
            for i in range(len(parts) - 1, max(0, len(parts) - 6), -1):
                folder = os.path.join('/', *parts[:i+1])
                if folder in project_map:
                    return project_map[folder]
            return None
        
        # SLOW PATH: Scan folders dynamically (only if project_map not provided)
        # Search up to 5 levels backwards
        for i in range(len(parts) - 1, max(0, len(parts) - 6), -1):
            folder = os.path.join('/', *parts[:i+1])
            
            # Check cache first
            if folder in self._project_cache:
                return self._project_cache[folder]
            
            try:
                for item in os.listdir(folder):
                    item_path = os.path.join(folder, item)
                    # Check for project files (.cpr, .als, etc.)
                    if os.path.isfile(item_path) and any(item.lower().endswith(ext) for ext in self.PROJECT_EXTENSIONS):
                        project_name = parts[i]
                        self._project_cache[folder] = project_name
                        return project_name
                    # Check for Logic project folders (.logicx)
                    elif os.path.isdir(item_path) and item.lower().endswith('.logicx'):
                        project_name = parts[i]
                        self._project_cache[folder] = project_name
                        return project_name
            except OSError:
                # Can't access folder, continue
                continue
        
        # No project found - cache the negative result
        self._project_cache[file_path] = None
        return None
    
    def extract_vendor_library(self, file_path: str, known_libraries: list = None, project_map: dict = None) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Extract vendor, library, and project from file path.
        
        🚀 PROJECT DETECTION: For audio files, checks if part of a DAW project first.
        If project detected, returns ('User', None, project_name).
        
        🚀 ROBUST: For audio files, checks if any known library name exists in path.
        This allows .wav files to inherit library names from .nki files.
        
        TWO-STAGE SEARCH (for robustness):
        Stage 1: Look for EXACT match folders (Instruments, Patches, etc.)
        Stage 2: If not found, look for compound names (Celtic Wind Instruments, etc.)
        
        Args:
            file_path: Path to any file (.nki, .wav, .ogg, etc.)
            known_libraries: Optional list of library names from database (for audio file matching)
            project_map: Optional pre-scanned map of {folder_path: project_name} for fast lookup
            
        Returns:
            (vendor, library, project) tuple
        """
        # Check for project first (only for audio files)
        project_name = self.detect_project(file_path, project_map)
        if project_name:
            return 'User', None, project_name
        
        parts = [p for p in Path(file_path).parts if p]
        
        if len(parts) < 2:  # Need at least a folder and filename
            return 'Unknown Vendor', 'Unknown Library', None
        
        # STAGE 1a: Look for "Instruments", "Instrument", "Samples", "Multis", "Snapshots", or "Layers" FIRST (highest priority!)
        # 🚀 CRITICAL: Structural detection comes FIRST (more reliable than string matching)
        # This ensures we find the main library folder, not subfolders like "Presets"
        # Search backwards from the file towards root
        library_name = None
        
        # Check file extension for special rules
        is_ytil_file = file_path.lower().endswith('.ytil')
        
        for i in range(len(parts) - 2, -1, -1):  # Search backwards
            folder = parts[i]
            folder_lower = folder.lower()
            
            # Build list of primary folders to check
            primary_folders = ['instruments', 'instrument', 'samples', 'multis', 'snapshots']
            
            # Add "layers" ONLY for Engine (.ytil) files
            if is_ytil_file:
                primary_folders.append('layers')
            
            # Check for primary library content folders (exact matches only)
            if folder_lower in primary_folders and folder_lower not in self.known_vendors:
                # 🚀 ROBUST: For "Samples", check sibling "Instruments" folder
                # This distinguishes: Library/Samples vs TopLevel/Samples/Library
                if folder_lower == 'samples' and i > 0:
                    parent_path = os.path.join('/', *parts[:i])
                    instruments_sibling = os.path.join(parent_path, 'Instruments')
                    instrument_sibling = os.path.join(parent_path, 'Instrument')
                    
                    if os.path.exists(instruments_sibling) or os.path.exists(instrument_sibling):
                        # Sibling exists → parent is the library
                        library_name = parts[i - 1]
                        break
                    elif i + 1 < len(parts):
                        # No sibling → check if next folder contains Instruments
                        next_folder_path = os.path.join('/', *parts[:i+2])
                        instruments_inside = os.path.join(next_folder_path, 'Instruments')
                        instrument_inside = os.path.join(next_folder_path, 'Instrument')
                        
                        if os.path.exists(instruments_inside) or os.path.exists(instrument_inside):
                            # Next folder has Instruments → it's the library
                            library_name = parts[i + 1]
                            break
                    # If neither, fall through to default behavior below
                
                # Default behavior for all other primary folders
                if library_name is None:
                    if i > 0:
                        library_name = parts[i - 1]
                    else:
                        library_name = folder
                    break
        
        # STAGE 1b: If "Instruments" not found, look for other exact matches
        if library_name is None:
            for i in range(len(parts) - 2, -1, -1):  # Search backwards
                folder = parts[i]
                
                if self._is_exact_instrument_folder(folder):
                    # Found exact match! Use its parent
                    if i > 0:
                        library_name = parts[i - 1]
                    else:
                        library_name = folder
                    break
        
        # STAGE 2: If no exact match, look for compound names
        if library_name is None:
            for i in range(len(parts) - 2, -1, -1):  # Search backwards
                folder = parts[i]
                
                if self._is_compound_instrument_folder(folder):
                    # Found compound match! Use its parent
                    if i > 0:
                        library_name = parts[i - 1]
                    else:
                        library_name = folder
                    break
        
        # STAGE 3: Fallback to known_libraries string matching (for audio files only)
        # 🚀 ROBUST: This is a fallback when structural detection fails
        # Only used for audio files to inherit library names from .nki files
        if library_name is None and known_libraries and file_path.lower().endswith(('.wav', '.aiff', '.ogg', '.flac', '.mp3')):
            # Sort by length (longest first) for most specific match
            for lib_name in sorted(known_libraries, key=len, reverse=True):
                if lib_name in file_path and lib_name != 'Unknown Library':
                    # Additional validation: Skip drive names (they tend to be short or have specific patterns)
                    # Only accept if library name is reasonably specific (> 5 chars) or contains multiple words
                    if len(lib_name) > 5 or ' ' in lib_name or '-' in lib_name:
                        library_name = lib_name
                        break
        
        # If still no match, use immediate parent (RULE 2)
        if library_name is None:
            library_name = parts[-2] if len(parts) >= 2 else 'Unknown Library'
        
        # Find vendor in the path
        vendor_name = self._find_vendor_in_path(file_path, parts)
        
        return vendor_name, library_name, None
    
    def _is_exact_instrument_folder(self, folder_name: str) -> bool:
        """
        Check for EXACT matches only (Stage 1 - highest priority).
        
        Matches:
        - "Instruments"
        - "Instrument"
        - "Patches"
        - "Multis"
        - "Samples"
        - etc.
        """
        folder_lower = folder_name.lower()
        
        # Check if it's a vendor first (exclude vendors!)
        if folder_lower in self.known_vendors:
            return False
        
        # Exact matches only
        return folder_lower in ['instruments', 'instrument', 'multis', 
                               'patches', 'presets', 'samples', 'sounds', 'snapshots']
    
    def _is_compound_instrument_folder(self, folder_name: str) -> bool:
        """
        Check for COMPOUND matches (Stage 2 - lower priority).
        
        Matches:
        - "Celtic Wind Instruments" (ends with)
        - "Instruments Main" (starts with)
        - "Main-Instruments" (ends with hyphen)
        - "Performance WAVs" (ends with WAV/WAVs) - NEW!
        """
        folder_lower = folder_name.lower()
        
        # Check if it's a vendor first (exclude vendors!)
        if folder_lower in self.known_vendors:
            return False
        
        # Starts with patterns
        if (folder_lower.startswith('instruments ') or 
            folder_lower.startswith('instrument ') or
            folder_lower.startswith('samples ') or
            folder_lower.startswith('patches ') or
            folder_lower.startswith('presets ')):
            return True
        
        # Ends with patterns
        if (folder_lower.endswith(' instruments') or 
            folder_lower.endswith(' instrument') or
            folder_lower.endswith('-instruments') or
            folder_lower.endswith('-instrument') or
            folder_lower.endswith(' samples') or
            folder_lower.endswith(' patches') or
            folder_lower.endswith(' wavs') or
            folder_lower.endswith(' wav') or
            folder_lower.endswith('-wavs') or
            folder_lower.endswith('-wav')):
            return True
        
        return False
    
    def _find_vendor_in_path(self, file_path: str, parts: list) -> str:
        """
        Find vendor name in the path.
        Searches through all folders for known vendors.
        Returns the canonical vendor name (not the alias).
        """
        path_lower = file_path.lower()
        
        # Method 1: Exact folder match
        for part in parts:
            part_lower = part.lower()
            if part_lower in self.known_vendors:
                # Return canonical name from alias map
                return self.vendor_aliases_map.get(part_lower, part)
        
        # Method 2: Partial match (for multi-word vendors)
        for vendor_alias in sorted(self.known_vendors, key=len, reverse=True):
            if vendor_alias in path_lower and len(vendor_alias) >= 3:
                # Return canonical name for this alias
                return self.vendor_aliases_map.get(vendor_alias, vendor_alias.title())
        
        return 'Unknown Vendor'
    
    def add_vendor(self, vendor_name: str):
        """Add a new vendor to the known vendors list"""
        self.known_vendors.add(vendor_name.lower())


# Convenience function
def extract_library_v3(file_path: str) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Quick extraction using V3 simple rules.
    
    Usage:
        vendor, library, project = extract_library_v3("/path/to/file.nki")
    """
    extractor = LibraryExtractorV3()
    return extractor.extract_vendor_library(file_path)


# Demo
if __name__ == "__main__":
    debug("\n🚀 LIBRARY EXTRACTOR V3 - SIMPLE & UNIVERSAL\n")
    debug("="*80)
    
    extractor = LibraryExtractorV3()
    
    test_paths = [
        # Your specific problem paths
        "/Volumes/Samsung 850 EVO/Non Player Libraries/Performance Samples/Pacific - Ensemble Strings/Instruments/Bonus Content/Lite Full Strings Patches/Pacific - Ens Strings - Lite Full Str - Spiccatos.nki",
        "/Volumes/Samsung 850 EVO/Non Player Libraries/8Dio/Agitato Grandiose Legato Ensemble & Divisi Cellos/8Dio Agitato Grandiose Cellos Divisi/Instruments/Agitato_Short_Dyn_Bow_Cellos_Divisi.nki",
        
        # Various structures
        "/Spitfire Audio/BBC Symphony Orchestra/Instruments/Strings/Violins.nki",
        "/Heavyocity/MS Ensemble Woods/Instruments/Kits/Bamboo.nki",
        "/DECADENCE - Trailer Toms/Instruments/WAR DRUM.nki",
        "/BBC Symphony/Violins.nki",  # No Instruments folder
        "/Libraries/GROTH/Instruments/Organic/Pad.nki",
    ]
    
    for path in test_paths:
        vendor, library, project = extractor.extract_vendor_library(path)
        debug(f"\nPath: ...{path[-70:]}")
        debug(f"  → {vendor} / {library}")
        if project:
            debug(f"  → Project: {project}")
    
    debug("\n" + "="*80)
    info("✅ V3 Extractor Demo Complete\n")

