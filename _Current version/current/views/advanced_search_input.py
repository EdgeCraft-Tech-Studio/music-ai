#!/usr/bin/env python3
"""
Advanced Search Input Widget
A custom widget that shows 3 search fields for advanced mode
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QLabel, 
    QFrame, QSpacerItem, QSizePolicy, QTextEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

class AdvancedSearchInput(QWidget):
    """Advanced search input with 3 horizontal search fields"""
    
    # Signal emitted when text changes (for compatibility with existing code)
    textChanged = Signal(str)
    # Signal emitted when return is pressed (for compatibility with existing code)
    returnPressed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_fields = []
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """Setup the advanced search input with 3 horizontal fields"""
        # Create main layout
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(16)
        
        # Set styling for the main container
        self.setStyleSheet("""
            QWidget {
                background-color: #2C2C2E;
                border: 1px solid #3C3C3E;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        
        # Create 3 search fields
        self.create_search_fields()
        
        # Initially hide the advanced search input
        self.setVisible(False)
    
    def create_search_fields(self):
        """Create the 3 horizontal search fields"""
        field_configs = [
            {
                'name': 'orField',
                'placeholder': 'OR keywords...',
                'label': 'OR KEYWORDS',
                'width': 321
            },
            {
                'name': 'andField', 
                'placeholder': 'AND keywords...',
                'label': 'AND KEYWORDS',
                'width': 331
            },
            {
                'name': 'notField',
                'placeholder': 'NOT keywords...',
                'label': 'NOT KEYWORDS',
                'width': 201
            }
        ]
        
        for config in field_configs:
            # Create field container
            field_container = QFrame()
            field_layout = QVBoxLayout(field_container)
            field_layout.setContentsMargins(0, 0, 0, 0)
            field_layout.setSpacing(8)
            
            # Create label
            label = QLabel(config['label'])
            label.setStyleSheet("""
                QLabel {
                    color: #FFFFFF;
                    font-size: 12px;
                    font-weight: 500;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }
            """)
            
            # Create text edit (using QTextEdit to match .ui file)
            text_edit = QTextEdit()
            text_edit.setPlaceholderText(config['placeholder'])
            text_edit.setObjectName(config['name'])
            text_edit.setMaximumHeight(100)  # Match the height from .ui file
            text_edit.setStyleSheet("""
                QTextEdit {
                    background-color: #1C1C1E;
                    border: 1px solid #3C3C3E;
                    border-radius: 8px;
                    color: #FFFFFF;
                    font-size: 14px;
                    font-weight: 400;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    padding: 12px 16px;
                }
                QTextEdit:focus {
                    border: 1px solid #007AFF;
                    background-color: #1C1C1E;
                }
                QTextEdit::placeholder {
                    color: #8E8E93;
                    font-size: 14px;
                    font-weight: 400;
                }
            """)
            
            # Add to layout
            field_layout.addWidget(label)
            field_layout.addWidget(text_edit)
            
            # Add to main layout
            self.main_layout.addWidget(field_container)
            
            # Store reference
            self.search_fields.append({
                'container': field_container,
                'label': label,
                'text_edit': text_edit,
                'name': config['name']
            })
    
    def setup_connections(self):
        """Setup signal connections"""
        # Connect each field's text changes
        for field in self.search_fields:
            field['text_edit'].textChanged.connect(self.on_field_text_changed)
            # Note: QTextEdit doesn't have returnPressed, so we'll handle this differently
    
    def on_field_text_changed(self):
        """Handle text changes in any field"""
        # Combine all field texts
        combined_text = self.get_combined_text()
        self.textChanged.emit(combined_text)
    
    def get_combined_text(self):
        """Get combined text from all fields"""
        texts = []
        for field in self.search_fields:
            text = field['text_edit'].toPlainText().strip()
            if text:
                texts.append(text)
        return " ".join(texts)
    
    def set_combined_text(self, text):
        """Set text by distributing across fields (basic implementation)"""
        # For now, just put all text in the first field
        if self.search_fields:
            self.search_fields[0]['text_edit'].setPlainText(text)
    
    def clear_all_fields(self):
        """Clear all search fields"""
        for field in self.search_fields:
            field['text_edit'].clear()
    
    def get_text(self):
        """Get combined text from all fields"""
        return self.get_combined_text()
    
    def set_text(self, text):
        """Set text by distributing across fields"""
        self.set_combined_text(text)
    
    # Proxy methods to make this widget behave like QLineEdit
    def text(self):
        return self.get_text()
    
    def setText(self, text):
        self.set_text(text)
    
    def clear(self):
        self.clear_all_fields()
    
    def setPlaceholderText(self, text):
        """Set placeholder text for the first field"""
        if self.search_fields:
            self.search_fields[0]['text_edit'].setPlaceholderText(text)
    
    def setStyleSheet(self, style):
        """Apply stylesheet to the main widget"""
        super().setStyleSheet(style)
    
    def setAlignment(self, alignment):
        """Set alignment for all fields"""
        for field in self.search_fields:
            field['text_edit'].setAlignment(alignment)
    
    def setMinimumSize(self, size):
        super().setMinimumSize(size)
    
    def setMaximumSize(self, size):
        super().setMaximumSize(size)
    
    def setSizePolicy(self, horizontal, vertical):
        super().setSizePolicy(horizontal, vertical)
    
    def hasFocus(self):
        """Check if any field has focus"""
        for field in self.search_fields:
            if field['text_edit'].hasFocus():
                return True
        return False
    
    def setFocus(self):
        """Set focus to the first field"""
        if self.search_fields:
            self.search_fields[0]['text_edit'].setFocus()
    
    def clearFocus(self):
        """Clear focus from all fields"""
        for field in self.search_fields:
            field['text_edit'].clearFocus() 