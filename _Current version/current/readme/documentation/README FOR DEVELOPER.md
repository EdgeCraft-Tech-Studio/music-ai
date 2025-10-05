# PatchIO - Developer README

**Welcome to PatchIO!** This guide will help you get started as a new developer working on the indexing system.

## 🚀 Quick Start - First Time Setup

### 1. Prerequisites
- **Python 3.11+** (currently using 3.11.8)
- **PySide6** (currently using 6.9.1)
- **macOS** (primary development platform)

### 2. Install Dependencies
```bash
cd "_Current version/current"
pip3 install -r requirements.txt
```

### 3. Run the Application
```bash
python3 patchio_main.py
```

### 4. Verify Everything Works
- The app should start and show the main window
- Check the console for any import errors
- Look for the log file at: `~/Library/Application Support/PatchIO/patchIO_logs.log`

---

## 📁 **Library Folders Configuration**

### Where to Change Scan Locations

**Primary Configuration File:**
```
settings/core_settings.py
```

**Look for this section (lines 43-47):**
```python
DEFAULT_SEARCH_FOLDERS = [
    '/Volumes/Samsung 850 EVO',
    '/Users/shaked/Desktop/Samples', 
    '/Users/shaked/Music'
]
```

### How to Add/Remove Folders

1. **Edit `settings/core_settings.py`**
   ```python
   DEFAULT_SEARCH_FOLDERS = [
       '/path/to/your/sample/library',
       '/another/path/to/samples',
       '/Users/yourname/Music/Samples'
   ]
   ```

2. **Restart the Application**
   - The new folders will be automatically detected on startup
   - The indexing system will scan these folders

### User-Configurable Folders

Users can also modify folders through the UI, which are stored in:
```
~/Library/Application Support/PatchIO/user_settings.json
```

The `UserSettingsModel` class manages these user preferences and falls back to `DEFAULT_SEARCH_FOLDERS` if no user settings exist.

---

## 🔍 **Indexing System - Core Files**

### **Primary Indexing Files**

#### 1. **`utils/database/file_index_manager.py`** - Main Index Manager
- **Purpose**: Orchestrates the entire indexing process
- **Key Features**:
  - Professional optimizations for 1.2M+ files
  - Batch processing (1000 files per batch)
  - Real-time progress reporting with ETA
  - Memory-efficient streaming processing
- **Main Methods**:
  - `sync_index_with_filesystem()` - Full sync
  - `start_monitoring()` - Real-time file watching
  - `stop_monitoring()` - Stop file watching

#### 2. **`utils/database/database_indexer.py`** - Core Indexer
- **Purpose**: Handles the actual file scanning and database operations
- **Key Features**:
  - Recursive file system scanning
  - Vendor/library extraction
  - Automatic tagging with AI
  - Batch database operations
- **Main Methods**:
  - `index_files()` - Index files from folders
  - `update_file_metadata()` - Update existing files
  - `extract_vendor_library()` - Extract vendor info

#### 3. **`utils/database/startup_sync.py`** - Startup Synchronization
- **Purpose**: Syncs database with filesystem on app startup
- **Key Features**:
  - Detects new, modified, and deleted files
  - Efficient change detection
  - Progress reporting
- **Main Methods**:
  - `sync_on_startup()` - Full startup sync
  - `detect_changes()` - Find filesystem changes

#### 4. **`utils/database/file_watcher.py`** - Real-time Monitoring
- **Purpose**: Monitors filesystem changes in real-time
- **Key Features**:
  - File system event monitoring
  - Automatic re-indexing of changed files
  - Background processing
- **Main Methods**:
  - `start_watching()` - Begin monitoring
  - `stop_watching()` - Stop monitoring
  - `on_file_changed()` - Handle file changes

### **Supporting Indexing Files**

#### 5. **`utils/database/automatic_tagger.py`** - AI Tagging
- **Purpose**: Automatically generates tags for files using AI
- **Integration**: Used by `database_indexer.py` during indexing

#### 6. **`utils/database/knowledge_database.py`** - Knowledge Management
- **Purpose**: Manages vendor/library knowledge and extraction
- **Integration**: Used for vendor detection during indexing

#### 7. **`utils/database/vendor_maintenance.py`** - Vendor Management
- **Purpose**: AI-powered vendor finding and maintenance
- **Integration**: Used for vendor database updates

---

## 🏗️ **Indexing Architecture Overview**

### **Data Flow**
```
1. App Startup → startup_sync.py
2. File System Scan → file_index_manager.py
3. File Processing → database_indexer.py
4. Real-time Monitoring → file_watcher.py
5. Database Storage → SQLite database
```

### **Database Schema**
The main database table structure:
```sql
CREATE TABLE files (
    id INTEGER PRIMARY KEY,
    file_path TEXT UNIQUE,
    file_name TEXT,
    file_type TEXT,
    vendor TEXT,
    library TEXT,
    keywords TEXT,
    tags TEXT,
    file_size INTEGER,
    modified_time REAL,
    created_time REAL
);
```

### **Performance Optimizations**
- **Batch Processing**: 1000 files per batch
- **Pre-compiled Patterns**: 100x faster filtering
- **Memory Streaming**: Handles unlimited files
- **Progress Reporting**: Real-time ETA calculation

---

## 🛠️ **Development Workflow**

### **Making Changes to Indexing**

1. **Understand the Flow**
   - Read `PROFESSIONAL_OPTIMIZATIONS_SUMMARY.md` for performance details
   - Study `ARCHITECTURE_GUIDELINES.md` for MVC patterns

2. **Test Your Changes**
   ```bash
   # Run the app
   python3 patchio_main.py
   
   # Check logs
   tail -f ~/Library/Application\ Support/PatchIO/patchIO_logs.log
   ```

3. **Debug Indexing Issues**
   - Check the log file for errors
   - Use `LOG_LEVEL = "DEBUG"` in `settings/core_settings.py`
   - Monitor database changes with SQLite browser

### **Key Configuration Files**

- **`settings/core_settings.py`** - All configuration constants
- **`models/user_settings_model.py`** - User preferences
- **`utils/logger.py`** - Logging system

### **Database Files**
- **`patchio_index.db`** - Main file index database
- **`patchio_knowledge.db`** - Vendor/library knowledge database

---

## 📊 **Indexing Performance**

### **Current Capabilities**
- **File Limit**: 1.2M+ files (tested)
- **Scan Rate**: 1000+ files/second
- **Memory Usage**: <100MB for large collections
- **Database Operations**: Batch processing with error handling

### **Monitoring Performance**
```python
# Check indexing stats
from utils.database.file_index_manager import FileIndexManager

manager = FileIndexManager("patchio_index.db", your_folders)
results = manager.sync_index_with_filesystem(force_full_sync=True)
print(f"Scanned: {results['files_scanned']:,} files")
print(f"Rate: {results['scan_rate']:.0f} files/sec")
```

---

## 🐛 **Common Issues & Solutions**

### **Indexing Not Working**
1. Check folder paths in `settings/core_settings.py`
2. Verify folder permissions
3. Check log file for errors
4. Ensure database file is writable

### **Slow Indexing**
1. Reduce batch size in `file_index_manager.py`
2. Check for network drives (can be slow)
3. Exclude unnecessary file types

### **Database Errors**
1. Check for UNIQUE constraint violations
2. Verify database file permissions
3. Try deleting and recreating database

---

## 📚 **Additional Resources**

### **Documentation Files**
- `PROJECT_STRUCTURE.md` - Complete project organization
- `ARCHITECTURE_GUIDELINES.md` - MVC patterns and rules
- `STYLING_GUIDELINES.md` - UI styling guidelines
- `PROFESSIONAL_OPTIMIZATIONS_SUMMARY.md` - Performance details
- `PRODUCT_VISION_ROADMAP.md` - Future development plans

### **Build System**
- `build_scripts/build_modern.sh` - Build script
- `Patchio_modern.spec` - PyInstaller configuration
- `requirements.txt` - Python dependencies

### **Testing**
- Built application: `builds/dist/PatchIO.app`
- Test with large file collections
- Monitor memory usage during indexing

---

## 🎯 **Next Steps for Indexing Development**

1. **Study the Code**: Start with `file_index_manager.py` and `database_indexer.py`
2. **Run Tests**: Test with your own sample libraries
3. **Monitor Performance**: Use the built-in progress reporting
4. **Check Logs**: Enable DEBUG logging to see detailed operations
5. **Experiment**: Try different batch sizes and configurations

---

## 💡 **Pro Tips**

- **Use the log system**: All indexing operations are logged
- **Monitor memory**: The system is optimized for large collections
- **Batch operations**: Changes are processed in batches for efficiency
- **Real-time updates**: File watching keeps the index current
- **AI integration**: Automatic tagging enhances search capabilities

---

**Happy coding!** 🚀

For questions or issues, check the log file first, then refer to the detailed documentation in the `readme/` folder.
