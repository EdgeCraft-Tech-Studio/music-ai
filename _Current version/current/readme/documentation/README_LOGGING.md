# PatchIO Logging System

This document explains how to use the enhanced logging system that supports proper log levels and matches the original `patchio_old.py` approach.

## Overview

The logging system provides **enhanced functionality** with proper log levels:
- **DEBUG** - Detailed debugging information (can be turned off)
- **INFO** - General information messages
- **WARNING** - Warning messages
- **ERROR** - Error messages
- **CRITICAL** - Critical error messages
- **error()** - Standard error logging (respects log levels)

## Log File Path Configuration

The log file path is now **easily configurable** in `settings/core_settings.py`:

```python
# App identity (matches original patchio_old.py)
APP_NAME = "PatchIO"
APP_AUTHOR = None  # No author or company name

# Log file configuration (matches original patchio_old.py)
LOG_FILE_NAME = "patchIO_logs.log"  # Same filename as original
LOG_LEVEL = "ERROR"  # Can be: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### **To Change Log File Location:**

1. **Change the filename:**
   ```python
   LOG_FILE_NAME = "my_custom_logs.log"
   ```

2. **Change the app name (affects directory):**
   ```python
   APP_NAME = "MyApp"
   ```

3. **Change the author (affects directory):**
   ```python
   APP_AUTHOR = "MyCompany"
   ```

### **Log File Location:**

The log file is stored in the same location as the original `patchio_old.py`:
- **macOS**: `~/Library/Application Support/PatchIO/patchIO_logs.log`
- **Windows**: `%APPDATA%\PatchIO\patchIO_logs.log`
- **Linux**: `~/.config/PatchIO/patchIO_logs.log`

## Log Levels

### DEBUG Level
```python
debug("🔍 Debug message - can be turned off")
```
- **Can be turned off** by setting log level to INFO or higher
- Use for detailed debugging information
- Examples: file paths, search terms, widget states

### INFO Level
```python
info("📁 Simple Search: piano")
```
- **Always logged** unless level is set to WARNING or higher
- Use for general application flow
- Examples: search started, results found, mode changes

### WARNING Level
```python
warning("⚠️ Warning message")
```
- **Always logged** unless level is set to ERROR or higher
- Use for non-critical issues
- Examples: missing files, permission issues, fallback scenarios

### ERROR Level
```python
error("❌ Error message")
```
- **Always logged** unless level is set to CRITICAL
- Use for actual errors
- Examples: file access errors, parsing errors, UI errors

### CRITICAL Level
```python
critical("💥 Critical error - app may crash")
```
- **Always logged** regardless of level
- Use for critical errors that may crash the app
- Examples: missing settings, import errors, startup failures


## Usage

### 1. Import the Logger

```python
from utils.logger import debug, info, warning, error, critical
```

### 2. Replace Print Statements

**Before:**
```python
print(f"⚠️ Error parsing search terms: {e}")
print(f"📁 Simple Search: {query}")
print(f"✅ Found match: {file_name}")
```

**After:**
```python
error(f"⚠️ Error parsing search terms: {e}")
info(f"📁 Simple Search: {query}")
debug(f"✅ Found match: {file_name}")
```

## Log Level Configuration

### Current Setting (ERROR)
- Shows: ERROR, CRITICAL, log_error()
- Hides: DEBUG, INFO, WARNING
- Good for production use

### To Enable Debug Messages
Change in `settings/core_settings.py`:
```python
LOG_LEVEL = "DEBUG"  # Shows all messages
```

### To Show Only Critical Errors
```python
LOG_LEVEL = "CRITICAL"  # Shows only critical errors
```

## Migration Guide

### Step 1: Replace Critical Errors
```python
# Replace
print(f"❌ CRITICAL ERROR: Cannot import settings.core_settings")

# With
critical(f"❌ CRITICAL ERROR: Cannot import settings.core_settings")
```

### Step 2: Replace Debug Messages
```python
# Replace
print(f"🔍 Debug - UI_FILE_PATH from settings: {UI_FILE_PATH}")

# With
debug(f"🔍 Debug - UI_FILE_PATH from settings: {UI_FILE_PATH}")
```

### Step 3: Replace Warning Messages
```python
# Replace
print(f"⚠️ Error parsing search terms: {e}")

# With
warning(f"⚠️ Error parsing search terms: {e}")
```

### Step 4: Replace Info Messages
```python
# Replace
print(f"📁 Simple Search: {query}")

# With
info(f"📁 Simple Search: {query}")
```

## Benefits

1. **Configurable Logging** - Turn off debug messages in production
2. **Proper Log Levels** - Different levels for different types of messages
3. **File Logging** - All messages saved to log file
4. **Console Output** - Still prints to console for immediate feedback
5. **Error Resilience** - Won't crash if logging fails
6. **Easy Debugging** - Find bugs by checking log file
7. **Backward Compatibility** - `log_error()` works exactly like original
8. **Easy Configuration** - Change log file path in `core_settings.py`

## Example Implementation

```python
from utils.logger import debug, info, warning, error, critical

def search_function(query: str):
    try:
        info(f"📁 Starting search: {query}")
        
        # Your search logic here
        results = perform_search(query)
        
        debug(f"✅ Found {len(results)} results")
        return results
        
    except PermissionError as e:
        warning(f"⚠️ Permission denied: {e}")
        return []
        
    except Exception as e:
        error(f"❌ Search failed: {e}")
        critical(f"💥 Critical search error: {e}")
        return []
```

## Log File Format

```
[2024-01-15 14:30:25] [INFO] 📁 Starting search: piano
[2024-01-15 14:30:26] [DEBUG] ✅ Found 15 results
[2024-01-15 14:30:27] [WARNING] ⚠️ Permission denied: /protected/folder
[2024-01-15 14:30:27] [ERROR] ❌ Search failed: File not found
[2024-01-15 14:30:27] [CRITICAL] 💥 Critical search error: File not found
```

## Configuration Options

### **Easy Log File Customization:**

1. **Change log filename:**
   ```python
   LOG_FILE_NAME = "my_app_logs.log"
   ```

2. **Change app name (affects directory):**
   ```python
   APP_NAME = "MyCustomApp"
   ```

3. **Change log level:**
   ```python
   LOG_LEVEL = "INFO"  # Hides DEBUG messages
   ```

4. **Change log format:**
   ```python
   LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
   ```

This gives you **enhanced logging capabilities** with the ability to control what gets logged and where, while maintaining compatibility with the original `patchio_old.py` approach. 