#!/usr/bin/env python3
"""
Tag Bubble Widget - Custom widget for filter pills
Displays selected filters with remove button
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QSizePolicy
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QFont, QIcon, QPainter, QColor, QPen


class TagBubbleWidget(QWidget):
    """Custom widget for filter pills with remove button"""
    
    def __init__(self, filter_type, filter_value, parent=None):
        super().__init__(parent)
        self.filter_type = filter_type
        self.filter_value = filter_value
        self.on_remove_callback = None
        
        self.setup_ui()
        self.setup_animation()
    
    def setup_ui(self):
        """Setup the UI for the tag bubble"""
        # Main layout
        layout = QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Filter value label (just the value, no type prefix)
        self.value_label = QLabel(self.filter_value)
        self.value_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 400;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background-color: transparent;
                border: none;
                padding: 8px 4px 8px 12px;
            }
        """)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.value_label)
        
        # Remove button (X) - positioned on the right side of bubble
        self.remove_button = QPushButton("×")
        self.remove_button.setObjectName("removeButton")
        self.remove_button.setMinimumSize(20, 20)
        self.remove_button.setMaximumSize(20, 20)
        self.remove_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 600;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                text-align: center;
                padding: 0px;
                margin: 0px;
                border-radius: 10px;
            }
            QPushButton:hover {
                color: #FFFFFF;
                background-color: rgba(255, 255, 255, 0.2);
                border-radius: 10px;
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.3);
                border-radius: 10px;
            }
        """)
        self.remove_button.clicked.connect(self.on_remove_clicked)
        layout.addWidget(self.remove_button)
        
        # Add right margin to the layout to prevent X button from touching the edge
        layout.setContentsMargins(0, 0, 8, 0)  # left, top, right, bottom
        
        # Size the widget properly like search bubbles - size to fit content exactly
        self.value_label.adjustSize()
        self.adjustSize()
        # Remove fixed height to let content determine size naturally
        
        # Set size policy to prevent auto-expansion
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        
        # Make bubble non-focusable so it doesn't steal focus
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    
    def paintEvent(self, event):
        """Custom paint event for bubble appearance - blue color scheme like search bubbles"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Use softer blue color scheme for dark mode (Apple's recommendation)
        color = QColor("#3478f6")  # Softer blue background for dark mode
        border_color = QColor("#2a70d6")  # Softer darker blue border
        
        # Draw bubble background
        painter.setBrush(color)
        painter.setPen(QPen(border_color, 1))
        painter.drawRoundedRect(self.rect(), 16, 16)  # 16px border radius like search bubbles
        
        # Call parent paint event for child widgets
        super().paintEvent(event)
    
    def setup_animation(self):
        """Setup animation for smooth appearance"""
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        
        # Let content determine size naturally
        self.adjustSize()
        
        # Use opacity animation instead of height animation to avoid cutting
        self.setGraphicsEffect(None)  # Ensure no graphics effects interfere
        
        # Animate in after a short delay
        QTimer.singleShot(50, self.animate_in)
    
    def animate_in(self):
        """Animate the widget into view"""
        # Let content determine size naturally
        self.adjustSize()
        
        # Force a layout update
        if self.parent():
            self.parent().updateGeometry()
        
        # Start the animation
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(self.geometry())
        self.animation.start()
    
    def animate_out(self, callback=None):
        """Animate the widget out of view"""
        self.animation.setStartValue(self.geometry())
        final_geometry = self.geometry()
        final_geometry.setHeight(0)
        self.animation.setEndValue(final_geometry)
        
        if callback:
            self.animation.finished.connect(callback)
        
        self.animation.start()
    
    def set_remove_callback(self, callback):
        """Set callback for when remove button is clicked"""
        self.on_remove_callback = callback
    
    def on_remove_clicked(self):
        """Handle remove button click"""
        if self.on_remove_callback:
            self.on_remove_callback(self.filter_type, self.filter_value)
    
    def get_filter_info(self):
        """Get filter type and value"""
        return self.filter_type, self.filter_value 