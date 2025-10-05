#!/usr/bin/env python3
"""
Settings package for PatchIO
Contains all configuration and settings modules
"""

from .core_settings import *

__all__ = [
    'DEFAULT_EXTENSIONS',
    'DEFAULT_SEARCH_FOLDERS', 
    'MAX_RESULTS_PER_LIBRARY',
    'MAX_TOTAL_RESULTS',
    'MAX_FILE_NAME_WIDTH',
    'MAX_FILE_TYPE_WIDTH',
    'MAX_KEYWORDS_WIDTH',
    'MAX_TAGS_WIDTH',
    'FILE_NAME_PADDING',
    'FILE_TYPE_PADDING',
    'KEYWORDS_PADDING',
    'TAGS_PADDING',
    'DEFAULT_WINDOW_WIDTH',
    'DEFAULT_WINDOW_HEIGHT',
    'MIN_WINDOW_WIDTH',
    'MIN_WINDOW_HEIGHT',
    'GENRE_KEYWORDS',
    'FILE_TYPE_MAPPINGS',
    'FILE_ICON_MAPPINGS'
] 