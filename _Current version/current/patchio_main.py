#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PatchIO - Modern Sound Library Manager
Entry point for the application
"""

import sys
import os

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from mvc_patchio_loader import MVCPatchIOLoader
from utils.logger import setup_logger, critical, error, info, debug
from models.user_settings_model import UserSettingsModel


def main():
    """Main entry point for PatchIO application"""
    try:
        # Initialize settings and logging
        settings = UserSettingsModel()
        logger = setup_logger(
            settings.get_log_file_path(), settings.get_log_config()["level"]
        )

        # Log application startup
        info("PatchIO application starting...")

        # Create and run the MVC application
        app = MVCPatchIOLoader()
        app.load_ui()
        return app.run()
    except Exception as e:
        error(f"❌ Failed to start PatchIO: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
