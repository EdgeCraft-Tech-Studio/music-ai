"""
PatchIO Core Search Engine
Simple adapter layer between modern UI and existing patchio.py functionality.

This module provides a clean interface to the search functionality 
without breaking existing code.
"""

import os
import sys
import re
from pathlib import Path

# Import settings
try:
    from core_settings import (
        DEFAULT_EXTENSIONS, 
        DEFAULT_SEARCH_FOLDERS,
        MAX_RESULTS_PER_LIBRARY,
        MAX_TOTAL_RESULTS,
        GENRE_KEYWORDS
    )
    print("✅ Successfully imported settings from core_settings")
except ImportError as e:
    print("⚠️ Could not import settings: {}".format(e))
    # Fallback defaults
    DEFAULT_EXTENSIONS = ['.wav', '.mp3', '.nki']
    DEFAULT_SEARCH_FOLDERS = ['/Volumes/Samsung 850 EVO']
    MAX_RESULTS_PER_LIBRARY = 50
    MAX_TOTAL_RESULTS = 1000
    GENRE_KEYWORDS = {}

def parse_terms(input_str):
    """
    Parse the input string into terms and detect which were quoted.
    Returns a tuple (terms, quoted_flags)
    (Exact copy from patchio.py)
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

def matches_term(term, text, quoted):
    """
    Check if term matches text, handling quoted vs unquoted matching
    (Exact copy from patchio.py)
    """
    term = term.lower()
    text = text.lower()

    if quoted:
        if ' ' in term:
            return term in text
        else:
            # Match whole word or surrounded by non-alphanumeric characters
            pattern = r'(?:^|[^a-zA-Z0-9])' + re.escape(term) + r'(?:[^a-zA-Z0-9]|$)'
            return re.search(pattern, text) is not None
    else:
        return term in text

def recursive_scan(folder, selected_extensions, excluded_folders=None):
    """
    Recursively scan folder for files with selected extensions
    (Adapted from patchio.py)
    """
    if excluded_folders is None:
        excluded_folders = []
    
    selected_extensions_lower = tuple(ext.lower() for ext in selected_extensions)
    
    try:
        for entry in os.scandir(folder):
            entry_path = os.path.normcase(os.path.abspath(entry.path))

            if entry.is_dir(follow_symlinks=False):
                # Skip excluded folders
                if any(entry_path == ex or entry_path.startswith(ex + os.sep) for ex in excluded_folders):
                    continue
                
                yield from recursive_scan(entry.path, selected_extensions, excluded_folders)

            elif entry.is_file(follow_symlinks=False):
                if entry.name.lower().endswith(selected_extensions_lower):
                    yield entry.path

    except PermissionError as e:
        print(f"PermissionError accessing '{folder}': {e}")
    except Exception as e:
        print(f"Unexpected error accessing '{folder}': {e}")

class SearchEngine:
    """Clean search interface for the modern UI"""
    
    def __init__(self):
        self.last_results = []
        self.search_folders = []
        
        # Use settings for extensions
        self.selected_extensions = DEFAULT_EXTENSIONS
        
    def setup_default_folders(self):
        """Setup default folders from settings"""
        try:
            # Use settings for default folders
            existing_folders = [f for f in DEFAULT_SEARCH_FOLDERS if os.path.exists(f)]
            self.set_search_folders(existing_folders)
            print("📁 Default search folders: {}".format(existing_folders))
            
            # Test if we can find any files at all - WITH ERROR HANDLING
            try:
                self.test_search_setup()
            except Exception as e:
                print("⚠️ Test search setup failed: {}".format(e))
                print("⚠️ Continuing without test search setup")
                
        except Exception as e:
            print("⚠️ Setup default folders failed: {}".format(e))
            # Set minimal fallback folders
            self.search_folders = []
            print("⚠️ Using empty search folders as fallback")
        
    def test_search_setup(self):
        """Test if search setup is working by counting files"""
        try:
            print("🧪 Testing search setup...")
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
                    print("  📂 {}: Found {} files".format(folder, folder_files))
                except (PermissionError, OSError) as e:
                    print("  ⚠️ Cannot access {}: {}".format(folder, e))
            
            print("🧪 Test complete: Found {} files across all folders".format(total_files))
            if total_files == 0:
                print("⚠️ WARNING: No files found in any search folder!")
                
        except Exception as e:
            print("⚠️ Test search setup failed: {}".format(e))
            print("⚠️ Continuing without test results")
        
    def set_search_folders(self, folders):
        """Set the folders to search in"""
        self.search_folders = [Path(f) for f in folders if os.path.exists(f)]
        print(f"🔧 Search folders configured: {[str(f) for f in self.search_folders]}")
        
    def ai_search(self, query):
        """AI-powered search (placeholder for now)"""
        print(f"🤖 AI Search: {query}")
        
        # TODO: Later integrate with patchio.py AI functions
        # For now, return mock results to test UI
        return [
            {"name": f"AI: Epic Drums for '{query}'", "path": "/path/to/epic_drums.wav", "type": "AI Result"},
            {"name": f"AI: Cinematic Strings matching '{query}'", "path": "/path/to/strings.wav", "type": "AI Result"},
            {"name": f"AI: Dark Bass inspired by '{query}'", "path": "/path/to/bass.wav", "type": "AI Result"},
        ]
    
    def simple_search(self, query):
        """
        Simple filename search using EXACT patchio.py logic
        """
        print(f"📁 Simple Search: {query}")
        print(f"🔍 Searching in folders: {[str(f) for f in self.search_folders]}")
        
        if not self.search_folders:
            print("⚠️ No search folders configured!")
            return []
        
        if not query.strip():
            print("⚠️ Empty search query!")
            return []
        
        # Parse search terms exactly like patchio.py
        try:
            simple_raw = query.strip().lower()
            or_terms, or_quoted = parse_terms(simple_raw)
            print(f"🔍 Parsed OR terms: {list(zip(or_terms, or_quoted))}")
        except Exception as e:
            print(f"⚠️ Error parsing search terms: {e}")
            return []
        
        if not or_terms:
            print("⚠️ No valid search terms found!")
            return []
        
        results = []
        excluded_folders = []  # Using dummy empty list as requested
        
        # Search each folder using the exact patchio.py logic
        for folder in self.search_folders:
            if not folder.exists():
                print(f"⚠️ Folder doesn't exist: {folder}")
                continue
                
            print(f"📂 Searching in: {folder}")
            folder_matches = 0
            
            try:
                # Use the exact recursive_scan from patchio.py
                for file_path in recursive_scan(str(folder), self.selected_extensions, excluded_folders):
                    full_path = file_path.lower()
                    
                    # Simple mode logic: OR matching (exact from patchio.py line 2321)
                    if any(matches_term(term, full_path, quoted) for term, quoted in zip(or_terms, or_quoted)):
                        folder_matches += 1
                        
                        # Get file info
                        file_name = os.path.basename(file_path)
                        
                        results.append({
                            "name": file_name,
                            "path": file_path,
                            "type": f"Simple Match in {folder.name}",
                            "is_audio": True  # All results are audio files due to extension filtering
                        })
                        
                        print(f"  ✅ Found match: {file_name}")
                        
                        # NO ARTIFICIAL LIMIT - find ALL matching files like original patchio.py
                            
            except Exception as e:
                print(f"  ⚠️ Cannot search in {folder}: {e}")
                continue
            
            print(f"  📊 Folder {folder.name}: {folder_matches} matches")
        
        print(f"📊 Simple search found {len(results)} matching files")
        
        if len(results) == 0:
            print(f"💡 No files found matching '{query}'. Try different search terms.")
        
        return results
    
    def advanced_search(self, query):
        """Advanced search with filters"""
        print(f"⚙️ Advanced Search: {query}")
        
        # TODO: Later integrate with patchio.py advanced search
        # For now, return mock results to test UI
        return [
            {"name": f"Advanced: Complex Pattern for '{query}'", "path": "/path/to/pattern.wav", "type": "Advanced Result"},
            {"name": f"Advanced: Filtered Sound matching '{query}'", "path": "/path/to/filtered.wav", "type": "Advanced Result"},
        ]
    
    def get_matched_keywords(self, file_path, search_terms):
        """Get the search terms that matched this specific file"""
        if not search_terms:
            return []
        
        # Parse the search terms
        terms, quoted_flags = parse_terms(search_terms)
        matched_terms = []
        
        # Get the file name and path for matching
        file_name = os.path.basename(file_path).lower()
        file_path_lower = file_path.lower()
        
        # Check which terms matched this file
        for term, quoted in zip(terms, quoted_flags):
            if matches_term(term, file_name, quoted) or matches_term(term, file_path_lower, quoted):
                matched_terms.append(term)
        
        return matched_terms
    
    def get_genre_keywords(self, file_path):
        """Extract genre keywords from file path using settings"""
        file_name = os.path.basename(file_path).lower()
        path_lower = file_path.lower()
        combined_text = (file_name + ' ' + path_lower).lower()
        
        genre_keywords = []
        
        # Use settings for genre keywords
        for category, keywords in GENRE_KEYWORDS.items():
            if any(word in combined_text for word in keywords):
                genre_keywords.append(category)
        
        return genre_keywords

# Global instance for the modern UI to use
search_engine = SearchEngine() 