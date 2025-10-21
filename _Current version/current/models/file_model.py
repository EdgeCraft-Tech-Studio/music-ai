#!/usr/bin/env python3
"""
File Model - MVC Model for file operations and metadata
Extracted from modern_patchio_ui_loader.py
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

from models.user_settings_model import UserSettingsModel

# Import file mappings directly from core settings
from settings.core_settings import FILE_TYPE_MAPPINGS, FILE_ICON_MAPPINGS

# 🚀 NEW: Using LibraryExtractorV3 for fast and accurate library/vendor extraction
from utils.database.library_extractor_v3 import LibraryExtractorV3

class FileModel:
    """Model for file operations and metadata extraction"""

    def __init__(self, settings_model: UserSettingsModel):
        self.settings = settings_model
        self.file_type_mappings = FILE_TYPE_MAPPINGS
        self.file_icon_mappings = FILE_ICON_MAPPINGS
        
        # 🚀 NEW: Initialize V3 library extractor with shared vendor cache
        # Thread-safe: Vendors loaded ONCE from knowledge DB, shared across all threads
        # No DB connections needed in workers (just reads from Python dict)
        self.library_extractor_v3 = LibraryExtractorV3(use_knowledge_db=True)
    
    def get_file_icon(self, file_path: str) -> str:
        """Get appropriate icon based on file extension for music producers"""
        _, ext = os.path.splitext(file_path.lower())

        # Use settings for file icons
        return self.file_icon_mappings.get(ext, "📄")

    def get_file_type_info(self, file_path: str) -> str:
        """Get file type information for display"""
        _, ext = os.path.splitext(file_path.lower())

        # Use settings for file type mappings
        return self.file_type_mappings.get(ext, "File")

    def extract_musical_metadata(
        self, file_name: str, file_path: str
    ) -> Dict[str, str]:
        """Extract BPM, key, and other musical info from filename - essential for producers"""
        metadata = {"bpm": "", "key": "", "genre": ""}

        name_lower = file_name.lower()

        # Extract BPM (critical for producers and composers)
        bpm_patterns = [
            r"(\d{2,3})\s*bpm",  # "120bpm", "128 bpm"
            r"(\d{2,3})bpm",  # "120bpm"
            r"_(\d{2,3})_",  # "_120_"
            r"(\d{2,3})$",  # ending with number
        ]

        for pattern in bpm_patterns:
            match = re.search(pattern, name_lower)
            if match:
                bpm_val = int(match.group(1))
                if 60 <= bpm_val <= 200:  # Reasonable BPM range
                    metadata["bpm"] = "{}bpm".format(bpm_val)
                    break

        # Extract musical key (essential for composers)
        key_patterns = [
            r"\b([A-G]#?m?)\b",  # C, Dm, F#, etc.
            r"_([A-G]#?m?)_",  # _Dm_
            r"([A-G]#?m?)$",  # ending with key
        ]

        for pattern in key_patterns:
            match = re.search(pattern, name_lower)
            if match:
                key_candidate = match.group(1)
                # Validate it's actually a key
                if len(key_candidate) <= 3 and key_candidate[0].upper() in "ABCDEFG":
                    metadata["key"] = key_candidate.upper()
                    break

        # Note: Genre detection moved to extract_tags_from_metadata using genre_keywords logic

        return metadata

    def extract_library_info(self, file_path: str) -> str:
        """
        Extract meaningful library name.
        
        🚀 NEW: Uses LibraryExtractorV3 (fast pattern-based extraction)
        Thread-safe: Creates knowledge DB connection in worker thread
        """
        if not file_path:
            return "Unknown Library"
        
        # 🚀 NEW: Use V3 extractor with project detection (vendors from shared cache - thread-safe)
        try:
            vendor, library, project = self.library_extractor_v3.extract_vendor_library(file_path)
            
            # Debug: Print what library name was extracted (only if debug logging enabled)
            from utils.logger import debug
            debug(f"🔍 Library extraction for {os.path.basename(file_path)}: {library}")
            
            # 🚀 Show project name in UI if file is part of a project (instead of library)
            if project:
                return project
            return library if library != 'Unknown Library' else "Unknown Library"
            
        except Exception as e:
            # Fallback to old method if V3 fails
            from utils.logger import warning
            warning(f"⚠️  V3 extraction failed for {file_path}: {e}")
            
            # Old fallback logic
            project_name = self._extract_project_name(file_path)
            if project_name:
                return project_name
            
            library_name = self.extract_library_root_patchio_style(file_path)
            if not library_name or library_name in ['samples', 'audio', 'sounds', 'instruments']:
                library_name = self.get_library_key_patchio_style(file_path)
            
            return library_name if library_name else "Unknown Library"
    
    def extract_library_root_patchio_style(self, path: str) -> str:
        """
        Extract library name by analyzing internal library structure patterns
        Focuses on the library content structure, not the path leading to it
        """
        parts = os.path.normpath(path).split(os.sep)

        # Common library organization folders (these contain libraries, not part of library name)
        organization_folders = [
            "volumes",
            "users",
            "applications",
            "desktop",
            "documents",
            "downloads",
            "libraries",
            "kontakt libraries",
            "player libraries",
            "non player libraries",
            "best service engine libraries",
            "service engine libraries",
            "sample libraries",
            "vst",
            "plugins",
            "cubase projects",
            "logic",
        ]

        # Step 1: Check for collection patterns (like "01. Trailer Stems" containing similar subfolders)
        # Disabled for now as it's causing false positives
        # collection_name = self._detect_collection_pattern(parts)
        # if collection_name:
        #     return collection_name

        # Step 2: Use the existing robust approach as fallback
        # More robust approach: Look for the actual library product folder
        # This is typically the folder that contains meaningful product names
        # and is followed by content folders (instruments, samples, etc.)

        # Find the deepest meaningful folder that looks like a library product
        best_library_folder = None
        best_score = 0

        for i, part in enumerate(parts):
            part_lower = part.lower()

            # Skip organization and system folders
            if part_lower in organization_folders or i < 3:
                continue

            # Skip files (anything with an extension)
            if "." in part and len(part.split(".")[-1]) <= 4:
                continue

            # Score this folder as a potential library
            score = 0

            # Longer names are usually more descriptive
            score += len(part)

            # Product names often have spaces, dashes, or parentheses
            if " " in part or "-" in part or "(" in part or ")" in part:
                score += 15

            # Version numbers or descriptive terms
            if any(char.isdigit() for char in part):
                score += 5

            # Check if this folder is followed by content folders (indicating it's a library root)
            if i + 1 < len(parts):
                next_part = parts[i + 1].lower()
                content_indicators = [
                    "instruments",
                    "samples",
                    "presets",
                    "patches",
                    "articulations",
                    "data",
                    "layers",
                    "keyswitches",
                    "resources",
                    "audio",
                    "sounds",
                    "loops",
                    "multis",
                    "banks",
                    "patches",
                    "samples",
                    "instruments",
                ]

                # If the next folder looks like content, this is likely a library
                if any(indicator in next_part for indicator in content_indicators):
                    score += 20

                # Also check if next folder contains common library content patterns
                if any(
                    word in next_part
                    for word in ["multis", "banks", "patches", "samples"]
                ):
                    score += 15

            # Check if this folder name looks like a product name (not just a generic folder)
            if len(part) > 3 and not part_lower in [
                "content",
                "files",
                "data",
                "library",
            ]:
                score += 10

            # Prefer folders that are closer to the "Samples" folder (not deeper in path)
            # This helps identify the actual library folder rather than sub-content folders
            samples_index = -1
            for j, p in enumerate(parts):
                if p.lower() == "samples":
                    samples_index = j
                    break

            if samples_index >= 0:
                # Give higher score to folders closer to the Samples folder
                distance_from_samples = abs(i - samples_index)
                score += max(0, 20 - distance_from_samples * 3)

                # Special bonus for folders that are the immediate parent of "Samples"
                # This handles cases like "Soundiron - Voice of Wind Adey/Samples"
                if i == samples_index - 1:
                    score += 50  # Strong bonus for library folder containing Samples
            else:
                # Fallback: prefer folders that are not too deep
                score += max(0, 10 - i)

            # Bonus for folders that look like vendor-library combinations
            # Pattern: "Vendor - Library Name" or "Vendor Library Name"
            if " - " in part or (
                len(part.split()) >= 2
                and any(
                    word in part.lower()
                    for word in ["library", "collection", "bundle", "pack"]
                )
            ):
                score += 30  # Strong bonus for vendor-library pattern folders

            # Special case: If this folder is a content category (instruments, samples, etc.)
            # and it's followed by more content folders, prefer the parent folder
            if part_lower in [
                "instruments",
                "samples",
                "presets",
                "patches",
                "articulations",
            ]:
                # Reduce score for content categories to prefer the actual library folder
                score -= 15

            if score > best_score:
                best_library_folder = part
                best_score = score

        if best_library_folder:
            return best_library_folder

        # Fallback: Use the folder just before the file
        if len(parts) > 1:
            return parts[-2]

        return None

    def _detect_collection_pattern(self, parts):
        """
        Detect collection patterns like:
        - "Trailer Stems" containing "KFDT - Stem 01", "KFDT - Stem 02"
        - "Action Stems" containing "KFDT - Action 01", "KFDT - Action 02"
        - Any folder containing multiple subfolders with similar naming patterns

        This method is conservative and only detects obvious collection patterns
        to avoid interfering with normal library detection.
        """
        import re

        # Look for folders that contain multiple similar subfolders
        for i, part in enumerate(parts):
            # Skip single-word folders that are likely content categories
            if len(part.split()) == 1 and part.lower() in [
                "up",
                "down",
                "left",
                "right",
                "close",
                "far",
                "wide",
                "spot",
                "mix",
                "decca",
            ]:
                continue

            folder_path = os.sep.join(parts[: i + 1])
            if os.path.isdir(folder_path):
                try:
                    subfolders = [
                        f
                        for f in os.listdir(folder_path)
                        if os.path.isdir(os.path.join(folder_path, f))
                    ]

                    # Need at least 3 subfolders to be considered a collection (more conservative)
                    if len(subfolders) >= 3:
                        # Extract prefixes from subfolder names
                        prefixes = [self._extract_prefix(sf) for sf in subfolders]

                        # Check if all subfolders have the same prefix pattern
                        if len(set(prefixes)) == 1 and prefixes[0]:
                            # This is a collection - return the collection name
                            return part

                        # Also check for patterns where subfolders share a common prefix
                        # but have different suffixes (like "KFDT - Stem 01", "KFDT - Stem 02")
                        common_prefixes = self._find_common_prefix_pattern(subfolders)
                        if common_prefixes:
                            return part

                except (OSError, PermissionError):
                    # Skip if we can't access the directory
                    continue

        return None

    def _find_common_prefix_pattern(self, subfolders):
        """
        Find common prefix patterns in subfolder names
        Returns True if a clear pattern is found
        """
        if len(subfolders) < 2:
            return False

        # Try different prefix extraction methods
        for method in ["dash_separated", "space_separated", "common_start"]:
            prefixes = []
            for sf in subfolders:
                prefix = self._extract_prefix_by_method(sf, method)
                if prefix:
                    prefixes.append(prefix)

            # Check if we have a consistent pattern
            if len(prefixes) == len(subfolders) and len(set(prefixes)) == 1:
                return True

        return False

    def _extract_prefix_by_method(self, folder_name, method):
        """
        Extract prefix using different methods
        """
        if method == "dash_separated":
            # For patterns like "KFDT - Stem 01" -> "KFDT - Stem"
            if " - " in folder_name:
                parts = folder_name.split(" - ")
                if len(parts) >= 2:
                    return " - ".join(parts[:-1])  # All but the last part

        elif method == "space_separated":
            # For patterns like "Stem 01 Spectre" -> "Stem"
            parts = folder_name.split()
            if len(parts) >= 2 and parts[1].isdigit():
                return parts[0]

        elif method == "common_start":
            # For patterns like "Stem01", "Stem02" -> "Stem"
            import re

            match = re.match(r"^([A-Za-z]+)\d+", folder_name)
            if match:
                return match.group(1)

        return None

    def _extract_prefix(self, folder_name):
        """
        Extract common prefix from folder names like:
        'KFDT - Stem 01' -> 'KFDT - Stem'
        'KFDT - Action 02' -> 'KFDT - Action'
        """
        import re

        # Remove numbers and common suffixes at the end
        # This handles patterns like "KFDT - Stem 01", "KFDT - Action 02"
        cleaned = re.sub(r"\s*\d+.*$", "", folder_name).strip()

        # Also handle patterns with additional descriptive text
        # Like "KFDT - Stem 03 - Spectre - F - 140 bpm" -> "KFDT - Stem"
        if " - " in cleaned:
            parts = cleaned.split(" - ")
            if len(parts) >= 2:
                # Take the first two parts as the prefix
                return " - ".join(parts[:2])

        return cleaned

    def _extract_project_name(self, path):
        """Extract project name for Logic/Cubase projects from a file path using project file extensions."""
        # First check if any path part is a project file
        parts = os.path.normpath(path).split(os.sep)
        for part in parts:
            if part.endswith((".logic", ".logicx", ".cpr")):
                return os.path.splitext(part)[0]

        # Then check if any parent directory contains a project file
        current_dir = os.path.dirname(path)
        while current_dir and current_dir != os.path.dirname(
            current_dir
        ):  # Stop at root
            try:
                for filename in os.listdir(current_dir):
                    if filename.endswith((".logic", ".logicx", ".cpr")):
                        # Return the folder name that contains the project file
                        return os.path.basename(
                            current_dir
                        )  # Stop immediately when found
            except (OSError, PermissionError):
                pass  # Skip if we can't access the directory
            current_dir = os.path.dirname(current_dir)

        return None

    def get_library_key_patchio_style(self, path: str) -> str:
        """
        Get library key using patchio.py's get_library_key logic
        Excludes generic directories to find meaningful library names
        """
        parts = os.path.normpath(path).split(os.sep)
        generic_dirs = {
            "samples",
            "instruments",
            "presets",
            "audio",
            "multis",
            "articulations",
            "data",
            "patches",
            "files",
            "programs",
            "kits",
            "output",
            "sounds",
            "loops",
            "sessions",
            "projects",
            "tracks",
            "stems",
            "mixdown",
        }

        # Walk backwards through path parts to find a meaningful library folder
        for i in range(len(parts) - 1, 1, -1):
            part_lower = parts[i].lower()

            # Skip generic directories
            if part_lower in generic_dirs or len(parts[i]) <= 3:
                continue

            # Skip organization folders that contain "libraries" but aren't the actual library
            if part_lower in [
                "libraries",
                "kontakt libraries",
                "player libraries",
                "non player libraries",
            ]:
                continue

            # This looks like a meaningful library folder
            return os.sep.join(parts[: i + 1])

        # For files directly in root folders (like Samsung drive), group by drive/folder name
        if len(parts) >= 4:  # At least /Volumes/DriveName/filename
            if parts[1] == "Volumes" and len(parts) >= 3:
                return parts[2]  # Return drive name (e.g., "Samsung 850 EVO")
            elif parts[1] == "Users" and len(parts) >= 4:
                return parts[3]  # Return folder name under user (e.g., "Music")

        # For project files, try to extract meaningful project names
        project_name = self._extract_project_name(path)
        if project_name:
            return project_name

        # Fallback: Try to extract a meaningful name from the filename
        filename = os.path.basename(path)
        if "." in filename:
            # Remove extension
            name_without_ext = os.path.splitext(filename)[0]
            # Try to extract meaningful parts (e.g., "8DIO Ambient Guitar - Horror pt1" -> "8DIO Ambient Guitar")
            if " - " in name_without_ext:
                return name_without_ext.split(" - ")[0]
            elif " pt" in name_without_ext.lower():
                return name_without_ext.split(" pt")[0]
            else:
                return name_without_ext

        return os.sep.join(parts[-3:]) if len(parts) >= 3 else path

    def group_results_by_library(
        self, results: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Group results by library for better organization - key for creative workflow"""
        libraries = {}

        for result in results:
            file_path = result.get("path", "")
            if not file_path:
                continue

            library_name = self.extract_library_info(file_path)

            if library_name not in libraries:
                libraries[library_name] = {
                    "files": [],
                    "tags": set(),
                    "file_types": set(),
                }

            # Add metadata
            file_name = result.get("name", "")
            metadata = self.extract_musical_metadata(file_name, file_path)

            result["metadata"] = metadata
            libraries[library_name]["files"].append(result)

            # Collect tags from individual files for library-level tags
            # Use the tags that were already computed in the search controller
            file_tags = result.get("tags", "")
            if file_tags:
                # Split by ' • ' and add individual tags to library set
                for tag in file_tags.split(" • "):
                    if tag.strip():
                        libraries[library_name]["tags"].add(tag.strip())

            file_type = self.get_file_type_info(file_path)
            libraries[library_name]["file_types"].add(file_type)

        return libraries
