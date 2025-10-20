#!/usr/bin/env python3
"""
Main Window View - MVC View for the main application window
Extracted from modern_patchio_ui_loader.py
"""

import os
import time
from PySide6.QtWidgets import (
    QMainWindow, QApplication, QTreeWidget, QTreeWidgetItem, 
    QHeaderView, QLabel, QVBoxLayout, QWidget, QToolButton, QSizePolicy, QPushButton
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QPixmap, QIcon

# Import our custom search inputs
from views.bubble_search_input import BubbleSearchInput
from views.advanced_search_input import AdvancedSearchInput

from models.user_settings_model import UserSettingsModel
# Import UI constants directly from core settings
from settings.core_settings import (
    MAX_FILE_NAME_WIDTH, MAX_FILE_TYPE_WIDTH, MAX_KEYWORDS_WIDTH, MAX_TAGS_WIDTH,
    MIN_FILE_NAME_WIDTH, MIN_FILE_TYPE_WIDTH, MIN_KEYWORDS_WIDTH, MIN_TAGS_WIDTH,
    FILE_NAME_PADDING, FILE_TYPE_PADDING, KEYWORDS_PADDING, TAGS_PADDING,
    DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT, MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT,
    ICON_PATHS, ICON_SIZES
)
from utils.logger import debug, info, warning, error, critical

class MainWindowView(QMainWindow):
    """Main window view - handles UI display and user interactions"""
    
    def __init__(self, settings_model: UserSettingsModel):
        super().__init__()
        self.settings = settings_model
        # Create UI settings dict from imported constants
        self.ui_settings = {
            'MAX_FILE_NAME_WIDTH': MAX_FILE_NAME_WIDTH,
            'MAX_FILE_TYPE_WIDTH': MAX_FILE_TYPE_WIDTH,
            'MAX_KEYWORDS_WIDTH': MAX_KEYWORDS_WIDTH,
            'MAX_TAGS_WIDTH': MAX_TAGS_WIDTH,
            'MIN_FILE_NAME_WIDTH': MIN_FILE_NAME_WIDTH,
            'MIN_FILE_TYPE_WIDTH': MIN_FILE_TYPE_WIDTH,
            'MIN_KEYWORDS_WIDTH': MIN_KEYWORDS_WIDTH,
            'MIN_TAGS_WIDTH': MIN_TAGS_WIDTH,
            'FILE_NAME_PADDING': FILE_NAME_PADDING,
            'FILE_TYPE_PADDING': FILE_TYPE_PADDING,
            'KEYWORDS_PADDING': KEYWORDS_PADDING,
            'TAGS_PADDING': TAGS_PADDING,
            'DEFAULT_WINDOW_WIDTH': DEFAULT_WINDOW_WIDTH,
            'DEFAULT_WINDOW_HEIGHT': DEFAULT_WINDOW_HEIGHT,
            'MIN_WINDOW_WIDTH': MIN_WINDOW_WIDTH,
            'MIN_WINDOW_HEIGHT': MIN_WINDOW_HEIGHT,
            'ICON_PATHS': ICON_PATHS,
            'ICON_SIZES': ICON_SIZES
        }
        self.controller = None  # Will be set by main controller
        
        # UI elements
        self.search_input = None
        self.advanced_search_input = None
        self.clear_button = None
        self.start_search_button = None
        self.results_tree = None
        self.results_area = None
        self.results_label = None
        self.classic_search_button = None
        self.keywords_editor_button = None
        self.ai_search_button = None
        self.search_bar_frame = None
        self.search_icon = None
        self.sidebar = None
        self.ui_widget = None
        
        # State tracking
        self.item_id_to_path = {}
        self.library_nodes = {}
        # Note: current_search_mode is now managed by the controller
        
        # Search progress tracking
        self.search_progress_timer = QTimer()
        self.search_progress_timer.timeout.connect(self.update_search_progress)
        self.search_progress_timer.start(100)  # Update every 100ms
        
        # 🚀 File scanning progress tracking
        self.is_scanning = False
        self.scan_progress_timer = QTimer()
        self.scan_progress_timer.timeout.connect(self.update_scan_progress)
        self.scan_progress_timer.start(500)  # Update every 500ms for scanning
        
        # Scan progress data
        self.scan_start_time = None
        self.scan_files_scanned = 0
        self.scan_files_relevant = 0
        self.scan_rate = 0
        self.scan_eta_minutes = 0
        self.search_start_time = None
        self.search_file_count = 0
        self.search_library_count = 0
        self.is_searching = False
        
        self.setup_window()
        self.setup_ui()
        self.setup_event_handlers()
    
    def setup_window(self):
        """Setup main window properties"""
        self.setWindowTitle("PatchIO - Modern Sound Library Manager")
        self.setMinimumSize(
            self.ui_settings.get('MIN_WINDOW_WIDTH', 1000),
            self.ui_settings.get('MIN_WINDOW_HEIGHT', 700)
        )
        self.resize(
            self.ui_settings.get('DEFAULT_WINDOW_WIDTH', 1200),
            self.ui_settings.get('DEFAULT_WINDOW_HEIGHT', 800)
        )
        
        # Note: setup_status_bar() will be called after UI is loaded in setup_ui_after_connection()
    
    def setup_ui(self):
        """Setup UI elements - this will be loaded from .ui file"""
        # This will be handled by the UI loader
        pass
    
    def setup_event_handlers(self):
        """Setup event handlers for UI interactions"""
        # Focus handling for web-app-like behavior
        self.installEventFilter(self)
        
        # Search input events are handled by the search controller
        # (connections are set up in MVC loader)
        
        # Add escape key handling for search cancellation
        # Note: search_input will be connected later in MVC loader
    
    def setup_ui_after_connection(self):
        """Setup UI elements after widgets are connected"""
        # Setup results area
        self.setup_results_area()
        
        # Setup status bar with progress indicators
        self.setup_status_bar()
        
        # Install global event filter for escape key handling
        self.installEventFilter(self)
        debug("🔍 Global event filter installed for escape key")
        
        # Setup cancel search button functionality
        self.setup_cancel_search_button_behavior()
        
        # Setup start search button functionality
        self.setup_start_search_button_behavior()
        
        # Setup advanced filters button
        self.setup_advanced_filters_button()
        
        # Setup logic toggle button from UI
        # self.setup_logic_toggle_button()  # REMOVED - logic toggle button no longer used
        
        # Set initial tooltip based on current mode
        self.update_search_tooltip()
        
        # Ensure correct mode button is checked on startup
        self.update_mode_buttons()
        
        # Mode button events are handled by the search controller
        # (connections are set up in MVC loader)
    
    def setup_results_area(self):
        """Setup the results area with initial content"""
        if not self.results_area:
            warning("⚠️ Results area not found")
            return

        try:
            from PySide6.QtWidgets import QLabel, QVBoxLayout
            from PySide6.QtCore import Qt

            debug(f"🔍 Setting up results area: {self.results_area}")

            # Create initial label (like the original)
            self.results_label = QLabel("Search results will appear here\n\nTry searching for files!")
            self.results_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            self.results_label.setWordWrap(True)
            # Let the UI file handle styling - only set alignment and text
            self.results_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            self.results_label.setWordWrap(True)

            # Set the label as the widget of the scroll area
            self.results_area.setWidget(self.results_label)

            info("✅ Results area setup completed")

        except Exception as e:
            error(f"⚠️ Error setting up results area: {e}")
            import traceback
            traceback.print_exc()
    
    def create_tree_widget(self):
        """Create tree widget to replace the label (like the original)"""
        if not self.results_area:
            return None

        try:
            from PySide6.QtWidgets import QTreeWidget, QHeaderView
            from PySide6.QtCore import Qt

            # Remove the existing label
            if self.results_label:
                self.results_label.setParent(None)
                self.results_label.deleteLater()
                self.results_label = None

            # Create tree widget (like the original)
            self.results_tree = QTreeWidget()
            self.results_tree.setHeaderLabels(["File Name", "File Type", "Tags"])
            self.results_tree.setAlternatingRowColors(False)
            
            # Set up header behavior
            header = self.results_tree.header()
            header.setStretchLastSection(True)  # Last column (Tags) stretches to fill remaining space
            header.setSectionResizeMode(0, QHeaderView.Interactive)  # File Name - user can resize
            header.setSectionResizeMode(1, QHeaderView.Interactive)  # File Type - allow manual resizing for bubble widgets
            header.setSectionResizeMode(2, QHeaderView.Stretch)  # Tags - stretches to fill remaining space
            
            # Set minimum section size to prevent columns from being too narrow
            header.setMinimumSectionSize(200)
            
            # Apply styling directly to the header object
            header.setStyleSheet("""
                QHeaderView {
                    background-color: #1A1A1C !important;
                    color: #FFFFFF !important;
                    border: none !important;
                    font-weight: 600;
                    font-size: 13px;
                    padding: 4px;
                    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', Roboto, sans-serif;
                    min-height: 40px;
                }
                QHeaderView::section {
                    background-color: #1A1A1C !important;
                    color: #FFFFFF !important;
                    border: none !important;
                    border-bottom: 1px solid #3A3A3C !important;
                    padding: 4px 8px;
                    font-weight: 600;
                    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', Roboto, sans-serif;
                    min-height: 40px;
                }
            """)
            
            # Disable horizontal scrolling - content will be clipped instead
            self.results_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            
            # Disable text elision globally to prevent truncation
            self.results_tree.setTextElideMode(Qt.ElideNone)
            
            # Disable word wrap to keep everything on one line
            self.results_tree.setWordWrap(False)
            
            # Apply modern styling to match the results area design
            self.results_tree.setStyleSheet("""
                QTreeWidget {
                    background-color: transparent;
                    color: #FFFFFF;
                    border: none;
                    outline: none;
                    font-size: 14px;
                    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', Roboto, sans-serif;
                }
                QTreeWidget::item {
                    padding: 12px 8px;
                    border: none;
                    min-height: 32px;
                    border-radius: 6px;
                    margin: 1px;
                }
                QTreeWidget::item:selected {
                    background-color: #3478f6;
                    color: #FFFFFF;
                    border: 1px solid #2a70d6;
                }
                QTreeWidget::item:selected:active {
                    background-color: #3478f6;
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
                    background-color: #3478f6;
                    color: #FFFFFF;
                    border: 1px solid #2a70d6;
                }
                QTreeWidget::item:hover {
                    background-color: #3A3A3C;
                    border-radius: 6px;
                }
                QTreeWidget::header {
                    background-color: #1A1A1C;
                    color: #FFFFFF;
                    border: none;
                    font-weight: 600;
                    font-size: 13px;
                    padding: 8px;
                    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', Roboto, sans-serif;
                }
                QTreeWidget::header::section {
                    background-color: #1A1A1C;
                    color: #FFFFFF;
                    border: none;
                    padding: 8px;
                    font-weight: 600;
                    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', Roboto, sans-serif;
                }
            """)

            # Set the tree widget as the widget of the scroll area
            self.results_area.setWidget(self.results_tree)

            debug("✅ Tree widget created")
            return self.results_tree

        except Exception as e:
            error(f"⚠️ Error creating tree widget: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def eventFilter(self, obj, event):
        """Global event filter for focus handling and search cancellation"""
        from PySide6.QtCore import QEvent, Qt
        
        if event.type() == QEvent.MouseButtonPress:
            # De-focus search input when clicking anywhere
            if self.search_input and self.search_input.hasFocus():
                self.search_input.clearFocus()
            
            # Clear bubble selections when clicking anywhere
            if (hasattr(self, 'search_input') and 
                hasattr(self.search_input, 'clear_selections')):
                self.search_input.clear_selections()
        
        elif event.type() == QEvent.KeyPress:
            # Handle escape key for search cancellation (global)
            if event.key() == Qt.Key_Escape:
                debug("🔍 Escape key pressed - cancelling search")
                if hasattr(self, 'controller') and self.controller:
                    # Call the search controller's cancel method
                    self.controller.search_controller.on_search_cancelled()
                return True
        
        return super().eventFilter(obj, event)
    

    

    
    def update_mode_buttons(self):
        """Update button states based on current mode"""
        # Get current mode from controller (single source of truth)
        current_mode = self.get_current_mode()
        
        if self.classic_search_button:
            self.classic_search_button.setChecked(current_mode == "classic_search")
            self.classic_search_button.setCursor(Qt.CursorShape.PointingHandCursor)
        if self.keywords_editor_button:
            self.keywords_editor_button.setChecked(current_mode == "keywords_editor")
            self.keywords_editor_button.setCursor(Qt.CursorShape.PointingHandCursor)
        if self.ai_search_button:
            self.ai_search_button.setChecked(current_mode == "ai")
            self.ai_search_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Update advanced filters button state
        if hasattr(self, 'advanced_filters_button') and self.advanced_filters_button:
            # Advanced filters button should be checked when in keywords_editor mode
            is_advanced_mode = current_mode == "keywords_editor"
            self.advanced_filters_button.setChecked(is_advanced_mode)
            
            # Update button text based on state
            if is_advanced_mode:
                self.advanced_filters_button.setText("Hide Advanced")
            else:
                self.advanced_filters_button.setText("Advanced Filters")
    
    def update_search_tooltip(self):
        """Update search input tooltip based on current mode"""
        if not self.search_input:
            return
        
        # Get current mode from controller (single source of truth)
        current_mode = self.get_current_mode()
            
        if current_mode == "classic_search":
            tooltip = """💡 Simple search tips:
• Use quotes for exact phrases: "soft piano"
• Separate terms with spaces: drums "trap drums" piano
• Simple search finds files matching ANY term"""
        elif current_mode == "keywords_editor":
            tooltip = """💡 Keywords Editor tips:
• Manage AI-generated keywords
• Use or:, and:, not: prefixes
• Example: or: drums and: piano not: bass
• Keywords Editor uses exact logic matching"""
        elif current_mode == "ai":
            tooltip = """💡 AI search tips:
• Describe what you're looking for naturally
• Example: "quirky comedy cue" or "epic battle music"
• AI will suggest relevant keywords"""
        else:
            tooltip = ""
            
        self.search_input.setToolTip(tooltip)
    
    def get_search_text(self) -> str:
        """Get current search text combining search bar text with filter bubbles using AND logic"""
        if hasattr(self, 'controller') and self.controller:
            # Get search text from search bar
            search_text = ""
            if self.search_input:
                if hasattr(self.search_input, 'get_text'):
                    search_text = self.search_input.get_text()
                else:
                    search_text = self.search_input.text()
            
            # Get active filters from the main controller
            active_filters = self.controller.get_active_filters()
            
            # Build search query from filter bubbles with OR/AND logic
            group_queries = []
            for filter_type, filter_values in active_filters.items():
                if filter_values:
                    # Wrap each filter value in quotes for exact matching
                    quoted_terms = [f'"{term}"' for term in filter_values]
                    # Join terms within the same group with OR
                    group_query = " OR ".join(quoted_terms)
                    group_queries.append(group_query)
            
            # Combine search text with filter queries using AND logic
            query_parts = []
            
            # Add search text if it exists
            if search_text.strip():
                query_parts.append(search_text.strip())
            
            # Add filter queries if they exist
            if group_queries:
                query_parts.extend(group_queries)
            
            # Join all parts with AND
            query = " AND ".join(query_parts)
            debug(f"🔍 get_search_text() - combined search and filters (AND logic): '{query}'")
            return query
        else:
            # Fallback to original method if controller not available
            if self.search_input:
                if hasattr(self.search_input, 'get_text'):
                    return self.search_input.get_text()
                else:
                    return self.search_input.text()
            return ""
    
    def set_search_text(self, text: str):
        """Set search text"""
        if self.search_input:
            # Use the custom set_text method for bubble search input
            if hasattr(self.search_input, 'set_text'):
                self.search_input.set_text(text)
            else:
                self.search_input.setText(text)
    
    def get_current_mode(self) -> str:
        """Get current search mode from controller (single source of truth)"""
        if hasattr(self, 'controller') and self.controller:
            return self.controller.current_mode
        else:
            # Fallback to classic search mode if controller not available
            return "classic_search"
    
    def switch_search_input(self, mode: str):
        """Switch between search inputs based on mode"""
        if not self.search_bar_frame:
            return
        
        # Create and add the appropriate search input
        if mode == "keywords_editor":
            # Hide the search bar frame
            self.search_bar_frame.setVisible(False)
            
            # Use advanced search input
            if not self.advanced_search_input:
                self.advanced_search_input = AdvancedSearchInput()
                # Set proper size policy for advanced mode
                self.advanced_search_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                self.advanced_search_input.setMinimumHeight(120)  # Match the height from .ui file
                
                # Add to the same parent as the search bar frame
                search_bar_parent = self.search_bar_frame.parent()
                if search_bar_parent:
                    parent_layout = search_bar_parent.layout()
                    if parent_layout:
                        parent_layout.addWidget(self.advanced_search_input)
            else:
                # If advanced search input already exists, make sure it's in the layout
                if not self.advanced_search_input.parent():
                    search_bar_parent = self.search_bar_frame.parent()
                    if search_bar_parent:
                        parent_layout = search_bar_parent.layout()
                        if parent_layout:
                            parent_layout.addWidget(self.advanced_search_input)
                            debug(f"🔍 Re-added advanced search input to layout")
                else:
                    # If it has a parent but was removed, re-add it
                    search_bar_parent = self.search_bar_frame.parent()
                    if search_bar_parent:
                        parent_layout = search_bar_parent.layout()
                        if parent_layout and self.advanced_search_input not in [parent_layout.itemAt(i).widget() for i in range(parent_layout.count())]:
                            parent_layout.addWidget(self.advanced_search_input)
                            warning(f"🔍 Re-added advanced search input to layout (was missing)")
            
            # Show all child widgets of the advanced search input
            for field in self.advanced_search_input.search_fields:
                field['container'].setVisible(True)
                field['text_edit'].setVisible(True)
                field['label'].setVisible(True)
            
            # Make sure the advanced search input itself is visible and properly sized
            self.advanced_search_input.setVisible(True)
            self.advanced_search_input.setMinimumHeight(120)
            self.advanced_search_input.updateGeometry()  # Force layout update
            debug(f"🔍 Showed advanced search input and all child widgets")
            debug(f"🔍 Advanced search input visible: {self.advanced_search_input.isVisible()}")
            debug(f"🔍 Advanced search input parent: {self.advanced_search_input.parent()}")
            debug(f"🔍 Advanced search input size: {self.advanced_search_input.size()}")
            
            # Set the active search input
            self.search_input = self.advanced_search_input
            
            # Disconnect signals from original search input to avoid conflicts
            if hasattr(self, 'original_search_input') and self.original_search_input:
                try:
                    self.original_search_input.returnPressed.disconnect()
                except:
                    pass  # No connections to disconnect
                try:
                    self.original_search_input.textChanged.disconnect()
                except:
                    pass  # No connections to disconnect
                debug(f"🔍 Disconnected signals from original search input")
            
        else:
            # Hide the advanced search input completely
            if self.advanced_search_input:
                # Hide all child widgets of the advanced search input
                for field in self.advanced_search_input.search_fields:
                    field['container'].setVisible(False)
                    field['text_edit'].setVisible(False)
                    field['label'].setVisible(False)
                
                self.advanced_search_input.setVisible(False)
                # Also remove it from its parent layout to ensure it's completely hidden
                if self.advanced_search_input.parent():
                    parent_layout = self.advanced_search_input.parent().layout()
                    if parent_layout:
                        parent_layout.removeWidget(self.advanced_search_input)
                        info(f"🔍 Removed advanced search input from layout")
                debug(f"🔍 Hidden advanced search input and all child widgets")
            
            # Show the search bar frame
            self.search_bar_frame.setVisible(True)
            debug(f"🔍 Restored search bar frame")
            
            # Use the original search input (bubble search input) that was set up initially
            if hasattr(self, 'original_search_input') and self.original_search_input:
                self.search_input = self.original_search_input
                debug(f"🔍 Restored original search input: {self.original_search_input}")
                
                # Reconnect signals for the bubble search input
                self.reconnect_search_input_signals()
            else:
                # Fallback: Find the bubble search input in the search bar frame
                from views.bubble_search_input import BubbleSearchInput
                bubble_search_input = None
                for child in self.search_bar_frame.findChildren(BubbleSearchInput):
                    bubble_search_input = child
                    break
                
                if bubble_search_input:
                    # Set the active search input to the bubble search input
                    self.search_input = bubble_search_input
                    debug(f"🔍 Found and set bubble search input: {bubble_search_input}")
                    
                    # Reconnect signals for the bubble search input
                    self.reconnect_search_input_signals()
                else:
                    warning(f"⚠️ Could not find bubble search input in search bar frame")
                    # Fallback to any search input in the frame
                    if self.search_input:
                        self.search_input.setVisible(True)
        
        # Update search tooltip
        self.update_search_tooltip()
        
        # Set focus to the active search input
        if self.search_input:
            self.search_input.setFocus()
        
        # Force update start search button visibility
        self.update_start_search_button_visibility()
    
    def reconnect_search_input_signals(self):
        """Reconnect signals for the current search input"""
        if not self.search_input:
            return
        
        debug(f"🔍 Reconnecting signals for search input: {self.search_input}")
        
        # Disconnect any existing connections to avoid duplicates
        try:
            self.search_input.returnPressed.disconnect()
        except:
            pass  # No connections to disconnect
        
        try:
            self.search_input.textChanged.disconnect()
        except:
            pass  # No connections to disconnect
        
        # Reconnect returnPressed signal
        self.search_input.returnPressed.connect(
            self.controller.search_controller.on_search_triggered
        )
        debug(f"🔍 Reconnected returnPressed signal")
        
        # Reconnect textChanged signal for start search button
        self.search_input.textChanged.connect(self.on_search_text_changed_for_start_button)
        debug(f"🔍 Reconnected textChanged signal")
        
        # Update search tooltip
        self.update_search_tooltip()
        
        # Force emit a textChanged signal to update the start search button
        if hasattr(self.search_input, 'get_text'):
            current_text = self.search_input.get_text()
        else:
            current_text = self.search_input.text()
        debug(f"🔍 Forcing textChanged signal with current text: '{current_text}'")
        self.search_input.textChanged.emit(current_text)
    
    def update_start_search_button_visibility(self):
        """Force update start search button visibility based on current text"""
        if self.search_input and self.start_search_button:
            # Use the custom get_text method for bubble search input
            if hasattr(self.search_input, 'get_text'):
                has_text = len(self.search_input.get_text().strip()) > 0
            else:
                has_text = len(self.search_input.text().strip()) > 0
            # Only show start search button if there's text AND no search is in progress
            should_show = has_text and not self.is_searching
            debug(f"🔍 Force update start search button: has_text={has_text}, is_searching={self.is_searching}, should_show={should_show}")
            self.start_search_button.setVisible(should_show)
            if should_show:
                # Position the start search button consistently
                self.position_search_button(self.start_search_button, is_cancel_button=False)
                debug(f"🔍 Force positioned start search button")
    
    def clear_results(self):
        """Clear the results tree"""
        if self.results_tree:
            self.results_tree.clear()
            self.item_id_to_path.clear()
            self.library_nodes.clear()
    
    def update_results_tree(self, results_data: dict):
        """Update the results tree with new data"""
        if not self.results_tree:
            return
        
        self.clear_results()
        
        # Set headers
        self.results_tree.setHeaderLabels(["File Name", "File Type", "Tags"])
        
        # Results tree setup and population is handled by the controller
        # (controller will call calculate_optimal_column_widths and populate_results_tree)
    

    

    
    def set_search_focus(self):
        """Set focus to search input"""
        if self.search_input:
            self.search_input.setFocus()
    
    def show_status_message(self, message: str):
        """Show status message to user"""
        # This could be implemented with a status bar
        debug(f"Status: {message}")
    
    def show_error_message(self, message: str):
        """Show error message to user"""
        # This could be implemented with a message box
        debug(f"Error: {message}")
    
    def setup_status_bar(self):
        """Setup status bar with progress indicators"""
        from PySide6.QtWidgets import QStatusBar, QProgressBar, QLabel
        from PySide6.QtCore import Qt
        
        # Create status bar directly (since we're a QMainWindow)
        self.status_bar = self.statusBar()
        if not self.status_bar:
            error("⚠️ Failed to create status bar")
            return
        
        # Make sure status bar is visible and styled
        self.status_bar.setVisible(True)
        
        # Create progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setMaximumHeight(16)
        
        # Create status label
        self.status_label = QLabel("Ready to search your sample libraries")
        
        # Clear any existing widgets and add our widgets
        self.status_bar.clearMessage()
        self.status_bar.addWidget(self.status_label, 1)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # Add left spacing to the status bar
        self.status_bar.setContentsMargins(8, 0, 0, 0)
        
        # Set initial state
        self.update_status_display("Ready to search your sample libraries", "ready")
    
    def update_status_display(self, message: str, state: str = "ready"):
        """Update status display with message and state"""
        if not hasattr(self, 'status_label'):
            debug(f"Status: {message}")
            return
        
        # Update message
        self.status_label.setText(message)
        
        # Update styling based on state - only use Python for truly dynamic states
        if state == "searching":
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate progress
        elif state == "scanning":
            # 🚀 NEW: Show progress bar for file scanning
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate progress
        elif state == "complete":
            self.progress_bar.setVisible(False)
        elif state == "error":
            # Only use Python styling for error state (truly dynamic)
            self.status_label.setStyleSheet("color: #FF453A; font-size: 12px; font-weight: normal;")
            self.progress_bar.setVisible(False)
        else:  # ready
            self.progress_bar.setVisible(False)
    
    def start_search_progress(self, query: str):
        """Start search progress tracking"""
        self.is_searching = True
        self.search_start_time = QTimer().remainingTime()
        self.search_file_count = 0
        self.search_library_count = 0
        
        # Hide start search button during search (ChatGPT style)
        if self.start_search_button:
            self.start_search_button.setVisible(False)
        
        # Show cancel button during search
        if self.clear_button:
            self.clear_button.setVisible(True)
            # Position cancel button consistently
            self.position_search_button(self.clear_button, is_cancel_button=True)
        
        # Update status
        self.update_status_display("🔍 Hunting for your sounds...", "searching")
    
    def update_search_progress(self):
        """Update search progress display"""
        if not self.is_searching:
            return
        
        # Update status message with live counts
        if self.search_file_count > 0:
            message = f"🔍 Found {self.search_file_count:,} samples in {self.search_library_count} libraries"
            self.update_status_display(message, "searching")
    
    def complete_search_progress(self, total_files: int, total_libraries: int):
        """Complete search progress tracking"""
        self.is_searching = False
        
        # Hide cancel button when search completes
        if self.clear_button:
            self.clear_button.setVisible(False)
        
        # Show start search button again if there's text (ChatGPT style)
        if self.start_search_button and self.search_input:
            has_text = len(self.search_input.text().strip()) > 0
            self.start_search_button.setVisible(has_text)
            if has_text:
                # Position start search button consistently
                self.position_search_button(self.start_search_button, is_cancel_button=False)
        
        # Show completion message
        if total_files > 0:
            message = f"🔍 Found {total_files:,} samples in {total_libraries} libraries"
        else:
            message = f"🔍 No samples found"
        
        self.update_status_display(message, "complete")
    
    def cancel_search_progress(self):
        """Cancel search progress tracking"""
        self.is_searching = False
        
        # Hide cancel button when search is cancelled
        if self.clear_button:
            self.clear_button.setVisible(False)
        
        # Show start search button again if there's text (ChatGPT style)
        if self.start_search_button and self.search_input:
            has_text = len(self.search_input.text().strip()) > 0
            self.start_search_button.setVisible(has_text)
            if has_text:
                # Position start search button consistently
                self.position_search_button(self.start_search_button, is_cancel_button=False)
        
        # Show cancellation message with current counts
        if self.search_file_count > 0:
            message = f"🔍 Search cancelled - Found {self.search_file_count:,} samples in {self.search_library_count} libraries"
        else:
            message = "🔍 Search cancelled"
        
        self.update_status_display(message, "complete")
    
    # 🚀 FILE SCANNING PROGRESS METHODS (similar to search progress)
    def start_scan_progress(self):
        """Start file scanning progress tracking"""
        self.is_scanning = True
        self.scan_start_time = time.time()
        self.scan_files_scanned = 0
        self.scan_files_relevant = 0
        self.scan_rate = 0
        self.scan_eta_minutes = 0
        
        # Update status to show scanning
        self.update_status_display("🔍 Scanning your sample libraries...", "scanning")
    
    def update_scan_progress(self):
        """Update file scanning progress display"""
        if not self.is_scanning:
            return
        
        # Update status message with live scan counts
        if self.scan_files_scanned > 0:
            message = f"🔍 Scanned {self.scan_files_scanned:,} files, found {self.scan_files_relevant:,} relevant files"
            if self.scan_rate > 0:
                message += f" • {self.scan_rate:.0f} files/sec"
            if self.scan_eta_minutes > 0:
                message += f" • ETA: {self.scan_eta_minutes:.1f} min"
            
            self.update_status_display(message, "scanning")
    
    def update_scan_progress_data(self, progress_info: dict):
        """Update scan progress data from background worker"""
        if not self.is_scanning:
            return
        
        # Update progress data
        self.scan_files_scanned = progress_info.get('scanned', 0)
        self.scan_files_relevant = progress_info.get('relevant', 0)
        self.scan_rate = progress_info.get('rate', 0)
        self.scan_eta_minutes = progress_info.get('eta_minutes', 0)
    
    def complete_scan_progress(self, sync_results: dict):
        """Complete file scanning progress tracking"""
        self.is_scanning = False
        
        # Show completion message with results
        files_added = sync_results.get('files_added', 0)
        files_removed = sync_results.get('files_removed', 0)
        files_updated = sync_results.get('files_updated', 0)
        sync_time = sync_results.get('sync_time', 0)
        
        if files_added > 0 or files_removed > 0 or files_updated > 0:
            # Create a clear, readable message
            parts = []
            if files_added > 0:
                parts.append(f"{files_added:,} added")
            if files_removed > 0:
                parts.append(f"{files_removed:,} removed")
            if files_updated > 0:
                parts.append(f"{files_updated:,} updated")
            
            changes_text = ", ".join(parts)
            message = f"✓ Index updated: {changes_text} in {sync_time:.1f}s"
        else:
            message = f"✓ Index up to date ({sync_time:.1f}s)"
        
        self.update_status_display(message, "complete")
    
    def cancel_scan_progress(self):
        """Cancel file scanning progress tracking"""
        self.is_scanning = False
        self.update_status_display("Ready to search your sample libraries", "ready")
    
    def update_search_counts(self, file_count: int, library_count: int):
        """Update search counts for progress display"""
        self.search_file_count = file_count
        self.search_library_count = library_count
    
    def show_stop_button(self):
        """Show stop button during search (ChatGPT style)"""
        # This will be implemented when we add the stop button
        pass
    
    def hide_stop_button(self):
        """Hide stop button when search is complete"""
        # This will be implemented when we add the stop button
        pass
    
    def set_controller(self, controller):
        """Set the controller reference for event handling"""
        self.controller = controller
    
    def position_search_button(self, button, is_cancel_button=False):
        """Position search button consistently for seamless replacement"""
        if not button or not button.parent():
            return
        
        parent_rect = button.parent().rect()
        button_width = button.width()
        button_height = button.height()
        
        # Use consistent positioning: 16px from right edge for both buttons
        button_x = parent_rect.width() - button_width - 16
        button_y = (parent_rect.height() - button_height) // 2  # Center vertically
        
        button.move(button_x, button_y)
        button.raise_()  # Ensure button is on top
        debug(f"🔍 Positioned {'cancel' if is_cancel_button else 'start search'} button at ({button_x}, {button_y})")
    
    def setup_cancel_search_button_behavior(self):
        """Setup cancel search button behavior (ChatGPT style)"""
        debug(f"🔍 Setting up cancel search button behavior:")
        debug(f"  search_input: {self.search_input}")
        debug(f"  cancel_search_button: {self.clear_button}")
        
        if not self.search_input or not self.clear_button:
            warning("⚠️ Missing search_input or cancel_search_button")
            return
        
        try:
            # Initially hide the cancel search button
            self.clear_button.setVisible(False)
            debug(f"🔍 Cancel search button initially hidden")
            
            # Use QToolButton for icon-only behavior with pointing hand cursor
            if isinstance(self.clear_button, QToolButton):
                self.clear_button.setToolButtonStyle(Qt.ToolButtonIconOnly)
                self.clear_button.setAutoRaise(True)
                self.clear_button.setCursor(Qt.PointingHandCursor)
                self.clear_button.setStyleSheet("""
                    QToolButton {
                        border: none;
                        background: transparent;
                        min-width: 40px;
                        min-height: 40px;
                        max-width: 40px;
                        max-height: 40px;
                    }
                    QToolButton:hover {
                        background: transparent;
                    }
                """)
            else:
                # Fallback for QPushButton
                self.clear_button.setCursor(Qt.PointingHandCursor)
                self.clear_button.setStyleSheet("""
                    QPushButton {
                        border: none;
                        background: transparent;
                        min-width: 32px;
                        min-height: 32px;
                        max-width: 32px;
                        max-height: 32px;
                    }
                    QPushButton:hover {
                        background: transparent;
                    }
                """)
            
            # Load and set the cancel search icon
            try:
                icon_name = 'cancel_search_button'
                icon_filename = self.ui_settings.get('ICON_PATHS', {}).get(icon_name, f'{icon_name}.png')
                icon_size = self.ui_settings.get('ICON_SIZES', {}).get(icon_name, (16, 16))
                
                # Calculate button size based on icon size (add some padding)
                button_size = (40, 40)  # Hardcoded bigger button for 32px icon
                
                icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icons", icon_filename)
                # Resolve the path to handle the ".." properly
                icon_path = os.path.abspath(icon_path)
                if os.path.exists(icon_path):
                    cancel_icon = QIcon(icon_path)
                    self.clear_button.setIcon(cancel_icon)
                    self.clear_button.setIconSize(QSize(32, 32))  # Hardcoded bigger icon
                    
                    # Update button size based on icon size
                    self.clear_button.setMinimumSize(*button_size)
                    self.clear_button.setMaximumSize(*button_size)
                    
                    # Update CSS with dynamic button size
                    css = f"""
                        QToolButton {{
                            border: none;
                            background: transparent;
                            min-width: {button_size[0]}px;
                            min-height: {button_size[1]}px;
                            max-width: {button_size[0]}px;
                            max-height: {button_size[1]}px;
                        }}
                        QToolButton:hover {{
                            background: transparent;
                        }}
                    """
                    self.clear_button.setStyleSheet(css)
                    
                    debug(f"✅ Cancel search icon loaded from {icon_path} with size {icon_size}")
                else:
                    warning(f"⚠️ Cancel search icon not found at {icon_path}")
                    # Fallback to text
                    self.clear_button.setText("×")
            except Exception as e:
                error(f"⚠️ Error loading cancel search icon: {e}")
                # Fallback to text
                self.clear_button.setText("×")
            
            # Ensure clear button is properly positioned and sized
            self.clear_button.setMinimumSize(40, 40)
            self.clear_button.setMaximumSize(40, 40)
            
            # Position the button consistently
            self.position_search_button(self.clear_button, is_cancel_button=True)
            
            # Initially hide the clear button
            self.clear_button.setVisible(False)
            
            # Search input events are handled by the search controller
            # (connections are set up in MVC loader)
            debug(f"🔍 Return pressed handled by controller")
            
            # Cancel button visibility is managed by search state, not text changes
            # (cancel button is only visible when search is ongoing)
            debug(f"🔍 Cancel button visibility managed by search state only")
            
            # Also connect to start search button handler
            self.search_input.textChanged.connect(self.on_search_text_changed_for_start_button)
            debug(f"🔍 Start search text changed connected")
            
            info("✅ Cancel search button behavior setup completed")
            
        except Exception as e:
            error(f"⚠️ Error setting up clear button behavior: {e}")
            import traceback
            traceback.print_exc()
    
    def on_cancel_search_button_clicked(self):
        """Handle cancel search button click - same behavior as escape key"""
        # Call controller method to cancel search (same as escape key)
        if hasattr(self, 'controller') and self.controller:
            # Call the search controller's cancel method
            self.controller.search_controller.on_search_cancelled()
    

    
    def setup_start_search_button_behavior(self):
        """Setup start search button behavior"""
        debug(f"🔍 Setting up start search button behavior:")
        debug(f"  search_input: {self.search_input}")
        debug(f"  start_search_button: {self.start_search_button}")
        
        if not self.search_input or not self.start_search_button:
            warning("⚠️ Missing search_input or start_search_button")
            return
        
        try:
            # Use QToolButton for icon-only behavior with pointing hand cursor
            if isinstance(self.start_search_button, QToolButton):
                self.start_search_button.setToolButtonStyle(Qt.ToolButtonIconOnly)
                self.start_search_button.setAutoRaise(True)
                self.start_search_button.setCursor(Qt.PointingHandCursor)
                self.start_search_button.setStyleSheet("""
                    QToolButton {
                        border: none;
                        background: white;
                        border-radius: 20px;
                        min-width: 40px;
                        min-height: 40px;
                        max-width: 40px;
                        max-height: 40px;
                        box-shadow: 0 2px 8px rgba(255, 255, 255, 0.15);
                    }
                    QToolButton:hover {
                        background: #f8f9fa;
                        box-shadow: 0 4px 12px rgba(255, 255, 255, 0.2);
                    }
                """)
            else:
                # Fallback for QPushButton
                self.start_search_button.setCursor(Qt.PointingHandCursor)
                self.start_search_button.setStyleSheet("""
                    QPushButton {
                        border: none;
                        background: transparent;
                        border-radius: 20px;
                        min-width: 40px;
                        min-height: 40px;
                        max-width: 40px;
                        max-height: 40px;
                        box-shadow: 0 2px 8px rgba(255, 255, 255, 0.15);
                    }
                    QPushButton:hover {
                        background: transparent;
                    }
                """)
            
            # Load and set the start search icon
            try:
                icon_name = 'start_search_button'
                icon_filename = self.ui_settings.get('ICON_PATHS', {}).get(icon_name, f'{icon_name}.png')
                icon_size = self.ui_settings.get('ICON_SIZES', {}).get(icon_name, (24, 24))
                
                # Calculate button size based on icon size (add some padding)
                button_size = (40, 40)  # Hardcoded bigger button for 32px icon
                
                icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icons", icon_filename)
                # Resolve the path to handle the ".." properly
                icon_path = os.path.abspath(icon_path)
                if os.path.exists(icon_path):
                    start_icon = QIcon(icon_path)
                    self.start_search_button.setIcon(start_icon)
                    self.start_search_button.setIconSize(QSize(32, 32))  # Hardcoded bigger icon
                    
                    # Update button size based on icon size
                    self.start_search_button.setMinimumSize(*button_size)
                    self.start_search_button.setMaximumSize(*button_size)
                    
                    # Update CSS with dynamic button size and shadow effect
                    css = f"""
                        QToolButton {{
                            border: none;
                            background: transparent;
                            border-radius: {button_size[0]//2}px;
                            min-width: {button_size[0]}px;
                            min-height: {button_size[1]}px;
                            max-width: {button_size[0]}px;
                            max-height: {button_size[1]}px;
                            box-shadow: 0 2px 8px rgba(255, 255, 255, 0.15);
                        }}
                        QToolButton:hover {{
                            background: transparent;
                        }}
                    """
                    self.start_search_button.setStyleSheet(css)
                    
                    debug(f"✅ Start search icon loaded from {icon_path} with size {icon_size}")
                else:
                    warning(f"⚠️ Start search icon not found at {icon_path}")
                    # No fallback - rely on icon only
            except Exception as e:
                error(f"⚠️ Error loading start search icon: {e}")
                # No fallback - rely on icon only
            
            # Initially hide the start search button
            self.start_search_button.setVisible(False)
            
            # Connect start search button click
            self.start_search_button.clicked.connect(self.on_start_search_clicked)
            
            # Connect search input text changes to show/hide start search button
            if self.search_input:
                self.search_input.textChanged.connect(self.on_search_text_changed_for_start_button)
                debug(f"🔍 Start search text changed connected")
            
            info("✅ Start search button behavior setup completed")
            
        except Exception as e:
            error(f"⚠️ Error setting up start search button behavior: {e}")
            import traceback
            traceback.print_exc()
    
    def on_start_search_clicked(self):
        """Handle start search button click"""
        debug("🔍 Start search button clicked!")
        # Trigger search
        if hasattr(self, 'controller') and self.controller:
            # Call the search controller's trigger method
            self.controller.search_controller.on_search_triggered()
    
    def on_search_text_changed_for_start_button(self):
        """Handle search text changes to show/hide start search button"""
        if self.search_input and self.start_search_button:
            # Use the custom get_text method for bubble search input
            if hasattr(self.search_input, 'get_text'):
                has_text = len(self.search_input.get_text().strip()) > 0
            else:
                has_text = len(self.search_input.text().strip()) > 0
            # Only show start search button if there's text AND no search is in progress
            should_show = has_text and not self.is_searching
            debug(f"🔍 Start search button: has_text={has_text}, is_searching={self.is_searching}, should_show={should_show}")
            self.start_search_button.setVisible(should_show)
            if should_show:
                # Position the start search button consistently
                self.position_search_button(self.start_search_button, is_cancel_button=False)
                debug(f"🔍 Positioned start search button")
            else:
                debug(f"🔍 Hidden start search button")
    
    def setup_advanced_filters_button(self):
        """Setup Advanced Filters button below the search bar"""
        debug("🔍 Setting up Advanced Filters button")
        
        # Find the search bar frame
        if not self.search_bar_frame:
            warning("⚠️ Search bar frame not found")
            return
        
        # Create the Advanced Filters button
        from PySide6.QtWidgets import QPushButton
        from PySide6.QtCore import Qt
        
        self.advanced_filters_button = QPushButton("Advanced Filters")
        self.advanced_filters_button.setObjectName("advancedFiltersButton")
        
        # Style the button with modern, subtle design
        self.advanced_filters_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #3C3C3E;
                border-radius: 6px;
                color: #8E8E93;
                font-size: 12px;
                font-weight: 500;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                padding: 6px 12px;
                margin: 4px 0px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #2C2C2E;
                border-color: #4A4A4C;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #1C1C1E;
                border-color: #3478f6;
                color: #3478f6;
            }
            QPushButton:checked {
                background-color: #3478f6;
                border-color: #3478f6;
                color: #FFFFFF;
                font-weight: 600;
            }
        """)
        
        # Set button properties
        self.advanced_filters_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.advanced_filters_button.setCheckable(True)  # Can be toggled on/off
        self.advanced_filters_button.setChecked(False)  # Initially unchecked
        
        # Set size policy to be compact
        from PySide6.QtWidgets import QSizePolicy
        self.advanced_filters_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.advanced_filters_button.setMinimumSize(120, 28)
        self.advanced_filters_button.setMaximumSize(150, 28)
        
        # Add the button to the layout below the search bar
        # Find the parent layout of the search bar frame
        search_bar_parent = self.search_bar_frame.parent()
        if search_bar_parent:
            parent_layout = search_bar_parent.layout()
            if parent_layout:
                # Insert the button after the search bar frame in the layout
                search_bar_index = parent_layout.indexOf(self.search_bar_frame)
                if search_bar_index >= 0:
                    parent_layout.insertWidget(search_bar_index + 1, self.advanced_filters_button)
                    debug(f"✅ Advanced Filters button added to layout at index {search_bar_index + 1}")
                else:
                    # Fallback: add to the end
                    parent_layout.addWidget(self.advanced_filters_button)
                    debug(f"✅ Advanced Filters button added to layout (fallback)")
                
                # Align the button to the left (same as search bar)
                parent_layout.setAlignment(self.advanced_filters_button, Qt.AlignmentFlag.AlignLeft)
                
                # Connect the button click event
                self.advanced_filters_button.clicked.connect(self.on_advanced_filters_clicked)
                
                info("✅ Advanced Filters button setup completed")
            else:
                warning("⚠️ Parent layout not found")
        else:
            warning("⚠️ Search bar parent not found")
    
    def on_advanced_filters_clicked(self):
        """Handle Advanced Filters button click"""
        debug("🔍 Advanced Filters button clicked!")
        
        # Toggle the button state
        is_checked = self.advanced_filters_button.isChecked()
        debug(f"🔍 Advanced Filters button state: {is_checked}")
        
        # Update button text based on state
        if is_checked:
            self.advanced_filters_button.setText("Hide Advanced")
            # Switch to keywords editor mode (advanced mode)
            if hasattr(self, 'controller') and self.controller:
                self.controller.on_mode_changed("keywords_editor")
        else:
            self.advanced_filters_button.setText("Advanced Filters")
            # Switch back to classic search mode
            if hasattr(self, 'controller') and self.controller:
                self.controller.on_mode_changed("classic_search")
        
        # Notify controller about the state change
        if hasattr(self, 'controller') and self.controller:
            if hasattr(self.controller, 'on_advanced_filters_toggled'):
                self.controller.on_advanced_filters_toggled(is_checked)
    
    # def setup_logic_toggle_button(self):
    #     """Setup Logic Toggle button from UI file - REMOVED"""
    #     # Find the button in the UI
    #     if hasattr(self, 'ui_widget'):
    #         self.logic_toggle_button = self.ui_widget.findChild(QPushButton, "logicToggleButton")
    #         if self.logic_toggle_button:
    #             # Make button checkable
    #             self.logic_toggle_button.setCheckable(True)
    #             self.logic_toggle_button.setChecked(False)  # Initially unchecked (operators hidden by default)
    #             
    #             # Set cursor to pointer
    #             from PySide6.QtCore import Qt
    #             self.logic_toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
    #             
    #             # Connect the button click event
    #             self.logic_toggle_button.clicked.connect(self.on_logic_toggle_clicked)
    #             
    #             # Connect to search input bubbles changed signal
    #             if hasattr(self, 'search_input') and hasattr(self.search_input, 'bubblesChanged'):
    #                 self.search_input.bubblesChanged.connect(self.on_bubbles_changed)
    #             
    #             # Set initial state: operators hidden by default
    #             if hasattr(self, 'search_input') and hasattr(self.search_input, 'show_operators'):
    #                 self.search_input.show_operators = False
    #                 self.search_input.update_operator_visibility()
    #             
    #             # Initially show the button (visible from the beginning)
    #             self.logic_toggle_button.setVisible(True)
    #             
    #             print("✅ Logic Toggle button setup completed")
    #         else:
    #             print("⚠️ Logic Toggle button not found in UI")
    #     else:
    #             print("⚠️ UI widget not available")
    
    # def on_logic_toggle_clicked(self):
    #     """Handle Logic Toggle button click - REMOVED"""
    #     print("🔍 Logic Toggle button clicked!")
    #     
    #     # Toggle the show_operators state in search input
    #     if hasattr(self, 'search_input') and hasattr(self.search_input, 'show_operators'):
    #         self.search_input.show_operators = not self.search_input.show_operators
    #         self.search_input.update_operator_visibility()
    #         
    #         # Update button text and checked state based on show_operators
    #         if self.search_input.show_operators:
    #             self.logic_toggle_button.setText("Hide Logic")
    #             self.logic_toggle_button.setChecked(True)
    #         else:
    #             self.logic_toggle_button.setText("Show Logic")
    #             self.logic_toggle_button.setChecked(False)
    #         
    #         print(f"🔍 Operators visible: {self.search_input.show_operators}")
    #         print(f"🔍 Button text: {self.logic_toggle_button.text()}")
    #         print(f"🔍 Button checked: {self.logic_toggle_button.isChecked()}")
    # 
    # def on_bubbles_changed(self, has_bubbles: bool):
    #     """Handle bubbles changed signal from search input - REMOVED"""
    #     print(f"🔍 Bubbles changed: has_bubbles={has_bubbles}")
    #     
    #     if hasattr(self, 'logic_toggle_button'):
    #         # Keep button visible at all times (no longer depends on bubble presence)
    #         # The button is now always visible from the beginning
    #         print(f"🔍 Logic Toggle button remains visible regardless of bubbles") 