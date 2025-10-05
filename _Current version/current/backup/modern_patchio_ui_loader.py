#!/usr/bin/env python3
"""
Modern PatchIO - Working Version
Gradually adds functionality to identify crash causes
"""

import sys
import os
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QHeaderView
from PySide6.QtCore import Qt, QFile, QIODevice
from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import QPixmap, QIcon



# Import the real search engine
try:
    from core_search import search_engine
    print("✅ Successfully imported search_engine from core_search")
except ImportError as e:
    print("⚠️ Could not import search_engine: {}".format(e))
    search_engine = None

# Import settings
from core_settings import (
    MAX_RESULTS_PER_LIBRARY,
    MAX_FILE_NAME_WIDTH, MAX_FILE_TYPE_WIDTH, MAX_KEYWORDS_WIDTH, MAX_TAGS_WIDTH,
    FILE_NAME_PADDING, FILE_TYPE_PADDING, KEYWORDS_PADDING, TAGS_PADDING,
    DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT, MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT,
    FILE_TYPE_MAPPINGS, FILE_ICON_MAPPINGS
)
print("✅ Successfully imported settings from core_settings")

class ModernPatchIOUILoader(QMainWindow):
    """Modern PatchIO using Qt Designer .ui file"""
    
    def get_file_icon(self, file_path):
        """Get appropriate icon based on file extension for music producers"""
        _, ext = os.path.splitext(file_path.lower())
        
        # Use settings for file icons
        return FILE_ICON_MAPPINGS.get(ext, "📄")

    def get_file_type_info(self, file_path):
        """Get file type information for display"""
        _, ext = os.path.splitext(file_path.lower())
        
        # Use settings for file type mappings
        return FILE_TYPE_MAPPINGS.get(ext, "File")
    
    def __init__(self):
        super().__init__()
        
        # Initialize tracking dictionaries for tree items
        self.item_id_to_path = {}
        self.library_nodes = {}
        
        # Initialize search engine
        self.search_engine = search_engine
        
        # Load the UI file
        self.load_ui()
        
        # Set up window properties
        self.setup_window()
        
        # Initialize widget references (minimal)
        self.setup_widget_references()
        
        print("🎉 PatchIO Working started successfully!")
    
    def load_ui(self):
        """Load the .ui file using QUiLoader"""
        ui_file_path = Path(__file__).parent / "patchio_current_ui.ui"
        
        if not ui_file_path.exists():
            raise RuntimeError("UI file not found: {}".format(ui_file_path))
        
        loader = QUiLoader()
        ui_file = QFile(str(ui_file_path))
        
        if not ui_file.open(QIODevice.ReadOnly):
            raise RuntimeError("Cannot open UI file: {}".format(ui_file_path))
        
        ui_widget = loader.load(ui_file, None)
        ui_file.close()
        
        if ui_widget is None:
            raise RuntimeError("Failed to load UI file")
        
        self.setCentralWidget(ui_widget)
        self.ui_widget = ui_widget
        
        print("✅ UI file loaded: {}".format(ui_file_path))
    
    def setup_window(self):
        """Configure main window properties"""
        self.setWindowTitle("PatchIO - Modern Version (UI Loader)")
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
        
        # Center window on screen
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
    
    def setup_widget_references(self):
        """Create easy references to UI widgets - MINIMAL VERSION"""
        print("🔍 Finding widgets...")
        
        # Find basic widgets first
        self.search_input = self.ui_widget.findChild(QWidget, "searchInput")
        self.results_area = self.ui_widget.findChild(QWidget, "resultsArea")
        self.search_icon = self.ui_widget.findChild(QWidget, "searchIcon")
        self.search_bar = self.ui_widget.findChild(QWidget, "searchBar")
        
        # Find search mode buttons
        self.ai_button = self.ui_widget.findChild(QWidget, "aiButton")
        self.simple_button = self.ui_widget.findChild(QWidget, "simpleButton")
        self.advanced_button = self.ui_widget.findChild(QWidget, "advancedButton")
        
        # Verify widgets
        found_widgets = []
        for name, widget in [
            ("search_input", self.search_input),
            ("results_area", self.results_area),
            ("search_icon", self.search_icon),
            ("search_bar", self.search_bar),
            ("ai_button", self.ai_button),
            ("simple_button", self.simple_button),
            ("advanced_button", self.advanced_button),
        ]:
            if widget is not None:
                found_widgets.append(name)
        
        print("✅ Found widgets: {}".format(', '.join(found_widgets)))
        
        # Setup results area - SIMPLIFIED VERSION
        if self.results_area:
            self.setup_simple_results_safe()
        
        # Setup search mode buttons
        if self.ai_button and self.simple_button and self.advanced_button:
            self.setup_search_mode_buttons()
        
        # Setup search input functionality
        if self.search_input:
            self.setup_search_input()
        
        # Setup search engine
        self.setup_search_engine()
        
        # Setup icons
        self.setup_icons()
        
        # Setup event filter for focus handling on all widgets
        self.setup_global_event_filters()
    
    def setup_icons(self):
        """Setup all icons for the UI"""
        try:
            print("🎨 Setting up icons...")
            
            # Setup search icon
            self.setup_search_icon()
            
            # Setup button icons
            self.setup_ai_button_icon()
            self.setup_simple_button_icon()
            self.setup_advanced_button_icon()
            
            print("✅ All icons setup completed")
            
        except Exception as e:
            print("⚠️ Error setting up icons: {}".format(e))
    
    def setup_search_icon(self):
        """Setup search icon"""
        try:
            if self.search_icon:
                # Try to load from .ui file first (if already set)
                if not self.search_icon.pixmap():
                    # Load from file as fallback
                    icon_path = Path(__file__).parent / "search_icon.png"
                    if icon_path.exists():
                        pixmap = QPixmap(str(icon_path))
                        if not pixmap.isNull():
                            self.search_icon.setPixmap(pixmap)
                            print("✅ Search icon loaded from file")
                        else:
                            print("⚠️ Could not load search icon from file")
                    else:
                        print("⚠️ Search icon file not found: {}".format(icon_path))
                else:
                    print("✅ Search icon already loaded from .ui file")
            else:
                print("⚠️ Search icon widget not found")
                
        except Exception as e:
            print("⚠️ Error setting up search icon: {}".format(e))
    
    def setup_ai_button_icon(self):
        """Setup AI button icon"""
        try:
            if self.ai_button and hasattr(self.ai_button, 'setIcon'): # Check if it's a QWidget with setIcon
                # Try to load from .ui file first (if already set)
                if not self.ai_button.icon():
                    # Load from file as fallback
                    icon_path = Path(__file__).parent / "ai_search_icon.png"
                    if icon_path.exists():
                        icon = QIcon(str(icon_path))
                        if not icon.isNull():
                            self.ai_button.setIcon(icon)
                            print("✅ AI button icon loaded from file")
                        else:
                            print("⚠️ Could not load AI button icon from file")
                    else:
                        print("⚠️ AI button icon file not found: {}".format(icon_path))
                else:
                    print("✅ AI button icon already loaded from .ui file")
            else:
                print("⚠️ AI button widget not found or does not have setIcon")
                
        except Exception as e:
            print("⚠️ Error setting up AI button icon: {}".format(e))
    
    def setup_simple_button_icon(self):
        """Setup Simple button icon"""
        try:
            if self.simple_button and hasattr(self.simple_button, 'setIcon'): # Check if it's a QWidget with setIcon
                # Try to load from .ui file first (if already set)
                if not self.simple_button.icon():
                    # Load from file as fallback
                    icon_path = Path(__file__).parent / "simple_mode.png"
                    if icon_path.exists():
                        icon = QIcon(str(icon_path))
                        if not icon.isNull():
                            self.simple_button.setIcon(icon)
                            print("✅ Simple button icon loaded from file")
                        else:
                            print("⚠️ Could not load Simple button icon from file")
                    else:
                        print("⚠️ Simple button icon file not found: {}".format(icon_path))
                else:
                    print("✅ Simple button icon already loaded from .ui file")
            else:
                print("⚠️ Simple button widget not found or does not have setIcon")
                
        except Exception as e:
            print("⚠️ Error setting up Simple button icon: {}".format(e))
    
    def setup_advanced_button_icon(self):
        """Setup Advanced button icon"""
        try:
            if self.advanced_button and hasattr(self.advanced_button, 'setIcon'): # Check if it's a QWidget with setIcon
                # Try to load from .ui file first (if already set)
                if not self.advanced_button.icon():
                    # Load from file as fallback
                    icon_path = Path(__file__).parent / "advanced_mode.png"
                    if icon_path.exists():
                        icon = QIcon(str(icon_path))
                        if not icon.isNull():
                            self.advanced_button.setIcon(icon)
                            print("✅ Advanced button icon loaded from file")
                        else:
                            print("⚠️ Could not load Advanced button icon from file")
                    else:
                        print("⚠️ Advanced button icon file not found: {}".format(icon_path))
                else:
                    print("✅ Advanced button icon already loaded from .ui file")
            else:
                print("⚠️ Advanced button widget not found or does not have setIcon")
                
        except Exception as e:
            print("⚠️ Error setting up Advanced button icon: {}".format(e))
    
    def eventFilter(self, obj, event):
        """Handle focus events for search input and background clicks"""
        try:
            from PySide6.QtCore import QEvent
            
            if event.type() == QEvent.MouseButtonPress and event.button() == 1:  # Left click
                # Simple web app behavior: any click except on search input clears focus
                if obj != self.search_input:
                    if self.search_input and self.search_input.hasFocus():
                        self.search_input.clearFocus()
            
            elif event.type() == QEvent.FocusIn:
                # Add blue border when search input gets focus
                if obj == self.search_input:
                    if hasattr(self, 'search_bar') and self.search_bar:
                        self.search_bar.setProperty("focused", True)
                        self.search_bar.style().unpolish(self.search_bar)
                        self.search_bar.style().polish(self.search_bar)

            
            elif event.type() == QEvent.FocusOut:
                # Remove blue border when search input loses focus
                if obj == self.search_input:
                    if hasattr(self, 'search_bar') and self.search_bar:
                        self.search_bar.setProperty("focused", False)
                        self.search_bar.style().unpolish(self.search_bar)
                        self.search_bar.style().polish(self.search_bar)

            
        except Exception as e:
            print("⚠️ Error in event filter: {}".format(e))
        
        # Always call parent event filter
        return super().eventFilter(obj, event)
    
    def mousePressEvent(self, event):
        """Handle mouse press events on the main window"""
        try:
            from PySide6.QtCore import Qt
            
            if event.button() == Qt.LeftButton:
                if self.search_input and self.search_input.hasFocus():
                    # Get the widget that was clicked
                    clicked_widget = self.childAt(event.position().toPoint())
                    
                    # If it's not the search input, clear focus
                    if clicked_widget != self.search_input:
                        self.search_input.clearFocus()
            
        except Exception as e:
            print("⚠️ Error in mousePressEvent: {}".format(e))
        
        # Always call parent mousePressEvent
        super().mousePressEvent(event)
    
    def setup_global_event_filters(self):
        """Setup event filters on all widgets for web app-like focus behavior"""
        try:
            print("🌐 Setting up global event filters for web app behavior...")
            
            # Install on main window
            self.installEventFilter(self)
            
            # Install on central widget
            if self.ui_widget:
                self.ui_widget.installEventFilter(self)
            
            # Install on ALL child widgets to catch clicks anywhere
            for widget in self.findChildren(QWidget):
                if widget != self.search_input:  # Don't install on search input itself
                    widget.installEventFilter(self)
            
            print("✅ Global event filters installed on all widgets")
            
        except Exception as e:
            print("⚠️ Error setting up global event filters: {}".format(e))
    
    def setup_search_mode_buttons(self):
        """Setup search mode buttons with radio button behavior"""
        try:
            print("🔧 Setting up search mode buttons...")
            
            # Connect button signals
            if self.ai_button:
                self.ai_button.clicked.connect(lambda: self.on_mode_button_clicked(self.ai_button))
            if self.simple_button:
                self.simple_button.clicked.connect(lambda: self.on_mode_button_clicked(self.simple_button))
            if self.advanced_button:
                self.advanced_button.clicked.connect(lambda: self.on_mode_button_clicked(self.advanced_button))
            
            # Set Simple as default selected
            if self.simple_button:
                self.simple_button.setChecked(True)
            
            print("✅ Search mode buttons setup completed")
            
        except Exception as e:
            print("⚠️ Error setting up search mode buttons: {}".format(e))
    
    def on_mode_button_clicked(self, clicked_button):
        """Handle search mode button clicks"""
        try:
            print("🎯 Mode button clicked: {}".format(clicked_button.objectName()))
            
            # Ensure only one button is checked (radio button behavior)
            for button in [self.ai_button, self.simple_button, self.advanced_button]:
                if button and button != clicked_button:
                    button.setChecked(False)
            
            # Update results area to show current mode
            self.update_results_for_mode()
            
        except Exception as e:
            print("⚠️ Error handling mode button click: {}".format(e))
    
    def update_results_for_mode(self):
        """Update results area to show current search mode"""
        try:
            current_mode = self.get_current_search_mode()
            
            if self.results_area:
                # Update the label text
                for child in self.results_area.children():
                    if isinstance(child, QLabel):
                        child.setText("Search results will appear here\n\nCurrent mode: {}\n\nTry searching for files!".format(current_mode))
                        break
                        
        except Exception as e:
            print("⚠️ Error updating results for mode: {}".format(e))
    
    def get_current_search_mode(self):
        """Get the currently selected search mode"""
        try:
            if self.ai_button and self.ai_button.isChecked():
                return "AI Search"
            elif self.simple_button and self.simple_button.isChecked():
                return "Simple"
            elif self.advanced_button and self.advanced_button.isChecked():
                return "Advanced"
            else:
                return "Simple"  # Default
        except Exception as e:
            print("⚠️ Error getting current search mode: {}".format(e))
            return "Simple"
    
    def setup_simple_results_safe(self):
        """Setup results area with minimal safe approach"""
        try:
            print("🔧 Setting up results area (safe mode)...")
            
            # Create simple label without clearing existing content
            self.results_label = QLabel("Search results will appear here\n\nTry searching for files!")
            self.results_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            self.results_label.setWordWrap(True)
            self.results_label.setStyleSheet("""
                QLabel {
                    color: #FFFFFF;
                    font-size: 14px;
                    padding: 20px;
                    background-color: #2C2C2E;
                    border-radius: 8px;
                }
            """)
            
            # Add to results area
            layout = QVBoxLayout(self.results_area)
            layout.addWidget(self.results_label)
            layout.setContentsMargins(0, 0, 0, 0)
            
            print("✅ Safe results area created")
            
        except Exception as e:
            print("⚠️ Error creating safe results area: {}".format(e))
    
    def create_tree_widget_safe(self):
        """Create tree widget safely by replacing the label"""
        try:
            print("🌳 Creating tree widget safely...")
            
            # Remove the existing label
            if hasattr(self, 'results_label') and self.results_label:
                self.results_label.setParent(None)
                self.results_label.deleteLater()
            
            # Create tree widget
            self.results_tree = QTreeWidget(self.results_area)
            self.results_tree.setHeaderLabels(["File Name", "Type", "Location"])
            self.results_tree.setAlternatingRowColors(False)  # Clean look without alternating colors
            self.results_tree.setStyleSheet("""
                QTreeWidget {
                    background-color: #2C2C2E;
                    color: #FFFFFF;
                    border: 1px solid #3C3C3E;
                    border-radius: 8px;
                    font-size: 14px;
                    outline: none;
                }
                QTreeWidget::item {
                    padding: 12px 8px;
                    border: none;
                    min-height: 32px;
                    border-radius: 6px;
                    margin: 1px;
                }
                QTreeWidget::item:selected {
                    background-color: #007AFF;
                    color: #FFFFFF;
                    border: 1px solid #0051D5;
                }
                QTreeWidget::item:selected:active {
                    background-color: #007AFF;
                    color: #FFFFFF;
                }
                QTreeWidget::item:selected:!active {
                    background-color: #4A90E2;
                    color: #FFFFFF;
                }
                QTreeWidget::item:alternate {
                    background-color: #262628;
                }
                QTreeWidget::item:alternate:selected {
                    background-color: #007AFF;
                    color: #FFFFFF;
                    border: 1px solid #0051D5;
                }
                QTreeWidget::item:hover {
                    background-color: #3A3A3C;
                    border-radius: 6px;
                }
                QTreeWidget::branch:closed:has-children {
                    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTYgNEwxMCA4TDYgMTJWNFoiIGZpbGw9IiNBQUFBQUEiLz4KPHN2Zz4K);
                }
                QTreeWidget::branch:open:has-children {
                    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTQgNkw4IDEwTDEyIDZINFoiIGZpbGw9IiNBQUFBQUEiLz4KPHN2Zz4K);
                }
            """)
            
            # Add to results area (replace the label)
            layout = self.results_area.layout()
            if layout:
                layout.addWidget(self.results_tree)
            
            print("✅ Tree widget created safely")
            return True
            
        except Exception as e:
            print("⚠️ Error creating tree widget: {}".format(e))
            return False
    
    def setup_tree_widget(self):
        """Setup tree widget for results display - called only when needed"""
        try:
            print("🌳 Setting up tree widget...")
            
            # Clear existing content
            for child in self.results_area.children():
                child.deleteLater()
            
            # Create tree widget
            self.results_tree = QTreeWidget(self.results_area)
            self.results_tree.setHeaderLabels(["File Name", "Type", "Location"])
            self.results_tree.setAlternatingRowColors(False)  # Clean look without alternating colors
            self.results_tree.setStyleSheet("""
                QTreeWidget {
                    background-color: #2C2C2E;
                    color: #FFFFFF;
                    border: 1px solid #3C3C3E;
                    border-radius: 8px;
                    font-size: 14px;
                    outline: none;
                }
                QTreeWidget::item {
                    padding: 12px 8px;
                    border: none;
                    min-height: 32px;
                    border-radius: 6px;
                    margin: 1px;
                }
                QTreeWidget::item:selected {
                    background-color: #007AFF;
                    color: #FFFFFF;
                    border: 1px solid #0051D5;
                }
                QTreeWidget::item:selected:active {
                    background-color: #007AFF;
                    color: #FFFFFF;
                }
                QTreeWidget::item:selected:!active {
                    background-color: #4A90E2;
                    color: #FFFFFF;
                }
                QTreeWidget::item:alternate {
                    background-color: #262628;
                }
                QTreeWidget::item:alternate:selected {
                    background-color: #007AFF;
                    color: #FFFFFF;
                    border: 1px solid #0051D5;
                }
                QTreeWidget::item:hover {
                    background-color: #3A3A3C;
                    border-radius: 6px;
                }
                QTreeWidget::branch:closed:has-children {
                    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTYgNEwxMCA4TDYgMTJWNFoiIGZpbGw9IiNBQUFBQUEiLz4KPHN2Zz4K);
                }
                QTreeWidget::branch:open:has-children {
                    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTQgNkw4IDEwTDEyIDZINFoiIGZpbGw9IiNBQUFBQUEiLz4KPHN2Zz4K);
                }
            """)
            
            # Add to results area
            layout = QVBoxLayout(self.results_area)
            layout.addWidget(self.results_tree)
            layout.setContentsMargins(0, 0, 0, 0)
            
            print("✅ Tree widget created successfully")
            
        except Exception as e:
            print("⚠️ Error creating tree widget: {}".format(e))
            # Fallback to simple label
            self.setup_simple_results_fallback()
    
    def setup_simple_results_fallback(self):
        """Fallback to simple label if tree widget fails"""
        try:
            print("📝 Setting up simple results fallback...")
            
            # Create a simple label for results
            results_label = QLabel("Search results will appear here\n\nTry searching for files!")
            results_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            results_label.setWordWrap(True)
            results_label.setStyleSheet("""
                QLabel {
                    color: #FFFFFF;
                    font-size: 14px;
                    padding: 20px;
                    background-color: #2C2C2E;
                    border-radius: 8px;
                }
            """)
            
            # Add to results area
            layout = QVBoxLayout(self.results_area)
            layout.addWidget(results_label)
            layout.setContentsMargins(0, 0, 0, 0)
            
            print("✅ Simple results fallback created")
            
        except Exception as e:
            print("⚠️ Error creating simple results fallback: {}".format(e))
    
    def setup_search_input(self):
        """Setup search input with Enter key support"""
        try:
            print("🔧 Setting up search input...")
            
            # Connect Enter key to search
            if hasattr(self.search_input, 'returnPressed'):
                self.search_input.returnPressed.connect(self.on_search_clicked)
            elif hasattr(self.search_input, 'textChanged'):
                # For QLineEdit, we can also connect textChanged for live search
                self.search_input.textChanged.connect(self.on_search_text_changed)
            
            # Install event filter on search input for focus handling
            if self.search_input:
                self.search_input.installEventFilter(self)
            
            print("✅ Search input setup completed")
            
        except Exception as e:
            print("⚠️ Error setting up search input: {}".format(e))
    
    def on_search_clicked(self):
        """Handle search button click or Enter key press"""
        try:
            search_text = self.get_search_text()
            current_mode = self.get_current_search_mode()
            
            print("🔍 Search triggered: '{}' in {} mode".format(search_text, current_mode))
            
            if not search_text.strip():
                self.update_results_message("Please enter a search term")
                return
            
            # Perform search based on mode
            if current_mode == "Simple":
                self.perform_simple_search(search_text)
            elif current_mode == "AI Search":
                self.perform_ai_search(search_text)
            elif current_mode == "Advanced":
                self.perform_advanced_search(search_text)
            else:
                self.perform_simple_search(search_text)  # Default to simple
                
        except Exception as e:
            print("⚠️ Error performing search: {}".format(e))
            self.update_results_message("Search error occurred")
    
    def on_search_text_changed(self):
        """Handle search text changes (for live search if needed)"""
        try:
            search_text = self.get_search_text()
            if len(search_text) > 2:  # Only search if 3+ characters
                # Could implement live search here
                pass
        except Exception as e:
            print("⚠️ Error handling text change: {}".format(e))
    
    def get_search_text(self):
        """Get the current search text"""
        try:
            if hasattr(self.search_input, 'toPlainText'):
                return self.search_input.toPlainText()
            elif hasattr(self.search_input, 'text'):
                return self.search_input.text()
            else:
                return ""
        except Exception as e:
            print("⚠️ Error getting search text: {}".format(e))
            return ""
    
    def perform_simple_search(self, query):
        """Perform simple file search using real search engine"""
        try:
            print("📁 Performing simple search for: '{}'".format(query))
            
            if self.search_engine is None:
                print("⚠️ Search engine not available, using mock results")
                results = [
                    {"name": "Sample File 1.wav", "path": "/path/to/file1.wav", "type": "Audio File"},
                    {"name": "Sample File 2.nki", "path": "/path/to/file2.nki", "type": "Kontakt Instrument"},
                    {"name": "Sample File 3.mp3", "path": "/path/to/file3.mp3", "type": "Audio File"},
                ]
                self.update_results_with_data(results, "Simple Search Results (Mock)")
                return
            
            # Use the real search engine
            print("🔍 Using real search engine...")
            results = self.search_engine.simple_search(query)
            
            if results:
                print("✅ Found {} real results".format(len(results)))
                self.update_results_with_data(results, "Simple Search Results")
            else:
                print("💡 No results found")
                self.update_results_message("No files found matching '{}'".format(query))
            
        except Exception as e:
            print("⚠️ Error in simple search: {}".format(e))
            self.update_results_message("Simple search error: {}".format(str(e)))
    
    def perform_ai_search(self, query):
        """Perform AI-powered search using real search engine"""
        try:
            print("🤖 Performing AI search for: '{}'".format(query))
            
            if self.search_engine is None:
                print("⚠️ Search engine not available, using mock results")
                results = [
                    {"name": "AI Generated Sound 1.wav", "path": "/ai/path1.wav", "type": "AI Generated"},
                    {"name": "AI Generated Sound 2.wav", "path": "/ai/path2.wav", "type": "AI Generated"},
                ]
                self.update_results_with_data(results, "AI Search Results (Mock)")
                return
            
            # Use the real search engine
            print("🔍 Using real AI search engine...")
            results = self.search_engine.ai_search(query)
            
            if results:
                print("✅ Found {} AI results".format(len(results)))
                self.update_results_with_data(results, "AI Search Results")
            else:
                print("💡 No AI results found")
                self.update_results_message("No AI results for '{}'".format(query))
            
        except Exception as e:
            print("⚠️ Error in AI search: {}".format(e))
            self.update_results_message("AI search error: {}".format(str(e)))
    
    def perform_advanced_search(self, query):
        """Perform advanced search with filters using real search engine"""
        try:
            print("⚙️ Performing advanced search for: '{}'".format(query))
            
            if self.search_engine is None:
                print("⚠️ Search engine not available, using mock results")
                results = [
                    {"name": "Advanced Filtered File 1.wav", "path": "/advanced/path1.wav", "type": "Advanced Result"},
                    {"name": "Advanced Filtered File 2.nki", "path": "/advanced/path2.nki", "type": "Advanced Result"},
                ]
                self.update_results_with_data(results, "Advanced Search Results (Mock)")
                return
            
            # Use the real search engine
            print("🔍 Using real advanced search engine...")
            results = self.search_engine.advanced_search(query)
            
            if results:
                print("✅ Found {} advanced results".format(len(results)))
                self.update_results_with_data(results, "Advanced Search Results")
            else:
                print("💡 No advanced results found")
                self.update_results_message("No advanced results for '{}'".format(query))
            
        except Exception as e:
            print("⚠️ Error in advanced search: {}".format(e))
            self.update_results_message("Advanced search error: {}".format(str(e)))
    
    def update_results_with_data(self, results, title):
        """Update results area with actual search data"""
        try:
            # If we have many results, try to create tree widget
            if len(results) > 5 and not hasattr(self, 'results_tree'):
                try:
                    if self.create_tree_widget_safe():
                        print("✅ Tree widget created for results display")
                    else:
                        print("⚠️ Could not create tree widget, using label")
                except Exception as e:
                    print("⚠️ Could not create tree widget: {}".format(e))
            
            # Use tree widget if available, otherwise use label
            if hasattr(self, 'results_tree') and self.results_tree:
                # Use tree widget
                self.update_tree_with_results(results, title)
            else:
                # Fallback to label
                self.update_label_with_results(results, title)
                        
        except Exception as e:
            print("⚠️ Error updating results with data: {}".format(e))
    
    def extract_library_info(self, file_path):
        """Extract meaningful library name using proven patchio.py logic"""
        
        # First, try the extract_library_root approach from patchio.py
        library_name = self.extract_library_root_patchio_style(file_path)
        
        # If that didn't work, fall back to get_library_key approach
        if not library_name or library_name in ['samples', 'audio', 'sounds', 'instruments']:
            library_name = self.get_library_key_patchio_style(file_path)
            library_name = os.path.basename(library_name.rstrip(os.sep)) if library_name else "Unknown Library"
        
        return library_name
    
    def extract_library_root_patchio_style(self, path):
        """
        Extract library name by analyzing internal library structure patterns
        Focuses on the library content structure, not the path leading to it
        """
        parts = os.path.normpath(path).split(os.sep)
        
        # Common library internal folders that indicate we're inside a library
        library_internal_folders = [
            'instruments', 'samples', 'presets', 'patches', 'multis', 'articulations',
            'data', 'layers', 'keyswitches', 'resources', 'audio', 'sounds', 'loops'
        ]
        
        # Common library organization folders (these contain libraries, not part of library name)
        organization_folders = [
            'volumes', 'users', 'applications', 'desktop', 'documents', 'downloads',
            'libraries', 'kontakt libraries', 'player libraries', 'non player libraries',
            'best service engine libraries', 'service engine libraries',
            'sample libraries', 'vst', 'plugins'
        ]
        
        # Find library boundaries by looking for internal structure
        library_start_index = -1
        library_end_index = -1
        
        # Step 1: Find the DEEPEST library internal structure (prefer inner folders over organization)
        best_library_start = -1
        best_library_end = -1
        
        for i, part in enumerate(parts):
            part_lower = part.lower()
            if part_lower in library_internal_folders:
                # Look backwards to find where meaningful names begin
                for j in range(i - 1, -1, -1):
                    prev_part = parts[j]
                    prev_lower = prev_part.lower()
                    
                    # Skip organization folders
                    if prev_lower in organization_folders:
                        continue
                    
                    # Skip system/drive paths (first 3 components usually)
                    if j < 3:
                        continue
                        
                    # This looks like a meaningful library name
                    if len(prev_part) > 2 and not prev_part.startswith('.'):
                        # Prefer deeper matches (higher i means deeper in path)
                        if i > best_library_end:
                            best_library_start = j
                            best_library_end = i - 1
                        break
        
        library_start_index = best_library_start
        library_end_index = best_library_end
        
        # Step 2: Extract the meaningful library name
        if library_start_index >= 0 and library_end_index >= library_start_index:
            # For simple cases: just one folder name
            if library_start_index == library_end_index:
                return parts[library_start_index]
            
            # For complex cases: combine relevant parts
            library_parts = parts[library_start_index:library_end_index + 1]
            
            # Handle special cases based on your examples:
            # Case 1: Vendor + Product (e.g., "Strezov Sampling" + "Strezov Sampling Freyja" -> "Strezov Sampling Freyja")
            if len(library_parts) == 2:
                vendor, product = library_parts
                # If product contains vendor name, just use product
                if vendor.lower() in product.lower():
                    return product
                # Otherwise combine them
                return "{} {}".format(vendor, product)
            
            # Case 2: Multiple parts - take the most descriptive one
            best_part = None
            best_score = 0
            
            for part in library_parts:
                score = len(part)  # Longer names are usually more descriptive
                if ' ' in part or '-' in part:  # Product names often have spaces/dashes
                    score += 10
                if any(char.isdigit() for char in part):  # Version numbers
                    score += 5
                    
                if score > best_score:
                    best_part = part
                    best_score = score
            
            return best_part if best_part else library_parts[-1]
        
        # Fallback: Use the folder just before common internal folders
        for i, part in enumerate(parts):
            if part.lower() in library_internal_folders and i > 0:
                candidate = parts[i - 1]
                if len(candidate) > 3 and candidate.lower() not in organization_folders:
                    return candidate
                    
        return None
    
    def get_library_key_patchio_style(self, path):
        """
        Get library key using patchio.py's get_library_key logic
        Excludes generic directories to find meaningful library names
        """
        parts = os.path.normpath(path).split(os.sep)
        generic_dirs = {
            "samples", "instruments", "presets", "audio", "multis", "articulations",
            "data", "patches", "files", "programs", "kits", "output", "sounds",
            "loops", "sessions", "projects", "tracks", "stems"
        }
        
        # Walk backwards through path parts to find a meaningful library folder
        for i in range(len(parts) - 1, 1, -1):
            if parts[i].lower() not in generic_dirs and len(parts[i]) > 3:
                return os.sep.join(parts[:i + 1])
                
        # Fallback
        return os.sep.join(parts[-3:]) if len(parts) >= 3 else path

    def extract_musical_metadata(self, file_name, file_path):
        """Extract BPM, key, and other musical info from filename - essential for producers"""
        metadata = {'bpm': '', 'key': '', 'genre': '', 'duration': ''}
        
        name_lower = file_name.lower()
        
        # Extract BPM (critical for producers and composers)
        import re
        bpm_patterns = [
            r'(\d{2,3})\s*bpm',      # "120bpm", "128 bpm"
            r'(\d{2,3})bpm',         # "120bpm"
            r'_(\d{2,3})_',          # "_120_"
            r'(\d{2,3})$',           # ending with number
        ]
        
        for pattern in bpm_patterns:
            match = re.search(pattern, name_lower)
            if match:
                bpm_val = int(match.group(1))
                if 60 <= bpm_val <= 200:  # Reasonable BPM range
                    metadata['bpm'] = "{}bpm".format(bpm_val)
                    break
        
        # Extract musical key (essential for composers)
        key_patterns = [
            r'\b([A-G]#?m?)\b',      # C, Dm, F#, etc.
            r'_([A-G]#?m?)_',        # _Dm_
            r'([A-G]#?m?)$',         # ending with key
        ]
        
        for pattern in key_patterns:
            match = re.search(pattern, name_lower)
            if match:
                key_candidate = match.group(1)
                # Validate it's actually a key
                if len(key_candidate) <= 3 and key_candidate[0].upper() in 'ABCDEFG':
                    metadata['key'] = key_candidate.upper()
                    break
        
        # Note: Genre detection moved to extract_tags_from_metadata using genre_keywords logic
        
        # Get file extension for type info
        _, ext = os.path.splitext(file_name.lower())
        if ext in ['.wav', '.mp3', '.aiff', '.flac', '.ogg']:
            metadata['duration'] = "[Audio]"
        elif ext in ['.nki', '.nkm']:
            metadata['duration'] = "[Kontakt]"
        elif ext in ['.mid', '.midi']:
            metadata['duration'] = "[MIDI]"
        
        return metadata

    def group_results_by_library(self, results):
        """Group results by library for better organization - key for creative workflow"""
        libraries = {}
        
        for result in results:
            file_path = result.get('path', '')
            if not file_path:
                continue
                
            library_name = self.extract_library_info(file_path)
            
            if library_name not in libraries:
                libraries[library_name] = {
                    'files': [],
                    'tags': set(),
                    'file_types': set()
                }
            
            # Add metadata
            file_name = result.get('name', '')
            metadata = self.extract_musical_metadata(file_name, file_path)
            
            result['metadata'] = metadata
            libraries[library_name]['files'].append(result)
            
            # Use single source for tags: genre_keywords logic
            tags = self.extract_tags_from_metadata(file_path)
            if tags:
                for tag in tags.split(' • '):
                    libraries[library_name]['tags'].add(tag.strip())
            
            file_type = self.get_file_type_info(file_path)
            libraries[library_name]['file_types'].add(file_type)
        
        return libraries

    def update_tree_with_results(self, results, title):
        """Update tree widget with library-organized results - optimized for music professionals"""
        try:
            print("🌳 Creating library-organized view with {} results".format(len(results)))
            
            # Clear existing items
            self.results_tree.clear()
            
            # Update headers for music production workflow
            self.results_tree.setHeaderLabels(["File Name", "File Type", "Keywords", "Tags"])
            
            # Calculate optimal column widths based on actual content
            self.calculate_optimal_column_widths(results)
            
            # Calculate the maximum width needed for Info column content
            self.calculate_and_set_info_column_width()
            
            # Set header resize modes for 4 columns - professional desktop app approach
            header = self.results_tree.header()
            header.setStretchLastSection(True)  # Last column (Tags) stretches to fill remaining space
            header.setSectionResizeMode(0, QHeaderView.Interactive)  # File Name - user can resize
            header.setSectionResizeMode(1, QHeaderView.Fixed)  # File Type - fixed width
            header.setSectionResizeMode(2, QHeaderView.Interactive)  # Keywords - user can resize
            header.setSectionResizeMode(3, QHeaderView.Stretch)  # Tags - stretches to fill remaining space
            
            # Enable horizontal scrolling for wide content
            self.results_tree.setHorizontalScrollMode(QTreeWidget.ScrollPerPixel)
            
            # Enable text elision for file names (shows "..." when too long)
            self.results_tree.setTextElideMode(Qt.ElideRight)
            
            # Disable word wrap to keep everything on one line
            self.results_tree.setWordWrap(False)
            
            # Group results by library
            libraries = self.group_results_by_library(results)
            
            # Add library groups to tree
            for library_name, library_data in libraries.items():
                files = library_data['files']
                tags = library_data['tags']
                file_types = library_data['file_types']
                
                # Create clean library header
                tags_str = ' • '.join(sorted(tags)) if tags else ''
                type_str = ', '.join(sorted(file_types)) if file_types else ''
                
                # Build clean library display
                library_display = "📁 {} ({} files)".format(library_name, len(files))
                
                # Extract keywords for the entire library (all files in this library)
                library_keywords = self.extract_library_keywords(files)
                
                # Create library node
                library_item = QTreeWidgetItem(self.results_tree)
                library_item.setText(0, library_display)
                library_item.setText(1, type_str if type_str else "Library")
                library_item.setText(2, library_keywords)  # Keywords for library
                library_item.setText(3, tags_str)  # Tags
                library_item.setExpanded(False)  # Collapsed by default - user can expand as needed
                
                # Add tooltips for library items
                library_item.setToolTip(0, library_name)  # Full library name
                library_item.setToolTip(2, library_keywords)  # Full keywords
                library_item.setToolTip(3, tags_str)  # Full tags
                
                # Add files under library
                for file_result in files[:MAX_RESULTS_PER_LIBRARY]:  # Limit per library for performance
                    file_path = file_result.get('path', '')
                    file_name = file_result.get('name', 'Unknown')
                    metadata = file_result.get('metadata', {})
                    
                    # Create engaging file display
                    icon = self.get_file_icon(file_path)
                    
                    # Extract keywords from search terms that matched this file
                    keywords = self.extract_keywords_from_search(file_path, self.get_search_text())
                    
                    # Extract tags using genre_keywords logic
                    tags = self.extract_tags_from_metadata(file_path)
                    
                    # Create file item
                    file_item = QTreeWidgetItem(library_item)
                    
                    # Always show full name - let Qt handle truncation with column width
                    file_item.setText(0, "{} {}".format(icon, file_name))
                    file_item.setText(1, self.get_file_type_info(file_path))  # File Type
                    file_item.setText(2, keywords)  # Keywords
                    file_item.setText(3, tags)  # Tags
                    
                    # Add tooltips for full content on hover
                    file_item.setToolTip(0, file_name)  # Full file name
                    file_item.setToolTip(2, keywords)  # Full keywords
                    file_item.setToolTip(3, tags)  # Full tags
                    
                    # Add tooltip with full name for convenience
                    file_item.setToolTip(0, file_name)
                    
                    # Store file path for future play button functionality
                    self.item_id_to_path[id(file_item)] = file_path
                
                if len(library_data['files']) > MAX_RESULTS_PER_LIBRARY:
                    # Add "more files" indicator
                    more_item = QTreeWidgetItem(library_item)
                    more_item.setText(0, "... and {} more files".format(len(library_data['files']) - MAX_RESULTS_PER_LIBRARY))
                    more_item.setText(1, "")
                    more_item.setText(2, "")
                    more_item.setText(3, "")
            
            print("✅ Library-organized tree created with {} libraries".format(len(libraries)))
            
        except Exception as e:
            print("⚠️ Error creating library view: {}".format(e))
    
    def calculate_and_set_info_column_width(self):
        """Calculate optimal width for Info column to prevent truncation"""
        if not hasattr(self, 'results_tree') or not self.results_tree:
            return
            
        # Sample content types that might appear in Info column (including longer ones)
        sample_contents = [
            "Audio • 120bpm • Em",
            "Kontakt • F#m",
            "Audio • 140bpm",
            "MIDI • Cm",
            "Audio • 85bpm • Ambient",
            "Audio, Kontakt • 50 samples",
            "Audio • 128bpm • Electronic",
            "Audio, Kontakt • 120bpm • Em",
            "Audio • 140bpm • Electronic",
            "Audio, Kontakt • 85bpm • Ambient"
        ]
        
        # Calculate width needed for longest content
        font_metrics = self.results_tree.fontMetrics()
        max_width = 0
        
        for content in sample_contents:
            width = font_metrics.horizontalAdvance(content)
            max_width = max(max_width, width)
        
        # Add moderate padding to allow some elision when needed
        optimal_width = max_width + 40
        
        # Set reasonable width that allows elision for very long content
        final_width = max(optimal_width, 200)
        
        print("🔧 Setting Info column width to: {}px".format(final_width))
        self.results_tree.setColumnWidth(1, final_width)
    
    def format_path_for_display(self, file_path):
        """Format path to show end with '...' prefix when too long"""
        if not file_path:
            return ""
        
        # Remove the library name part to show only the relevant path
        # For example: /Volumes/Samsung 850 EVO/Non Player Libraries/Audio Imperia/Instruments/file.nki
        # Should show: .../Instruments/file.nki
        
        # Split the path into parts
        path_parts = file_path.split('/')
        
        # Find the library name (usually the meaningful part)
        library_name = self.extract_library_info(file_path)
        
        if library_name and library_name in path_parts:
            # Find the index of the library name
            try:
                library_index = path_parts.index(library_name)
                # Get everything after the library name
                relevant_parts = path_parts[library_index + 1:]
                if relevant_parts:
                    relevant_path = '/'.join(relevant_parts)
                    return ".../{}".format(relevant_path)
            except ValueError:
                pass
        
        # Fallback: show last 2-3 parts of the path
        if len(path_parts) > 3:
            last_parts = path_parts[-3:]
            return ".../{}".format('/'.join(last_parts))
        else:
            return file_path
    
    def extract_keywords_from_search(self, file_path, search_terms):
        """Extract the search terms that matched this file"""
        if not hasattr(self, 'search_engine') or not self.search_engine:
            return ""
        
        # Get the matched keywords from the search engine
        matched_keywords = self.search_engine.get_matched_keywords(file_path, search_terms)
        return ' • '.join(matched_keywords) if matched_keywords else ""
    
    def extract_tags_from_metadata(self, file_path):
        """Extract tags using the genre_keywords logic from patchio.py"""
        if not hasattr(self, 'search_engine') or not self.search_engine:
            return ""
        
        # Use the genre_keywords logic from the search engine
        tags = self.search_engine.get_genre_keywords(file_path)
        return ' • '.join(tags) if tags else ""
    
    def extract_library_keywords(self, files):
        """Extract all unique keywords that matched files in this library"""
        if not files:
            return ""
        
        all_keywords = set()
        search_terms = self.get_search_text()
        
        for file_result in files:
            file_path = file_result.get('path', '')
            if file_path:
                keywords = self.extract_keywords_from_search(file_path, search_terms)
                if keywords:
                    # Split by ' • ' and add individual keywords
                    for keyword in keywords.split(' • '):
                        all_keywords.add(keyword.strip())
        
        return ' • '.join(sorted(all_keywords)) if all_keywords else ""
    
    def calculate_optimal_column_widths(self, results):
        """Calculate optimal column widths based on actual content"""
        if not results:
            return
        
        # Sample content for each column
        file_names = []
        file_types = []
        keywords_list = []
        tags_list = []
        
        # Collect content from all results
        for result in results:
            file_path = result.get('path', '')
            file_name = result.get('name', '')
            
            # File names (with icon)
            icon = self.get_file_icon(file_path)
            file_names.append("{} {}".format(icon, file_name))
            
            # File types
            file_types.append(self.get_file_type_info(file_path))
            
            # Keywords
            keywords = self.extract_keywords_from_search(file_path, self.get_search_text())
            if keywords:
                keywords_list.append(keywords)
            
            # Tags
            tags = self.extract_tags_from_metadata(file_path)
            if tags:
                tags_list.append(tags)
        
        # Also check library headers
        libraries = self.group_results_by_library(results)
        for library_name, library_data in libraries.items():
            # Library keywords
            library_keywords = self.extract_library_keywords(library_data['files'])
            if library_keywords:
                keywords_list.append(library_keywords)
            
            # Library tags
            tags = library_data.get('tags', set())
            if tags:
                tags_list.append(' • '.join(sorted(tags)))
        
        # Calculate optimal widths using font metrics
        font_metrics = self.results_tree.fontMetrics()
        
        # File Name column - find longest name
        max_file_name_width = 0
        for name in file_names:
            width = font_metrics.horizontalAdvance(name)
            max_file_name_width = max(max_file_name_width, width)
        
        # File Type column - find longest type
        max_file_type_width = 0
        for file_type in file_types:
            width = font_metrics.horizontalAdvance(file_type)
            max_file_type_width = max(max_file_type_width, width)
        
        # Keywords column - find longest keywords
        max_keywords_width = 0
        for keywords in keywords_list:
            width = font_metrics.horizontalAdvance(keywords)
            max_keywords_width = max(max_keywords_width, width)
        
        # Tags column - find longest tags
        max_tags_width = 0
        for tags in tags_list:
            width = font_metrics.horizontalAdvance(tags)
            max_tags_width = max(max_tags_width, width)
        
        # Set optimal widths with padding using settings
        self.results_tree.setColumnWidth(0, min(max_file_name_width + FILE_NAME_PADDING, MAX_FILE_NAME_WIDTH))
        self.results_tree.setColumnWidth(1, min(max_file_type_width + FILE_TYPE_PADDING, MAX_FILE_TYPE_WIDTH))
        self.results_tree.setColumnWidth(2, min(max_keywords_width + KEYWORDS_PADDING, MAX_KEYWORDS_WIDTH))
        self.results_tree.setColumnWidth(3, min(max_tags_width + TAGS_PADDING, MAX_TAGS_WIDTH))
        
        print("🔧 Optimal column widths calculated:")
        print(f"  File Name: {self.results_tree.columnWidth(0)}px")
        print(f"  File Type: {self.results_tree.columnWidth(1)}px")
        print(f"  Keywords: {self.results_tree.columnWidth(2)}px")
        print(f"  Tags: {self.results_tree.columnWidth(3)}px")
    
    def update_label_with_results(self, results, title):
        try:
            if self.results_area:
                # Create results text
                result_text = "{}: {} results\n\n".format(title, len(results))
                
                for i, result in enumerate(results, 1):
                    result_text += "{}. {}\n".format(i, result['name'])
                    result_text += "   Type: {}\n".format(result['type'])
                    result_text += "   Path: {}\n\n".format(result['path'])
                    
                    # Limit to first 50 results for label display
                    if i >= 50:
                        result_text += "... and {} more results\n".format(len(results) - 50)
                        break
                
                # Update the label
                for child in self.results_area.children():
                    if isinstance(child, QLabel):
                        child.setText(result_text)
                        break
                        
        except Exception as e:
            print("⚠️ Error updating label: {}".format(e))
    
    def setup_search_engine(self):
        """Setup the search engine with default folders"""
        try:
            print("🔧 Setting up search engine...")
            
            if self.search_engine is None:
                print("⚠️ Search engine not available")
                return
            
            # Initialize search engine with default folders
            self.search_engine.setup_default_folders()
            print("✅ Search engine setup completed")
            
        except Exception as e:
            print("⚠️ Error setting up search engine: {}".format(e))
    
    def update_results_message(self, message):
        """Update results area with a simple message"""
        try:
            if hasattr(self, 'results_tree') and self.results_tree:
                # Clear tree and add message
                self.results_tree.clear()
                item = QTreeWidgetItem(self.results_tree)
                item.setText(0, message)
                item.setText(1, "")
                item.setText(2, "")
            elif hasattr(self, 'results_label') and self.results_label:
                # Update label
                self.results_label.setText(message)
        except Exception as e:
            print("⚠️ Error updating results message: {}".format(e))


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    
    app.setApplicationName("PatchIO Working")
    app.setApplicationVersion("1.0.0")
    
    try:
        window = ModernPatchIOUILoader()
        window.show()
        
        print("🎉 PatchIO Modern UI Loader started successfully!")
        print("🎨 Using Qt Designer .ui file for interface")
        
        sys.exit(app.exec())
        
    except Exception as e:
        print("❌ Error starting application: {}".format(e))
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    main() 