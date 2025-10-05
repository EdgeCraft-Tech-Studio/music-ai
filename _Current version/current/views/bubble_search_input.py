#!/usr/bin/env python3
"""
Bubble Search Input Widget
A custom QLineEdit that converts comma-separated text into bubbles
"""

from PySide6.QtWidgets import QLineEdit, QHBoxLayout, QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QPainter, QColor, QPen
import re

class ORLabel(QLabel):
    """Beautiful clickable operator label between bubbles"""
    
    def __init__(self, parent=None):
        super().__init__("OR", parent)
        self.operators = ["OR", "AND", "NOT"]
        self.current_index = 0
        self.setup_ui()
        self.setup_events()
    
    def setup_ui(self):
        """Setup operator label appearance"""
        font = QFont()
        font.setPointSize(10)
        font.setWeight(QFont.Weight.Medium)
        font.setFamily("-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif")
        self.setFont(font)
        
        self.setStyleSheet("""
            QLabel {
                color: #8E8E93;
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 2px 8px;
                font-weight: 500;
            }
            QLabel:hover {
                color: #007AFF;
                background-color: rgba(0, 122, 255, 0.1);
                border-color: #007AFF;
            }
        """)
        
        self.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.setFixedHeight(32)  # Match bubble height
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def setup_events(self):
        """Setup click events for operator cycling"""
        self.setMouseTracking(True)
    
    def mousePressEvent(self, event):
        """Handle click to cycle through operators"""
        self.cycle_operator()
        # Don't call super() to prevent focus issues
        # Ensure the line edit maintains focus
        if hasattr(self.parent(), 'main_input') and hasattr(self.parent().main_input, 'line_edit'):
            self.parent().main_input.line_edit.setFocus()
    
    def cycle_operator(self):
        """Cycle through OR -> AND -> NOT -> OR"""
        self.current_index = (self.current_index + 1) % len(self.operators)
        new_operator = self.operators[self.current_index]
        self.setText(new_operator)
        
        # Update color based on operator type
        if new_operator == "OR":
            color = "#8E8E93"  # Default gray
        elif new_operator == "AND":
            color = "#34C759"  # Green for AND
        else:  # NOT
            color = "#FF3B30"  # Red for NOT
        
        self.setStyleSheet(f"""
            QLabel {{
                color: {color};
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 2px 8px;
                font-weight: 500;
            }}
            QLabel:hover {{
                color: #007AFF;
                background-color: rgba(0, 122, 255, 0.1);
                border-color: #007AFF;
            }}
        """)
        
        print(f"🔍 Operator changed to: {new_operator}")
    
    def get_current_operator(self):
        """Get the current operator text"""
        return self.operators[self.current_index]

class BubbleWidget(QWidget):
    """Individual bubble widget"""
    
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.text = text.strip()
        self.is_selected = False
        self.setup_ui()
        self.setup_events()
    
    def setup_ui(self):
        """Setup bubble appearance"""
        # Create main layout - only for the label
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Create label for text
        self.label = QLabel(self.text, self)
        font = QFont()
        font.setPointSize(11)
        font.setWeight(QFont.Weight.Medium)
        font.setFamily("-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif")
        self.label.setFont(font)
        self.label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                background-color: transparent;
                border: none;
                padding: 8px 20px 8px 16px;
            }
        """)
        self.label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        # No close button needed - using selection-based deletion
        
        # Add only label to layout
        self.layout.addWidget(self.label)
        
        # Size the widget properly
        self.label.adjustSize()
        self.adjustSize()
        self.setFixedHeight(32)
        
        # Make bubble non-focusable so it doesn't steal focus from line edit
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        # Set cursor to pointer to indicate clickability
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # No dynamic width adjustment needed - bubbles are naturally sized
    
    def setup_events(self):
        """Setup click events for selection"""
        self.setMouseTracking(True)
        self.is_hovered = False
    
    def mousePressEvent(self, event):
        """Handle click to select/deselect bubble"""
        self.toggle_selection()
        # Don't call super() to prevent the bubble from getting focus
        # Instead, ensure the line edit maintains focus
        if hasattr(self, 'main_input') and hasattr(self.main_input, 'line_edit'):
            self.main_input.line_edit.setFocus()
    
    def enterEvent(self, event):
        """Handle mouse enter event for hover"""
        self.is_hovered = True
        self.update()  # Trigger repaint to show hover state
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave event for hover"""
        self.is_hovered = False
        self.update()  # Trigger repaint to show normal state
        super().leaveEvent(event)
    
    def toggle_selection(self):
        """Toggle selection state - only one bubble can be selected at a time"""
        # If this bubble is already selected, deselect it
        if self.is_selected:
            self.is_selected = False
        else:
            # Clear all other selections first
            if hasattr(self, 'main_input') and hasattr(self.main_input, 'clear_selections'):
                self.main_input.clear_selections()
            # Then select this bubble
            self.is_selected = True
        
        self.update()  # Trigger repaint to show new color
        # Notify main input of selection change
        if hasattr(self, 'main_input') and hasattr(self.main_input, 'on_bubble_selection_changed'):
            self.main_input.on_bubble_selection_changed(self)
        
        # Ensure line edit maintains focus for keyboard events
        if hasattr(self, 'main_input') and hasattr(self.main_input, 'line_edit'):
            self.main_input.line_edit.setFocus()
    
    def set_selected(self, selected):
        """Set selection state"""
        if self.is_selected != selected:
            self.is_selected = selected
            self.update()  # Trigger repaint
    
    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
    
    def paintEvent(self, event):
        """Custom paint event for bubble appearance"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Choose color based on selection and hover state - blue shades for search keywords
        if self.is_selected:
            color = QColor("#5BB5FF")  # Brightest blue when selected
        elif self.is_hovered:
            color = QColor("#4DA6FF")  # Medium blue for hover
        else:
            color = QColor("#007AFF")  # Normal blue
        
        # Draw bubble background
        painter.setBrush(color)
        painter.setPen(QPen(color, 1))
        painter.drawRoundedRect(self.rect(), 16, 16)

class BubbleSearchInput(QWidget):
    """Custom search input with bubbles functionality"""
    
    # Signal emitted when text changes (for compatibility with existing code)
    textChanged = Signal(str)
    # Signal emitted when return is pressed (for compatibility with existing code)
    returnPressed = Signal()
    # Signal emitted when bubbles are added or removed
    bubblesChanged = Signal(bool)
    # Signal emitted when text should be converted to filter bubble
    textToFilterBubble = Signal(str)
    
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bubbles = []
        self.or_labels = []  # List of OR labels between bubbles
        self.line_edit = None
        self.bubble_container = None
        self.original_text = ""
        self.current_search_text = ""  # Store the current search text
        self.show_operators = True  # Default to showing operators
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """Setup the main layout with line edit and bubble container"""
        # Create main layout
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create the line edit
        self.line_edit = QLineEdit()
        self.reset_line_edit_style()
        
        # Create container for bubbles
        self.bubble_container = QWidget()
        self.bubble_layout = QHBoxLayout(self.bubble_container)
        self.bubble_layout.setContentsMargins(0, 0, 0, 0)
        self.bubble_layout.setSpacing(4)
        self.bubble_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        # Initially hide the bubble container
        self.bubble_container.setVisible(False)
        self.bubble_container.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
        """)
        
        # Add widgets to main layout
        self.main_layout.addWidget(self.bubble_container)
        self.main_layout.addWidget(self.line_edit, 1)  # Line edit takes remaining space
    
    def setup_connections(self):
        """Setup signal connections"""
        # Connect text changes to bubble processing
        self.line_edit.textChanged.connect(self.on_text_changed)
        
        # Connect return pressed signal
        self.line_edit.returnPressed.connect(self.returnPressed.emit)
        
        # Connect key press events to both the line edit and the main widget
        self.line_edit.installEventFilter(self)
        self.installEventFilter(self)
        
        # Also connect to key press events directly
        self.line_edit.keyPressEvent = self.on_line_edit_key_press
        
        # Store original keyPressEvent for fallback
        self._original_key_press_event = QLineEdit.keyPressEvent
        
        # Ensure our textChanged signal is properly connected
        # This will be connected by the main controller
    
    def eventFilter(self, obj, event):
        """Handle key press events and mouse clicks"""
        from PySide6.QtCore import QEvent
        
        if event.type() == QEvent.Type.MouseButtonPress:
            # Clear bubble selections when clicking in the search input
            if self.bubbles:
                self.clear_selections()
            return False  # Let the event continue to normal handling
        
        elif event.type() == QEvent.Type.KeyPress:
            print(f"🔍 KeyPress event: key={event.key()}, obj={obj}, bubbles={len(self.bubbles) if self.bubbles else 0}")
            
            # Check if we can add more bubbles (space is full)
            if self.bubbles and not self.can_add_bubble():
                # Space is full - only block printable characters (text input)
                if event.key() == Qt.Key.Key_Backspace:
                    # Allow backspace to remove bubbles
                    selected_bubble = self.get_selected_bubble()
                    if selected_bubble:
                        print(f"🔍 Backspace - removing selected bubble: '{selected_bubble.text}'")
                        self.remove_bubble(selected_bubble)
                        return True
                    elif len(self.line_edit.text()) == 0:
                        print(f"🔍 Backspace - removing last bubble")
                        self.remove_last_bubble()
                        return True
                    else:
                        # Allow backspace on text in line edit
                        return False  # Let normal backspace handle it
                elif event.text() and event.text().isprintable():
                    # Block only printable characters (text input) when space is full
                    print(f"🔍 Blocking text input: '{event.text()}' - space is full")
                    return True  # Block the event
                else:
                    # Allow all non-printable keys (function keys, modifiers, etc.)
                    return False
            
            if event.key() in [Qt.Key.Key_Return, Qt.Key.Key_Enter]:
                # Clear bubble selections when pressing Enter
                if self.bubbles:
                    self.clear_selections()
                
                # Only convert to bubbles if there's text to convert
                if self.line_edit.text().strip():
                    self.textToFilterBubble.emit(self.line_edit.text().strip())
                    # Don't emit returnPressed signal when converting text to bubbles
                    print(f"🔍 Converting text to filter bubble, not starting search")
                    return True
                # If no text and no bubbles, don't start search
                elif not self.bubbles:
                    print(f"🔍 No text and no bubbles - not starting search")
                    return True
                # If no text but there are bubbles, start the search
                else:
                    print(f"🔍 No text but bubbles exist - starting search")
                    self.returnPressed.emit()
                    return True
            elif event.key() == Qt.Key.Key_Backspace:
                print(f"🔍 Backspace detected! Bubbles: {len(self.bubbles)}, Text: '{self.line_edit.text()}'")
                # Handle backspace to remove selected bubble or last bubble
                if self.bubbles:
                    # Check if any bubble is selected
                    selected_bubble = self.get_selected_bubble()
                    if selected_bubble:
                        print(f"🔍 Backspace - removing selected bubble: '{selected_bubble.text}'")
                        self.remove_bubble(selected_bubble)
                        return True
                    elif len(self.line_edit.text()) == 0:
                        # Only remove last bubble if no text and no selection
                        print(f"🔍 Backspace - removing last bubble")
                        self.remove_last_bubble()
                        return True
                    else:
                        print(f"🔍 Backspace in bubble mode but text not empty: '{self.line_edit.text()}'")
                else:
                    print(f"🔍 Backspace but no bubbles to remove")
            else:
                print(f"🔍 Other key: {event.key()} (Backspace should be {Qt.Key.Key_Backspace})")
                # Clear bubble selections when user starts typing
                if self.bubbles:
                    self.clear_selections()
        
        return super().eventFilter(obj, event)
    
    def on_line_edit_key_press(self, event):
        """Handle key press events directly on the line edit"""
        print(f"🔍 Direct KeyPress: key={event.key()}, bubbles={len(self.bubbles) if self.bubbles else 0}")
        
        # Check if we can add more bubbles (space is full)
        if self.bubbles and not self.can_add_bubble():
            # Space is full - only block printable characters (text input)
            if event.key() == Qt.Key.Key_Backspace:
                # Allow backspace to remove bubbles
                selected_bubble = self.get_selected_bubble()
                if selected_bubble:
                    print(f"🔍 Direct Backspace - removing selected bubble: '{selected_bubble.text}'")
                    self.remove_bubble(selected_bubble)
                    return  # Don't call parent
                elif len(self.line_edit.text()) == 0:
                    print(f"🔍 Direct Backspace - removing last bubble")
                    self.remove_last_bubble()
                    return  # Don't call parent
                else:
                    # Allow backspace on text in line edit
                    self._original_key_press_event(self.line_edit, event)
                    return
            elif event.text() and event.text().isprintable():
                # Block only printable characters (text input) when space is full
                print(f"🔍 Direct Blocking text input: '{event.text()}' - space is full")
                return  # Block the event
            else:
                # Allow all non-printable keys (function keys, modifiers, etc.)
                self._original_key_press_event(self.line_edit, event)
                return
        
        if event.key() in [Qt.Key.Key_Return, Qt.Key.Key_Enter]:
            # Clear bubble selections when pressing Enter
            if self.bubbles:
                self.clear_selections()
            
            # Only convert to bubbles if there's text to convert
            if self.line_edit.text().strip():
                self.textToFilterBubble.emit(self.line_edit.text().strip())
                # Don't emit returnPressed signal when converting text to bubbles
                print(f"🔍 Direct Converting text to filter bubble, not starting search")
                return  # Don't call parent
            # If no text and no bubbles, don't start search
            elif not self.bubbles:
                print(f"🔍 Direct No text and no bubbles - not starting search")
                return  # Don't call parent
            # If no text but there are bubbles, start the search
            else:
                print(f"🔍 Direct No text but bubbles exist - starting search")
                self.returnPressed.emit()
                return  # Don't call parent
        elif event.key() == Qt.Key.Key_Backspace:
            print(f"🔍 Direct Backspace detected!")
            if self.bubbles:
                selected_bubble = self.get_selected_bubble()
                if selected_bubble:
                    print(f"🔍 Direct Backspace - removing selected bubble: '{selected_bubble.text}'")
                    self.remove_bubble(selected_bubble)
                    return  # Don't call parent
                elif len(self.line_edit.text()) == 0:
                    print(f"🔍 Direct Backspace - removing last bubble")
                    self.remove_last_bubble()
                    return  # Don't call parent
                else:
                    print(f"🔍 Direct Backspace - letting normal behavior handle text")
        else:
            print(f"🔍 Direct Other key: {event.key()} (Backspace should be {Qt.Key.Key_Backspace})")
            # Clear bubble selections when user starts typing
            if self.bubbles:
                self.clear_selections()
        
        # Call the original keyPressEvent
        self._original_key_press_event(self.line_edit, event)
    
    def on_text_changed(self, text):
        """Handle text changes"""
        # Save the current search text
        self.current_search_text = text
        
        # Always emit textChanged signal for compatibility with existing code
        # This ensures the start search button shows/hides properly
        if not self.bubbles:
            self.original_text = text
            self.textChanged.emit(text)
            print(f"🔍 Emitted normal text: '{text}'")
        else:
            # When in bubble mode, emit the bubble text
            bubble_text = " ".join([f'"{bubble.text}"' for bubble in self.bubbles])
            self.textChanged.emit(bubble_text)
            print(f"🔍 Emitted bubble text: '{bubble_text}'")
    
    def convert_to_bubbles(self):
        """Convert current text to bubbles - DISABLED"""
        # DISABLED: Blue search bubbles functionality is disabled
        # Text is now converted to filter bubbles instead
        print(f"🔍 Blue search bubbles conversion disabled - using filter bubbles instead")
        return
    
    def can_add_bubble(self):
        """Check if there's enough space to add another bubble"""
        if not self.bubbles:
            return True  # Always allow first bubble
        
        # Use the initial default width from the UI geometry (1089px)
        # This provides a consistent baseline for space calculations
        INITIAL_WINDOW_WIDTH = 824
        
        # Calculate current bubble width including spacing
        current_bubble_width = 0
        for bubble in self.bubbles:
            current_bubble_width += bubble.width() + 4  # 4px spacing between bubbles
        
        # Only prevent adding if there's literally no space left for the line edit
        # Reserve just enough space to see the cursor (20px)
        min_line_edit_space = 20
        
        can_add = (current_bubble_width + min_line_edit_space) < INITIAL_WINDOW_WIDTH - 24 # 24px is padding
        
        # Debug output
        print(f"🔍 Space check: initial_width={INITIAL_WINDOW_WIDTH}, current_bubbles={current_bubble_width}, min_line_space={min_line_edit_space}, can_add={can_add}")
        
        return can_add
    
    def reset_line_edit_style(self):
        """Reset line edit to normal style"""
        self.line_edit.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                border: none;
                color: #FFFFFF;
                font-size: 15px;
                font-weight: 400;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                padding: 0px 0px;
                text-align: left;
                qproperty-alignment: AlignVCenter;
            }
            QLineEdit:focus {
                border: none;
                outline: none;
            }
            QLineEdit::placeholder {
                color: #98989D;
                font-size: 15px;
                font-weight: 400;
            }
        """)
    
    def resizeEvent(self, event):
        """Handle resize events to recalculate bubble space"""
        super().resizeEvent(event)
        # Recalculate space when widget is resized
        if self.bubbles:
            # Force a layout update to get accurate measurements
            self.bubble_container.updateGeometry()
            self.update()
    
    def convert_free_text_to_bubbles(self):
        """Convert any free text in the line edit to bubbles - DISABLED"""
        # DISABLED: Blue search bubbles functionality is disabled
        # Text is now converted to filter bubbles instead
        print(f"🔍 Blue search bubbles conversion disabled - using filter bubbles instead")
        return
    
    def get_selected_bubble(self):
        """Get the currently selected bubble"""
        for bubble in self.bubbles:
            if bubble.is_selected:
                return bubble
        return None
    
    def clear_selections(self):
        """Clear all bubble selections"""
        for bubble in self.bubbles:
            bubble.set_selected(False)
    
    def on_bubble_selection_changed(self, selected_bubble):
        """Handle bubble selection changes"""
        print(f"🔍 Bubble selection changed: '{selected_bubble.text}' selected={selected_bubble.is_selected}")
        # Clear other selections when one is selected
        for bubble in self.bubbles:
            if bubble != selected_bubble:
                bubble.set_selected(False)
        
        # Ensure line edit has focus for keyboard events
        self.line_edit.setFocus()
    
    def remove_bubble(self, bubble_widget):
        """Remove a specific bubble"""
        if bubble_widget in self.bubbles:
            bubble_index = self.bubbles.index(bubble_widget)
            self.bubbles.remove(bubble_widget)
            self.bubble_layout.removeWidget(bubble_widget)
            bubble_widget.deleteLater()
            
            # Remove associated OR label if it exists
            # OR labels are added BEFORE each bubble (except the first)
            # Layout: [Bubble1] [OR] [Bubble2] [OR] [Bubble3]
            # When removing a bubble at index i:
            # - If i == 0: remove or_labels[0] (OR after first bubble)
            # - If i > 0: remove or_labels[i-1] (OR before this bubble)
            if bubble_index == 0 and len(self.or_labels) > 0:
                # Remove the first OR label (which comes after the first bubble)
                or_label = self.or_labels.pop(0)
                self.bubble_layout.removeWidget(or_label)
                or_label.deleteLater()
            elif bubble_index > 0 and bubble_index - 1 < len(self.or_labels):
                # Remove the OR label that comes before this bubble
                or_label = self.or_labels.pop(bubble_index - 1)
                self.bubble_layout.removeWidget(or_label)
                or_label.deleteLater()
            
            # Update text
            if self.bubbles:
                bubble_text = " ".join([f'"{bubble.text}"' for bubble in self.bubbles])
                self.textChanged.emit(bubble_text)
            else:
                # Hide container when all bubbles are removed
                self.bubble_container.setVisible(False)
                # Emit bubbles changed signal
                self.bubblesChanged.emit(False)
                # Restore placeholder text when all bubbles are removed
                self.line_edit.setPlaceholderText(self.DEFAULT_PLACEHOLDER)
                self.textChanged.emit("")
            
            # Force layout update to recalculate space
            self.bubble_container.updateGeometry()
            self.update()
            
            # Auto-convert to OR when only one bubble remains
            if len(self.bubbles) == 1 and self.or_labels:
                # Convert any remaining OR labels to "OR" since there's only one bubble left
                for or_label in self.or_labels:
                    or_label.set_text("OR")
                print("🔍 Auto-converted to OR: only one bubble remaining")
            
            # Reset line edit style if space is now available
            if self.can_add_bubble():
                self.reset_line_edit_style()
    
    def remove_last_bubble(self):
        """Remove the last bubble"""
        if not self.bubbles:
            return
        
        # Remove last bubble
        last_bubble = self.bubbles.pop()
        self.bubble_layout.removeWidget(last_bubble)
        last_bubble.deleteLater()
        
        # Remove the last OR label if it exists
        if self.or_labels:
            last_or_label = self.or_labels.pop()
            self.bubble_layout.removeWidget(last_or_label)
            last_or_label.deleteLater()
        
        # Always update text
        if self.bubbles:
            bubble_text = " ".join([f'"{bubble.text}"' for bubble in self.bubbles])
            self.textChanged.emit(bubble_text)
        else:
            # Hide container when all bubbles are removed
            self.bubble_container.setVisible(False)
            # Emit bubbles changed signal
            self.bubblesChanged.emit(False)
            # Restore placeholder text when all bubbles are removed
            self.line_edit.setPlaceholderText(self.DEFAULT_PLACEHOLDER)
            self.textChanged.emit("")
        
        # Force layout update to recalculate space
        self.bubble_container.updateGeometry()
        self.update()
        
        # Auto-convert to OR when only one bubble remains
        if len(self.bubbles) == 1 and self.or_labels:
            # Convert any remaining OR labels to "OR" since there's only one bubble left
            for or_label in self.or_labels:
                or_label.set_text("OR")
            print("🔍 Auto-converted to OR: only one bubble remaining")
        
        # Reset line edit style if space is now available
        if self.can_add_bubble():
            self.reset_line_edit_style()
    
    def clear_bubbles(self):
        """Clear all bubbles and return to normal text input"""
        for bubble in self.bubbles:
            self.bubble_layout.removeWidget(bubble)
            bubble.deleteLater()
        
        self.bubbles = []
        
        # Clear all OR labels
        for or_label in self.or_labels:
            self.bubble_layout.removeWidget(or_label)
            or_label.deleteLater()
        self.or_labels.clear()
        
        self.bubble_container.setVisible(False)
        self.line_edit.clear()
        
        # Emit bubbles changed signal
        self.bubblesChanged.emit(False)
        
        # Restore original placeholder text
        self.line_edit.setPlaceholderText(self.DEFAULT_PLACEHOLDER)
        
        self.textChanged.emit("")
    
    def get_text(self):
        """Get current text from the stored search text"""
        # Return the stored search text that was saved when user typed
        print(f"🔍 get_text() returning stored search text: '{self.current_search_text}'")
        return self.current_search_text
    
    def set_text(self, text):
        """Set text (clears bubbles if any)"""
        self.clear_bubbles()
        self.line_edit.setText(text)
    
    # Proxy methods to make this widget behave like QLineEdit
    def text(self):
        return self.get_text()
    
    def setText(self, text):
        self.set_text(text)
    
    def clear(self):
        self.clear_bubbles()
    
    def setPlaceholderText(self, text):
        """Set placeholder text and update the constant"""
        self.DEFAULT_PLACEHOLDER = text
        self.line_edit.setPlaceholderText(text)
    
    def placeholderText(self):
        """Get placeholder text"""
        return self.line_edit.placeholderText()
    
    def alignment(self):
        """Get alignment"""
        return self.line_edit.alignment()
    
    def minimumSize(self):
        """Get minimum size"""
        return self.line_edit.minimumSize()
    
    def maximumSize(self):
        """Get maximum size"""
        return self.line_edit.maximumSize()
    
    def sizePolicy(self):
        """Get size policy"""
        return self.line_edit.sizePolicy()
    
    def set_placeholder_from_ui(self, placeholder_text):
        """Set the placeholder text from UI and update the constant"""
        self.DEFAULT_PLACEHOLDER = placeholder_text
        self.line_edit.setPlaceholderText(placeholder_text)
    
    def setStyleSheet(self, style):
        # Apply to line edit
        self.line_edit.setStyleSheet(style)
    
    def setAlignment(self, alignment):
        self.line_edit.setAlignment(alignment)
    
    def setMinimumSize(self, size):
        super().setMinimumSize(size)
        self.line_edit.setMinimumSize(size)
    
    def setMaximumSize(self, size):
        super().setMaximumSize(size)
        self.line_edit.setMaximumSize(size)
    
    def setSizePolicy(self, policy):
        super().setSizePolicy(policy)
        self.line_edit.setSizePolicy(policy)
    
    def hasFocus(self):
        return self.line_edit.hasFocus()
    
    def setFocus(self):
        self.line_edit.setFocus()
    
    def clearFocus(self):
        self.line_edit.clearFocus()
    
    def update_operator_visibility(self):
        """Update visibility of OR operators"""
        for or_label in self.or_labels:
            or_label.setVisible(self.show_operators) 