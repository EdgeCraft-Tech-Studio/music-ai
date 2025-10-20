#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Library Folder Mapper - Two-Pass Library Extraction

CONCEPT:
1. First pass: Extract library names from .nki files (using V3 rules)
2. Build mapping: folder_path → library_name
3. Second pass: All files in same folder get same library name

This ensures consistency across .nki, .wav, .aiff, and all other files!
"""

import os
from pathlib import Path
from typing import Dict, Tuple, Optional
from library_extractor_v3 import LibraryExtractorV3
from utils.logger import debug, info, warning, error, critical


class LibraryFolderMapper:
    """
    Two-pass library mapping system for consistent library names across all file types.
    """
    
    def __init__(self):
        # The V3 extractor for getting library names from .nki files
        self.nki_extractor = LibraryExtractorV3()
        
        # Mapping: library_root_folder → (vendor, library_name)
        # This is built from .nki files and used for all other files
        self.folder_to_library = {}
    
    def build_library_mapping(self, file_paths: list) -> Dict[str, Tuple[str, str]]:
        """
        Build library mapping from .nki files.
        
        Args:
            file_paths: List of ALL file paths (mixed .nki, .wav, etc.)
            
        Returns:
            Dictionary mapping library root folder → (vendor, library)
        """
        debug("🔍 Step 1: Building library mapping from .nki files...")
        
        # Filter for .nki files only
        nki_files = [path for path in file_paths if path.lower().endswith(('.nki', '.nkm', '.nksn'))]
        
        debug(f"   Found {len(nki_files):,} Kontakt files to analyze")
        
        # Extract library names from .nki files
        for nki_path in nki_files:
            vendor, library, project = self.nki_extractor.extract_vendor_library(nki_path)
            
            if library != 'Unknown Library':
                # Find the library root folder (where this library starts)
                library_root = self._find_library_root_folder(nki_path, library)
                
                if library_root:
                    # Store the mapping
                    self.folder_to_library[library_root] = (vendor, library)
        
        debug(f"   ✅ Built mapping for {len(self.folder_to_library):,} library folders\n")
        
        return self.folder_to_library
    
    def _find_library_root_folder(self, file_path: str, library_name: str) -> Optional[str]:
        """
        Find the root folder of a library by looking for the folder that matches library_name.
        
        Uses intelligent parent detection:
        - If parent is similar to library name → Use parent (catches sibling folders)
        - Otherwise → Use library folder itself (avoids mapping to vendor)
        
        Example:
            Path: /Keepforest/Evolution Devastator.../Evolution - Devastator.../Instruments/file.nki
            Library: "Evolution - Devastator Deathmatch"
            Parent similar? YES (same name, different hyphen)
            Root: "/Keepforest/Evolution Devastator Deathmatch/" (parent)
        """
        parts = Path(file_path).parts
        
        # Find the folder that matches the library name
        for i, part in enumerate(parts):
            if part == library_name or part.lower() == library_name.lower():
                # Found exact match! 
                # Check if we should use parent folder as root
                if i > 0 and self._are_similar(parts[i-1], library_name):
                    # Parent is similar to library → Use parent (sibling folder scenario)
                    library_root = os.path.join(*parts[:i])
                    return library_root
                else:
                    # Parent not similar → Use library folder itself
                    library_root = os.path.join(*parts[:i+1])
                    return library_root
        
        # If exact match not found, try fuzzy match (first part of library name)
        library_first_word = library_name.split()[0] if library_name else None
        if library_first_word and len(library_first_word) > 3:
            for i, part in enumerate(parts):
                if library_first_word.lower() in part.lower() and len(part) > 5:
                    # Check if we should use parent
                    if i > 0 and self._are_similar(parts[i-1], library_name):
                        library_root = os.path.join(*parts[:i])
                        return library_root
                    else:
                        library_root = os.path.join(*parts[:i+1])
                        return library_root
        
        return None
    
    def _are_similar(self, name1: str, name2: str) -> bool:
        """
        Check if two folder names are similar (variations of same name).
        
        Uses word overlap logic (no vendor list needed!):
        - If parent has no unique words AND library has additions → Vendor prefix (don't use)
        - If both have same words → Formatting variation (use parent)
        
        Examples:
            "Evolution Devastator Deathmatch" vs "Evolution - Devastator Deathmatch" → True (same words)
            "Embertone" vs "Embertone - Chapman Trumpet" → False (vendor prefix)
            "BBC Symphony" vs "Spitfire Audio" → False (different words)
        """
        # Extract words (split on spaces, hyphens, underscores)
        parent_words = set(name1.lower().replace('-', ' ').replace('_', ' ').split())
        library_words = set(name2.lower().replace('-', ' ').replace('_', ' ').split())
        
        # Calculate unique words
        parent_unique = parent_words - library_words  # Words only in parent
        library_unique = library_words - parent_words  # Words only in library
        
        # If parent has no unique words AND library has additions
        # → Parent is likely a vendor prefix (e.g., "Embertone" vs "Embertone - Chapman Trumpet")
        if len(parent_unique) == 0 and len(library_unique) > 0:
            return False  # Don't use parent
        
        # If both have same words (no unique words on either side)
        # → They're formatting variations (e.g., "Evolution Devastator" vs "Evolution - Devastator")
        if len(parent_unique) == 0 and len(library_unique) == 0:
            return True  # Use parent
        
        # If words are different
        return False
    
    def extract_vendor_library(self, file_path: str, all_file_paths: list = None) -> Tuple[str, str]:
        """
        Extract vendor and library for ANY file type.
        
        Args:
            file_path: Path to file (.nki, .wav, .aiff, anything)
            all_file_paths: Optional list of all paths (for building mapping)
            
        Returns:
            (vendor, library) tuple
        """
        # If this is a .nki file, extract directly
        if file_path.lower().endswith(('.nki', '.nkm', '.nksn')):
            return self.nki_extractor.extract_vendor_library(file_path)
        
        # For other files, try to use the library mapping
        if self.folder_to_library:
            # Find which library folder this file belongs to
            for library_root, (vendor, library) in self.folder_to_library.items():
                if file_path.startswith(library_root):
                    # This file is inside a known library folder!
                    return vendor, library
        
        # Fallback: If no mapping available, try to extract anyway
        # (This might not be as accurate for .wav files, but better than nothing)
        return self.nki_extractor.extract_vendor_library(file_path)
    
    def get_statistics(self) -> Dict:
        """Get statistics about the library mapping"""
        return {
            'total_libraries_mapped': len(self.folder_to_library),
            'library_folders': list(self.folder_to_library.keys()),
            'library_names': list(set(lib for _, lib in self.folder_to_library.values()))
        }


# Two-pass extraction for file indexing
class TwoPassLibraryExtractor:
    """
    High-level interface for two-pass library extraction during file indexing.
    
    Usage:
        # During file indexing:
        extractor = TwoPassLibraryExtractor()
        
        # Pass 1: Give it all file paths
        extractor.initialize(all_file_paths)
        
        # Pass 2: Extract for each file
        for path in all_file_paths:
            vendor, library = extractor.extract(path)
    """
    
    def __init__(self):
        self.mapper = LibraryFolderMapper()
        self.initialized = False
    
    def initialize(self, all_file_paths: list):
        """
        Initialize by building library mapping from .nki files.
        Call this once with all file paths before extracting.
        
        Args:
            all_file_paths: List of ALL file paths to be indexed
        """
        debug("\n🔧 Initializing Two-Pass Library Extractor...")
        self.mapper.build_library_mapping(all_file_paths)
        self.initialized = True
        info("✅ Initialization complete!\n")
    
    def extract(self, file_path: str) -> Tuple[str, str]:
        """
        Extract vendor and library for a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            (vendor, library) tuple
        """
        if not self.initialized:
            # If not initialized, use direct extraction (less accurate for .wav files)
            warning("⚠️  Warning: TwoPassLibraryExtractor not initialized. Using direct extraction.")
            return LibraryExtractorV3().extract_vendor_library(file_path)
        
        return self.mapper.extract_vendor_library(file_path)
    
    def get_statistics(self) -> Dict:
        """Get statistics about the extraction"""
        return self.mapper.get_statistics()


if __name__ == "__main__":
    # Demo
    debug("\n🧪 TWO-PASS LIBRARY EXTRACTOR DEMO\n")
    debug("="*80)
    
    # Simulate a library with mixed file types
    demo_paths = [
        # .nki files (will be used to determine library name)
        "/Folk Winds - Hereafter Soundtracks/Instruments/Pads/Ocarina.nki",
        "/Folk Winds - Hereafter Soundtracks/Instruments/Leads/Flute.nki",
        
        # .wav files (will inherit library name from .nki files)
        "/Folk Winds - Hereafter Soundtracks/Samples/Shed Recorder/file1.wav",
        "/Folk Winds - Hereafter Soundtracks/Samples/Shed Recorder/file2.wav",
        "/Folk Winds - Hereafter Soundtracks/Docs/manual.pdf",
    ]
    
    # Create extractor
    extractor = TwoPassLibraryExtractor()
    
    # Pass 1: Initialize with all paths
    extractor.initialize(demo_paths)
    
    # Pass 2: Extract for each file
    debug("\n📄 Extracting library names:\n")
    for path in demo_paths:
        vendor, library = extractor.extract(path)
        file_type = Path(path).suffix
        debug(f"{file_type:5s} → {library:40s} ({vendor})")
        debug(f"       {path}")
        debug()
    
    # Statistics
    stats = extractor.get_statistics()
    debug(f"\n📊 Statistics:")
    debug(f"   Libraries mapped: {stats['total_libraries_mapped']}")
    
    debug("\n" + "="*80)
    debug("✅ All files in same library get same library name!\n")

