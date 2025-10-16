#!/usr/bin/env python3
"""
Settings Model - MVC Model for user-configurable settings management
Static constants should be imported directly from settings.core_settings
"""

import os
import json
import logging
import appdirs
from typing import Dict, Any, List, Optional

# Import static constants from core settings
try:
    from settings.core_settings import (
        APP_NAME,
        APP_AUTHOR,
        LOG_FILE_NAME,
        LOG_LEVEL,
        LOG_FORMAT,
        LOG_DATE_FORMAT,
    )

    # Try to import logger, but don't fail if it's not initialized yet
    try:
        from utils.logger import info, debug, warning, error, critical

        info("✅ Successfully imported settings from settings.core_settings")
    except RuntimeError:
        # Logger not initialized yet, use print instead
        print("✅ Successfully imported settings from settings.core_settings")

except ImportError as e:
    # Try to use logger, but fall back to print if not available
    try:
        from utils.logger import critical, error

        critical(f"❌ CRITICAL ERROR: Cannot import settings.core_settings")
        error(f"🔍 Error details: {e}")
        error("❌ Application cannot start without settings.core_settings")
    except RuntimeError:
        print(f"❌ CRITICAL ERROR: Cannot import settings.core_settings")
        print(f"🔍 Error details: {e}")
        print("❌ Application cannot start without settings.core_settings")
    raise ImportError(f"Failed to import settings.core_settings: {e}")


class UserSettingsModel:
    """Model for user-configurable settings only.
    Static constants should be imported directly from settings.core_settings"""

    def __init__(self):
        # Use same app identity as original patchio_old.py
        self.app_name = APP_NAME
        self.app_author = APP_AUTHOR

        # Setup config directory (matches original patchio_old.py)
        self.config_dir = appdirs.user_config_dir(self.app_name, self.app_author)
        os.makedirs(self.config_dir, exist_ok=True)

        # Settings file path (matches original patchio_old.py)
        self.settings_file = os.path.join(self.config_dir, "patchIO_settings.json")

        # Log file path (matches original patchio_old.py)
        self.log_file = os.path.join(self.config_dir, LOG_FILE_NAME)

        # Load current settings
        self.current_settings = self.load_settings()

    def get_log_file_path(self) -> str:
        """Get the log file path (matches original patchio_old.py)"""
        return self.log_file

    def get_log_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return {
            "filename": self.log_file,
            "filemode": "a",  # Append mode
            "level": LOG_LEVEL,  # Return as string
            "format": LOG_FORMAT,
            "datefmt": LOG_DATE_FORMAT,
        }

    def _load_current_settings(self) -> Dict[str, Any]:
        """Load current settings from file or create defaults"""
        try:
            # Temporarily ignore old JSON file to avoid format conflicts
            # TODO: Add migration logic for old JSON format
            debug(f"📁 Using default settings (ignoring old JSON file for now)")
            return self._get_default_settings()

            # Original code (commented out until we handle old format):
            # if os.path.exists(self.settings_file):
            #     with open(self.settings_file, 'r', encoding='utf-8') as f:
            #         settings = json.load(f)
            #         debug(f"📁 Loaded settings from: {self.settings_file}")
            #         return settings
            # else:
            #     debug(f"📁 Settings file not found, using defaults: {self.settings_file}")
            #     return self._get_default_settings()
        except Exception as e:
            error(f"⚠️ Error loading settings: {e}")
            return self._get_default_settings()

    def _get_default_settings(self) -> Dict[str, Any]:
        """Get default user-configurable settings only"""
        # Import default values from core settings for initial setup
        from settings.core_settings import DEFAULT_EXTENSIONS, DEFAULT_SEARCH_FOLDERS

        return {
            "last_folders": [],
            "extensions": DEFAULT_EXTENSIONS,  # User can modify these
            "search_folders": DEFAULT_SEARCH_FOLDERS,  # User can modify these
            "excluded_folders": [],
            "cubase_key_command": "",
            "shown_key_command_warning": False,
        }

    def load_settings(self) -> Dict[str, Any]:
        """Load settings from file"""
        try:
            return self._load_current_settings()
        except Exception as e:
            error(f"⚠️ Error loading settings: {e}")
            return self._get_default_settings()

    def save_settings(self, settings: Dict[str, Any]) -> None:
        """Save settings to file"""
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)
            debug(f"💾 Settings saved to: {self.settings_file}")
        except Exception as e:
            error(f"⚠️ Error saving settings: {e}")

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a specific user setting value"""
        return self.current_settings.get(key, default)

    def update_setting(self, key: str, value: Any) -> None:
        """Update a specific user setting value"""
        try:
            self.current_settings[key] = value
            self.save_settings(self.current_settings)
            debug(f"🔧 Updated setting: {key} = {value}")
        except Exception as e:
            error(f"⚠️ Error updating setting {key}: {e}")
