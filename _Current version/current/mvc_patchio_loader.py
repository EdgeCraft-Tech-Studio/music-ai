#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MVC PatchIO Loader - Connects .ui file with MVC architecture
This replaces modern_patchio_ui_loader.py with proper MVC separation
"""

import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile

from controllers.main_controller import MainController
from utils.logger import debug, info, warning, error, critical

# UI file path constant - get directly from core settings
from settings.core_settings import UI_FILE_PATH, ICON_PATHS, ICON_SIZES
from models.user_settings_model import UserSettingsModel

settings = UserSettingsModel()

# Debug: Print what we got from settings
debug(f"🔍 Debug - UI_FILE_PATH from core settings: {UI_FILE_PATH}")
debug(f"🔍 Debug - All available settings: {list(settings.current_settings.keys())}")


class MVCPatchIOLoader:
    """MVC-based UI loader that connects .ui file with MVC architecture"""

    def __init__(self):
        self.app = None
        self.main_controller = None
        self.ui_file = UI_FILE_PATH

    def load_ui(self):
        """Load the UI from .ui file and connect to MVC"""
        # Create QApplication if it doesn't exist
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication(sys.argv)

        # Create main controller (which creates models and view)
        self.main_controller = MainController()

        # Load UI file and connect to the main window view
        self.load_ui_file()

        # Setup UI connections
        self.setup_ui_connections()

        # Setup UI elements after widgets are connected
        self.main_controller.main_window.setup_ui_after_connection()

        # Set the controller reference in the main window view
        self.main_controller.main_window.set_controller(self.main_controller)

        # Setup icons (like the original)
        self.setup_icons()

        # ✅ Return controller last
        return self.main_controller

    def load_ui_file(self):
        """Load the .ui file and connect it to the main window view"""
        # Check if UI file path is valid
        if not self.ui_file:
            critical("❌ CRITICAL ERROR: UI file path is None or empty")
            error("🔍 This usually means the settings file cannot be loaded")
            error("🔍 Expected UI file path from settings: UI_FILE_PATH")
            error("🔍 Fallback path: views/patchio_current_ui.ui")
            error("")
            error("❌ Application cannot start without a valid UI file path")
            error(
                "❌ Please check that settings/core_settings.py exists and contains UI_FILE_PATH"
            )
            raise ValueError(
                "UI file path is None - settings may not be loaded correctly"
            )

        # Use absolute path to the UI file
        import os

        full_ui_path = os.path.join(os.path.dirname(__file__), self.ui_file)
        ui_file_path = QFile(full_ui_path)
        if not ui_file_path.exists():
            warning(f"⚠️ UI file not found: {ui_file_path.fileName()}")
            warning(
                f"🔍 Expected path: {os.path.join(os.path.dirname(__file__), self.ui_file)}"
            )
            warning(f"🔍 Current working directory: {os.getcwd()}")
            error("❌ Please ensure the UI file exists at the specified path")
            return

        # Load UI file
        loader = QUiLoader()
        ui_file_path.open(QFile.ReadOnly)
        ui_widget = loader.load(ui_file_path, None)  # Load with None like the original
        ui_file_path.close()

        if not ui_widget:
            warning(f"⚠️ Failed to load UI file: {self.ui_file}")
            return

        # Set the central widget first (like the original)
        self.main_controller.main_window.setCentralWidget(ui_widget)

        # Connect UI elements to the main window view
        self.connect_ui_elements(ui_widget)

    def connect_ui_elements(self, ui_widget):
        """Connect UI elements from .ui file to the main window view"""
        main_window = self.main_controller.main_window

        # Connect search elements (using QWidget like the original)
        from PySide6.QtWidgets import QWidget, QLineEdit
        from views.bubble_search_input import BubbleSearchInput
        from views.advanced_search_input import AdvancedSearchInput

        # Find the original search input
        original_search_input = ui_widget.findChild(QLineEdit, "searchInput")

        if original_search_input:
            # Replace with our custom bubble search input
            search_bar_frame = ui_widget.findChild(QWidget, "searchBar")
            if search_bar_frame:
                # Get the layout of the search bar frame
                layout = search_bar_frame.layout()
                if layout:
                    # Find the index of the original search input in the layout
                    for i in range(layout.count()):
                        item = layout.itemAt(i)
                        if item.widget() == original_search_input:
                            # Create our custom bubble search input
                            bubble_search_input = BubbleSearchInput()

                            # Copy properties from original
                            bubble_search_input.setPlaceholderText(
                                original_search_input.placeholderText()
                            )
                            bubble_search_input.setStyleSheet(
                                original_search_input.styleSheet()
                            )
                            bubble_search_input.setAlignment(
                                original_search_input.alignment()
                            )
                            bubble_search_input.setMinimumSize(
                                original_search_input.minimumSize()
                            )
                            bubble_search_input.setMaximumSize(
                                original_search_input.maximumSize()
                            )
                            bubble_search_input.setSizePolicy(
                                original_search_input.sizePolicy()
                            )

                            # Replace the original widget in the layout
                            layout.replaceWidget(
                                original_search_input, bubble_search_input
                            )

                            # Delete the original widget
                            original_search_input.deleteLater()

                            # Set our custom widget as the search input
                            main_window.search_input = bubble_search_input
                            break

        # Connect other search elements
        main_window.clear_button = ui_widget.findChild(QWidget, "clearButton")
        main_window.start_search_button = ui_widget.findChild(
            QWidget, "startSearchButton"
        )
        main_window.results_area = ui_widget.findChild(QWidget, "resultsArea")
        main_window.search_icon = ui_widget.findChild(QWidget, "searchIcon")
        main_window.search_bar_frame = ui_widget.findChild(QWidget, "searchBar")

        # Debug: Print what widgets were found
        debug("🔍 Debug - Widgets found:")
        debug(f"  search_input: {main_window.search_input}")
        debug(f"  clear_button: {main_window.clear_button}")
        debug(f"  start_search_button: {main_window.start_search_button}")
        debug(f"  results_area: {main_window.results_area}")
        debug(f"  search_icon: {main_window.search_icon}")
        debug(f"  search_bar_frame: {main_window.search_bar_frame}")
        debug(f"  classic_search_button: {main_window.classic_search_button}")
        debug(f"  keywords_editor_button: {main_window.keywords_editor_button}")
        debug(f"  ai_search_button: {main_window.ai_search_button}")
        debug(f"  sidebar: {main_window.sidebar}")

        # Connect mode buttons (using actual names from .ui file)
        main_window.classic_search_button = ui_widget.findChild(QWidget, "simpleButton")
        main_window.keywords_editor_button = ui_widget.findChild(
            QWidget, "advancedButton"
        )
        main_window.ai_search_button = ui_widget.findChild(QWidget, "aiButton")

        # Connect sidebar
        main_window.sidebar = ui_widget.findChild(QWidget, "sidebar")

        # Debug: Print what widgets were found
        debug("🔍 Debug - Widgets found:")
        debug(f"  search_input: {main_window.search_input}")
        debug(f"  results_area: {main_window.results_area}")
        debug(f"  search_icon: {main_window.search_icon}")
        debug(f"  search_bar_frame: {main_window.search_bar_frame}")
        debug(f"  classic_search_button: {main_window.classic_search_button}")
        debug(f"  keywords_editor_button: {main_window.keywords_editor_button}")
        debug(f"  ai_search_button: {main_window.ai_search_button}")
        debug(f"  sidebar: {main_window.sidebar}")

        # Store the UI widget for later use
        main_window.ui_widget = ui_widget

        debug("✅ UI elements connected to MVC architecture")

    def setup_ui_connections(self):
        """Setup connections between UI and controllers"""
        main_window = self.main_controller.main_window
        search_controller = self.main_controller.search_controller

        # Connect search input events
        if main_window.search_input:
            main_window.search_input.returnPressed.connect(
                search_controller.on_search_triggered
            )
            # Store reference to original search input for mode switching
            main_window.original_search_input = main_window.search_input

        # Connect cancel search button events
        if main_window.clear_button:
            main_window.clear_button.clicked.connect(
                main_window.on_cancel_search_button_clicked
            )

        # Connect mode button events
        if main_window.classic_search_button:
            main_window.classic_search_button.clicked.connect(
                lambda: search_controller.on_mode_changed("classic_search")
            )
        if main_window.keywords_editor_button:
            main_window.keywords_editor_button.clicked.connect(
                lambda: search_controller.on_mode_changed("keywords_editor")
            )
        if main_window.ai_search_button:
            main_window.ai_search_button.clicked.connect(
                lambda: search_controller.on_mode_changed("ai")
            )

        debug("✅ UI connections established")

    def setup_icons(self):
        """Setup all icons for the UI (like the original)"""
        try:
            debug("🎨 Setting up icons...")

            # Setup search icon
            self.setup_search_icon()

            # Setup button icons
            self.setup_ai_button_icon()
            self.setup_classic_search_button_icon()
            self.setup_keywords_editor_button_icon()

            # Setup filter button arrow icons
            self.setup_filter_button_icons()

            debug("✅ All icons setup completed")

        except Exception as e:
            error("⚠️ Error setting up icons: {}".format(e))

    def setup_filter_button_icons(self):
        """Setup arrow icons for filter buttons"""
        try:
            from PySide6.QtGui import QIcon
            from PySide6.QtWidgets import QWidget
            from pathlib import Path

            debug("🔍 Setting up filter button icons...")

            # Get the filter buttons
            main_window = self.main_controller.main_window
            instruments_button = main_window.findChild(QWidget, "instrumentsDropdown")
            genres_button = main_window.findChild(QWidget, "genresDropdown")
            vendor_button = main_window.findChild(QWidget, "vendorDropdown")

            debug(
                f"🔍 Found buttons: instruments={instruments_button}, genres={genres_button}, vendor={vendor_button}"
            )

            # Load arrow icon
            icon_path = Path(__file__).parent / "assets/icons" / "arrow_down.png"
            icon_path = icon_path.resolve()

            debug(f"🔍 Looking for arrow icon at: {icon_path}")

            if icon_path.exists():
                icon = QIcon(str(icon_path))
                if not icon.isNull():
                    # Set icons for all filter buttons
                    if instruments_button and hasattr(instruments_button, "setIcon"):
                        instruments_button.setIcon(icon)
                        debug("✅ Set icon for instruments button")
                    if genres_button and hasattr(genres_button, "setIcon"):
                        genres_button.setIcon(icon)
                        debug("✅ Set icon for genres button")
                    if vendor_button and hasattr(vendor_button, "setIcon"):
                        vendor_button.setIcon(icon)
                        debug("✅ Set icon for vendor button")
                    debug("✅ Filter button arrow icons loaded from file")
                else:
                    warning("⚠️ Could not load arrow_down.png icon")
                    self.setup_filter_button_fallback_arrows()
            else:
                warning("⚠️ Arrow icon file not found: {}".format(icon_path))
                # Fallback to Unicode arrow if icon file doesn't exist
                self.setup_filter_button_fallback_arrows()

        except Exception as e:
            error("⚠️ Error setting up filter button icons: {}".format(e))
            # Fallback to Unicode arrow on error
            self.setup_filter_button_fallback_arrows()

    def setup_filter_button_fallback_arrows(self):
        """Setup fallback Unicode arrows for filter buttons"""
        try:
            from PySide6.QtGui import QIcon, QPixmap, QPainter, QFont, QColor
            from PySide6.QtWidgets import QWidget
            from PySide6.QtCore import Qt

            debug("🔍 Setting up fallback arrows...")

            # Get the filter buttons
            main_window = self.main_controller.main_window
            instruments_button = main_window.findChild(QWidget, "instrumentsDropdown")
            genres_button = main_window.findChild(QWidget, "genresDropdown")
            vendor_button = main_window.findChild(QWidget, "vendorDropdown")

            debug(
                f"🔍 Found buttons for fallback: instruments={instruments_button}, genres={genres_button}, vendor={vendor_button}"
            )

            # Create a small pixmap with the arrow
            pixmap = QPixmap(12, 12)
            pixmap.fill(Qt.GlobalColor.transparent)

            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Set font for the arrow
            font = QFont()
            font.setPointSize(8)
            font.setFamily(
                "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
            )
            painter.setFont(font)

            # Draw white arrow
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "▼")
            painter.end()

            icon = QIcon(pixmap)

            # Set icons for all filter buttons
            if instruments_button and hasattr(instruments_button, "setIcon"):
                instruments_button.setIcon(icon)
                debug("✅ Set fallback icon for instruments button")
            if genres_button and hasattr(genres_button, "setIcon"):
                genres_button.setIcon(icon)
                debug("✅ Set fallback icon for genres button")
            if vendor_button and hasattr(vendor_button, "setIcon"):
                vendor_button.setIcon(icon)
                debug("✅ Set fallback icon for vendor button")

            debug("✅ Filter button fallback arrows set")

        except Exception as e:
            error("⚠️ Error setting up filter button fallback arrows: {}".format(e))

    def setup_search_icon(self):
        """Setup search icon"""
        try:
            search_icon = self.main_controller.main_window.search_icon
            if search_icon:
                # Try to load from .ui file first (if already set)
                if not search_icon.pixmap():
                    # Load from file as fallback
                    from pathlib import Path

                    icon_filename = ICON_PATHS.get("search_icon", "search_icon.png")
                    icon_path = Path(__file__).parent / "assets/icons" / icon_filename
                    # Resolve the path to handle relative paths properly
                    icon_path = icon_path.resolve()
                    if icon_path.exists():
                        from PySide6.QtGui import QPixmap

                        pixmap = QPixmap(str(icon_path))
                        if not pixmap.isNull():
                            search_icon.setPixmap(pixmap)
                            debug("✅ Search icon loaded from file")
                        else:
                            warning("⚠️ Could not load search icon from file")
                    else:
                        warning("⚠️ Search icon file not found: {}".format(icon_path))
                else:
                    debug("✅ Search icon already loaded from .ui file")
            else:
                warning("⚠️ Search icon widget not found")

        except Exception as e:
            error("⚠️ Error setting up search icon: {}".format(e))

    def setup_ai_button_icon(self):
        """Setup AI button icon"""
        try:
            ai_button = self.main_controller.main_window.ai_search_button
            if ai_button and hasattr(ai_button, "setIcon"):
                # Try to load from .ui file first (if already set)
                if not ai_button.icon():
                    # Load from file as fallback
                    from pathlib import Path

                    icon_filename = ICON_PATHS.get(
                        "ai_search_icon", "ai_search_icon.png"
                    )
                    icon_path = Path(__file__).parent / "assets/icons" / icon_filename
                    # Resolve the path to handle relative paths properly
                    icon_path = icon_path.resolve()
                    if icon_path.exists():
                        from PySide6.QtGui import QIcon

                        icon = QIcon(str(icon_path))
                        if not icon.isNull():
                            ai_button.setIcon(icon)
                            debug("✅ AI button icon loaded from file")
                        else:
                            warning("⚠️ Could not load AI button icon from file")
                    else:
                        warning("⚠️ AI button icon file not found: {}".format(icon_path))
                else:
                    debug("✅ AI button icon already loaded from .ui file")
            else:
                warning("⚠️ AI button widget not found or does not have setIcon")

        except Exception as e:
            error("⚠️ Error setting up AI button icon: {}".format(e))

    def setup_classic_search_button_icon(self):
        """Setup Classic Search button icon"""
        try:
            classic_search_button = (
                self.main_controller.main_window.classic_search_button
            )
            if classic_search_button and hasattr(classic_search_button, "setIcon"):
                # Try to load from .ui file first (if already set)
                if not classic_search_button.icon():
                    # Load from file as fallback
                    from pathlib import Path

                    icon_filename = ICON_PATHS.get("classic_search", "simple_mode.png")
                    icon_path = Path(__file__).parent / "assets/icons" / icon_filename
                    # Resolve the path to handle relative paths properly
                    icon_path = icon_path.resolve()
                    if icon_path.exists():
                        from PySide6.QtGui import QIcon

                        icon = QIcon(str(icon_path))
                        if not icon.isNull():
                            classic_search_button.setIcon(icon)
                            debug("✅ Classic Search button icon loaded from file")
                        else:
                            warning(
                                "⚠️ Could not load Classic Search button icon from file"
                            )
                    else:
                        warning(
                            "⚠️ Classic Search button icon file not found: {}".format(
                                icon_path
                            )
                        )
                else:
                    debug("✅ Classic Search button icon already loaded from .ui file")
            else:
                warning(
                    "⚠️ Classic Search button widget not found or does not have setIcon"
                )

        except Exception as e:
            error("⚠️ Error setting up Classic Search button icon: {}".format(e))

    def setup_keywords_editor_button_icon(self):
        """Setup Keywords Editor button icon"""
        try:
            keywords_editor_button = (
                self.main_controller.main_window.keywords_editor_button
            )
            if keywords_editor_button and hasattr(keywords_editor_button, "setIcon"):
                # Try to load from .ui file first (if already set)
                if not keywords_editor_button.icon():
                    # Load from file as fallback
                    from pathlib import Path

                    icon_filename = ICON_PATHS.get(
                        "keywords_editor", "advanced_mode.png"
                    )
                    icon_path = Path(__file__).parent / "assets/icons" / icon_filename
                    # Resolve the path to handle relative paths properly
                    icon_path = icon_path.resolve()
                    if icon_path.exists():
                        from PySide6.QtGui import QIcon

                        icon = QIcon(str(icon_path))
                        if not icon.isNull():
                            keywords_editor_button.setIcon(icon)
                            debug("✅ Keywords Editor button icon loaded from file")
                        else:
                            warning(
                                "⚠️ Could not load Keywords Editor button icon from file"
                            )
                    else:
                        warning(
                            "⚠️ Keywords Editor button icon file not found: {}".format(
                                icon_path
                            )
                        )
                else:
                    debug("✅ Keywords Editor button icon already loaded from .ui file")
            else:
                warning(
                    "⚠️ Keywords Editor button widget not found or does not have setIcon"
                )

        except Exception as e:
            error("⚠️ Error setting up Keywords Editor button icon: {}".format(e))

    def run(self):
        """Run the MVC application"""
        if not self.main_controller:
            warning("⚠️ Main controller not initialized")
            return 1

        # Setup dropdown connections after UI is loaded
        self.main_controller.setup_dropdown_connections()

        # Show the main window
        main_window = self.main_controller.main_window
        main_window.show()
        main_window.set_search_focus()

        debug("🚀 Starting PatchIO with MVC architecture")

        # Start the application
        return self.app.exec()


def main():
    """Main entry point for MVC PatchIO"""
    loader = MVCPatchIOLoader()
    controller = loader.load_ui()

    if controller:
        return loader.run()
    else:
        warning("⚠️ Failed to initialize MVC application")
        return 1


if __name__ == "__main__":
    sys.exit(main())
