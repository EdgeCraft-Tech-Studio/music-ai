#!/usr/bin/env python3
"""
Main Controller - MVC Controller for coordinating the application
Coordinates between models and views
"""

import sys
import os
import sqlite3
from typing import Dict, Optional, List
from PySide6.QtWidgets import QApplication, QPushButton, QFrame, QCheckBox, QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy, QSpacerItem, QLabel, QDialog
from PySide6.QtCore import QTimer, QObject, Qt, QThread, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QFont

# Add the parent directory to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.user_settings_model import UserSettingsModel
from models.search_model import SearchModel
from models.file_model import FileModel
from views.main_window import MainWindowView
from controllers.search_controller import SearchController
from utils.logger import debug, info, warning, error, critical

# Import FileEvent for type hints
try:
    from utils.database.file_watcher import FileEvent
except ImportError:
    # Fallback for when the module isn't available
    class FileEvent:
        pass


# Constants for UI text labels
SEARCH_RESULTS_LABEL = "Search results for:"


class BackgroundVendorExtractionWorker(QThread):
    """Background worker for vendor/library extraction after fast scan"""

    extraction_completed = Signal(dict)
    extraction_progress = Signal(str)
    
    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path
        self.should_stop = False
    
    def stop_extraction(self):
        """Stop the extraction process"""
        self.should_stop = True
    
    def run(self):
        """🚀 OPTIMIZED vendor extraction - batch processing with original logic"""
        try:
            self.extraction_progress.emit("🔍 Starting optimized vendor extraction...")
            
            # Get unique library folders with unknown vendor/library
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get one file per unique library folder that needs vendor/library extraction
            cursor.execute(
                """
                SELECT DISTINCT 
                    SUBSTR(path, 1, LENGTH(path) - LENGTH(name) - 1) as library_folder,
                    MIN(path) as sample_file
                FROM files 
                WHERE vendor = 'Unknown Vendor' OR library = 'Unknown Library'
                GROUP BY library_folder
            """
            )
            
            library_folders = cursor.fetchall()
            conn.close()
            
            if not library_folders:
                self.extraction_progress.emit(
                    "✅ All files already have vendor/library information"
                )
                self.extraction_completed.emit(
                    {"files_processed": 0, "files_updated": 0}
                )
                return
            
            self.extraction_progress.emit(f"🔍 Found {len(library_folders)} library folders to process...")
            
            # 🚀 OPTIMIZED BATCH PROCESSING: Process folders in batches with original logic
            batch_size = 500  # Process 500 folders per batch (larger batches for maximum speed)
            total_files_updated = 0
            folders_processed = 0
            
            # Initialize knowledge database once for all batches
            knowledge_db = self._get_knowledge_database()
            
            for batch_start in range(0, len(library_folders), batch_size):
                if self.should_stop:
                    return
                
                batch_end = min(batch_start + batch_size, len(library_folders))
                batch_folders = library_folders[batch_start:batch_end]
                
                # Process batch using original comprehensive method
                batch_updates = self._process_batch_optimized(batch_folders, knowledge_db)
                total_files_updated += batch_updates
                folders_processed += len(batch_folders)
                
                # Progress update
                self.extraction_progress.emit(f"🔍 Processed {folders_processed}/{len(library_folders)} folders ({batch_updates} files updated in this batch)")
            
            self.extraction_progress.emit(f"✅ Optimized extraction completed: {total_files_updated} files updated across {folders_processed} library folders")
            self.extraction_completed.emit({'files_processed': folders_processed, 'files_updated': total_files_updated})
            
        except Exception as e:
            self.extraction_progress.emit(f"❌ Vendor extraction failed: {e}")
    
    def _get_knowledge_database(self):
        """
        Get knowledge database instance (cached).
        Uses centralized AppDirs path from KnowledgeDatabase.get_default_db_path().
        """
        try:
            from utils.database.knowledge_database import KnowledgeDatabase
            
            # KnowledgeDatabase() automatically uses AppDirs location (single source of truth)
            # Will create DB if it doesn't exist
            return KnowledgeDatabase()
        except Exception as e:
            error(f"❌ Error getting knowledge database: {e}")
            return None
    
    def _process_batch_optimized(self, batch_folders, knowledge_db):
        """🚀 OPTIMIZED batch processing - extract vendor/library using original comprehensive logic"""
        try:
            # Prepare batch data structures
            folder_updates = {}  # library_folder -> (vendor, library)
            
            # 🚀 PHASE 1: Extract vendor/library for all folders in batch using original logic
            for library_folder, sample_file in batch_folders:
                if self.should_stop:
                    return 0
                
                # Use optimized extraction method with shared knowledge database
                vendor, library = self._extract_vendor_library_for_folder(sample_file, knowledge_db)
                
                if vendor != 'Unknown Vendor' or library != 'Unknown Library':
                    folder_updates[library_folder] = (vendor, library)
            
            if not folder_updates:
                return 0  # No updates needed
            
            # 🚀 PHASE 2: Batch update database (single transaction)
            return self._batch_update_database(folder_updates)
            
        except Exception as e:
            error(f"❌ Error in optimized batch processing: {e}")
            return 0
    
    
    def _batch_update_database(self, folder_updates):
        """🚀 ULTRA-FAST batch database update - single transaction for all updates"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            total_updated = 0
            
            # Prepare batch update data
            update_data = []
            for library_folder, (vendor, library) in folder_updates.items():
                update_data.append((vendor, library, library_folder))
            
            # Execute batch updates
            for vendor, library, library_folder in update_data:
                cursor.execute("""
                    UPDATE files 
                    SET vendor = CASE 
                        WHEN vendor = 'Unknown Vendor' THEN ? 
                        ELSE vendor 
                    END,
                    library = CASE 
                        WHEN library = 'Unknown Library' THEN ? 
                        ELSE library 
                    END
                    WHERE path LIKE ? AND (vendor = 'Unknown Vendor' OR library = 'Unknown Library')
                """, (vendor, library, f"{library_folder}%"))
                
                total_updated += cursor.rowcount
            
            conn.commit()
            conn.close()
            
            return total_updated
            
        except Exception as e:
            error(f"❌ Error in batch database update: {e}")
            return 0
    
    def _extract_vendor_library_for_folder(self, sample_file_path: str, knowledge_db=None):
        """
        🚀 NEW: Using LibraryExtractorV3 (fast pattern-based extraction)
        Replaces old knowledge_db.extract_vendor_library() (slow method)
        """
        try:
            # 🚀 NEW: Use V3 extractor (fast, accurate, thread-safe)
            from utils.database.library_extractor_v3 import LibraryExtractorV3
            
            # Create or reuse V3 extractor (uses shared vendor cache)
            if not hasattr(self, '_v3_extractor'):
                self._v3_extractor = LibraryExtractorV3(use_knowledge_db=True)
            
            vendor, library, project = self._v3_extractor.extract_vendor_library(sample_file_path)
            return vendor, library
            
        except Exception as e:
            error(f"❌ Error extracting vendor/library for folder: {e}")
            return 'Unknown Vendor', 'Unknown Library'
    
    def _update_folder_files(self, library_folder: str, vendor: str, library: str):
        """Update all files in a library folder with the same vendor/library"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Update only files that need vendor/library information
            cursor.execute(
                """
                UPDATE files 
                SET vendor = CASE 
                    WHEN vendor = 'Unknown Vendor' THEN ? 
                    ELSE vendor 
                END,
                library = CASE 
                    WHEN library = 'Unknown Library' THEN ? 
                    ELSE library 
                END,
                updated_at = strftime('%s', 'now')
                WHERE path LIKE ? AND (vendor = 'Unknown Vendor' OR library = 'Unknown Library')
            """,
                (vendor, library, f"{library_folder}%"),
            )
            
            files_updated = cursor.rowcount
            conn.commit()
            conn.close()
            
            return files_updated
            
        except Exception as e:
            error(f"❌ Error updating folder files: {e}")
            return 0
    
    def _fast_extract_vendor_library(self, file_path: str):
        """🚀 ULTRA-FAST vendor/library extraction - same method as initial indexing"""
        import os
        
        # Use string operations instead of Path() for speed
        path_lower = file_path.lower()
        
        # Pre-compiled vendor patterns for speed
        vendor_patterns = {
            "native instruments": "Native Instruments",
            "spitfire": "Spitfire Audio",
            "heavyocity": "Heavyocity",
            "eastwest": "EastWest",
            "cinesamples": "Cinesamples",
            "synthogy": "Synthogy",
            "apple": "Apple",
            "steinberg": "Steinberg",
            "image-line": "Image-Line",
            "avid": "Avid",
            "cockos": "Cockos",
            "bitwig": "Bitwig",
            "reason studios": "Reason Studios",
            "output": "Output",
            "8dio": "8DIO",
            "orchestral tools": "Orchestral Tools",
            "audio imperia": "Audio Imperia",
            "keep forest": "Keep Forest",
            "heavyocity": "Heavyocity",
            "sonokinetic": "Sonokinetic",
            "project sam": "Project SAM",
            "cinesamples": "Cinesamples",
            "spitfire audio": "Spitfire Audio",
            "native instruments": "Native Instruments",
            "kontakt": "Native Instruments",
            "omnisphere": "Spectrasonics",
            "spectrasonics": "Spectrasonics",
            "arturia": "Arturia",
            "u-he": "u-he",
            "fabfilter": "FabFilter",
            "izotope": "iZotope",
            "waves": "Waves",
            "plugin alliance": "Plugin Alliance",
            "softube": "Softube",
            "valhalla": "Valhalla DSP",
            "soundtoys": "Soundtoys",
            "output": "Output",
            "splice": "Splice",
            "loopmasters": "Loopmasters",
            "black octopus": "Black Octopus",
            "ghost syndicate": "Ghost Syndicate",
            "vengeance": "Vengeance",
            "prime loops": "Prime Loops",
            "sample magic": "Sample Magic",
            "big fish audio": "Big Fish Audio",
            "zero-g": "Zero-G",
            "best service": "Best Service",
            "engine": "Best Service",
            "east west": "EastWest",
            "composer cloud": "EastWest",
            "hollywood": "EastWest",
            "play": "EastWest",
            "opus": "EastWest",
            "symphonic orchestra": "EastWest",
            "hollywood strings": "EastWest",
            "hollywood brass": "EastWest",
            "hollywood woodwinds": "EastWest",
            "hollywood percussion": "EastWest",
            "hollywood choir": "EastWest",
            "hollywood solo strings": "EastWest",
            "hollywood backup singers": "EastWest",
            "hollywood solo woodwinds": "EastWest",
            "hollywood solo brass": "EastWest",
            "hollywood solo percussion": "EastWest",
            "hollywood solo choir": "EastWest",
            "hollywood solo backup singers": "EastWest",
            "hollywood solo solo strings": "EastWest",
            "hollywood solo solo woodwinds": "EastWest",
            "hollywood solo solo brass": "EastWest",
            "hollywood solo solo percussion": "EastWest",
            "hollywood solo solo choir": "EastWest",
            "hollywood solo solo backup singers": "EastWest",
        }
        
        # Find vendor in path
        vendor = "Unknown Vendor"
        library = "Unknown Library"
        
        for pattern, vendor_name in vendor_patterns.items():
            if pattern in path_lower:
                vendor = vendor_name
                # Extract library name (folder after vendor)
                parts = file_path.split(os.sep)
                for i, part in enumerate(parts):
                    if pattern in part.lower():
                        # Look for library in next few folders
                        for j in range(i + 1, min(i + 4, len(parts))):
                            next_part = parts[j]
                            if (
                                len(next_part) > 2
                                and len(next_part) <= 30
                                and next_part.lower()
                                not in {
                                    "samples",
                                    "patches",
                                    "instruments",
                                    "presets",
                                    "content",
                                    "data",
                                    "library",
                                    "libraries",
                                }
                            ):
                                library = next_part
                                break
                        break
                break
        
        return vendor, library


class BackgroundSyncWorker(QThread):
    """🚀 PROFESSIONAL background worker for database synchronization with progress tracking"""

    sync_completed = Signal(dict)
    sync_failed = Signal(str)
    sync_progress = Signal(str)  # Progress updates
    
    # 🚀 NEW: Detailed progress signals for professional progress tracking
    scan_progress = Signal(dict)  # Detailed scan progress with rate, ETA, etc.
    start_scan_ui = Signal()  # Signal to start scan progress UI
    
    def __init__(self, db_path, indexed_folders):
        super().__init__()
        self.db_path = db_path
        self.indexed_folders = indexed_folders
        self.should_stop = False  # For cancellation support
    
    def stop_sync(self):
        """Stop the sync process"""
        self.should_stop = True
    
    def run(self):
        """🚀 Run the sync in background thread with professional progress tracking"""
        try:
            from utils.database.file_index_manager import FileIndexManager

            self.sync_progress.emit("🔄 Starting PROFESSIONAL file index sync...")
            
            # Create file index manager
            file_index_manager = FileIndexManager(self.db_path, self.indexed_folders)
            
            # 🚀 PROFESSIONAL progress callback for detailed updates
            def progress_callback(progress_info):
                if self.should_stop:
                    return  # Stop if requested
                
                # Emit detailed progress information
                self.scan_progress.emit(progress_info)
                
                # Also emit simple progress message
                if progress_info.get("phase") == "streaming_scan":
                    scanned = progress_info.get("scanned", 0)
                    relevant = progress_info.get("relevant", 0)
                    rate = progress_info.get("rate", 0)
                    eta_minutes = progress_info.get("eta_minutes", 0)
                    
                    message = f"🔍 Scanned {scanned:,} files, found {relevant:,} relevant files..."
                    if rate > 0:
                        message += (
                            f" Rate: {rate:.0f} files/sec, ETA: {eta_minutes:.1f} min"
                        )
                    
                    self.sync_progress.emit(message)
            
            # Emit signal to start scan progress UI
            self.start_scan_ui.emit()
            
            # Perform startup sync with progress callback
            self.sync_progress.emit("🔍 Scanning filesystem for changes...")
            sync_results = file_index_manager.sync_index_with_filesystem(
                force_full_sync=False, progress_callback=progress_callback
            )
            
            if self.should_stop:
                self.sync_progress.emit("🛑 File sync cancelled")
                return
            
            self.sync_progress.emit("✅ Background sync completed")
            self.sync_completed.emit(sync_results)
        except Exception as e:
            self.sync_failed.emit(str(e))
        finally:
            # Ensure the thread properly finishes
            debug("🧵 BackgroundSyncWorker thread finishing...")


class MaterialCheckBox(QCheckBox):
    """Material Design style checkbox with proper tick mark"""
    
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(
            """
            QCheckBox {
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 400;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                padding: 6px 12px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 0px;
                height: 0px;
                border: none;
                background: transparent;
            }
        """
        )
    
    def paintEvent(self, event):
        """Custom paint event for Material Design checkbox"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate checkbox position (smaller size, better alignment)
        checkbox_size = 14  # Smaller checkbox
        checkbox_x = 12  # More padding from left
        checkbox_y = (self.height() - checkbox_size) // 2  # center vertically
        
        # Draw the checkbox background
        if self.isChecked():
            # Blue background when checked
            painter.setBrush(QColor("#3478f6"))
            painter.setPen(QPen(QColor("#3478f6"), 1))  # Thin border
        else:
            # Very thin grey border when unchecked
            painter.setBrush(QColor(0, 0, 0, 0))  # Transparent
            painter.setPen(QPen(QColor("#444444"), 1))  # Very light grey border
        
        # Draw rounded rectangle
        painter.drawRoundedRect(
            checkbox_x, checkbox_y, checkbox_size, checkbox_size, 2, 2
        )  # Smaller radius
        
        # Draw tick mark if checked
        if self.isChecked():
            # Load and draw the tick.png icon
            from PySide6.QtGui import QPixmap

            tick_pixmap = QPixmap("_Current version/current/assets/icons/tick.png")
            
            # Scale the tick icon to fit the checkbox
            scaled_tick = tick_pixmap.scaled(
                checkbox_size - 4,
                checkbox_size - 4,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            
            # Draw the tick icon centered in the checkbox
            tick_x = checkbox_x + (checkbox_size - scaled_tick.width()) // 2
            tick_y = checkbox_y + (checkbox_size - scaled_tick.height()) // 2
            painter.drawPixmap(tick_x, tick_y, scaled_tick)
        
        # Draw the text (better alignment)
        text_x = checkbox_x + checkbox_size + 8  # 8px spacing from checkbox
        text_y = self.height() // 2 + 4  # Better vertical alignment
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(text_x, text_y, self.text())
    
    def mousePressEvent(self, event):
        """Handle mouse clicks to toggle checkbox"""
        if event.button() == Qt.LeftButton:
            self.setChecked(not self.isChecked())
            self.clicked.emit(self.isChecked())
        super().mousePressEvent(event)


class FloatingDropdown(QWidget):
    """Reusable floating dropdown widget with consistent design"""
    
    def __init__(self, name, items, parent=None):
        super().__init__()
        self.name = name
        self.items = items
        self.parent = parent
        
        # Set up as top-level floating widget
        self.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint
        )
        self.setObjectName(f"{name}DropdownMenu")
        self.setVisible(False)
        self.setMinimumSize(200, 0)
        self.setMaximumSize(200, 16777215)
        
        # Apply consistent styling with more rounded corners
        self.setStyleSheet(
            """
            QWidget {
                background-color: #2C2C2E;
                border: none;
                border-radius: 12px;
                margin: 4px 0px;
            }
        """
        )
        
        # Enable custom painting for rounded corners
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        
        # Create layout
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 8, 0, 8)
        
        # Add checkboxes for items
        self.checkboxes = {}
        for item_name, item_text in items:
            checkbox = MaterialCheckBox(item_text)
            checkbox.setObjectName(item_name)
            self.checkboxes[item_name] = checkbox
            self.layout.addWidget(checkbox)
        
        # Add buttons
        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.setSpacing(8)
        self.buttons_layout.setContentsMargins(12, 8, 12, 0)
        
        # Clear button
        self.clear_button = QPushButton("Clear")
        self.clear_button.setObjectName(f"{name}ClearButton")
        self.clear_button.setMinimumSize(60, 28)
        self.clear_button.setMaximumSize(60, 28)
        self.clear_button.setCursor(Qt.PointingHandCursor)
        self.clear_button.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: 1px solid #3C3C3E;
                border-radius: 8px;
                color: #8E8E93;
                font-size: 12px;
                font-weight: 500;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                padding: 4px 8px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #3A3A3C;
                border-color: #4A4A4C;
                color: #FFFFFF;
            }
        """
        )
        
        # Close button
        self.close_button = QPushButton("Close")
        self.close_button.setObjectName(f"{name}CloseButton")
        self.close_button.setMinimumSize(60, 28)
        self.close_button.setMaximumSize(60, 28)
        self.close_button.setCursor(Qt.PointingHandCursor)
        self.close_button.setStyleSheet(
            """
            QPushButton {
                background-color: #3478f6;
                border: 1px solid #3478f6;
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 12px;
                font-weight: 500;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                padding: 4px 8px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #2a70d6;
                border-color: #2a70d6;
            }
        """
        )
        
        # Add buttons to layout
        self.buttons_layout.addWidget(self.clear_button)
        self.buttons_layout.addSpacerItem(
            QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        )
        self.buttons_layout.addWidget(self.close_button)
        
        self.layout.addLayout(self.buttons_layout)
        
        # Connect buttons
        self.clear_button.clicked.connect(self.clear_checkboxes)
        self.close_button.clicked.connect(self.hide)
        
        # Connect checkbox changes to parent controller
        self.on_checkbox_changed_callback = None
        
        debug(f"✅ Created floating {name} dropdown")
    
    def paintEvent(self, event):
        """Custom paint event to draw rounded background"""
        from PySide6.QtGui import QPainter, QPainterPath, QColor
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create rounded rectangle path
        path = QPainterPath()
        rect = self.rect()
        radius = 12  # Match the border-radius from CSS
        
        # Create rounded rectangle
        path.addRoundedRect(rect, radius, radius)
        
        # Fill with background color
        painter.fillPath(path, QColor("#2C2C2E"))
        
        # Call parent paint event for child widgets
        super().paintEvent(event)
    
    def clear_checkboxes(self):
        """Clear all checkboxes in this dropdown"""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(False)
    
    def get_checked_items(self):
        """Get list of checked item names"""
        return [
            name for name, checkbox in self.checkboxes.items() if checkbox.isChecked()
        ]
    
    def set_checkbox_changed_callback(self, callback):
        """Set callback for when checkboxes change"""
        self.on_checkbox_changed_callback = callback
        
        # Connect all checkboxes to the callback
        for checkbox in self.checkboxes.values():
            checkbox.toggled.connect(self.on_checkbox_toggled)
    
    def on_checkbox_toggled(self, checked):
        """Handle checkbox toggle events"""
        if self.on_checkbox_changed_callback:
            # Get the checkbox that was toggled
            sender = self.sender()
            for item_name, checkbox in self.checkboxes.items():
                if checkbox == sender:
                    self.on_checkbox_changed_callback(self.name, item_name, checked)
                    break


class MainController(QObject):
    """Main controller - coordinates between models and views"""
    
    def __init__(self):
        super().__init__()
        # Initialize models
        self.settings_model = UserSettingsModel()
        self.search_model = SearchModel(self.settings_model)
        self.file_model = FileModel(self.settings_model)
        
        # Initialize file watcher
        self.file_watcher = None
        self._setup_file_watcher()
        
        # Initialize vendor extraction worker
        self.vendor_extraction_worker = None
        
        # Initialize view
        self.main_window = MainWindowView(self.settings_model)
        
        # Initialize sub-controllers
        self.search_controller = SearchController(
            self.search_model, self.file_model, self.main_window
        )
        
        # Set main controller reference in search controller
        self.search_controller.main_controller = self
        
        # Setup connections
        self.setup_connections()
        
        # Initialize search
        self.search_model.setup_default_folders()
        
        # Initialize filter management
        
        # Setup file watcher
        self._setup_file_watcher()
        self.active_filters = {}
        self.filter_tags = {}
        self.filter_summary_label = None
    
    def setup_connections(self):
        """Setup signal connections"""
        # Note: textToFilterBubble signal connection moved to setup_dropdown_connections
        # to ensure UI is fully loaded before connecting
        info("✅ Main controller connections setup complete")
    
    def setup_preferences_button(self):
        """Setup the preferences button in the sidebar"""
        # Find the preferences button
        preferences_button = self.main_window.findChild(QLabel, "preferencesButton")
        if preferences_button:
            # Make it clickable by installing an event filter
            preferences_button.installEventFilter(self)
            # Store reference for event filtering
            self.preferences_button = preferences_button
            debug("✅ Preferences button connected")
        else:
            warning("⚠️ Preferences button not found in UI")
    
    def on_preferences_clicked(self):
        """Handle preferences button click - open preferences window"""
        try:
            from views.preferences_window import PreferencesWindow
            
            # Get current folders BEFORE opening dialog
            old_folders = self.settings_model.get_setting('search_folders', [])
            
            # Create and show preferences window
            preferences_window = PreferencesWindow(self.settings_model, self.main_window)
            result = preferences_window.exec()
            
            if result == QDialog.Accepted:
                # Get NEW folders AFTER save
                new_folders = self.settings_model.get_setting('search_folders', [])
                
                info(f"✅ Preferences saved: {len(new_folders)} folder(s)")
                for i, folder in enumerate(new_folders, 1):
                    debug(f"  {i}. {folder}")
                
                # Check if folders changed
                if set(old_folders) != set(new_folders):
                    info("🔄 Folders changed - syncing database...")
                    self.sync_database_after_folder_change(new_folders, old_folders)
                else:
                    warning("   No folder changes detected")
            # Note: preferences_window.py already logs when cancelled, no need to duplicate
                
        except Exception as e:
            error(f"❌ Error opening preferences window: {e}")
            import traceback
            traceback.print_exc()
    
    def check_first_time_setup(self):
        """Check if this is first-time setup (no folders configured)"""
        search_folders = self.settings_model.get_setting('search_folders', [])
        
        if not search_folders or len(search_folders) == 0:
            warning("🎯 First-time setup: No folders configured")
            return True
        
        return False
    
    def handle_first_time_setup(self):
        """Handle first-time setup by auto-opening preferences"""
        if self.check_first_time_setup():
            info("🎯 Opening preferences for first-time setup...")
            # Show message briefly
            if hasattr(self.main_window, 'update_status_display'):
                self.main_window.update_status_display(
                    "Welcome! Please configure your sample folders to get started.",
                    "ready"
                )
            # Auto-open preferences after brief delay
            QTimer.singleShot(1000, self.open_preferences_for_first_time)
    
    def open_preferences_for_first_time(self):
        """Open preferences specifically for first-time setup"""
        from views.preferences_window import PreferencesWindow
        
        preferences_window = PreferencesWindow(self.settings_model, self.main_window)
        result = preferences_window.exec()
        
        if result == QDialog.Accepted:
            folders = self.settings_model.get_setting('search_folders', [])
            if folders:
                info(f"✅ First-time setup complete: {len(folders)} folder(s)")
                # Trigger initial database sync
                self.sync_database_after_folder_change(folders, [])
            else:
                warning("⚠️ No folders selected - user must configure before using app")
        else:
            warning("⚠️ First-time setup cancelled - app may not function properly")
    
    def sync_database_after_folder_change(self, new_folders, old_folders):
        """
        Sync database when folders change
        - Remove files from folders no longer in the list
        - Add files from new folders
        """
        import appdirs
        from settings.core_settings import APP_NAME, APP_AUTHOR
        
        info("🔄 Syncing database after folder change...")
        debug(f"  Old folders: {len(old_folders)}")
        debug(f"  New folders: {len(new_folders)}")
        
        # Get database path
        config_dir = appdirs.user_config_dir(APP_NAME, APP_AUTHOR)
        db_path = os.path.join(config_dir, 'patchio_index.db')
        
        new_folders_set = set(new_folders)
        old_folders_set = set(old_folders)
        
        # Folders to remove (in old but not in new)
        folders_to_remove = old_folders_set - new_folders_set
        
        # Folders to add (in new but not in old)
        folders_to_add = new_folders_set - old_folders_set
        
        if folders_to_remove:
            info(f"🗑️  Removing {len(folders_to_remove)} folder(s) from index:")
            for folder in folders_to_remove:
                debug(f"    - {folder}")
                self.remove_folder_from_database(db_path, folder)
        
        if folders_to_add or folders_to_remove:
            # Restart file watcher with new folders
            info("🔄 Restarting file index manager with updated folders...")
            self.restart_file_watcher(new_folders_set)
        else:
            warning("✅ No folder changes detected")
    
    def remove_folder_from_database(self, db_path, folder_path):
        """Remove all files from a specific folder from the database"""
        try:
            import sqlite3
            
            conn = sqlite3.connect(db_path, timeout=10.0)
            cursor = conn.cursor()
            
            # Remove all files that start with this folder path
            cursor.execute("""
                DELETE FROM files 
                WHERE path LIKE ?
            """, (f"{folder_path}%",))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            info(f"   Removed {deleted_count} file(s) from {os.path.basename(folder_path)}")
            
        except Exception as e:
            error(f"❌ Error removing folder from database: {e}")
    
    def restart_file_watcher(self, new_folders):
        """Restart file watcher with new folder configuration"""
        # Stop existing file watcher if running
        if hasattr(self, 'file_index_manager') and self.file_index_manager:
            self.file_index_manager.stop_real_time_monitoring()
            info("🛑 Stopped existing file watcher")
        
        # Stop sync worker if running
        if hasattr(self, 'sync_worker') and self.sync_worker and self.sync_worker.isRunning():
            self.sync_worker.stop_sync()
            self.sync_worker.quit()
            self.sync_worker.wait(2000)
            info("🛑 Stopped existing sync worker")
        
        # Clear the sync worker reference so a new one can be created
        self.sync_worker = None
        
        # Re-initialize file watcher with new folders
        self._setup_file_watcher()
        
        # Show appropriate message based on whether folders exist
        if new_folders and len(new_folders) > 0:
            info(f"✅ File watcher restarted with {len(new_folders)} folder(s)")
        else:
            warning("✅ File watcher stopped (no folders configured)")
    
    def on_text_to_filter_bubble(self, text):
        """Handle search text when user presses Enter - keep text in search bar and start search"""
        if not text.strip():
            return
        
        # Keep the text in the search bar (don't clear it)
        # Start the search with the text from the search bar
        # Filters will adjust the query as needed
        
        info(f"🔍 Starting search with text: '{text.strip()}' from search bar")
        
        # Update the filter summary to include the search term
        self.update_search_summary(text.strip())
        
        # Trigger the search using the search controller
        if hasattr(self, "search_controller"):
            self.search_controller.start_search_with_text(text.strip())
    
    # def remove_existing_search_filters(self):
    #     """Remove any existing search term filters to replace with new search term - REMOVED"""
    #     if "search" in self.active_filters:
    #         # Get all existing search terms
    #         existing_search_terms = self.active_filters["search"].copy()
    #             
    #         # Remove each existing search term
    #         for search_term in existing_search_terms:
    #             self.remove_filter("search", search_term)
    #             
    #         print(f"🔍 Removed {len(existing_search_terms)} existing search term filters")
    
    def setup_dropdown_connections(self):
        """Setup connections for filter dropdowns - called after UI is loaded"""
        # Connect the new signal for converting text to filter bubbles
        if hasattr(self.main_window, 'search_input') and hasattr(self.main_window.search_input, 'textToFilterBubble'):
            self.main_window.search_input.textToFilterBubble.connect(self.on_text_to_filter_bubble)
            debug("✅ Connected textToFilterBubble signal")
        
        # Removed textChanged connection - search summary only updates when search starts
        
        # Get dropdown buttons
        instruments_button = self.main_window.findChild(
            QPushButton, "instrumentsDropdown"
        )
        genres_button = self.main_window.findChild(QPushButton, "genresDropdown")
        vendor_button = self.main_window.findChild(QPushButton, "vendorDropdown")
        
        debug(f"🔍 Dropdown setup - Instruments: {instruments_button is not None}")
        debug(f"🔍 Dropdown setup - Genres: {genres_button is not None}")
        debug(f"🔍 Dropdown setup - Vendor: {vendor_button is not None}")
        
        # Create floating dropdown menus using unified approach
        self.create_unified_dropdowns()
        
        # Connect dropdown buttons
        if instruments_button and hasattr(self, 'instruments_dropdown'):
            instruments_button.clicked.connect(lambda: self.toggle_dropdown(self.instruments_dropdown))
            debug("✅ Connected Instruments dropdown")
        if genres_button and hasattr(self, 'genres_dropdown'):
            genres_button.clicked.connect(lambda: self.toggle_dropdown(self.genres_dropdown))
            debug("✅ Connected Genres dropdown")
        if vendor_button and hasattr(self, 'vendor_dropdown'):
            vendor_button.clicked.connect(lambda: self.toggle_dropdown(self.vendor_dropdown))
            debug("✅ Connected Vendor dropdown")
        
        # Setup click outside handler
        self.setup_click_outside_handler()
        
        # Connect Clear All button
        clear_filters_button = self.main_window.findChild(
            QPushButton, "clearFiltersButton"
        )
        if clear_filters_button:
            clear_filters_button.clicked.connect(self.clear_all_filters)
            debug("✅ Connected Clear All button")
        else:
            warning("⚠️ Clear All button not found")
        
        # Setup filter management after a short delay to ensure UI is fully loaded
        QTimer.singleShot(100, self.setup_filter_management)
        
        # Setup preferences button (after UI is loaded)
        self.setup_preferences_button()
    
    def create_unified_dropdowns(self):
        """Create all dropdowns using the unified FloatingDropdown class"""
        # Define dropdown configurations
        dropdown_configs = {
            "instruments": [
                ("instrumentsSynth", "synth (11)"),
                ("instrumentsDrums", "drums (2)"),
                ("instrumentsVocals", "vocals (2)"),
                ("instrumentsSnares", "snares (1)"),
                ("instrumentsModular", "modular (1)"),
                ("instrumentsPercussion", "percussion (1)"),
            ],
            "genres": [
                ("genresAction", "action (8)"),
                ("genresTrailer", "trailer (6)"),
                ("genresJazz", "jazz (3)"),
                ("genresElectronic", "electronic (2)"),
            ],
            "vendor": [
                ("vendorNativeInstruments", "Native Instruments (15)"),
                ("vendorSpitfire", "Spitfire Audio (12)"),
                ("vendorEastWest", "EastWest (8)"),
                ("vendorAuthenticSoundware", "Authentic Soundware (3)"),
            ],
        }
        
        # Create dropdowns using unified class
        self.instruments_dropdown = FloatingDropdown(
            "instruments", dropdown_configs["instruments"]
        )
        self.genres_dropdown = FloatingDropdown("genres", dropdown_configs["genres"])
        self.vendor_dropdown = FloatingDropdown("vendor", dropdown_configs["vendor"])
        
        debug("✅ Created all dropdown menus")
        
        # Set up checkbox change callbacks
        self.instruments_dropdown.set_checkbox_changed_callback(
            self.on_filter_checkbox_changed
        )
        self.genres_dropdown.set_checkbox_changed_callback(
            self.on_filter_checkbox_changed
        )
        self.vendor_dropdown.set_checkbox_changed_callback(
            self.on_filter_checkbox_changed
        )
        
        debug("✅ Set up checkbox change callbacks")
    
    def toggle_dropdown(self, dropdown_menu):
        """Toggle dropdown menu visibility with proper positioning"""
        if dropdown_menu:
            current_visible = dropdown_menu.isVisible()
            # Hide all dropdowns first
            self.hide_all_dropdowns()
            # Show this dropdown if it wasn't visible
            if not current_visible:
                # Position the dropdown below the button
                self.position_dropdown(dropdown_menu)
                dropdown_menu.setVisible(True)
                # Ensure dropdown is on top
                dropdown_menu.raise_()
    
    def position_dropdown(self, dropdown_menu):
        """Position dropdown menu below its parent button - allow floating freely"""
        # Find the parent button for this dropdown
        button_name = None
        if dropdown_menu == self.instruments_dropdown:
            button_name = "instrumentsDropdown"
        elif dropdown_menu == self.genres_dropdown:
            button_name = "genresDropdown"
        elif dropdown_menu == self.vendor_dropdown:
            button_name = "vendorDropdown"
        
        if button_name:
            button = self.main_window.findChild(QPushButton, button_name)
            if button:
                # Get button position in global screen coordinates
                button_global_pos = button.mapToGlobal(button.rect().bottomLeft())
                
                # Position dropdown below button, aligned to left edge
                # Allow it to float freely without bounds checking
                dropdown_x = button_global_pos.x()
                dropdown_y = button_global_pos.y() + 4  # Small gap below button
                
                dropdown_menu.move(dropdown_x, dropdown_y)
                debug(f"🔍 Positioned {dropdown_menu.objectName()} at global ({dropdown_x}, {dropdown_y}) - floating freely")
            else:
                warning(f"⚠️ Could not find button {button_name}")
        else:
            warning(f"⚠️ Could not determine button name for {dropdown_menu.objectName()}")
    
    def hide_all_dropdowns(self):
        """Hide all dropdown menus"""
        if hasattr(self, "instruments_dropdown"):
            self.instruments_dropdown.setVisible(False)
        if hasattr(self, "genres_dropdown"):
            self.genres_dropdown.setVisible(False)
        if hasattr(self, "vendor_dropdown"):
            self.vendor_dropdown.setVisible(False)
    
    def setup_click_outside_handler(self):
        """Setup event filter to close dropdowns when clicking outside"""
        # Install event filter on main window
        self.main_window.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """Event filter to handle click outside dropdowns, escape key, and preferences button"""
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QMouseEvent, QKeyEvent
        
        if event.type() == QEvent.MouseButtonPress:
            # Check if preferences button was clicked
            if hasattr(self, 'preferences_button') and obj == self.preferences_button:
                debug("🔍 Preferences button clicked!")
                self.on_preferences_clicked()
                return True
            
            # Check if click is outside dropdown menus
            dropdowns = []
            if hasattr(self, "instruments_dropdown"):
                dropdowns.append(self.instruments_dropdown)
            if hasattr(self, "genres_dropdown"):
                dropdowns.append(self.genres_dropdown)
            if hasattr(self, "vendor_dropdown"):
                dropdowns.append(self.vendor_dropdown)
            
            for dropdown in dropdowns:
                if dropdown and dropdown.isVisible():
                    # For top-level widgets, check if click is outside using global coordinates
                    click_global_pos = event.globalPos()
                    dropdown_rect = dropdown.geometry()
                    dropdown_global_pos = dropdown.mapToGlobal(dropdown_rect.topLeft())
                    
                    # Create global rect for the dropdown
                    from PySide6.QtCore import QRect

                    dropdown_global_rect = QRect(
                        dropdown_global_pos, dropdown_rect.size()
                    )
                    
                    if not dropdown_global_rect.contains(click_global_pos):
                        dropdown.setVisible(False)
                        debug(f"🔍 Closed {dropdown.objectName()} - clicked outside")
        
        # Call parent event filter
        return super().eventFilter(obj, event)
    
    def run(self):
        """Run the application"""
        info("🚀 Starting PatchIO with MVC architecture")
        return self.main_window.show()
    
    def get_search_controller(self):
        """Get the search controller"""
        return self.search_controller
    
    def get_settings_model(self):
        """Get the settings model"""
        return self.settings_model
    
    def get_file_model(self):
        """Get the file model"""
        return self.file_model
    
    def setup_filter_management(self):
        """Setup filter management after UI is loaded"""
        # Get the filter tags container and summary label
        self.filter_tags_container = self.main_window.findChild(
            QWidget, "filterTagsContainer"
        )
        self.filter_summary_label = self.main_window.findChild(
            QLabel, "filterSummaryLabel"
        )
        
        debug(f"🔍 Debug - Main window: {self.main_window}")
        debug(f"🔍 Debug - Filter tags container: {self.filter_tags_container}")
        debug(f"🔍 Debug - Filter summary label: {self.filter_summary_label}")
        
        if self.filter_tags_container:
            debug("✅ Filter tags container found")
        else:
            warning("⚠️ Filter tags container not found")
        
        if self.filter_summary_label:
            debug("✅ Filter summary label found")
        else:
            warning("⚠️ Filter summary label not found")
    
    def add_filter(self, filter_type, filter_value):
        """Add a filter and create a bubble"""
        if filter_type not in self.active_filters:
            self.active_filters[filter_type] = []
        
        if filter_value not in self.active_filters[filter_type]:
            self.active_filters[filter_type].append(filter_value)
            
            # Create and add filter bubble (just the value, not the type)
            self.create_filter_bubble(filter_value)
            
            # Update filter summary
            self.update_filter_summary()
            
            # Trigger search update
            self.search_controller.on_filters_changed()
            
            debug(f"✅ Added filter bubble: {filter_value}")
    
    def remove_filter(self, filter_type, filter_value):
        """Remove a filter and its bubble"""
        if (
            filter_type in self.active_filters
            and filter_value in self.active_filters[filter_type]
        ):
            self.active_filters[filter_type].remove(filter_value)
            
            # Clean up empty filter type entries
            if not self.active_filters[filter_type]:
                del self.active_filters[filter_type]
                info(f"🔍 Removed empty filter type: {filter_type}")
            
            # Remove filter bubble
            self.remove_filter_bubble(filter_value)
            
            # Update dropdown checkbox to reflect removal
            self.uncheck_dropdown_item(filter_type, filter_value)
            
            # Update filter summary
            self.update_filter_summary()
            
            # Check if no more active filters - clear the tree and stop search
            if not self.active_filters:
                debug("🔍 No more active filters - clearing results tree and stopping search")
                if hasattr(self, 'main_window') and self.main_window:
                    self.main_window.clear_results()
                
                # Stop any running search since there's nothing to search for
                if hasattr(self, "search_controller") and self.search_controller:
                    self.search_controller.on_search_cancelled()
                    debug("🔍 Cancelled running search - no filters active")
            
            # Trigger search update
            self.search_controller.on_filters_changed()
            
            info(f"✅ Removed filter bubble: {filter_value}")
            debug(f"🔍 Active filters after removal: {self.active_filters}")
    
    def uncheck_dropdown_item(self, filter_type, filter_value):
        """Uncheck the corresponding dropdown item when a filter is removed"""
        # Map filter types to dropdown names
        dropdown_map = {
            "Instrument": "instruments",
            "Genre": "genres",
            "Vendor": "vendor",
        }
        
        dropdown_name = dropdown_map.get(filter_type)
        if not dropdown_name:
            return
        
        # Get the dropdown
        dropdown = getattr(self, f"{dropdown_name}_dropdown", None)
        if not dropdown:
            return
        
        # Map filter value back to item name for the dropdown
        if dropdown_name == "instruments":
            value_to_item_map = {
                "Synth": "instrumentsSynth",
                "Drums": "instrumentsDrums",
                "Vocals": "instrumentsVocals",
                "Snares": "instrumentsSnares",
                "Modular": "instrumentsModular",
                "Percussion": "instrumentsPercussion",
                "Piano": "instrumentsPiano",
            }
        elif dropdown_name == "genres":
            value_to_item_map = {
                "Action": "genresAction",
                "Trailer": "genresTrailer",
                "Jazz": "genresJazz",
                "Electronic": "genresElectronic",
                "Dark": "genresDark",
            }
        elif dropdown_name == "vendor":
            value_to_item_map = {
                "Native Instruments": "vendorNativeInstruments",
                "Spitfire": "vendorSpitfire",
                "EastWest": "vendorEastWest",
                "Authentic Soundware": "vendorAuthenticSoundware",
            }
        else:
            value_to_item_map = {}
        
        item_name = value_to_item_map.get(filter_value, filter_value)
        
        # Uncheck the checkbox in the dropdown
        if hasattr(dropdown, "checkboxes") and item_name in dropdown.checkboxes:
            checkbox = dropdown.checkboxes[item_name]
            checkbox.setChecked(False)
            debug(f"🔍 Unchecked dropdown item: {dropdown_name} -> {item_name}")
    
    def create_filter_bubble(self, filter_value):
        """Create and add a filter bubble to the UI"""
        if not self.filter_tags_container:
            return
        
        # Import the tag bubble widget
        from views.tag_bubble_widget import TagBubbleWidget
        from PySide6.QtWidgets import QSpacerItem, QSizePolicy
        
        # Create the bubble widget (just the value, no type prefix)
        bubble = TagBubbleWidget("", filter_value)  # Empty type for individual bubbles
        bubble.set_remove_callback(self.remove_filter_bubble_callback)
        
        # Add to the filter tags layout
        layout = self.filter_tags_container.findChild(QHBoxLayout, "filterTagsLayout")
        if layout:
            # Clear any existing spacer
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if isinstance(item, QSpacerItem):
                    layout.removeItem(item)
            
            # Add the bubble
            layout.addWidget(bubble)
            
            # Add a spacer to push bubbles to the left
            spacer = QSpacerItem(
                40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
            )
            layout.addItem(spacer)
            
            # Store reference to bubble
            self.filter_tags[filter_value] = bubble
    
    def remove_filter_bubble(self, filter_value):
        """Remove a filter bubble from the UI"""
        if filter_value in self.filter_tags:
            bubble = self.filter_tags[filter_value]
            
            # Remove immediately like search bubbles (no animation delay)
            from PySide6.QtWidgets import QSpacerItem, QSizePolicy
            
            layout = self.filter_tags_container.findChild(
                QHBoxLayout, "filterTagsLayout"
            )
            if layout:
                layout.removeWidget(bubble)
                bubble.deleteLater()
                
                # Remove the spacer as well
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if isinstance(item, QSpacerItem):
                        layout.removeItem(item)
                        break
                
                # If there are still bubbles, add the spacer back
                if layout.count() > 0:
                    spacer = QSpacerItem(
                        40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
                    )
                    layout.addItem(spacer)
            
            del self.filter_tags[filter_value]
    
    def update_filter_summary(self):
        """Update the filter summary text - only shows filters, preserves existing search term"""
        if not self.filter_summary_label:
            return
        
        # Get current text to see if there's an active search
        current_text = self.filter_summary_label.text()
        
        # Build filter summary text
        summary_parts = []
        for filter_type, values in self.active_filters.items():
            if values:
                summary_parts.extend(values)
        
        # If there's already a search results text, preserve it and add filters
        if SEARCH_RESULTS_LABEL in current_text:
            if summary_parts:
                # Extract the search term from current text
                search_part = current_text.split(". Filtered by:")[0]
                summary_text = f"{search_part}. Filtered by: {', '.join(summary_parts)}"
            else:
                # Keep just the search part
                summary_text = current_text.split(". Filtered by:")[0]
        else:
            # No search term, just show filters
            if summary_parts:
                summary_text = f"Filtered by: {', '.join(summary_parts)}"
            else:
                summary_text = ""
        
        if summary_text:
            self.filter_summary_label.setText(summary_text)
            self.filter_summary_label.setVisible(True)
        else:
            self.filter_summary_label.setText("")
            self.filter_summary_label.setVisible(
                True
            )  # Keep visible to maintain consistent spacing
    
    def update_search_summary(self, search_text: str):
        """Update the filter summary text to include search term when search starts"""
        if not self.filter_summary_label:
            return
        
        # Build filter summary text
        summary_parts = []
        for filter_type, values in self.active_filters.items():
            if values:
                summary_parts.extend(values)
        
        # Create the combined summary text
        if search_text and summary_parts:
            summary_text = f"{SEARCH_RESULTS_LABEL} \"{search_text}\". Filtered by: {', '.join(summary_parts)}"
        elif search_text:
            summary_text = f'{SEARCH_RESULTS_LABEL} "{search_text}"'
        elif summary_parts:
            summary_text = f"Filtered by: {', '.join(summary_parts)}"
        else:
            summary_text = ""
        
        if summary_text:
            self.filter_summary_label.setText(summary_text)
            self.filter_summary_label.setVisible(True)
        else:
            self.filter_summary_label.setText("")
            self.filter_summary_label.setVisible(
                True
            )  # Keep visible to maintain consistent spacing
    
    def get_active_filters(self):
        """Get all active filters"""
        return self.active_filters.copy()
    
    def clear_all_filters(self):
        """Clear all active filters"""
        # Remove all filter pills
        for key, pill in list(self.filter_tags.items()):
            pill.animate_out()
        
        # Clear the layout completely
        layout = self.filter_tags_container.findChild(QHBoxLayout, "filterTagsLayout")
        if layout:
            # Remove all items from layout
            while layout.count() > 0:
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        
        # Clear active filters
        self.active_filters.clear()
        self.filter_tags.clear()
        
        # Uncheck all dropdown checkboxes
        self.uncheck_all_dropdown_items()
        
        # Update summary
        self.update_filter_summary()
        
        # Trigger search update
        self.search_controller.on_filters_changed()
        
        debug("✅ Cleared all filters")
    
    def uncheck_all_dropdown_items(self):
        """Uncheck all dropdown checkboxes when clearing all filters"""
        # Uncheck all checkboxes in all dropdowns
        for dropdown_name in ["instruments", "genres", "vendor"]:
            dropdown = getattr(self, f"{dropdown_name}_dropdown", None)
            if dropdown and hasattr(dropdown, "checkboxes"):
                for checkbox in dropdown.checkboxes.values():
                    checkbox.setChecked(False)
                debug(f"🔍 Unchecked all items in {dropdown_name} dropdown")
    
    def remove_filter_bubble_callback(self, filter_type, filter_value):
        """Callback for when a filter bubble is removed"""
        debug(f"🔍 Filter bubble X clicked: filter_type={filter_type}, filter_value={filter_value}")
        debug(f"🔍 Current active_filters before removal: {self.active_filters}")
        
        # Find which filter type this value belongs to
        for filter_type, values in self.active_filters.items():
            if filter_value in values:
                debug(f"🔍 Found filter to remove: {filter_type} -> {filter_value}")
                self.remove_filter(filter_type, filter_value)
                break
        else:
            warning(f"⚠️ Could not find filter to remove: {filter_value}")
    
    def on_filter_checkbox_changed(self, dropdown_name, item_name, checked):
        """Handle filter checkbox changes"""
        # Map dropdown names to filter types
        filter_type_map = {
            "instruments": "Instrument",
            "genres": "Genre",
            "vendor": "Vendor",
        }
        
        filter_type = filter_type_map.get(dropdown_name, dropdown_name.title())
        
        # Extract the display value from item name (remove the prefix)
        if dropdown_name == "instruments":
            # Map item names to display values
            value_map = {
                "instrumentsSynth": "Synth",
                "instrumentsDrums": "Drums",
                "instrumentsVocals": "Vocals",
                "instrumentsSnares": "Snares",
                "instrumentsModular": "Modular",
                "instrumentsPercussion": "Percussion",
                "instrumentsPiano": "Piano",  # Added Piano
            }
            filter_value = value_map.get(item_name, item_name)
        elif dropdown_name == "genres":
            value_map = {
                "genresAction": "Action",
                "genresTrailer": "Trailer",
                "genresJazz": "Jazz",
                "genresElectronic": "Electronic",
                "genresDark": "Dark",  # Added Dark
            }
            filter_value = value_map.get(item_name, item_name)
        elif dropdown_name == "vendor":
            value_map = {
                "vendorNativeInstruments": "Native Instruments",
                "vendorSpitfire": "Spitfire",  # Changed to just "Spitfire"
                "vendorEastWest": "EastWest",
                "vendorAuthenticSoundware": "Authentic Soundware",
            }
            filter_value = value_map.get(item_name, item_name)
        else:
            filter_value = item_name
        
        if checked:
            # Add filter
            self.add_filter(filter_type, filter_value)
        else:
            # Remove filter
            self.remove_filter(filter_type, filter_value)
        
        # Close the dropdown after selection
        dropdown = getattr(self, f"{dropdown_name}_dropdown", None)
        if dropdown:
            dropdown.hide()
    
    def _setup_file_watcher(self):
        """Setup the comprehensive file index manager"""
        try:
            from utils.database.file_index_manager import FileIndexManager
            import appdirs
            from settings.core_settings import APP_NAME, APP_AUTHOR
            
            # Get database path
            config_dir = appdirs.user_config_dir(APP_NAME, APP_AUTHOR)
            db_path = os.path.join(config_dir, "patchio_index.db")
            
            # Get indexed folders from settings
            indexed_folders = set(self.settings_model.get_setting("search_folders", []))
            
            # DON'T start file watcher if no folders configured
            if not indexed_folders:
                warning("⚠️ File index manager not started - no folders configured")
                debug("   Configure folders in Preferences to enable scanning")
                return
            
            if indexed_folders:
                # Create comprehensive file index manager
                self.file_index_manager = FileIndexManager(db_path, indexed_folders)
                
                # Only start sync worker if one doesn't already exist
                if not hasattr(self, "sync_worker") or self.sync_worker is None:
                    # Start background sync worker to avoid blocking UI
                    info("🔄 Starting background file index sync...")
                    self.sync_worker = BackgroundSyncWorker(db_path, indexed_folders)
                    self.sync_worker.sync_progress.connect(self._on_sync_progress)
                    self.sync_worker.sync_completed.connect(self._on_sync_completed)
                    self.sync_worker.sync_failed.connect(self._on_sync_failed)
                    # 🚀 NEW: Connect detailed scan progress signal
                    self.sync_worker.scan_progress.connect(self._on_scan_progress)
                    self.sync_worker.start_scan_ui.connect(self._on_start_scan_ui)
                    self.sync_worker.start()
                else:
                    warning("⚠️ Sync worker already exists, skipping creation")
                
                # Note: Scan progress will be started after UI is fully initialized
                
                # Start real-time monitoring immediately (doesn't block)
                def handle_file_event(event):
                    debug(f"📁 Real-time event: {event.event_type} - {os.path.basename(event.path)}")
                
                self.file_index_manager.start_real_time_monitoring(handle_file_event)
                debug("✅ File index manager started for {} folders".format(len(indexed_folders)))
            else:
                warning("⚠️ File index manager not started - no indexed folders configured")
                
        except Exception as e:
            error("❌ Failed to setup file index manager: {}".format(e))
    
    def _on_sync_progress(self, message: str):
        """Handle sync progress updates"""
        debug(message)
    
    def _on_scan_progress(self, progress_info: dict):
        """🚀 Handle detailed scan progress updates"""
        # Update the main window with detailed progress information
        if hasattr(self.main_window, "update_scan_progress_data"):
            self.main_window.update_scan_progress_data(progress_info)
    
    def _on_start_scan_ui(self):
        """🚀 Handle start scan UI signal"""
        if hasattr(self.main_window, "start_scan_progress"):
            self.main_window.start_scan_progress()
    
    def _on_sync_completed(self, sync_results: dict):
        """Handle sync completion"""
        info(f"✅ Background sync completed: {sync_results}")
        
        # Print detailed completion message
        sync_time = sync_results.get("sync_time", 0)
        files_added = sync_results.get("files_added", 0)
        files_removed = sync_results.get("files_removed", 0)
        files_updated = sync_results.get("files_updated", 0)
        
        if files_added > 0 or files_removed > 0 or files_updated > 0:
            info(f"✅ Background sync completed in {sync_time:.2f}s: +{files_added} -{files_removed} ~{files_updated}")
        else:
            info(f"⚡ Background sync completed in {sync_time:.2f}s: No changes needed")
        
        # 🚀 Complete scan progress in UI
        if hasattr(self.main_window, "complete_scan_progress"):
            self.main_window.complete_scan_progress(sync_results)
        
        # Start vendor extraction worker after sync completes
        self._start_vendor_extraction_worker()
        
        # Properly clean up the sync worker thread with a slight delay
        if hasattr(self, 'sync_worker') and self.sync_worker:
            debug("🧹 Cleaning up sync worker thread...")
            # Use QTimer to delay cleanup slightly to ensure thread has finished
            QTimer.singleShot(100, self._cleanup_sync_worker)
    
    def _cleanup_sync_worker(self):
        """Clean up the sync worker thread"""
        if hasattr(self, 'sync_worker') and self.sync_worker:
            debug("🧹 Performing sync worker cleanup...")
            self.sync_worker.quit()
            self.sync_worker.wait(5000)  # Wait up to 5 seconds for thread to finish
            if self.sync_worker.isRunning():
                warning("⚠️ Sync worker still running, forcing termination...")
                self.sync_worker.terminate()
                self.sync_worker.wait(1000)  # Wait 1 more second
            self.sync_worker.deleteLater()
            self.sync_worker = None
            debug("✅ Sync worker thread cleaned up successfully")
    
    def _start_vendor_extraction_worker(self):
        """Start the vendor extraction worker"""
        try:
            import appdirs
            from settings.core_settings import APP_NAME, APP_AUTHOR
            
            # Get database path
            config_dir = appdirs.user_config_dir(APP_NAME, APP_AUTHOR)
            db_path = os.path.join(config_dir, "patchio_index.db")
            
            # Only start if we don't already have one running
            if not hasattr(self, 'vendor_extraction_worker') or self.vendor_extraction_worker is None:
                info("🔍 Starting background vendor extraction...")
                self.vendor_extraction_worker = BackgroundVendorExtractionWorker(db_path)
                self.vendor_extraction_worker.extraction_progress.connect(self._on_vendor_extraction_progress)
                self.vendor_extraction_worker.extraction_completed.connect(self._on_vendor_extraction_completed)
                self.vendor_extraction_worker.start()
            else:
                warning("⚠️ Vendor extraction worker already running")
                
        except Exception as e:
            error(f"❌ Error starting vendor extraction worker: {e}")
    
    def _on_vendor_extraction_progress(self, message: str):
        """Handle vendor extraction progress updates"""
        debug(f"🔍 Vendor extraction: {message}")
    
    def _on_vendor_extraction_completed(self, results: dict):
        """Handle vendor extraction completion"""
        files_processed = results.get("files_processed", 0)
        files_updated = results.get("files_updated", 0)
        
        if files_updated > 0:
            info(f"✅ Vendor extraction completed: {files_updated} files updated with vendor/library information")
        else:
            warning("✅ Vendor extraction completed: No files needed updating")
        
        # Clean up the vendor extraction worker
        if hasattr(self, "vendor_extraction_worker") and self.vendor_extraction_worker:
            self.vendor_extraction_worker.quit()
            self.vendor_extraction_worker.wait(5000)
            if self.vendor_extraction_worker.isRunning():
                self.vendor_extraction_worker.terminate()
                self.vendor_extraction_worker.wait(1000)
            self.vendor_extraction_worker.deleteLater()
            self.vendor_extraction_worker = None
    
    def _on_sync_failed(self, error_message: str):
        """Handle sync failure"""
        error(f"❌ Background sync failed: {error_message}")
        
        # 🚀 Cancel scan progress in UI
        if hasattr(self.main_window, "cancel_scan_progress"):
            self.main_window.cancel_scan_progress()
        
        # Properly clean up the sync worker thread with a slight delay
        if hasattr(self, 'sync_worker') and self.sync_worker:
            debug("🧹 Cleaning up sync worker thread after failure...")
            # Use QTimer to delay cleanup slightly to ensure thread has finished
            QTimer.singleShot(100, self._cleanup_sync_worker)
    
    def _handle_file_event(self, event: FileEvent):
        """Handle file system events from the professional watcher"""
        try:
            # Import here to avoid circular imports
            from utils.database.file_watcher import init_event_tracking_db
            import appdirs
            from settings.core_settings import APP_NAME, APP_AUTHOR
            
            # Get database path
            config_dir = appdirs.user_config_dir(APP_NAME, APP_AUTHOR)
            db_path = os.path.join(config_dir, "patchio_index.db")
            
            # Initialize event tracking if needed
            init_event_tracking_db(db_path)
            
            # Process the event based on type
            if event.event_type == "created":
                self._add_file_to_database(db_path, event.path)
            elif event.event_type == "deleted":
                self._remove_file_from_database(db_path, event.path)
            elif event.event_type == "moved":
                self._move_file_in_database(db_path, event.path, event.dest_path)
            elif event.event_type == "modified":
                self._update_file_in_database(db_path, event.path)
            
            # Log the event
            debug(f"📁 {event.event_type.upper()}: {os.path.basename(event.path)}")
            
        except Exception as e:
            error(f"❌ Error handling file event: {e}")
    
    def _add_file_to_database(self, db_path: str, file_path: str):
        """Add a file to the database using existing logic"""
        try:
            conn = sqlite3.connect(db_path, timeout=10.0)
            cursor = conn.cursor()
            
            # Get indexed folders from settings
            indexed_folders = set(self.settings_model.get_setting("search_folders", []))
            
            # Use the existing file watcher logic
            from utils.database.file_watcher import PatchIOFileHandler

            handler = PatchIOFileHandler(db_path, indexed_folders)
            handler._add_file_to_db(cursor, file_path)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            error(f"❌ Error adding file to database: {e}")
    
    def _remove_file_from_database(self, db_path: str, file_path: str):
        """Remove a file from the database using existing logic"""
        try:
            conn = sqlite3.connect(db_path, timeout=10.0)
            cursor = conn.cursor()
            
            # Get indexed folders from settings
            indexed_folders = set(self.settings_model.get_setting("search_folders", []))
            
            # Use the existing file watcher logic
            from utils.database.file_watcher import PatchIOFileHandler

            handler = PatchIOFileHandler(db_path, indexed_folders)
            handler._remove_file_from_db(cursor, file_path)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            error(f"❌ Error removing file from database: {e}")
    
    def _move_file_in_database(self, db_path: str, old_path: str, new_path: str):
        """Move/rename a file in the database using existing logic"""
        try:
            conn = sqlite3.connect(db_path, timeout=10.0)
            cursor = conn.cursor()
            
            # Get indexed folders from settings
            indexed_folders = set(self.settings_model.get_setting("search_folders", []))
            
            # Use the existing file watcher logic
            from utils.database.file_watcher import PatchIOFileHandler

            handler = PatchIOFileHandler(db_path, indexed_folders)
            handler._move_file_in_db(cursor, old_path, new_path)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            error(f"❌ Error moving file in database: {e}")
    
    def _update_file_in_database(self, db_path: str, file_path: str):
        """Update a file in the database using existing logic"""
        try:
            conn = sqlite3.connect(db_path, timeout=10.0)
            cursor = conn.cursor()
            
            # Get indexed folders from settings
            indexed_folders = set(self.settings_model.get_setting("search_folders", []))
            
            # Use the existing file watcher logic
            from utils.database.file_watcher import PatchIOFileHandler

            handler = PatchIOFileHandler(db_path, indexed_folders)
            handler._update_file_in_db(cursor, file_path)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            error(f"❌ Error updating file in database: {e}")
    
    def stop_file_watcher(self):
        """Stop the file index manager when application closes"""
        if hasattr(self, "file_index_manager") and self.file_index_manager:
            self.file_index_manager.stop_real_time_monitoring()
            info("🛑 File index manager stopped")
        
        # Stop background sync worker if running
        if hasattr(self, "sync_worker") and self.sync_worker.isRunning():
            self.sync_worker.quit()
            self.sync_worker.wait()
    
    def sync_index_with_filesystem(self, force_full_sync: bool = False) -> Dict:
        """
        Public method to sync the file index with the filesystem
        
        Args:
            force_full_sync: If True, performs full rescan regardless of timestamps
            
        Returns:
            Dictionary with sync statistics
        """
        if hasattr(self, "file_index_manager") and self.file_index_manager:
            return self.file_index_manager.sync_index_with_filesystem(force_full_sync)
        else:
            warning("⚠️ File index manager not available")
            return {}
    
    def get_file_metadata(self, file_path: str) -> Optional[Dict]:
        """Get metadata for a specific file"""
        if hasattr(self, "file_index_manager") and self.file_index_manager:
            return self.file_index_manager.get_file_metadata(file_path)
        return None
    
    def update_file_metadata(self, file_path: str, metadata: Dict):
        """Update metadata for a specific file"""
        if hasattr(self, "file_index_manager") and self.file_index_manager:
            self.file_index_manager.update_file_metadata(file_path, metadata)
    
    def search_files(self, query: str, limit: int = 100) -> List[Dict]:
        """Search for files in the index"""
        if hasattr(self, "file_index_manager") and self.file_index_manager:
            return self.file_index_manager.search_files(query, limit)
        return []
    
    def get_index_statistics(self) -> Dict:
        """Get file index statistics"""
        if hasattr(self, 'file_index_manager') and self.file_index_manager:
            return self.file_index_manager.get_statistics()
        return {} 