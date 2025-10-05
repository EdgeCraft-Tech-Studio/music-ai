#!/usr/bin/env python3
"""
Results Tree Bubble Widget
A custom widget that displays items as bubbles in the result tree
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPainter, QColor, QPen

class ResultsTreeBubbleWidget(QWidget):
    """Widget that displays items as bubbles in the result tree"""
    
    def __init__(self, items_text, parent=None):
        super().__init__(parent)
        self.items_text = items_text
        self.items = self.parse_items(items_text)
        self.setup_ui()
    
    def parse_items(self, items_text):
        """Parse items from text (separated by ' • ' or ', ')"""
        if not items_text:
            return []
        # Handle both ' • ' and ', ' separators
        if ' • ' in items_text:
            return [item.strip() for item in items_text.split(' • ') if item.strip()]
        else:
            return [item.strip() for item in items_text.split(', ') if item.strip()]
    
    def setup_ui(self):
        """Setup the bubble layout"""
        # Create main layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(4)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        # Create bubble widgets for each item
        for item in self.items:
            bubble = ResultsTreeBubble(item, self)
            self.layout.addWidget(bubble)
        
        # Add stretch to push bubbles to the left
        self.layout.addStretch()
        
        # Let content determine height naturally (like tag bubbles)
        # self.setFixedHeight(24)
        
        # Make widget non-focusable
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

class ResultsTreeBubble(QWidget):
    """Individual result tree bubble"""
    
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.text = text
        self.setup_ui()
    
    def setup_ui(self):
        """Setup bubble appearance"""
        # Create main layout - only for the label
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Create label for text
        self.label = QLabel(self.text, self)
        font = QFont()
        font.setPointSize(10)
        font.setWeight(QFont.Weight.Medium)
        font.setFamily("-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif")
        self.label.setFont(font)
        self.label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                background-color: transparent;
                border: none;
                padding: 4px 12px 4px 12px;
            }
        """)
        self.label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        # Add only label to layout
        self.layout.addWidget(self.label)
        
        # Size the widget properly
        self.label.adjustSize()
        self.adjustSize()
        # Let content determine height naturally (like tag bubbles)
        # self.setFixedHeight(20)
        
        # Set size policy to prevent auto-expansion (like tag bubbles)
        from PySide6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        
        # Make bubble non-focusable
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    
    def paintEvent(self, event):
        """Custom paint event for bubble appearance"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Use grey colors for result tree bubbles (same as previous search bubble colors)
        color = QColor("#484848")  # Light grey for normal state
        
        # Draw bubble background
        painter.setBrush(color)
        painter.setPen(QPen(color, 1))
        painter.drawRoundedRect(self.rect(), 16, 16) 