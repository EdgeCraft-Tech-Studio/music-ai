#!/usr/bin/env python3
"""
PatchIO Core Settings
Centralized configuration for easy editing and future JSON integration.
"""

# ============================================================================
# APP CONFIGURATION
# ============================================================================

# App identity (matches original patchio_old.py)
APP_NAME = "PatchIO"
APP_AUTHOR = None  # No author or company name

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Log file configuration (matches original patchio_old.py)
LOG_FILE_NAME = "patchIO_logs.log"  # Same filename as original
LOG_LEVEL = "DEBUG"  # Can be: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ============================================================================
# SEARCH CONFIGURATION
# ============================================================================

# Search limits and performance (these are constants, not user-configurable)
MAX_RESULTS_PER_LIBRARY = 50
MAX_TOTAL_RESULTS = 1000

# Initial search mode (can be: "classic_search", "keywords_editor", "ai")
INITIAL_SEARCH_MODE = "classic_search"

# Default values for user-configurable settings (used by user_settings_model.py)
DEFAULT_EXTENSIONS = [
    ".wav",
    ".mp3",
    ".aiff",
    ".flac",
    ".m4a",
    ".ogg",
    ".aac",
    ".nki",
    ".nkm",
    ".nkb",
    ".nks",
    ".rex",
    ".rx2",
    ".aup",
    ".als",
    ".cwp",
    ".reason",
    ".ytil",
]

DEFAULT_SEARCH_FOLDERS = [
    # Empty by default - users must configure folders in Preferences
    "/home/elvis/Music",
]
# /home/elvis/.config/PatchIO

# ============================================================================
# UI CONFIGURATION
# ============================================================================

# Column width limits
MAX_FILE_NAME_WIDTH = 400
MAX_FILE_TYPE_WIDTH = (
    150  # Increased from 100 to show full file types like "Audio, Kontakt"
)
MAX_KEYWORDS_WIDTH = 250
MAX_TAGS_WIDTH = 300

# Minimum column widths (users can't make columns smaller than this)
MIN_FILE_NAME_WIDTH = 200
MIN_FILE_TYPE_WIDTH = 120  # Minimum width to show "Audio, Kontakt"
MIN_KEYWORDS_WIDTH = 150
MIN_TAGS_WIDTH = 100

# Column padding for optimal display
FILE_NAME_PADDING = 40
FILE_TYPE_PADDING = 30
KEYWORDS_PADDING = 30
TAGS_PADDING = 30

# Window configuration
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 800
MIN_WINDOW_WIDTH = 1200
MIN_WINDOW_HEIGHT = 700

# UI file configuration
UI_FILE_PATH = "views/patchio_current_ui.ui"

# ============================================================================
# ICON CONFIGURATION
# ============================================================================

# Icon paths (relative to assets/icons folder)
ICON_PATHS = {
    "search_icon": "search_icon.png",
    "ai_search_icon": "ai_search_icon.png",
    "classic_search": "simple_mode.png",
    "keywords_editor": "advanced_mode.png",
    "start_search_button": "start_search_button.png",
    "cancel_search_button": "cancel_search_button.png",
}

# Icon sizes
ICON_SIZES = {
    "search_icon": (24, 24),
    "ai_search_icon": (24, 24),
    "classic_search": (24, 24),
    "keywords_editor": (24, 24),
    "start_search_button": (34, 34),
    "cancel_search_button": (16, 16),
}

# ============================================================================
# GENRE KEYWORDS CONFIGURATION
# ============================================================================

# Music production categories for tag generation
GENRE_KEYWORDS = {
    "Rhythm": ["bass", "kick", "snare", "hihat", "drum", "808"],
    "Atmospheric": ["pad", "ambient", "atmospheric", "texture", "soundscape"],
    "Melodic": ["lead", "melody", "solo", "hook"],
    "Strings": ["string", "violin", "cello", "viola", "orchestra"],
    "Brass": ["brass", "horn", "trumpet", "trombone"],
    "Percussion": ["percussion", "drum", "cymbal", "tom", "perc"],
    "Keys": ["piano", "keys", "synth", "keyboard"],
    "Guitar": ["guitar", "acoustic", "electric"],
    "Cinematic": ["cinematic", "epic", "trailer", "orchestral", "film"],
    "Electronic": ["electronic", "edm", "dubstep", "trap", "house", "techno"],
    "Hip-Hop": ["hip-hop", "hiphop", "rap", "beats", "boom-bap"],
    "Vocal": ["vocal", "voice", "choir", "lead"],
}

# ============================================================================
# FILE TYPE CONFIGURATION
# ============================================================================

# File type mappings for display
FILE_TYPE_MAPPINGS = {
    ".wav": "Audio",
    ".mp3": "Audio",
    ".aiff": "Audio",
    ".flac": "Audio",
    ".m4a": "Audio",
    ".ogg": "Audio",
    ".aac": "Audio",
    ".nki": "Kontakt",
    ".nkm": "Kontakt",
    ".nks": "NKS",
    ".mid": "MIDI",
    ".midi": "MIDI",
    ".fxp": "Preset",
    ".fxb": "Preset",
    ".als": "Ableton",
    ".cpr": "Cubase",
    ".rex": "REX Loop",
    ".rx2": "REX Loop",
}

# ============================================================================
# VENDOR AND LIBRARY MAPPING CONFIGURATION
# ============================================================================
# NOTE: Vendor and library mappings are now stored in vendor_library.db
# Use manage_vendor_db.py to manage vendor/library data
# Use utils.database_vendor_extractor for vendor/library extraction

# Patterns to remove from library names during cleaning
LIBRARY_CLEANING_PATTERNS = [
    r"\bKONTAKT\b",
    r"\bV\d+\.?\d*\b",  # Version numbers like V1.2, V1.6
    r"\bFULL LIBRARY\b",
    r"\bUPDATE\b",
    r"\bCORE\b",
    r"\bPRO\b",
    r"\bSTUDIO\b",
    r"\bEDITION\b",
    r"\bVOLUME\s+\d+\b",
    r"\bVOL\s+\d+\b",
    r"\b\d+\.\d+\b",  # Version numbers like 1.6, 2.0
    r"\b\(\d+\)\b",  # Numbers in parentheses
    r"\bBUNDLE\b",
    r"\bincl\.?\s+EXP?\s+[A-Z]\b",  # "incl. EXP A" patterns
    r"\bEXP?\s+[A-Z]\b",  # "EXP A" patterns
    r"\bTimpani\b",
    r"\bKONTAKT\b",
    r"\b\d+\.\d+\.\d+\b",  # Version numbers like 1.1.1
    r"\b\(\d+\)\b",  # Numbers in parentheses
    r"\b-\s*\d+\b",  # Numbers after dash
    r"\b\d+\s*BIT\b",  # "16BIT", "24BIT" etc
    r"\bMP3\s+\d+KBPS\b",  # "MP3 320KBPS"
    r"\bSofter\b",  # Common suffix
    r"\bAlternative\b",  # Common suffix
    r"\bSoft\b",  # Common suffix
    r"\bHard\b",  # Common suffix
    r"\bNormal\b",  # Common suffix
    r"\bTremolo\b",  # Common suffix
    r"\bmp\b",  # Common suffix
    r"\bmf\b",  # Common suffix
    r"\bff\b",  # Common suffix
    r"\bpp\b",  # Common suffix
    r"\bC\d+\b",  # Note names like C5
    r"\b[A-G]#?\d+\b",  # Note names like F#1, G5
]

# Specific library name corrections
LIBRARY_NAME_CORRECTIONS = {
    "berlin percussion bundle incl. exp a timpani": "Berlin Percussion",
    "berlin percussion": "Berlin Percussion",
    "berlin strings": "Berlin Strings",
    "berlin brass": "Berlin Brass",
    "berlin woodwinds": "Berlin Woodwinds",
    "spitfire symphonic strings library": "Spitfire Symphonic Strings",
    "logic samples": "Logic Samples",
    "alchemy samples": "Alchemy Samples",
    "synthogy - ivory grand pianos": "Ivory Grand Pianos",
    "don't stop me now (5)": "Don't Stop Me Now",
    "vox processed kits": "Vox Processed Kits",
    "electronic drums": "Electronic Drums",
    "instrument library": "Instrument Library",
    "application support": "Application Support",
    "02 electronic drum kits": "Electronic Drum Kits",
    "bandura phrases": "Bandura Phrases",
    "violins 1": "Violins 1",
    "violins 2": "Violins 2",
    "digital bass": "Digital Bass",
    "01 acoustic pianos": "Acoustic Pianos",
    "bandura effects": "Bandura Effects",
    "unusual drums": "Unusual Drums",
    "01 synth bass": "Synth Bass",
    "electric guitars": "Electric Guitars",
    "05 synthesizers": "Synthesizers",
    "eleanor improv phrases": "Eleanor Improv Phrases",
}

# Note: Vendor mapping is now handled through patchio_knowledge.db
# The old VENDOR_MAP_PATH has been deprecated in favor of the centralized database configuration

# ============================================================================
# FILE ICON MAPPINGS
# ============================================================================

# File icons for display
FILE_ICON_MAPPINGS = {
    ".wav": "🎵",
    ".mp3": "🎵",
    ".aiff": "🎵",
    ".flac": "🎵",
    ".m4a": "🎵",
    ".ogg": "🎵",
    ".aac": "🎵",
    ".nki": "🎹",
    ".nkm": "🎹",
    ".nkb": "🎹",
    ".nks": "🎹",
    ".mid": "🎼",
    ".midi": "🎼",
    ".fxp": "🎛️",
    ".fxb": "🎛️",
    ".als": "🎚️",
    ".rex": "🔄",
    ".rx2": "🔄",
    ".zip": "📦",
    ".rar": "📦",
    ".7z": "📦",
}

# ============================================================================
# ELASTICSEARCH CONFIGURATION
# ============================================================================

# Elasticsearch configuration
ELASTICSEARCH_ENABLED = True
ELASTICSEARCH_HOSTS = ["http://localhost:9200"]
ELASTICSEARCH_USERNAME = None
ELASTICSEARCH_PASSWORD = None
ELASTICSEARCH_SSL_VERIFY = False
ELASTICSEARCH_INDEX = "patchio_files"
ELASTICSEARCH_AUTOCOMPLETE_MIN_CHARS = 2
ELASTICSEARCH_BULK_SIZE = 2000
ELASTICSEARCH_BULK_CONCURRENCY = 2
ELASTICSEARCH_MAX_RESULTS = 1000

# curl -X GET "http://localhost:9200/patchio_files/_search?pretty&size=10"
