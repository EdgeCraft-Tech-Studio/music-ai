#!/usr/bin/env python3
"""
Preferences Window View - Dialog for configuring application preferences
"""

import os
from functools import partial
from PySide6.QtWidgets import QDialog, QFileDialog, QLineEdit, QPushButton
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, Qt
from utils.logger import debug, info, warning, error, critical

class PreferencesWindow(QDialog):
    """Preferences window for configuring application settings"""
    
    def __init__(self, settings_model, parent=None):
        super().__init__(parent)
        self.settings_model = settings_model
        
        # Lists to store references to all folder widgets
        self.folder_inputs = []  # List of 6 QLineEdit widgets
        self.browse_buttons = []  # List of 6 browse buttons
        self.clear_buttons = []  # List of 6 clear buttons
        
        # Setup UI
        self.setup_ui()
        
        # Load folders from settings
        self.load_folders_from_settings()
        
        # Connect signals
        self.connect_signals()
    
    def setup_ui(self):
        """Load UI from .ui file and setup widgets"""
        # Get the path to the .ui file
        ui_file_path = os.path.join(os.path.dirname(__file__), "preferences.ui")
        
        # Load the UI file
        ui_file = QFile(ui_file_path)
        if not ui_file.open(QFile.ReadOnly):
            error(f"❌ Cannot open UI file: {ui_file_path}")
            return
        
        loader = QUiLoader()
        ui_widget = loader.load(ui_file, self)
        ui_file.close()
        
        if ui_widget is None:
            error(f"❌ Failed to load UI from: {ui_file_path}")
            return
        
        # Copy properties from loaded widget to self
        self.setWindowTitle(ui_widget.windowTitle())
        self.setMinimumSize(ui_widget.minimumSize())
        self.setMaximumSize(ui_widget.maximumSize())
        self.setStyleSheet(ui_widget.styleSheet())
        
        # Set layout from loaded widget
        self.setLayout(ui_widget.layout())
        
        # Get references to all folder widgets (1-6)
        for i in range(1, 7):
            folder_input = self.findChild(QLineEdit, f"folder{i}PathEdit")
            browse_button = self.findChild(QPushButton, f"folder{i}BrowseButton")
            clear_button = self.findChild(QPushButton, f"folder{i}ClearButton")
            
            if folder_input and browse_button and clear_button:
                self.folder_inputs.append(folder_input)
                self.browse_buttons.append(browse_button)
                self.clear_buttons.append(clear_button)
            else:
                warning(f"⚠️ Could not find widgets for folder {i}")
        
        # Get save and cancel buttons
        self.save_button = self.findChild(QPushButton, "saveButton")
        self.cancel_button = self.findChild(QPushButton, "cancelButton")
        
        debug(f"✅ Preferences UI loaded: {len(self.folder_inputs)} folder inputs found")
    
    def connect_signals(self):
        """Connect button signals to their handlers"""
        # Connect each browse button with its index
        for i, browse_button in enumerate(self.browse_buttons):
            browse_button.clicked.connect(partial(self.on_browse_clicked, i))
        
        # Connect each clear button with its index
        for i, clear_button in enumerate(self.clear_buttons):
            clear_button.clicked.connect(partial(self.on_clear_clicked, i))
        
        # Connect save and cancel buttons
        if self.save_button:
            self.save_button.clicked.connect(self.on_save_clicked)
        
        if self.cancel_button:
            self.cancel_button.clicked.connect(self.on_cancel_clicked)
        
        debug("✅ Preferences signals connected")
    
    def load_folders_from_settings(self):
        """Load all folders from settings and populate the inputs"""
        if not self.settings_model:
            return
        
        # Get existing folders from settings
        folders = self.settings_model.get_setting('search_folders', [])
        
        debug(f"📁 Loading {len(folders)} folder(s) from settings")
        
        # Populate inputs (up to 6)
        for i, folder in enumerate(folders[:6]):
            if i < len(self.folder_inputs):
                self.folder_inputs[i].setText(folder)
                debug(f"  {i+1}. {folder}")
    
    def on_browse_clicked(self, index):
        """Handle browse button click for specific folder index"""
        if index >= len(self.folder_inputs):
            return
        
        # Get current folder or use home directory as starting point
        current_folder = self.folder_inputs[index].text()
        if not current_folder or current_folder == "No folder selected":
            current_folder = os.path.expanduser("~")
        
        # Open native folder picker dialog
        folder = QFileDialog.getExistingDirectory(
            self,
            f"Select Folder {index + 1}",
            current_folder,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if folder:
            # Update the folder input
            self.folder_inputs[index].setText(folder)
            debug(f"📁 Folder {index + 1} selected: {folder}")
    
    def on_clear_clicked(self, index):
        """Handle clear button click for specific folder index"""
        if index >= len(self.folder_inputs):
            return
        
        # Clear the folder input
        self.folder_inputs[index].clear()
        info(f"🗑️ Folder {index + 1} cleared")
    
    def get_all_folders(self):
        """Get all non-empty folder paths from the inputs"""
        folders = []
        for folder_input in self.folder_inputs:
            folder_path = folder_input.text().strip()
            # Only include non-empty paths that aren't the placeholder
            if folder_path and folder_path != "No folder selected":
                folders.append(folder_path)
        return folders
    
    def on_save_clicked(self):
        """Handle save button click - save all folders to settings"""
        # Get all non-empty folders
        folders = self.get_all_folders()
        
        if self.settings_model:
            # Save to settings
            self.settings_model.update_setting('search_folders', folders)
            info(f"💾 Saved {len(folders)} folder(s) to settings")
            for i, folder in enumerate(folders, 1):
                debug(f"  {i}. {folder}")
        else:
            warning("⚠️ No settings model available")
        
        # Close dialog with success
        self.accept()
    
    def on_cancel_clicked(self):
        """Handle cancel button click - close dialog without saving"""
        info("❌ Preferences cancelled")
        self.reject()
    
    def get_selected_folders(self):
        """Get the currently selected folders (for compatibility)"""
        return self.get_all_folders()
