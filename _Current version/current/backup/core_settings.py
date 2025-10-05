#!/usr/bin/env python3
"""
PatchIO Core Settings
Centralized configuration for easy editing and future JSON integration.
"""

# ============================================================================
# SEARCH CONFIGURATION
# ============================================================================

# Default file extensions to search for
DEFAULT_EXTENSIONS = [
    '.wav', '.mp3', '.aiff', '.flac', '.m4a', '.ogg', '.aac', 
    '.nki', '.nkm', '.nkb', '.nks', '.rex', '.rx2', '.aup',
    '.als', '.cwp', '.ptx', '.reason'
]

# Default folders to search in (will be replaced by JSON config)
DEFAULT_SEARCH_FOLDERS = [
    '/Volumes/Samsung 850 EVO',
    '/Users/shaked/Desktop/Samples',
    '/Users/shaked/Music'
]

# Search limits and performance
MAX_RESULTS_PER_LIBRARY = 50
MAX_TOTAL_RESULTS = 1000

# ============================================================================
# UI CONFIGURATION
# ============================================================================

# Column width limits
MAX_FILE_NAME_WIDTH = 400
MAX_FILE_TYPE_WIDTH = 100
MAX_KEYWORDS_WIDTH = 250
MAX_TAGS_WIDTH = 300

# Column padding for optimal display
FILE_NAME_PADDING = 40
FILE_TYPE_PADDING = 20
KEYWORDS_PADDING = 30
TAGS_PADDING = 30

# Window configuration
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 800
MIN_WINDOW_WIDTH = 1000
MIN_WINDOW_HEIGHT = 700

# ============================================================================
# GENRE KEYWORDS CONFIGURATION
# ============================================================================

# Music production categories for tag generation
GENRE_KEYWORDS = {
    'Rhythm': ['bass', 'kick', 'snare', 'hihat', 'drum', '808'],
    'Atmospheric': ['pad', 'ambient', 'atmospheric', 'texture', 'soundscape'],
    'Melodic': ['lead', 'melody', 'solo', 'hook'],
    'Strings': ['string', 'violin', 'cello', 'viola', 'orchestra'],
    'Brass': ['brass', 'horn', 'trumpet', 'trombone'],
    'Percussion': ['percussion', 'drum', 'cymbal', 'tom', 'perc'],
    'Keys': ['piano', 'keys', 'synth', 'keyboard'],
    'Guitar': ['guitar', 'acoustic', 'electric'],
    'Cinematic': ['cinematic', 'epic', 'trailer', 'orchestral', 'film'],
    'Electronic': ['electronic', 'edm', 'dubstep', 'trap', 'house', 'techno'],
    'Hip-Hop': ['hip-hop', 'hiphop', 'rap', 'beats', 'boom-bap'],
    'Vocal': ['vocal', 'voice', 'choir', 'lead']
}

# ============================================================================
# FILE TYPE CONFIGURATION
# ============================================================================

# File type mappings for display
FILE_TYPE_MAPPINGS = {
    '.wav': 'Audio',
    '.mp3': 'Audio', 
    '.aiff': 'Audio',
    '.flac': 'Audio',
    '.m4a': 'Audio',
    '.ogg': 'Audio',
    '.aac': 'Audio',
    '.nki': 'Kontakt',
    '.nkm': 'Kontakt',
    '.nks': 'NKS',
    '.mid': 'MIDI',
    '.midi': 'MIDI',
    '.fxp': 'Preset',
    '.fxb': 'Preset',
    '.als': 'Ableton',
    '.rex': 'REX Loop',
    '.rx2': 'REX Loop'
}

# File icons for display
FILE_ICON_MAPPINGS = {
    '.wav': '🎵',
    '.mp3': '🎵',
    '.aiff': '🎵',
    '.flac': '🎵',
    '.m4a': '🎵',
    '.ogg': '🎵',
    '.aac': '🎵',
    '.nki': '🎹',
    '.nkm': '🎹',
    '.nkb': '🎹',
    '.nks': '🎹',
    '.mid': '🎼',
    '.midi': '🎼',
    '.fxp': '🎛️',
    '.fxb': '🎛️',
    '.als': '🎚️',
    '.rex': '🔄',
    '.rx2': '🔄',
    '.zip': '📦',
    '.rar': '📦',
    '.7z': '📦'
} 