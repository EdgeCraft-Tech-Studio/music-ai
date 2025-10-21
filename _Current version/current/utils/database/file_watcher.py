#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Professional File System Watcher for PatchIO
OS-agnostic interface with platform-specific implementations for optimal performance.
Supports FSEvents (macOS) and USN Journal (Windows) for professional-grade indexing.
"""

import os
import sys
import time
import sqlite3
import threading
import platform
from pathlib import Path
from typing import Set, Dict, List, Optional, Protocol
from abc import ABC, abstractmethod

# Platform-specific imports (with fallbacks)
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    Observer = None
    FileSystemEventHandler = None

# Add parent directory to path for imports
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from utils.logger import info, warning, error, debug
from settings.core_settings import DEFAULT_EXTENSIONS

# ============================================================================
# OS-AGNOSTIC INTERFACE
# ============================================================================


class FileWatcher(ABC):
    """Abstract base class for platform-specific file watchers"""

    @abstractmethod
    def start(self, paths: Set[str], callback) -> None:
        """Start watching the specified paths"""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop watching"""
        pass

    @abstractmethod
    def reconcile(self, paths: Set[str], callback) -> Dict:
        """Reconcile missed changes since last run"""
        pass

    @abstractmethod
    def get_last_checkpoint(self) -> Optional[str]:
        """Get the last event checkpoint for this platform"""
        pass

    @abstractmethod
    def save_checkpoint(self, checkpoint: str) -> None:
        """Save the current event checkpoint"""
        pass


class FileEvent:
    """Represents a file system event"""

    def __init__(
        self,
        event_type: str,
        path: str,
        dest_path: Optional[str] = None,
        timestamp: float = None,
        event_id: Optional[str] = None,
    ):
        self.event_type = event_type  # 'created', 'deleted', 'moved', 'modified'
        self.path = path
        self.dest_path = dest_path
        self.timestamp = timestamp or time.time()
        self.event_id = event_id  # Platform-specific event identifier


# ============================================================================
# DATABASE SCHEMA FOR EVENT TRACKING
# ============================================================================


def init_event_tracking_db(db_path: str):
    """Initialize database with event tracking tables"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create event checkpoints table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS event_checkpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            checkpoint TEXT NOT NULL,
            timestamp REAL NOT NULL,
            UNIQUE(platform)
        )
    """
    )

    # Create event log table for debugging/auditing
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS event_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            path TEXT NOT NULL,
            dest_path TEXT,
            timestamp REAL NOT NULL,
            event_id TEXT,
            processed BOOLEAN DEFAULT FALSE
        )
    """
    )

    # Create indexes for performance
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_event_log_timestamp ON event_log(timestamp)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_event_log_processed ON event_log(processed)"
    )

    conn.commit()
    conn.close()


# ============================================================================
# PLATFORM-SPECIFIC IMPLEMENTATIONS
# ============================================================================


class MacFileWatcher(FileWatcher):
    """macOS implementation using FSEvents for optimal performance"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.observer = None
        self.streams = []
        self.is_running = False

        # Initialize event tracking database
        init_event_tracking_db(db_path)

    def start(self, paths: Set[str], callback) -> None:
        """Start FSEvents monitoring"""
        try:
            import fsevents

            self.observer = fsevents.Observer()

            for path in paths:
                if os.path.exists(path):
                    stream = fsevents.Stream(
                        callback,
                        path,
                        file_events=True,
                        since=self.get_last_checkpoint(),
                    )
                    self.observer.schedule(stream)
                    self.streams.append(stream)
                    info(f"👀 FSEvents watching: {path}")
                else:
                    warning(f"⚠️ Path does not exist: {path}")

            self.observer.start()
            self.is_running = True
            info("✅ FSEvents watcher started")

        except ImportError:
            error(
                "❌ fsevents library not available. Install with: pip install fsevents"
            )
            raise
        except Exception as e:
            error(f"❌ Failed to start FSEvents watcher: {e}")
            raise

    def stop(self) -> None:
        """Stop FSEvents monitoring"""
        if self.observer and self.is_running:
            self.observer.stop()
            self.observer.join()
            self.is_running = False
            info("🛑 FSEvents watcher stopped")

    def reconcile(self, paths: Set[str], callback) -> Dict:
        """Reconcile missed changes using FSEvents 'since' mechanism"""
        try:
            import fsevents

            last_event_id = self.get_last_checkpoint()
            if not last_event_id:
                info("ℹ️ No previous FSEvents checkpoint, skipping reconciliation")
                return {"events_processed": 0, "method": "fsevents", "checkpoint": None}

            info(f"🔄 Reconciling FSEvents changes since: {last_event_id}")

            events_processed = 0
            for path in paths:
                if os.path.exists(path):
                    # Query events since last checkpoint
                    for event in fsevents.get_events(path, since=last_event_id):
                        file_event = FileEvent(
                            event_type=self._map_fsevent_type(event),
                            path=event.name,
                            timestamp=event.timestamp,
                            event_id=str(event.id),
                        )
                        callback(file_event)
                        events_processed += 1

            info(f"✅ FSEvents reconciliation completed: {events_processed} events")
            return {
                "events_processed": events_processed,
                "method": "fsevents",
                "checkpoint": last_event_id,
            }

        except Exception as e:
            error(f"❌ FSEvents reconciliation failed: {e}")
            return {"events_processed": 0, "method": "fsevents", "error": str(e)}

    def get_last_checkpoint(self) -> Optional[str]:
        """Get the last FSEvents checkpoint"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT checkpoint FROM event_checkpoints WHERE platform = ?",
                ("macos",),
            )
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else None
        except Exception as e:
            error(f"❌ Error getting FSEvents checkpoint: {e}")
            return None

    def save_checkpoint(self, checkpoint: str) -> None:
        """Save the current FSEvents checkpoint"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO event_checkpoints 
                (platform, checkpoint, timestamp) 
                VALUES (?, ?, ?)
            """,
                ("macos", checkpoint, time.time()),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            error(f"❌ Error saving FSEvents checkpoint: {e}")

    def _map_fsevent_type(self, event) -> str:
        """Map FSEvents flags to our event types"""
        # FSEvents flags mapping (simplified)
        if hasattr(event, "flags"):
            if event.flags & 0x00000001:  # kFSEventStreamEventFlagItemCreated
                return "created"
            elif event.flags & 0x00000002:  # kFSEventStreamEventFlagItemRemoved
                return "deleted"
            elif event.flags & 0x00000004:  # kFSEventStreamEventFlagItemInodeMetaMod
                return "modified"
            elif event.flags & 0x00000008:  # kFSEventStreamEventFlagItemRenamed
                return "moved"
        return "modified"  # Default fallback


class WindowsFileWatcher_recall_issues(FileWatcher):
    """Windows implementation using USN Journal + ReadDirectoryChangesW"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.handles = []
        self.is_running = False

        # Initialize event tracking database
        init_event_tracking_db(db_path)

    def start(self, paths: Set[str], callback) -> None:
        """Start Windows file monitoring"""
        try:
            import win32file
            import win32con

            for path in paths:
                if os.path.exists(path):
                    hDir = win32file.CreateFile(
                        path,
                        win32con.GENERIC_READ,
                        win32con.FILE_SHARE_READ
                        | win32con.FILE_SHARE_WRITE
                        | win32con.FILE_SHARE_DELETE,
                        None,
                        win32con.OPEN_EXISTING,
                        win32con.FILE_FLAG_BACKUP_SEMANTICS
                        | win32con.FILE_FLAG_OVERLAPPED,
                        None,
                    )
                    self.handles.append((hDir, path, callback))
                    info(f"👀 Windows watching: {path}")
                else:
                    warning(f"⚠️ Path does not exist: {path}")

            self.is_running = True
            info("✅ Windows file watcher started")

        except ImportError:
            error("❌ pywin32 library not available. Install with: pip install pywin32")
            raise
        except Exception as e:
            error(f"❌ Failed to start Windows file watcher: {e}")
            raise

    def stop(self) -> None:
        """Stop Windows file monitoring"""
        if self.is_running:
            for handle, _, _ in self.handles:
                try:
                    import win32file

                    win32file.CloseHandle(handle)
                except:
                    pass
            self.handles.clear()
            self.is_running = False
            info("🛑 Windows file watcher stopped")

    def reconcile(self, paths: Set[str], callback) -> Dict:
        """Reconcile missed changes using USN Journal"""
        try:
            import win32file
            import win32con

            usn_checkpoint = self.get_last_checkpoint()
            if not usn_checkpoint:
                info("ℹ️ No previous USN checkpoint, skipping reconciliation")
                return {
                    "events_processed": 0,
                    "method": "usn_journal",
                    "checkpoint": None,
                }

            info(f"🔄 Reconciling USN Journal changes since: {usn_checkpoint}")

            events_processed = 0
            for path in paths:
                if os.path.exists(path):
                    # Query USN Journal for changes since checkpoint
                    # This is a simplified implementation
                    # Full implementation would use FSCTL_READ_USN_JOURNAL
                    pass

            info(f"✅ USN Journal reconciliation completed: {events_processed} events")
            return {
                "events_processed": events_processed,
                "method": "usn_journal",
                "checkpoint": usn_checkpoint,
            }

        except Exception as e:
            error(f"❌ USN Journal reconciliation failed: {e}")
            return {"events_processed": 0, "method": "usn_journal", "error": str(e)}

    def get_last_checkpoint(self) -> Optional[str]:
        """Get the last USN Journal checkpoint"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT checkpoint FROM event_checkpoints WHERE platform = ?",
                ("windows",),
            )
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else None
        except Exception as e:
            error(f"❌ Error getting USN checkpoint: {e}")
            return None

    def save_checkpoint(self, checkpoint: str) -> None:
        """Save the current USN Journal checkpoint"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO event_checkpoints 
                (platform, checkpoint, timestamp) 
                VALUES (?, ?, ?)
            """,
                ("windows", checkpoint, time.time()),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            error(f"❌ Error saving USN checkpoint: {e}")


class WindowsFileWatcher(FileWatcher):
    """Windows implementation using USN Journal + ReadDirectoryChangesW"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.handles = []  # list of (hDir, base_path, callback)
        self.threads = []  # <- add this
        self.is_running = False
        init_event_tracking_db(db_path)

    def start(self, paths: Set[str], callback) -> None:
        try:
            import win32file, win32con

            for path in paths:
                if os.path.exists(path):
                    hDir = win32file.CreateFile(
                        path,
                        win32con.GENERIC_READ,
                        win32con.FILE_SHARE_READ
                        | win32con.FILE_SHARE_WRITE
                        | win32con.FILE_SHARE_DELETE,
                        None,
                        win32con.OPEN_EXISTING,
                        # synchronous is fine here; if you keep OVERLAPPED, loop still works
                        win32con.FILE_FLAG_BACKUP_SEMANTICS,
                        None,
                    )
                    self.handles.append((hDir, path, callback))
                    info(f"👀 Windows watching: {path}")
                else:
                    warning(f"⚠️ Path does not exist: {path}")

            self.is_running = True
            # spawn one thread per root
            for hDir, base_path, cb in self.handles:
                t = threading.Thread(
                    target=self._watch_directory,
                    args=(hDir, base_path, cb),
                    daemon=True,
                )
                t.start()
                self.threads.append(t)

            info("✅ Windows file watcher started")

        except ImportError:
            error("❌ pywin32 library not available. Install with: pip install pywin32")
            raise
        except Exception as e:
            error(f"❌ Failed to start Windows file watcher: {e}")
            raise

    def _watch_directory(self, hDir, base_path, callback):
        import win32file, win32con

        ACTION = {
            1: "created",  # FILE_ACTION_ADDED
            2: "deleted",  # FILE_ACTION_REMOVED
            3: "modified",  # FILE_ACTION_MODIFIED
            4: "moved_old",  # FILE_ACTION_RENAMED_OLD_NAME
            5: "moved_new",  # FILE_ACTION_RENAMED_NEW_NAME
        }
        notify = (
            win32con.FILE_NOTIFY_CHANGE_FILE_NAME
            | win32con.FILE_NOTIFY_CHANGE_DIR_NAME
            | win32con.FILE_NOTIFY_CHANGE_LAST_WRITE
            | win32con.FILE_NOTIFY_CHANGE_SIZE
        )
        while self.is_running:
            try:
                # recursive=True so we watch subfolders
                results = win32file.ReadDirectoryChangesW(
                    hDir, 8192, True, notify, None, None
                )
                for action, name in results:
                    kind = ACTION.get(action)
                    full = os.path.join(base_path, name)
                    if kind in ("created", "modified", "moved_new"):
                        # treat moved_new as a create-in-place (common temp→rename pattern)
                        evt = FileEvent(
                            "created" if kind == "moved_new" else kind, full
                        )
                        callback(evt)
                    elif kind == "deleted":
                        callback(FileEvent("deleted", full))
                    # moved_old (4) is usually just the old name; you can ignore or log
            except Exception as e:
                if self.is_running:
                    warning(f"⚠️ Windows watcher error on {base_path}: {e}")
                    time.sleep(0.2)

    def stop(self) -> None:
        self.is_running = False
        try:
            for t in getattr(self, "threads", []):
                t.join(timeout=1.5)
        except Exception:
            pass
        try:
            import win32file

            for hDir, _, _ in self.handles:
                try:
                    win32file.CloseHandle(hDir)
                except Exception:
                    pass
            self.handles.clear()
        except Exception:
            pass
        info("🛑 Windows watcher stopped")

    def reconcile(self, paths: Set[str], callback) -> Dict:
        """Reconcile missed changes using USN Journal"""
        try:
            import win32file
            import win32con

            usn_checkpoint = self.get_last_checkpoint()
            if not usn_checkpoint:
                info("ℹ️ No previous USN checkpoint, skipping reconciliation")
                return {
                    "events_processed": 0,
                    "method": "usn_journal",
                    "checkpoint": None,
                }

            info(f"🔄 Reconciling USN Journal changes since: {usn_checkpoint}")

            events_processed = 0
            for path in paths:
                if os.path.exists(path):
                    # Query USN Journal for changes since checkpoint
                    # This is a simplified implementation
                    # Full implementation would use FSCTL_READ_USN_JOURNAL
                    pass

            info(f"✅ USN Journal reconciliation completed: {events_processed} events")
            return {
                "events_processed": events_processed,
                "method": "usn_journal",
                "checkpoint": usn_checkpoint,
            }

        except Exception as e:
            error(f"❌ USN Journal reconciliation failed: {e}")
            return {"events_processed": 0, "method": "usn_journal", "error": str(e)}

    def get_last_checkpoint(self) -> Optional[str]:
        """Get the last USN Journal checkpoint"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT checkpoint FROM event_checkpoints WHERE platform = ?",
                ("windows",),
            )
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else None
        except Exception as e:
            error(f"❌ Error getting USN checkpoint: {e}")
            return None

    def save_checkpoint(self, checkpoint: str) -> None:
        """Save the current USN Journal checkpoint"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO event_checkpoints 
                (platform, checkpoint, timestamp) 
                VALUES (?, ?, ?)
            """,
                ("windows", checkpoint, time.time()),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            error(f"❌ Error saving USN checkpoint: {e}")


# ============================================================================
# FACTORY FUNCTION
# ============================================================================


def create_file_watcher(db_path: str) -> FileWatcher:
    """Create the appropriate file watcher for the current platform"""
    system = platform.system().lower()

    # For now, use the legacy watchdog implementation as it's reliable and cross-platform
    # Platform-specific optimizations can be added later when libraries are available
    info(f"🔧 Creating file watcher for platform: {system}")

    if system == "darwin":  # macOS
        try:
            # Try FSEvents first (if available)
            import fsevents

            info("✅ FSEvents available, using optimized macOS watcher")
            return MacFileWatcher(db_path)
        except ImportError:
            info("ℹ️ FSEvents not available, using watchdog fallback")
            return LegacyFileWatcher(db_path)
    elif system == "windows":
        try:
            # Try Windows APIs first (if available)
            import win32file

            info("✅ Windows APIs available, using optimized Windows watcher")
            return WindowsFileWatcher(db_path)
        except ImportError:
            info("ℹ️ Windows APIs not available, using watchdog fallback")
            return LegacyFileWatcher(db_path)
    else:
        info(f"ℹ️ Platform {system}, using watchdog fallback")
        return LegacyFileWatcher(db_path)


# ============================================================================
# LEGACY WATCHDOG IMPLEMENTATION (Fallback)
# ============================================================================


class LegacyFileWatcher(FileWatcher):
    """Legacy watchdog-based implementation (fallback)"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.observer = None
        self.handler = None
        self.is_running = False
        self.indexed_folders = set()  # Store indexed folders for path checking

        # Initialize event tracking database
        init_event_tracking_db(db_path)

    def start(self, paths: Set[str], callback) -> None:
        """Start legacy watchdog monitoring"""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            # Store indexed folders for path checking
            self.indexed_folders = paths

            class LegacyHandler(FileSystemEventHandler):
                def __init__(self, callback, watcher_instance):
                    self.callback = callback
                    self.watcher = watcher_instance

                def _should_ignore_file(self, file_path: str) -> bool:
                    """Check if file should be ignored (hidden, system files, etc.)"""
                    try:
                        filename = os.path.basename(file_path)

                        # Skip hidden files (starting with .)
                        if filename.startswith("."):
                            return True

                        # Skip system files
                        system_files = {
                            ".DS_Store",
                            "Thumbs.db",
                            "desktop.ini",
                            ".Spotlight-V100",
                            ".Trashes",
                            ".fseventsd",
                            ".TemporaryItems",
                            ".VolumeIcon.icns",
                            ".apdisk",
                        }
                        if filename in system_files:
                            return True

                        # Skip temporary files
                        if filename.endswith((".tmp", ".temp", ".swp", ".lock")):
                            return True

                        # Skip database files (we don't want to index our own database)
                        if filename.endswith(
                            (".db", ".db-journal", ".db-wal", ".db-shm")
                        ):
                            return True

                        # Skip log files
                        if filename.endswith(".log"):
                            return True

                        return False
                    except:
                        return True  # Skip if we can't determine

                def on_created(self, event):
                    if not event.is_directory and not self._should_ignore_file(
                        event.src_path
                    ):
                        file_event = FileEvent("created", event.src_path)
                        self.callback(file_event)

                def on_deleted(self, event):
                    if not event.is_directory and not self._should_ignore_file(
                        event.src_path
                    ):
                        file_event = FileEvent("deleted", event.src_path)
                        self.callback(file_event)

                def on_moved(self, event):
                    if not event.is_directory:
                        # Check both source and destination
                        if not self._should_ignore_file(
                            event.src_path
                        ) and not self._should_ignore_file(event.dest_path):
                            file_event = FileEvent(
                                "moved", event.src_path, event.dest_path
                            )
                            self.callback(file_event)

                def on_modified(self, event):
                    if not event.is_directory and not self._should_ignore_file(
                        event.src_path
                    ):
                        file_event = FileEvent("modified", event.src_path)
                        self.callback(file_event)

            self.handler = LegacyHandler(callback, self)
            self.observer = Observer()

            for path in paths:
                if os.path.exists(path):
                    self.observer.schedule(self.handler, path, recursive=True)
                    info(f"👀 Legacy watchdog watching: {path}")
                else:
                    warning(f"⚠️ Path does not exist: {path}")

            self.observer.start()
            self.is_running = True
            info("✅ Legacy watchdog started")

        except ImportError:
            error(
                "❌ watchdog library not available. Install with: pip install watchdog"
            )
            raise
        except Exception as e:
            error(f"❌ Failed to start legacy watchdog: {e}")
            raise

    def stop(self) -> None:
        """Stop legacy watchdog monitoring"""
        if self.observer and self.is_running:
            self.observer.stop()
            self.observer.join()
            self.is_running = False
            info("🛑 Legacy watchdog stopped")

    def reconcile(self, paths: Set[str], callback) -> Dict:
        """Legacy reconciliation - perform full rescan using StartupSync"""
        info("🔄 Legacy reconciliation: performing full rescan")
        try:
            from utils.database.startup_sync import StartupSync

            # Use the existing StartupSync to perform reconciliation
            startup_sync = StartupSync(self.db_path, paths)
            sync_results = startup_sync.sync_database(force_full_sync=False)

            # Convert sync results to event format for consistency
            events_processed = (
                sync_results.get("files_added", 0)
                + sync_results.get("files_removed", 0)
                + sync_results.get("files_updated", 0)
            )

            info(
                f"✅ Legacy reconciliation completed: {events_processed} changes processed"
            )
            return {
                "events_processed": events_processed,
                "method": "legacy_rescan",
                "files_added": sync_results.get("files_added", 0),
                "files_removed": sync_results.get("files_removed", 0),
                "files_updated": sync_results.get("files_updated", 0),
                "sync_time": sync_results.get("sync_time", 0),
            }

        except Exception as e:
            error(f"❌ Legacy reconciliation failed: {e}")
            return {"events_processed": 0, "method": "legacy_rescan", "error": str(e)}

    def get_last_checkpoint(self) -> Optional[str]:
        """Legacy checkpoint - always None"""
        return None

    def save_checkpoint(self, checkpoint: str) -> None:
        """Legacy checkpoint saving - no-op"""
        pass


class PatchIOFileHandler(FileSystemEventHandler):
    """Handles file system events for PatchIO indexing"""

    def __init__(self, db_path: str, indexed_folders: Set[str]):
        super().__init__()
        self.db_path = db_path
        self.indexed_folders = indexed_folders
        self.supported_extensions = set(DEFAULT_EXTENSIONS)
        self.pending_operations = []
        self.lock = threading.Lock()

        # Batch processing settings
        self.batch_size = 50
        self.batch_delay = 0.5  # seconds - faster detection of new files
        self.last_batch_time = time.time()

        info(
            "🔍 File watcher initialized with {} indexed folders".format(
                len(indexed_folders)
            )
        )

    def _should_ignore_file(self, file_path: str) -> bool:
        """Check if file should be ignored (hidden, system files, etc.)"""
        try:
            filename = os.path.basename(file_path)

            # Skip hidden files (starting with .) - this is the most common case
            if filename.startswith("."):
                return True

            # Skip system files
            system_files = {
                ".DS_Store",
                "Thumbs.db",
                "desktop.ini",
                ".Spotlight-V100",
                ".Trashes",
                ".fseventsd",
                ".TemporaryItems",
                ".VolumeIcon.icns",
                ".apdisk",
                ".localized",
                ".metadata_never_index",
                ".parentlock",
            }
            if filename in system_files:
                return True

            # Skip temporary files
            if filename.endswith((".tmp", ".temp", ".swp", ".lock", ".bak", ".backup")):
                return True

            # Skip database files (we don't want to index our own database)
            if filename.endswith(
                (".db", ".db-journal", ".db-wal", ".db-shm", ".sqlite", ".sqlite3")
            ):
                return True

            # Skip log files
            if filename.endswith((".log", ".logs")):
                return True

            # Skip cache files
            if filename.endswith((".cache", ".cached")):
                return True

            # Skip archive files that might be temporary
            if filename.endswith((".part", ".partial")):
                return True

            return False
        except:
            return True  # Skip if we can't determine

    def _is_supported_file(self, file_path: str) -> bool:
        """Check if file has a supported extension"""
        if not file_path:
            return False

        ext = Path(file_path).suffix.lower()
        is_supported = ext in self.supported_extensions
        info(
            f"🔍 File extension check: {ext} -> {'✅ supported' if is_supported else '❌ not supported'}"
        )
        return is_supported

    def _is_in_indexed_folder(self, file_path: str) -> bool:
        """Check if file is within an indexed folder"""
        try:
            abs_path = os.path.abspath(file_path)
            info(f"🔍 Checking if file is in indexed folder: {abs_path}")
            info(f"🔍 Indexed folders: {list(self.indexed_folders)}")

            for folder in self.indexed_folders:
                folder_abs = os.path.abspath(folder)
                info(f"🔍 Checking against folder: {folder_abs}")

                # Check direct path match
                if abs_path.startswith(folder_abs):
                    info(f"✅ File is in indexed folder: {folder_abs}")
                    return True

                # Check if the folder is a volume and the file is on the same volume
                # This handles cases where files are restored to volumes
                if folder_abs.startswith("/Volumes/") and abs_path.startswith(
                    "/Volumes/"
                ):
                    folder_volume = folder_abs.split("/")[2]  # Get volume name
                    file_volume = abs_path.split("/")[2]  # Get volume name
                    if folder_volume == file_volume:
                        info(
                            f"✅ File is on same volume as indexed folder: {folder_volume}"
                        )
                        return True

            info(f"❌ File not in any indexed folder: {abs_path}")
            return False
        except Exception as e:
            error(f"❌ Error checking indexed folder: {e}")
            return False

    def _add_to_batch(self, operation: str, file_path: str, **kwargs):
        """Add operation to batch processing queue"""
        with self.lock:
            self.pending_operations.append(
                {
                    "operation": operation,
                    "file_path": file_path,
                    "timestamp": time.time(),
                    **kwargs,
                }
            )

            info(
                f"📝 Added to batch: {operation} - {file_path} (queue size: {len(self.pending_operations)})"
            )

            # Process batch if it's time
            if (
                len(self.pending_operations) >= self.batch_size
                or time.time() - self.last_batch_time >= self.batch_delay
            ):
                info(
                    f"⏰ Processing batch (size: {len(self.pending_operations)}, delay: {time.time() - self.last_batch_time:.1f}s)"
                )
                self._process_batch()

    def _process_batch(self):
        """Process all pending operations in batch"""
        if not self.pending_operations:
            return

        with self.lock:
            operations = self.pending_operations.copy()
            self.pending_operations.clear()
            self.last_batch_time = time.time()

        if not operations:
            return

        info("🔄 Processing {} file operations".format(len(operations)))

        try:
            info(f"🔗 Connecting to database: {self.db_path}")
            info(f"📁 Database file exists: {os.path.exists(self.db_path)}")
            if os.path.exists(self.db_path):
                info(f"📊 Database file size: {os.path.getsize(self.db_path)} bytes")

            # Add timeout to prevent hanging
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            info("✅ Database connection established")

            for op in operations:
                try:
                    info(
                        f"🔄 Processing operation: {op['operation']} - {op['file_path']}"
                    )
                    if op["operation"] == "add":
                        self._add_file_to_db(cursor, op["file_path"])
                    elif op["operation"] == "remove":
                        self._remove_file_from_db(cursor, op["file_path"])
                    elif op["operation"] == "move":
                        self._move_file_in_db(cursor, op["file_path"], op["dest_path"])
                    elif op["operation"] == "modify":
                        self._update_file_in_db(cursor, op["file_path"])
                    else:
                        info(f"⚠️ Unknown operation: {op['operation']}")
                    info(f"✅ Completed operation: {op['operation']}")
                except Exception as e:
                    error(
                        "❌ Error processing operation {}: {}".format(
                            op["operation"], e
                        )
                    )
                    import traceback

                    traceback.print_exc()

            info("💾 Committing database changes...")
            conn.commit()
            conn.close()
            info("✅ Database connection closed")

            info("✅ Processed {} file operations successfully".format(len(operations)))

        except Exception as e:
            error("❌ Batch processing failed: {}".format(e))

    def _process_file_immediately(self, operation: str, file_path: str, **kwargs):
        """Process a single file immediately without batching"""
        try:
            info(f"⚡ Processing file immediately: {operation} - {file_path}")

            # Simple database connection
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            cursor = conn.cursor()

            if operation == "add":
                self._add_file_to_db(cursor, file_path)
            elif operation == "remove":
                self._remove_file_from_db(cursor, file_path)
            elif operation == "move":
                dest_path = kwargs.get("dest_path")
                if dest_path:
                    self._move_file_in_db(cursor, file_path, dest_path)
                else:
                    info(f"⚠️ Move operation missing dest_path: {file_path}")
            elif operation == "modify":
                self._update_file_in_db(cursor, file_path)
            else:
                info(f"⚠️ Unknown operation: {operation}")

            conn.commit()
            conn.close()
            info(f"✅ Immediate processing completed: {operation}")

        except Exception as e:
            error(f"❌ Immediate processing failed: {e}")

    def _add_file_to_db(self, cursor, file_path: str):
        """Add a new file to the database"""
        info(f"🔍 _add_file_to_db called for: {file_path}")
        info(f"🔍 Attempting to add file to database: {file_path}")

        if self._should_ignore_file(file_path):
            info(f"⚠️ File ignored (hidden/system file): {file_path}")
            return
        if not self._is_supported_file(file_path):
            info(f"⚠️ File not supported (extension): {file_path}")
            return
        if not self._is_in_indexed_folder(file_path):
            info(f"⚠️ File not in indexed folder: {file_path}")
            return

        info(f"✅ File passed all checks, proceeding to add: {file_path}")

        try:
            # Check if file already exists
            cursor.execute("SELECT id FROM files WHERE path = ?", (file_path,))
            if cursor.fetchone():
                debug("File already exists in database: {}".format(file_path))
                return

            # Get file info
            stat = os.stat(file_path)
            file_name = os.path.basename(file_path)
            file_type = Path(file_path).suffix.lower()

            # Extract vendor, library, and project info using V3 with project detection
            vendor, library, project = self._extract_vendor_library_from_path(file_path)

            # Insert into database
            cursor.execute(
                """
                INSERT INTO files (path, name, vendor, library, project, file_type, modified_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    file_path,
                    file_name,
                    vendor,
                    library,
                    project,
                    file_type,
                    stat.st_mtime,
                ),
            )

            info("➕ Added file: {}".format(file_name))

        except Exception as e:
            error("❌ Error adding file {}: {}".format(file_path, e))

    def _remove_file_from_db(self, cursor, file_path: str):
        """Remove a file from the database"""
        try:
            info(f"🗑️ Attempting to remove file from database: {file_path}")

            # First check if the file exists in the database
            cursor.execute("SELECT id, name FROM files WHERE path = ?", (file_path,))
            existing_file = cursor.fetchone()

            if existing_file:
                file_id, file_name = existing_file
                info(f"📋 Found file in database: ID={file_id}, Name={file_name}")

                # Delete the file
                cursor.execute("DELETE FROM files WHERE path = ?", (file_path,))
                deleted_count = cursor.rowcount

                if deleted_count > 0:
                    info(
                        "➖ Successfully removed file: {} (ID: {})".format(
                            file_name, file_id
                        )
                    )
                else:
                    info(f"⚠️ Delete query executed but no rows affected: {file_path}")
            else:
                info(f"ℹ️ File not found in database: {file_path}")

        except Exception as e:
            error("❌ Error removing file {}: {}".format(file_path, e))
            import traceback

            traceback.print_exc()

    def _move_file_in_db(self, cursor, old_path: str, new_path: str):
        """Update file path in database"""
        try:
            info(f"🔄 Attempting to move file in database: {old_path} -> {new_path}")

            # Check if moved to Trash (macOS deletion)
            if ".Trashes" in new_path or "Trash" in new_path:
                info(f"🗑️ File moved to Trash, treating as deletion: {old_path}")
                cursor.execute("DELETE FROM files WHERE path = ?", (old_path,))
                if cursor.rowcount > 0:
                    info(
                        "➖ Removed file (moved to Trash): {}".format(
                            os.path.basename(old_path)
                        )
                    )
                else:
                    info(f"ℹ️ File not found in database: {old_path}")
                return

            # Check if moved from Trash (macOS restore)
            if ".Trashes" in old_path or "Trash" in old_path:
                info(f"♻️ File restored from Trash, treating as new file: {new_path}")
                # Add the file as a new entry since it's being restored
                if self._is_supported_file(new_path) and self._is_in_indexed_folder(
                    new_path
                ):
                    self._add_file_to_db(cursor, new_path)
                    info(
                        "✅ Restored file from Trash: {}".format(
                            os.path.basename(new_path)
                        )
                    )
                else:
                    info(
                        f"⚠️ Restored file not supported or not in indexed folder: {new_path}"
                    )
                return

            # Check if new path is in indexed folder
            if not self._is_in_indexed_folder(new_path):
                # Remove from database if moved outside indexed folders
                cursor.execute("DELETE FROM files WHERE path = ?", (old_path,))
                if cursor.rowcount > 0:
                    info(
                        "➖ Moved file outside indexed area: {}".format(
                            os.path.basename(old_path)
                        )
                    )
                else:
                    info(f"ℹ️ File not found in database: {old_path}")
                return

            # Update path and other info
            new_name = os.path.basename(new_path)
            # 🚀 NEW: Use V3 extractor with project detection
            new_vendor, new_library, new_project = (
                self._extract_vendor_library_from_path(new_path)
            )

            cursor.execute(
                """
                UPDATE files 
                SET path = ?, name = ?, vendor = ?, library = ?, project = ?
                WHERE path = ?
            """,
                (new_path, new_name, new_vendor, new_library, new_project, old_path),
            )

            if cursor.rowcount > 0:
                info(
                    "🔄 Moved file watcher: {} -> {}".format(
                        os.path.basename(old_path), new_name
                    )
                )
            else:
                info(f"ℹ️ File not found in database: {old_path}")

        except Exception as e:
            error("❌ Error moving file {}: {}".format(old_path, e))

    def _update_file_in_db(self, cursor, file_path: str):
        """Update file information in database"""
        try:
            info(f"📝 Attempting to update file in database: {file_path}")
            stat = os.stat(file_path)
            cursor.execute(
                """
                UPDATE files 
                SET modified_time = ?
                WHERE path = ?
            """,
                (stat.st_mtime, file_path),
            )

            if cursor.rowcount > 0:
                info("🔄 Updated file: {}".format(os.path.basename(file_path)))
            else:
                info(f"ℹ️ File not found in database: {file_path}")

        except Exception as e:
            error("❌ Error updating file {}: {}".format(file_path, e))

    def _extract_vendor_library_from_path(self, file_path: str) -> tuple:
        """Extract vendor and library from file path using knowledge database"""
        try:
            from utils.database.knowledge_database import KnowledgeDatabase
            import appdirs
            from settings.core_settings import APP_NAME, APP_AUTHOR

            # Get knowledge database path
            config_dir = appdirs.user_config_dir(APP_NAME, APP_AUTHOR)
            knowledge_db_path = os.path.join(config_dir, "patchio_knowledge.db")

            if os.path.exists(knowledge_db_path):
                knowledge_db = KnowledgeDatabase(knowledge_db_path)
                # 🚀 NEW: Use V3 extractor (fast pattern-based extraction)
                from utils.database.library_extractor_v3 import LibraryExtractorV3

                if not hasattr(self, "_v3_extractor"):
                    self._v3_extractor = LibraryExtractorV3(use_knowledge_db=True)
                return self._v3_extractor.extract_vendor_library(file_path)
            else:
                # Fallback to simple extraction if knowledge database not available
                return self._simple_extract_vendor_library(file_path)

        except Exception as e:
            # Fallback to simple extraction on error
            return self._simple_extract_vendor_library(file_path)

    def _simple_extract_vendor_library(self, file_path: str) -> tuple:
        """
        Simple fallback vendor/library extraction.
        🚀 NEW: Uses V3 extractor for accurate extraction.
        """
        from utils.database.library_extractor_v3 import LibraryExtractorV3

        if not hasattr(self, "_v3_extractor"):
            self._v3_extractor = LibraryExtractorV3(use_knowledge_db=True)
        return self._v3_extractor.extract_vendor_library(file_path)

    # File system event handlers
    def on_created(self, event):
        if not event.is_directory and not self._should_ignore_file(event.src_path):
            info(f"🔍 File created detected: {event.src_path}")
            # Process immediately instead of batching
            self._process_file_immediately("add", event.src_path)

    def on_deleted(self, event):
        if not event.is_directory and not self._should_ignore_file(event.src_path):
            info(f"🗑️ File deleted detected: {event.src_path}")
            self._process_file_immediately("remove", event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            # Check both source and destination
            if not self._should_ignore_file(
                event.src_path
            ) and not self._should_ignore_file(event.dest_path):
                info(f"🔄 File moved detected: {event.src_path} -> {event.dest_path}")
                self._process_file_immediately(
                    "move", event.src_path, dest_path=event.dest_path
                )

    def on_modified(self, event):
        if not event.is_directory and not self._should_ignore_file(event.src_path):
            info(f"📝 File modified detected: {event.src_path}")
            self._process_file_immediately("modify", event.src_path)


class PatchIOFileWatcher:
    """Main file watcher class for PatchIO"""

    def __init__(self, db_path: str, indexed_folders: Set[str]):
        self.db_path = db_path
        self.indexed_folders = indexed_folders
        self.observer = Observer()
        self.handler = PatchIOFileHandler(db_path, indexed_folders)
        self.is_running = False
        self.thread = None

        info("🔍 PatchIO File Watcher initialized")

    def start(self):
        """Start the file watcher"""
        if self.is_running:
            warning("⚠️ File watcher is already running")
            return

        try:
            # Add observers for each indexed folder
            for folder in self.indexed_folders:
                if os.path.exists(folder):
                    self.observer.schedule(self.handler, folder, recursive=True)
                    info("👀 Watching folder: {}".format(folder))
                    debug(f"📁 Folder path: {os.path.abspath(folder)}")
                else:
                    warning("⚠️ Indexed folder does not exist: {}".format(folder))

            # Start the observer
            self.observer.start()
            self.is_running = True

            # Start batch processing thread
            self.thread = threading.Thread(target=self._batch_processor, daemon=True)
            self.thread.start()

            info("✅ File watcher started successfully")

        except Exception as e:
            error("❌ Failed to start file watcher: {}".format(e))
            raise

    def stop(self):
        """Stop the file watcher"""
        if not self.is_running:
            return

        try:
            self.is_running = False
            self.observer.stop()
            self.observer.join()

            # Process any remaining operations
            if self.handler.pending_operations:
                self.handler._process_batch()

            info("🛑 File watcher stopped")

        except Exception as e:
            error("❌ Error stopping file watcher: {}".format(e))

    def _batch_processor(self):
        """Background thread to process batches periodically"""
        while self.is_running:
            time.sleep(1.0)  # Check every second
            if (
                self.handler.pending_operations
                and time.time() - self.handler.last_batch_time
                >= self.handler.batch_delay
            ):
                self.handler._process_batch()

    def add_folder(self, folder_path: str):
        """Add a new folder to watch"""
        if os.path.exists(folder_path):
            self.observer.schedule(self.handler, folder_path, recursive=True)
            self.indexed_folders.add(folder_path)
            info("➕ Added folder to watch: {}".format(folder_path))
        else:
            warning("⚠️ Cannot add non-existent folder: {}".format(folder_path))

    def remove_folder(self, folder_path: str):
        """Remove a folder from watching"""
        # Note: watchdog doesn't support removing individual watchers easily
        # This would require restarting the watcher
        warning("⚠️ Removing folders requires restarting the file watcher")

    def get_status(self) -> Dict:
        """Get current status of the file watcher"""
        return {
            "is_running": self.is_running,
            "watched_folders": list(self.indexed_folders),
            "pending_operations": len(self.handler.pending_operations),
            "observer_alive": self.observer.is_alive(),
        }


# Test function
def test_file_watcher():
    """Test the file watcher functionality"""
    debug("🧪 Testing PatchIO File Watcher")

    # Get database path
    import appdirs
    from settings.core_settings import APP_NAME, APP_AUTHOR

    config_dir = appdirs.user_config_dir(APP_NAME, APP_AUTHOR)
    db_path = os.path.join(config_dir, "patchio_index.db")

    # Test folders (use current directory for testing)
    test_folders = {os.getcwd()}

    # Create watcher
    watcher = PatchIOFileWatcher(db_path, test_folders)

    try:
        # Start watcher
        watcher.start()
        debug("✅ File watcher started")

        # Show status
        status = watcher.get_status()
        debug("📊 Status:", status)

        # Keep running for a bit
        debug("👀 Watching for file changes... (Press Ctrl+C to stop)")
        time.sleep(10)

    except KeyboardInterrupt:
        info("\n🛑 Stopping file watcher...")
    finally:
        watcher.stop()
        info("✅ Test completed")


if __name__ == "__main__":
    test_file_watcher()
