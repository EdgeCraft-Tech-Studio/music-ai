#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automatic Tagging System for PatchIO
Intelligent tagging system that extracts instrument, genre, mood, and format tags
from library names, file paths, and filenames.
"""

import sqlite3
import os
import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class TagResult:
    """Result of automatic tagging"""

    instrument: List[str] = None
    genre: List[str] = None
    mood: List[str] = None
    format: List[str] = None
    confidence: float = 0.0
    source: str = ""  # "rule_based", "ai_enhanced", "fallback"

    def __post_init__(self):
        """Initialize empty lists if None"""
        if self.instrument is None:
            self.instrument = []
        if self.genre is None:
            self.genre = []
        if self.mood is None:
            self.mood = []
        if self.format is None:
            self.format = []


class AutomaticTagger:
    """Intelligent automatic tagging system for PatchIO files"""

    def __init__(self, knowledge_db_path: str = "patchio_knowledge.db"):
        """Initialize the automatic tagger"""
        self.knowledge_db_path = knowledge_db_path
        self.conn = None
        self.cursor = None

        # Initialize tag mappings
        self._init_tag_database()
        self._load_tag_mappings()

    def _init_tag_database(self):
        """Initialize the tag mappings database using the knowledge database"""
        try:
            # Use the knowledge database instead of creating our own
            from utils.database.knowledge_database import KnowledgeDatabase

            self.knowledge_db = KnowledgeDatabase("patchio_knowledge.db")
            self.conn = self.knowledge_db.conn
            self.cursor = self.knowledge_db.cursor

            # Load tag mappings from knowledge database
            self._load_tag_mappings()

        except Exception as e:
            print(f"❌ Error initializing tag database: {e}")
            raise

    def _populate_default_mappings(self):
        """Populate database with default tag mappings"""
        try:
            # Check if mappings already exist
            self.cursor.execute("SELECT COUNT(*) FROM tag_mappings")
            if self.cursor.fetchone()[0] > 0:
                return

            print("📝 Populating default tag mappings...")

            # Default instrument mappings
            instrument_mappings = [
                # Brass instruments
                ("cinebrass", "instrument", "brass", 0.9),
                ("brass", "instrument", "brass", 0.8),
                ("trumpet", "instrument", "brass", 0.9),
                ("trombone", "instrument", "brass", 0.9),
                ("horn", "instrument", "brass", 0.8),
                ("tuba", "instrument", "brass", 0.9),
                ("french horn", "instrument", "brass", 0.9),
                # FX and Effects
                ("fx", "instrument", "fx", 0.9),
                ("effects", "instrument", "fx", 0.9),
                ("stabs", "instrument", "stabs", 0.9),
                ("hits", "instrument", "hits", 0.9),
                ("impacts", "instrument", "impacts", 0.9),
                ("risers", "instrument", "risers", 0.9),
                ("sweeps", "instrument", "sweeps", 0.9),
                ("transitions", "instrument", "transitions", 0.9),
                ("strings fx", "instrument", "fx", 0.8),
                ("brass stabs", "instrument", "stabs", 0.8),
                ("piano fx", "instrument", "fx", 0.8),
                # String instruments
                ("strings", "instrument", "strings", 0.8),
                ("violin", "instrument", "strings", 0.9),
                ("viola", "instrument", "strings", 0.9),
                ("cello", "instrument", "strings", 0.9),
                ("bass", "instrument", "strings", 0.8),
                ("guitar", "instrument", "strings", 0.9),
                ("piano", "instrument", "piano", 0.9),
                ("harp", "instrument", "strings", 0.9),
                # Woodwind instruments
                ("woodwind", "instrument", "woodwind", 0.8),
                ("wind", "instrument", "woodwind", 0.9),
                ("reed", "instrument", "woodwind", 0.9),
                ("flute", "instrument", "woodwind", 0.9),
                ("oboe", "instrument", "woodwind", 0.9),
                ("clarinet", "instrument", "woodwind", 0.9),
                ("bassoon", "instrument", "woodwind", 0.9),
                ("saxophone", "instrument", "woodwind", 0.9),
                ("sax", "instrument", "woodwind", 0.9),
                ("trumpet", "instrument", "brass", 0.9),
                ("trombone", "instrument", "brass", 0.9),
                ("upright bass", "instrument", "strings", 0.9),
                ("double bass", "instrument", "strings", 0.9),
                ("drum kit", "instrument", "percussion", 0.9),
                ("drums", "instrument", "percussion", 0.9),
                ("crumhorn", "instrument", "woodwind", 0.95),
                ("shawm", "instrument", "woodwind", 0.95),
                ("recorder", "instrument", "woodwind", 0.95),
                ("bagpipe", "instrument", "woodwind", 0.95),
                ("pan flute", "instrument", "woodwind", 0.95),
                ("bamboo flute", "instrument", "woodwind", 0.95),
                # Ethnic Woodwind Instruments
                ("ney", "instrument", "woodwind", 0.95),
                ("dizi", "instrument", "woodwind", 0.95),
                ("bansuri", "instrument", "woodwind", 0.95),
                ("shakuhachi", "instrument", "woodwind", 0.95),
                ("tin whistle", "instrument", "woodwind", 0.95),
                ("uilleann pipes", "instrument", "woodwind", 0.95),
                ("bodhran", "instrument", "percussion", 0.95),
                ("duduk", "instrument", "woodwind", 0.95),
                ("zurna", "instrument", "woodwind", 0.95),
                ("kaval", "instrument", "woodwind", 0.95),
                # Percussion
                ("percussion", "instrument", "percussion", 0.8),
                ("drums", "instrument", "percussion", 0.9),
                ("drum", "instrument", "percussion", 0.9),
                ("snare", "instrument", "percussion", 0.8),
                ("kick", "instrument", "percussion", 0.8),
                ("hihat", "instrument", "percussion", 0.8),
                ("cymbal", "instrument", "percussion", 0.8),
                # Synth/Electronic
                ("synth", "instrument", "synthesizer", 0.9),
                ("synthesizer", "instrument", "synthesizer", 0.9),
                ("pad", "instrument", "synthesizer", 0.8),
                ("lead", "instrument", "synthesizer", 0.8),
                ("bass", "instrument", "synthesizer", 0.7),
            ]

            # Default genre mappings
            genre_mappings = [
                # Orchestral and Cinematic
                ("orchestral", "genre", "orchestral", 0.9),
                ("orchestra", "genre", "orchestral", 0.9),
                ("cinematic", "genre", "cinematic", 0.9),
                ("film", "genre", "cinematic", 0.8),
                ("movie", "genre", "cinematic", 0.8),
                ("epic", "genre", "epic", 0.9),
                ("trailer", "genre", "epic", 0.8),
                ("epic orchestral", "genre", "epic", 0.8),
                ("dark cinematic", "genre", "cinematic", 0.8),
                # Modern Genres
                ("jazz", "genre", "jazz", 0.9),
                ("swing", "genre", "jazz", 0.9),
                ("swing!", "genre", "jazz", 0.9),
                ("swing more", "genre", "jazz", 0.9),
                ("swing more!", "genre", "jazz", 0.9),
                ("blues", "genre", "blues", 0.9),
                ("rock", "genre", "rock", 0.9),
                ("pop", "genre", "pop", 0.9),
                ("electronic", "genre", "electronic", 0.9),
                ("ambient", "genre", "ambient", 0.9),
                ("folk", "genre", "folk", 0.9),
                ("classical", "genre", "classical", 0.9),
                ("baroque", "genre", "classical", 0.8),
                ("romantic", "genre", "classical", 0.8),
                # World/Ethnic Genres
                ("world", "genre", "world", 0.8),
                ("ethnic", "genre", "ethnic", 0.9),
                # Persian/Middle Eastern
                ("persian", "genre", "persian", 0.95),
                ("iranian", "genre", "persian", 0.9),
                ("middle eastern", "genre", "middle eastern", 0.9),
                ("arabic", "genre", "arabic", 0.95),
                ("turkish", "genre", "turkish", 0.95),
                ("ottoman", "genre", "turkish", 0.9),
                # Chinese/Asian
                ("chinese", "genre", "chinese", 0.95),
                ("asian", "genre", "asian", 0.8),
                ("japanese", "genre", "japanese", 0.95),
                ("korean", "genre", "korean", 0.95),
                ("indian", "genre", "indian", 0.95),
                ("hindu", "genre", "indian", 0.9),
                # European Ethnic
                ("celtic", "genre", "celtic", 0.95),
                ("irish", "genre", "celtic", 0.9),
                ("scottish", "genre", "celtic", 0.9),
                ("germanic", "genre", "germanic", 0.9),
                ("nordic", "genre", "nordic", 0.95),
                ("viking", "genre", "nordic", 0.9),
                ("slavic", "genre", "slavic", 0.9),
                ("russian", "genre", "slavic", 0.9),
                # African
                ("african", "genre", "african", 0.95),
                ("tribal", "genre", "tribal", 0.9),
                # Latin American
                ("latin", "genre", "latin", 0.9),
                ("mexican", "genre", "latin", 0.9),
                ("brazilian", "genre", "latin", 0.9),
                ("cuban", "genre", "latin", 0.9),
                # Historical Periods
                ("medieval", "genre", "medieval", 0.95),
                ("renaissance", "genre", "renaissance", 0.95),
                ("ancient", "genre", "ancient", 0.95),
                ("baroque", "genre", "baroque", 0.95),
                ("romantic", "genre", "romantic", 0.95),
                ("victorian", "genre", "victorian", 0.9),
            ]

            # Default mood mappings
            mood_mappings = [
                ("dark", "mood", "dark", 0.9),
                ("bright", "mood", "bright", 0.9),
                ("happy", "mood", "happy", 0.9),
                ("sad", "mood", "sad", 0.9),
                ("melancholy", "mood", "sad", 0.8),
                ("aggressive", "mood", "aggressive", 0.9),
                ("peaceful", "mood", "peaceful", 0.9),
                ("calm", "mood", "peaceful", 0.8),
                ("tense", "mood", "tense", 0.9),
                ("suspenseful", "mood", "tense", 0.8),
                ("mysterious", "mood", "mysterious", 0.9),
                ("mystical", "mood", "mysterious", 0.8),
                ("romantic", "mood", "romantic", 0.9),
                ("intimate", "mood", "intimate", 0.9),
                ("powerful", "mood", "powerful", 0.9),
                ("dramatic", "mood", "dramatic", 0.9),
                ("minimal", "mood", "minimal", 0.9),
                ("complex", "mood", "complex", 0.9),
                ("simple", "mood", "simple", 0.9),
                ("rhythmic", "mood", "rhythmic", 0.8),
                ("melodic", "mood", "melodic", 0.8),
                ("atmospheric", "mood", "atmospheric", 0.8),
                ("aggressive", "mood", "aggressive", 0.8),
                ("gentle", "mood", "gentle", 0.8),
                ("epic", "mood", "epic", 0.8),
            ]

            # Default format mappings (playback type)
            format_mappings = [
                ("loop", "format", "loop", 0.9),
                ("one shot", "format", "one-shot", 0.9),
                ("oneshot", "format", "one-shot", 0.9),
                ("phrase", "format", "phrase", 0.8),
                ("stabs", "format", "stabs", 0.8),
                ("sustained", "format", "sustained", 0.8),
                ("short", "format", "short", 0.7),
                ("long", "format", "long", 0.7),
            ]

            # Insert all mappings
            all_mappings = (
                instrument_mappings + genre_mappings + mood_mappings + format_mappings
            )

            self.cursor.executemany(
                """
                INSERT INTO tag_mappings (pattern, tag_type, tag_value, confidence)
                VALUES (?, ?, ?, ?)
            """,
                all_mappings,
            )

            self.conn.commit()
            print(f"✅ Populated {len(all_mappings)} default tag mappings")

        except Exception as e:
            print(f"❌ Error populating default mappings: {e}")
            raise

    def _load_tag_mappings(self):
        """Load tag mappings into memory for fast lookup"""
        try:
            # Use the new database structure
            self.cursor.execute(
                "SELECT pattern, instrument, genre, mood, format, confidence, is_regex FROM tag_mappings"
            )
            mappings = self.cursor.fetchall()

            self.tag_mappings = defaultdict(list)
            for (
                pattern,
                instrument,
                genre,
                mood,
                format,
                confidence,
                is_regex,
            ) in mappings:
                # Add each tag type that has a value
                tag_types = {
                    "instrument": instrument,
                    "genre": genre,
                    "mood": mood,
                    "format": format,
                }

                for tag_type, tag_value in tag_types.items():
                    if tag_value:  # Only add if the tag value exists
                        # Parse JSON values to lists
                        parsed_values = self._parse_tag_value(tag_value)
                        if parsed_values:
                            # Create separate entries for each value
                            for value in parsed_values:
                                self.tag_mappings[tag_type].append(
                                    {
                                        "pattern": pattern,
                                        "value": value,
                                        "confidence": confidence,
                                        "is_regex": bool(is_regex),
                                    }
                                )

            total_mappings = sum(
                len(mappings) for mappings in self.tag_mappings.values()
            )
            print(f"📚 Loaded {total_mappings} tag mappings into memory")

        except Exception as e:
            print(f"❌ Error loading tag mappings: {e}")
            self.tag_mappings = defaultdict(list)

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

    def _extract_tags_rule_based(self, text: str) -> TagResult:
        """Extract tags using rule-based pattern matching"""
        text_lower = text.lower()
        result = TagResult(source="rule_based")
        total_confidence = 0.0
        match_count = 0

        # Check each tag type
        for tag_type in ["instrument", "genre", "mood", "format"]:
            matches = []
            confidences = []
            pattern_details = []  # Store pattern info for priority sorting

            for mapping in self.tag_mappings[tag_type]:
                pattern = mapping["pattern"]
                confidence = mapping["confidence"]

                if mapping["is_regex"]:
                    # Use regex matching
                    if re.search(pattern, text_lower):
                        matches.append(mapping["value"])
                        confidences.append(confidence)
                        pattern_details.append((pattern, confidence, len(pattern)))
                else:
                    # Use simple substring matching (case-insensitive)
                    if pattern.lower() in text_lower:
                        # Check for context conflicts - if pattern is part of a larger word, reduce confidence
                        adjusted_confidence = confidence

                        # Special case: "bass" in "Crumhorn Bass" should not match strings/synthesizer
                        if pattern.lower() == "bass" and "crumhorn" in text_lower:
                            adjusted_confidence = 0.1  # Very low confidence
                        # Special case: "horn" in "Crumhorn" should not match brass
                        elif pattern.lower() == "horn" and "crumhorn" in text_lower:
                            adjusted_confidence = 0.1  # Very low confidence

                        matches.append(mapping["value"])
                        confidences.append(adjusted_confidence)
                        pattern_details.append(
                            (pattern, adjusted_confidence, len(pattern))
                        )

            if matches:
                # Sort by pattern length (longer = more specific) and confidence
                # This ensures "crumhorn" beats "horn" and "wind" beats generic patterns
                sorted_matches = sorted(
                    zip(matches, confidences, pattern_details),
                    key=lambda x: (x[2][2], x[1]),
                    reverse=True,
                )

                # Smart conflict resolution: prioritize more specific patterns
                unique_matches = []
                seen = set()

                # Only apply family-based conflict resolution for instruments
                if tag_type == "instrument":
                    # Group matches by instrument family to avoid conflicts
                    instrument_families = {
                        "woodwind": [
                            "woodwind",
                            "flute",
                            "oboe",
                            "clarinet",
                            "bassoon",
                            "saxophone",
                            "crumhorn",
                            "shawm",
                            "recorder",
                            "bagpipe",
                        ],
                        "brass": [
                            "brass",
                            "trumpet",
                            "trombone",
                            "horn",
                            "tuba",
                            "french horn",
                        ],
                        "strings": [
                            "strings",
                            "violin",
                            "viola",
                            "cello",
                            "bass",
                            "guitar",
                            "harp",
                        ],
                        "percussion": [
                            "percussion",
                            "drums",
                            "drum",
                            "snare",
                            "kick",
                            "hihat",
                            "cymbal",
                        ],
                        "synthesizer": ["synthesizer", "synth", "pad", "lead", "bass"],
                        "piano": ["piano"],
                        "fx": [
                            "fx",
                            "effects",
                            "stabs",
                            "hits",
                            "impacts",
                            "risers",
                            "sweeps",
                            "transitions",
                        ],
                    }

                    # Find the best match for each instrument family
                    family_best_matches = {}

                    for match, confidence, pattern_info in sorted_matches:
                        pattern, conf, length = pattern_info

                        # Find which family this match belongs to
                        match_family = None
                        for family, instruments in instrument_families.items():
                            if match in instruments:
                                match_family = family
                                break

                        if match_family:
                            # Keep the best (longest pattern, highest confidence) match for each family
                            if (
                                match_family not in family_best_matches
                                or length > family_best_matches[match_family][2][2]
                            ):
                                family_best_matches[match_family] = (
                                    match,
                                    confidence,
                                    pattern_info,
                                )

                    # Add the best match from each family (only if confidence is reasonable)
                    for match, confidence, pattern_info in family_best_matches.values():
                        if (
                            match not in seen and confidence > 0.3
                        ):  # Filter out very low confidence matches
                            unique_matches.append(match)
                            seen.add(match)
                else:
                    # For non-instrument tags (genre, mood, format), just add all matches with good confidence
                    for match, confidence, pattern_info in sorted_matches:
                        if (
                            match not in seen and confidence > 0.3
                        ):  # Filter out very low confidence matches
                            unique_matches.append(match)
                            seen.add(match)

                setattr(result, tag_type, unique_matches)
                total_confidence += max(
                    confidences
                )  # Use highest confidence for this tag type
                match_count += 1

        # Calculate overall confidence
        if match_count > 0:
            result.confidence = total_confidence / match_count

        return result

    def _extract_tags_ai_enhanced(self, text: str) -> TagResult:
        """Extract tags using AI-enhanced analysis (placeholder for future implementation)"""
        # This would integrate with your existing AI system
        # For now, return empty result
        return TagResult(source="ai_enhanced", confidence=0.0)

    def _extract_tags_from_library_name(self, library_name: str) -> TagResult:
        """Extract tags specifically from library names"""
        if not library_name or library_name == "Unknown Library":
            return TagResult(source="fallback", confidence=0.0)

        # Use rule-based extraction on library name
        result = self._extract_tags_rule_based(library_name)

        # Add library-specific logic
        library_lower = library_name.lower()

        # Special handling for known libraries with ethnic/cultural genres
        if "ancient era persia" in library_lower or "persia" in library_lower:
            if not result.genre:
                result.genre = ["persian", "ancient", "ethnic"]
            else:
                for genre in ["persian", "ancient", "ethnic"]:
                    if genre not in result.genre:
                        result.genre.append(genre)

        elif "ancient era china" in library_lower or "china" in library_lower:
            if not result.genre:
                result.genre = ["chinese", "ancient", "ethnic"]
            else:
                for genre in ["chinese", "ancient", "ethnic"]:
                    if genre not in result.genre:
                        result.genre.append(genre)

        elif "dark era" in library_lower:
            if not result.genre:
                result.genre = ["nordic", "viking", "ancient"]
            else:
                for genre in ["nordic", "viking", "ancient"]:
                    if genre not in result.genre:
                        result.genre.append(genre)
            if not result.mood:
                result.mood = ["dark"]
            elif "dark" not in result.mood:
                result.mood.append("dark")

        elif "ancient era" in library_lower or "era ii" in library_lower:
            if not result.genre:
                result.genre = ["ancient", "medieval"]
            else:
                for genre in ["ancient", "medieval"]:
                    if genre not in result.genre:
                        result.genre.append(genre)

        elif "bbc symphony" in library_lower:
            if not result.genre:
                result.genre = ["orchestral"]
            elif "orchestral" not in result.genre:
                result.genre.append("orchestral")

        elif "albion" in library_lower:
            if not result.genre:
                result.genre = ["orchestral", "cinematic"]
            else:
                for genre in ["orchestral", "cinematic"]:
                    if genre not in result.genre:
                        result.genre.append(genre)

        elif "cine" in library_lower:
            if not result.genre:
                result.genre = ["cinematic"]
            elif "cinematic" not in result.genre:
                result.genre.append("cinematic")
            if not result.mood:
                result.mood = ["modern"]
            elif "modern" not in result.mood:
                result.mood.append("modern")

        elif "spitfire" in library_lower:
            if not result.genre:
                result.genre = ["orchestral"]
            elif "orchestral" not in result.genre:
                result.genre.append("orchestral")

        elif "native instruments" in library_lower or "kontakt" in library_lower:
            if not result.mood:
                result.mood = ["modern"]
            elif "modern" not in result.mood:
                result.mood.append("modern")

        return result

    def _extract_tags_from_filename(self, filename: str) -> TagResult:
        """Extract tags from individual filenames"""
        if not filename:
            return TagResult(source="fallback", confidence=0.0)

        # Remove file extension
        name_without_ext = Path(filename).stem.lower()

        # Use rule-based extraction
        result = self._extract_tags_rule_based(name_without_ext)

        # Add filename-specific logic
        if "loop" in name_without_ext:
            if not result.format:
                result.format = ["loop"]
            elif "loop" not in result.format:
                result.format.append("loop")

        if any(word in name_without_ext for word in ["bpm", "tempo", "speed"]):
            if not result.mood:
                result.mood = ["rhythmic"]
            elif "rhythmic" not in result.mood:
                result.mood.append("rhythmic")

        return result

    def tag_file(
        self, file_path: str, library_name: str = "", vendor_name: str = ""
    ) -> TagResult:
        """
        Automatically tag a file with instrument, genre, mood, and format

        Args:
            file_path: Full path to the file
            library_name: Library name (if known)
            vendor_name: Vendor name (if known)

        Returns:
            TagResult with extracted tags
        """
        try:
            filename = Path(file_path).name

            # Strategy 1: Extract from library name (highest priority)
            library_result = self._extract_tags_from_library_name(library_name)

            # Strategy 2: Extract from filename
            filename_result = self._extract_tags_from_filename(filename)

            # Strategy 3: Extract from full path
            path_result = self._extract_tags_rule_based(file_path)

            # Combine results with priority weighting
            final_result = TagResult()

            # Library name has highest priority
            for tag_type in ["instrument", "genre", "mood", "format"]:
                library_values = getattr(library_result, tag_type)
                filename_values = getattr(filename_result, tag_type)
                path_values = getattr(path_result, tag_type)

                # Combine all values, prioritizing library name
                combined_values = []

                # Add library values first (highest priority)
                if library_values and library_result.confidence > 0.5:
                    combined_values.extend(library_values)

                # Add filename values (medium priority)
                if filename_values and filename_result.confidence > 0.5:
                    for value in filename_values:
                        if value not in combined_values:
                            combined_values.append(value)

                # Add path values (lowest priority)
                if path_values and path_result.confidence > 0.5:
                    for value in path_values:
                        if value not in combined_values:
                            combined_values.append(value)

                setattr(final_result, tag_type, combined_values)

            # Calculate overall confidence
            confidences = [
                r.confidence
                for r in [library_result, filename_result, path_result]
                if r.confidence > 0
            ]
            if confidences:
                final_result.confidence = max(confidences)

            # Determine source
            if library_result.confidence > 0.5:
                final_result.source = "library_name"
            elif filename_result.confidence > 0.5:
                final_result.source = "filename"
            elif path_result.confidence > 0.5:
                final_result.source = "file_path"
            else:
                final_result.source = "fallback"

            return final_result

        except Exception as e:
            print(f"⚠️ Error tagging file {file_path}: {e}")
            return TagResult(source="error", confidence=0.0)

    def add_tag_mapping(
        self,
        pattern: str,
        tag_type: str,
        tag_value: str,
        confidence: float = 1.0,
        is_regex: bool = False,
    ) -> bool:
        """Add a new tag mapping to the database using the knowledge database"""
        try:
            # Use the knowledge database's add_tag_mapping method
            if hasattr(self, "knowledge_db"):
                # Map tag_type to the appropriate parameter
                kwargs = {
                    "pattern": pattern,
                    "confidence": confidence,
                    "is_regex": is_regex,
                }
                kwargs[tag_type] = tag_value

                success = self.knowledge_db.add_tag_mapping(**kwargs)
                if success:
                    # Reload mappings to include the new one
                    self._load_tag_mappings()
                    print(f"✅ Added tag mapping: {pattern} → {tag_type}:{tag_value}")
                return success
            else:
                print("❌ Knowledge database not available")
                return False

        except Exception as e:
            print(f"❌ Error adding tag mapping: {e}")
            return False

    def get_tag_statistics(self) -> Dict[str, Any]:
        """Get statistics about tag mappings"""
        try:
            stats = {}

            for tag_type in ["instrument", "genre", "mood", "format"]:
                self.cursor.execute(
                    f"SELECT COUNT(*) FROM tag_mappings WHERE {tag_type} IS NOT NULL"
                )
                count = self.cursor.fetchone()[0]
                stats[f"{tag_type}_mappings"] = count

            self.cursor.execute("SELECT COUNT(*) FROM tag_mappings")
            stats["total_mappings"] = self.cursor.fetchone()[0]

            return stats

        except Exception as e:
            print(f"❌ Error getting tag statistics: {e}")
            return {}

    def close(self):
        """Close database connection"""
        if hasattr(self, "knowledge_db"):
            self.knowledge_db.close()
        elif self.conn:
            self.conn.close()


# Convenience function for backward compatibility
def tag_file(
    file_path: str,
    library_name: str = "",
    vendor_name: str = "",
    tag_db_path: str = "patchio_knowledge.db",
) -> TagResult:
    """Tag a file using the automatic tagging system"""
    tagger = AutomaticTagger(tag_db_path)
    try:
        return tagger.tag_file(file_path, library_name, vendor_name)
    finally:
        tagger.close()


# Testing function
def test_automatic_tagger():
    """Test the automatic tagging system"""
    test_files = [
        {
            "path": "/Volumes/Samples/CineBrass/Core/Trumpets/Trumpet Ensemble.nki",
            "library": "CineBrass Core",
            "vendor": "Cinesamples",
        },
        {
            "path": "/Volumes/Samples/Spitfire Audio/BBC Symphony Orchestra/Instruments/Strings/Violin Section.nki",
            "library": "BBC Symphony Orchestra",
            "vendor": "Spitfire Audio",
        },
        {
            "path": "/Volumes/Samples/Native Instruments/Kontakt Factory Library/Instruments/Piano/Steinway Piano.nki",
            "library": "Kontakt Factory Library",
            "vendor": "Native Instruments",
        },
        {
            "path": "/Volumes/Samples/Output/Exhale/Voices/Choir/Dark Choir.wav",
            "library": "Exhale",
            "vendor": "Output",
        },
    ]

    print("🧪 Testing Automatic Tagging System")
    print("=" * 60)

    tagger = AutomaticTagger()

    for test_file in test_files:
        result = tagger.tag_file(
            test_file["path"], test_file["library"], test_file["vendor"]
        )

        print(f"File: {Path(test_file['path']).name}")
        print(f"  Library: {test_file['library']}")
        print(f"  Instrument: {result.instrument}")
        print(f"  Genre: {result.genre}")
        print(f"  Mood: {result.mood}")
        print(f"  Format: {result.format}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Source: {result.source}")
        print()

    # Show statistics
    stats = tagger.get_tag_statistics()
    print("📊 Tag Mapping Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    tagger.close()


if __name__ == "__main__":
    test_automatic_tagger()
