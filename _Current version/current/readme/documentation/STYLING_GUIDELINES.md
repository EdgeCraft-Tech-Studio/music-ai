# Styling Guidelines - Single Source of Truth

## Overview
This project follows a "single source of truth" approach for styling to ensure maintainability and consistency.

## Principles

### 1. UI File is Primary Source
- **All static styling should be in `.ui` files**
- **Python code should only handle dynamic styling**
- **UI files are the single source of truth for appearance**

### 2. When to Use Python Styling
Only use Python `setStyleSheet()` for:
- **Dynamic theming** (light/dark mode switching)
- **Conditional styling** (based on user preferences)
- **Runtime color changes** (based on application state)
- **Temporary styling** (for debugging or special states)

### 3. What Goes in UI Files
- **Background colors and borders**
- **Font families and sizes**
- **Padding and margins**
- **Border radius and shadows**
- **Hover and selection states**
- **Default colors and themes**

### 4. What Goes in Python Code
- **Alignment and layout properties** (`setAlignment()`, `setWordWrap()`)
- **Functional properties** (size policies, scroll policies)
- **Dynamic content** (text changes, icon updates)
- **Event-driven styling** (hover effects, focus states)

## Examples

### ✅ Good - UI File Styling
```xml
<property name="styleSheet">
 <string notr="true">QWidget {
    background-color: #1A1A1C;
    border: 1px solid #3A3A3C;
    border-radius: 12px;
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text';
}</string>
</property>
```

### ✅ Good - Python Functional Properties
```python
# Only set functional properties, not styling
self.results_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
self.results_label.setWordWrap(True)
```

### ❌ Bad - Hardcoded Styles in Python
```python
# Don't do this - styling should be in UI file
self.results_label.setStyleSheet("""
    QLabel {
        background-color: #2C2C2E;
        border-radius: 8px;
    }
""")
```

## Benefits
1. **Easy editing** - All styles in one place (UI file)
2. **Consistency** - No conflicting styles between UI and Python
3. **Maintainability** - Changes only need to be made in UI file
4. **Designer-friendly** - Qt Designer can edit UI file styles
5. **Version control** - Clear diff of style changes

## Current Implementation
- **Results area styling** - All in `patchio_current_ui.ui`
- **Tree widget styling** - All in UI file with comprehensive selectors
- **Status bar styling** - All in UI file (status bar, progress bar, labels)
- **Python code** - Only handles functional properties and truly dynamic content (error states)

## Recent Improvements
- ✅ **Moved status bar styling** from Python to UI file
- ✅ **Moved progress bar styling** from Python to UI file  
- ✅ **Moved status label styling** from Python to UI file
- ✅ **Kept error state styling** in Python (truly dynamic)
- ✅ **Updated background colors** to modern `#1A1A1C` instead of old `#2C2C2E` 