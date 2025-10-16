#!/usr/bin/env python3
"""
Vendor Normalization Utilities
Provides functions to normalize vendor names using patchio_knowledge.db as the source of truth.
"""

import sqlite3
import os
import sys
import appdirs
from typing import Dict, Optional

# Add the parent directory to the path to import settings
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from settings.core_settings import APP_NAME, APP_AUTHOR


def get_database_path():
    """Get the absolute path to the knowledge database file."""
    config_dir = appdirs.user_config_dir(APP_NAME, APP_AUTHOR)
    return os.path.join(config_dir, "patchio_knowledge.db")


def load_vendor_map():
    """
    Load the vendor mapping from patchio_knowledge.db.

    Returns:
        Dict[str, str]: Dictionary mapping raw vendor names to normalized names.

    Raises:
        FileNotFoundError: If the database file doesn't exist.
        sqlite3.Error: If there's an error accessing the database.
    """
    db_path = get_database_path()
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Knowledge database not found: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get vendor aliases from the database
        # We'll use vendor_specific_words as aliases for now
        cursor.execute(
            """
            SELECT word, vendor_name 
            FROM vendor_specific_words
        """
        )

        vendor_map = {}
        for word, vendor_name in cursor.fetchall():
            vendor_map[word] = vendor_name

        # Also add the vendor names themselves as mappings to themselves
        cursor.execute("SELECT vendor_name FROM vendor_profiles")
        for (vendor_name,) in cursor.fetchall():
            vendor_map[vendor_name] = vendor_name

        conn.close()
        return vendor_map

    except sqlite3.Error as e:
        raise sqlite3.Error(f"Database error: {e}")


def save_vendor_map(vendor_map: Dict[str, str]) -> bool:
    """
    Save the vendor mapping to patchio_knowledge.db.
    Note: This function is deprecated as vendor mappings should be managed through the database directly.

    Args:
        vendor_map (Dict[str, str]): Dictionary mapping raw vendor names to normalized names.

    Returns:
        bool: True if successful, False otherwise.
    """
    print(
        "⚠️ Warning: save_vendor_map is deprecated. Please update the database directly."
    )
    return False


def normalize_vendor(raw_vendor_name: str) -> str:
    """
    Normalize a vendor name using the mapping.

    Args:
        raw_vendor_name (str): The raw vendor name to normalize.

    Returns:
        str: The normalized vendor name, or the raw name if not found in mapping.

    Raises:
        FileNotFoundError: If the vendor map file doesn't exist.
        json.JSONDecodeError: If the JSON file is malformed.
        IOError: If there's an error reading the file.
    """
    if not raw_vendor_name:
        return raw_vendor_name

    vendor_map = load_vendor_map()

    # Try exact match first
    if raw_vendor_name in vendor_map:
        return vendor_map[raw_vendor_name]

    # Try case-insensitive match
    for raw_name, normalized_name in vendor_map.items():
        if raw_vendor_name.lower() == raw_name.lower():
            return normalized_name

    # If no match found, return the original name
    return raw_vendor_name


def add_vendor_mapping(raw_name: str, normalized_name: str) -> bool:
    """
    Add a new vendor mapping to patchio_knowledge.db.
    Note: This function is deprecated as vendor mappings should be managed through the database directly.

    Args:
        raw_name (str): The raw vendor name.
        normalized_name (str): The normalized vendor name.

    Returns:
        bool: True if successful, False otherwise.
    """
    print(
        "⚠️ Warning: add_vendor_mapping is deprecated. Please update the database directly."
    )
    return False


def remove_vendor_mapping(raw_name: str) -> bool:
    """
    Remove a vendor mapping from patchio_knowledge.db.
    Note: This function is deprecated as vendor mappings should be managed through the database directly.

    Args:
        raw_name (str): The raw vendor name to remove.

    Returns:
        bool: True if successful, False otherwise.
    """
    print(
        "⚠️ Warning: remove_vendor_mapping is deprecated. Please update the database directly."
    )
    return False


def get_all_normalized_vendors() -> set:
    """
    Get all unique normalized vendor names from patchio_knowledge.db.

    Returns:
        set: Set of all normalized vendor names.

    Raises:
        FileNotFoundError: If the database file doesn't exist.
        sqlite3.Error: If there's an error accessing the database.
    """
    db_path = get_database_path()
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Knowledge database not found: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all vendor names from vendor_profiles
        cursor.execute("SELECT vendor_name FROM vendor_profiles")
        vendors = set(row[0] for row in cursor.fetchall())

        conn.close()
        return vendors

    except sqlite3.Error as e:
        raise sqlite3.Error(f"Database error: {e}")


# Test function for isolation testing
def test_vendor_normalization():
    """
    Test function to verify vendor normalization works correctly.
    """
    print("Testing vendor normalization...")

    # Test cases
    test_cases = [
        ("Native Instruments", "Native Instruments"),
        ("NI", "Native Instruments"),
        ("NativeInstruments", "Native Instruments"),
        ("Spitfire Audio", "Spitfire Audio"),
        ("Spitfire", "Spitfire Audio"),
        ("Unknown Vendor", "Unknown Vendor"),  # Should return original
        ("", ""),  # Empty string
        ("Native Instruments", "Native Instruments"),  # Exact match
    ]

    for raw_name, expected in test_cases:
        result = normalize_vendor(raw_name)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{raw_name}' -> '{result}' (expected: '{expected}')")

    # Test adding new mapping
    print("\nTesting add_vendor_mapping...")
    success = add_vendor_mapping("Test Vendor", "Test Vendor Normalized")
    print(f"Add mapping: {'✓' if success else '✗'}")

    # Test the new mapping
    result = normalize_vendor("Test Vendor")
    print(f"New mapping test: {'✓' if result == 'Test Vendor Normalized' else '✗'}")

    # Test removing mapping
    print("\nTesting remove_vendor_mapping...")
    success = remove_vendor_mapping("Test Vendor")
    print(f"Remove mapping: {'✓' if success else '✗'}")

    # Verify removal
    result = normalize_vendor("Test Vendor")
    print(f"Removal test: {'✓' if result == 'Test Vendor' else '✗'}")


if __name__ == "__main__":
    test_vendor_normalization()
