#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Search Controller - MVC Controller for search functionality
Handles search logic and results display
"""

import os
import threading
import queue
from typing import List, Dict, Any
from PySide6.QtWidgets import QTreeWidgetItem
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QTreeWidget, QHeaderView
from PySide6.QtCore import Qt

from models.search_model import SearchModel
from models.file_model import FileModel
from views.main_window import MainWindowView
from views.results_tree_bubble_widget import ResultsTreeBubbleWidget
from utils.logger import debug, info, warning, error
from settings.core_settings import INITIAL_SEARCH_MODE

# Constants for UI text labels
SEARCH_RESULTS_LABEL = "Search results for:"


class SearchController:
    """Search controller - handles search logic and results display"""

    def __init__(
        self,
        search_model: SearchModel,
        file_model: FileModel,
        main_window: MainWindowView,
    ):
        self.search_model = search_model
        self.file_model = file_model
        self.main_window = main_window

        # Search state
        self.current_mode = INITIAL_SEARCH_MODE
        self.current_query = ""
        self.current_search_term = ""  # Store the search term from search bar
        self.search_queue = queue.Queue()
        self.search_thread = None
        self.current_search_id = 0  # Track current search ID
        self.should_stop_search = False  # Flag to stop current search

        # Library tracking for dynamic results
        self.library_nodes = {}

        # Performance optimization: Result batching
        self.pending_results = []
        self.last_update_time = 0
        self.update_throttle_ms = 100  # Update UI every 100ms instead of 25ms
        self.batch_size = 10  # Process results in batches of 10

        # Dynamic performance adjustment for large result sets
        self.total_results_processed = 0
        self.performance_adjustment_threshold = 100  # Adjust after 100 results

        # Setup polling for dynamic results with reduced frequency
        self.polling_timer = QTimer()
        self.polling_timer.timeout.connect(self.poll_search_results)
        self.polling_timer.start(
            100
        )  # Poll every 100ms instead of 25ms for better performance

        # Setup double-click handler for opening parent folder
        self.setup_double_click_handler()

        # Filter management - use main controller's active filters instead
        # self.active_filters = {}  # Removed - using main controller's filters

        # Search query building
        self.current_search_text = ""  # Store the search text from search bar

    def on_search_triggered(self):
        """Handle search trigger from UI - ChatGPT style: stop current search and start new one"""
        # Convert any free text to bubbles before search
        self.convert_free_text_to_bubbles()

        # Get search text from search bar
        search_text = ""
        if self.main_window.search_input:
            if hasattr(self.main_window.search_input, "get_text"):
                search_text = self.main_window.search_input.get_text()
            else:
                search_text = self.main_window.search_input.text()

        # Don't start search if there's no search text and no active filters
        main_controller_filters = (
            self.main_controller.get_active_filters()
            if hasattr(self, "main_controller")
            else {}
        )
        if not search_text.strip() and not main_controller_filters:
            debug("🛑 No search text and no active filters - not starting search")
            return

        # Stop current search if running (ChatGPT style)
        if self.search_thread and self.search_thread.is_alive():
            info("🛑 Stopping current search to start new one...")
            self.should_stop_search = True

        # Save the search text
        self.current_search_text = search_text.strip()

        # Build the complete query using search text and active filters
        query = self.build_search_query(search_text.strip())

        self.current_query = query
        self.main_window.clear_results()
        self.library_nodes = {}  # Clear library tracking for new search

        # Start progress tracking
        self.main_window.start_search_progress(query)

        # Start search in background thread
        self.start_search(query)

    def start_search_with_text(self, text: str):
        """Start search with specific text from search bar"""
        if not text.strip():
            return

        # Stop current search if running
        if self.search_thread and self.search_thread.is_alive():
            info("🛑 Stopping current search to start new one...")
            self.should_stop_search = True

        # Save the search text
        self.current_search_text = text.strip()

        # Build the complete query using search text and active filters
        query = self.build_search_query(text.strip())

        # Set as current query
        self.current_query = query
        self.main_window.clear_results()
        self.library_nodes = {}  # Clear library tracking for new search

        # Start progress tracking
        self.main_window.start_search_progress(query)

        # Start search in background thread
        self.start_search(query)

    def build_search_query(
        self, search_text: str = None, active_filters: dict = None
    ) -> str:
        """Build search query from search text and active filters using AND logic"""
        # Use provided parameters or get from current state
        if search_text is None:
            search_text = self.current_search_text

        if active_filters is None:
            if hasattr(self, "main_controller") and hasattr(
                self.main_controller, "get_active_filters"
            ):
                active_filters = self.main_controller.get_active_filters()
            else:
                active_filters = {}

        # Build query parts
        query_parts = []

        # Add search text if it exists - split into individual words and quote each
        if search_text and search_text.strip():
            # Split search text into individual words and quote each one
            search_words = search_text.strip().split()
            quoted_search_terms = [f'"{word}"' for word in search_words if word.strip()]
            if quoted_search_terms:
                # Join search terms with AND operator
                search_query = " AND ".join(quoted_search_terms)
                query_parts.append(search_query)

        # Add filter queries
        if active_filters:
            for filter_type, filter_values in active_filters.items():
                if filter_values:
                    # Wrap each filter value in quotes for exact matching
                    quoted_terms = [f'"{term}"' for term in filter_values]
                    # Join terms within the same group with OR
                    group_query = " OR ".join(quoted_terms)
                    query_parts.append(group_query)

        # Combine all parts with AND logic
        combined_query = " AND ".join(query_parts)

        return combined_query

    def convert_free_text_to_bubbles(self):
        """Convert any free text in the search input to bubbles"""
        if not self.main_window.search_input:
            return

        # Convert free text to bubbles (we always use bubble search input)
        if hasattr(self.main_window.search_input, "convert_free_text_to_bubbles"):
            self.main_window.search_input.convert_free_text_to_bubbles()

    def on_mode_changed(self, mode: str):
        try:
            debug(f"🔄 Search mode changed to: {mode}")
            self.current_mode = mode

            # mirror to main controller so the view's helper methods can read it
            if hasattr(self, "main_controller"):
                setattr(self.main_controller, "current_mode", mode)

            # also set the view’s own field if it has one
            if hasattr(self.main_window, "current_search_mode"):
                self.main_window.current_search_mode = mode

            # now safe to call view helpers
            if self.main_window:
                self.main_window.update_mode_buttons()
                self.main_window.update_search_tooltip()
                self.main_window.switch_search_input(mode)

            debug(f"✅ Mode changed to {mode} - current results preserved")
        except Exception as e:
            error(f"⚠️ Error changing search mode: {e}")

    def on_search_cancelled(self):
        """Handle search cancellation (Escape key) - ChatGPT style: cancel without starting new search"""
        if self.search_thread and self.search_thread.is_alive():
            info("🛑 Cancelling search (Escape key)...")
            self.should_stop_search = True

        # Clear the search queue to prevent any remaining results from being processed
        while not self.search_queue.empty():
            try:
                self.search_queue.get_nowait()
            except queue.Empty:
                break

        # Clear pending results
        self.pending_results = []

        # Stop the polling timer to prevent repeated cancellation checks
        if hasattr(self, "polling_timer") and self.polling_timer.isActive():
            self.polling_timer.stop()
            debug("🛑 Stopped polling timer after search cancellation")

        # Always reset the UI to cancelled state
        self.main_window.cancel_search_progress()

    def on_advanced_filters_toggled(self, is_enabled: bool):
        """Handle advanced filters toggle"""
        try:
            debug(f"🔧 Advanced filters toggled: {is_enabled}")

            if is_enabled:
                # Show advanced filters interface
                # TODO: Implement advanced filters UI
                info("🔧 Advanced filters enabled - TODO: Show advanced interface")

                # For now, we can switch to keywords editor mode which has advanced functionality
                self.on_mode_changed("keywords_editor")
            else:
                # Hide advanced filters interface
                # TODO: Hide advanced filters UI
                info("🔧 Advanced filters disabled - TODO: Hide advanced interface")

                # Switch back to classic search mode
                self.on_mode_changed("classic_search")

        except Exception as e:
            error(f"❌ Error toggling advanced filters: {e}")

    def on_search_cleared(self):
        """Handle search clear (X button) - ChatGPT style: cancel and clear results"""
        if self.search_thread and self.search_thread.is_alive():
            info("🛑 Cancelling search and clearing results (X button)...")
            self.should_stop_search = True

        # Clear the search queue to prevent any remaining results from being processed
        while not self.search_queue.empty():
            try:
                self.search_queue.get_nowait()
            except queue.Empty:
                break

        # Clear pending results
        self.pending_results = []

        # Stop the polling timer to prevent repeated cancellation checks
        if hasattr(self, "polling_timer") and self.polling_timer.isActive():
            self.polling_timer.stop()
            debug("🛑 Stopped polling timer after search clear")

        # Clear search input
        if self.main_window.search_input:
            self.main_window.search_input.clear()

        # Clear results and reset search state
        self.main_window.clear_results()
        self.main_window.update_status_display(
            "Ready to search your sound files", "ready"
        )

        # Reset search state
        self.current_query = ""
        self.current_search_text = ""  # Also clear the search text

    def start_search(self, query: str):
        """Start search in background thread"""
        # Signal current search to stop
        self.should_stop_search = True

        # Stop any existing search with longer timeout
        if self.search_thread and self.search_thread.is_alive():
            info("🛑 Stopping previous search thread...")
            self.search_thread.join(timeout=1.0)  # Wait up to 1 second

        # Clear queue
        while not self.search_queue.empty():
            try:
                self.search_queue.get_nowait()
            except queue.Empty:
                break

        # Increment search ID for new search
        self.current_search_id += 1
        self.should_stop_search = False

        # Restart polling timer for new search
        if hasattr(self, "polling_timer"):
            if not self.polling_timer.isActive():
                self.polling_timer.start(100)  # Poll every 100ms
                debug("🔄 Restarted polling timer for new search")
            else:
                debug("🔄 Polling timer already active for new search")

        # Reset performance parameters for new search
        self.update_throttle_ms = 100
        self.batch_size = 10
        self.total_results_processed = 0
        self.pending_results = []

        # Start new search thread
        self.search_thread = threading.Thread(
            target=self._perform_search,
            args=(query, self.current_mode, self.current_search_id),
            daemon=True,
        )
        self.search_thread.start()
        debug(f"🚀 Started new search (ID: {self.current_search_id}) for: {query}")

    def _perform_search(self, query: str, mode: str, search_id: int):
        """Perform search in background thread with dynamic updates"""
        try:
            # Check if this search has been cancelled
            if self.should_stop_search or search_id != self.current_search_id:
                debug(f"🛑 Search {search_id} cancelled before starting")
                return

            # Clear results at start
            self.search_queue.put(
                {"type": "clear", "query": query, "mode": mode, "search_id": search_id}
            )

            if mode == "classic_search":
                self._perform_database_search_dynamic(query, search_id)
            elif mode == "ai":
                self._perform_ai_search_dynamic(query, search_id)
            elif mode == "advanced":
                self._perform_advanced_search_dynamic(query, search_id)

            # Check if search was cancelled before completion
            if self.should_stop_search or search_id != self.current_search_id:
                debug(f"🛑 Search {search_id} cancelled before completion")
                return

            # Signal search completion
            self.search_queue.put(
                {
                    "type": "complete",
                    "query": query,
                    "mode": mode,
                    "search_id": search_id,
                }
            )

        except Exception as e:
            error(f"⚠️ Search error: {e}")
            self.search_queue.put(
                {
                    "type": "error",
                    "query": query,
                    "mode": mode,
                    "error": str(e),
                    "search_id": search_id,
                }
            )

    def apply_filters_to_result(self, result: Dict[str, Any]) -> bool:
        """Apply active filters to a search result. Returns True if result passes all filters."""
        # Get the main controller to access active filters
        if not hasattr(self, 'main_controller') or not hasattr(self.main_controller, 'get_active_filters'):
            debug(f"🔍 DEBUG: No main controller or get_active_filters method")
            return True  # No main controller, skip filtering

        active_filters = self.main_controller.get_active_filters()
        debug(f"🔍 DEBUG: Active filters from main controller: {active_filters}")
        
        if not active_filters:
            debug(f"🔍 DEBUG: No active filters found")
            return True  # No active filters

        # Apply each filter type with AND logic between all filter types
        for filter_type, filter_values in active_filters.items():
            if not filter_values:
                continue
            
            debug(f"🔍 DEBUG: Checking filter type '{filter_type}' with values: {filter_values}")
            
            # Handle different filter types
            if filter_type == "search":
                # Search filters: check if any search term matches the file path or name
                file_path = result.get("path", "").lower()
                file_name = result.get("name", "").lower()
                file_text = f"{file_path} {file_name}"
                
                debug(f"🔍 DEBUG: Search filter - file text: '{file_text}'")
                
                # All search filter values must match (AND logic)
                for search_term in filter_values:
                    if search_term.lower() not in file_text:
                        warning(f"🔍 DEBUG: Search term '{search_term}' not found in file text")
                        return False  # This result doesn't match all search filters

            elif filter_type == "instruments":
                # Instrument filters: check if any instrument term matches the file
                file_path = result.get("path", "").lower()
                file_name = result.get("name", "").lower()
                file_text = f"{file_path} {file_name}"
                
                debug(f"🔍 DEBUG: Instrument filter - file text: '{file_text}'")
                
                # At least one instrument filter must match (OR logic within instruments)
                instrument_match = False
                for instrument_term in filter_values:
                    if instrument_term.lower() in file_text:
                        instrument_match = True
                        debug(f"🔍 DEBUG: Instrument term '{instrument_term}' found in file text")
                        break

                if not instrument_match:
                    debug(f"🔍 DEBUG: No instrument terms found in file text")
                    return False  # This result doesn't match any instrument filter

            elif filter_type == "genres":
                # Genre filters: check if any genre term matches the file
                file_path = result.get("path", "").lower()
                file_name = result.get("name", "").lower()
                file_text = f"{file_path} {file_name}"
                
                debug(f"🔍 DEBUG: Genre filter - file text: '{file_text}'")
                
                # At least one genre filter must match (OR logic within genres)
                genre_match = False
                for genre_term in filter_values:
                    if genre_term.lower() in file_text:
                        genre_match = True
                        debug(f"🔍 DEBUG: Genre term '{genre_term}' found in file text")
                        break

                if not genre_match:
                    debug(f"🔍 DEBUG: No genre terms found in file text")
                    return False  # This result doesn't match any genre filter

            elif filter_type == "vendor":
                # Vendor filters: check if any vendor term matches the file
                file_path = result.get("path", "").lower()
                file_name = result.get("name", "").lower()
                file_text = f"{file_path} {file_name}"
                
                debug(f"🔍 DEBUG: Vendor filter - file text: '{file_text}'")
                
                # At least one vendor filter must match (OR logic within vendors)
                vendor_match = False
                for vendor_term in filter_values:
                    if vendor_term.lower() in file_text:
                        vendor_match = True
                        debug(f"🔍 DEBUG: Vendor term '{vendor_term}' found in file text")
                        break

                if not vendor_match:
                    debug(f"🔍 DEBUG: No vendor terms found in file text")
                    return False  # This result doesn't match any vendor filter
        
        debug(f"🔍 DEBUG: All filters passed for file: {result.get('name', '')}")
        return True  # Result passed all filters

    def _perform_simple_search_dynamic(self, query: str, search_id: int):
        """Perform simple search with dynamic result streaming"""
        debug(f"📁 Dynamic Simple Search: {query}")

        # Parse search terms with operators
        try:
            simple_raw = query.strip()
            or_terms, and_terms, not_terms, or_quoted, and_quoted, not_quoted = (
                self.search_model._parse_bubble_query(simple_raw)
            )
            debug(f"🔍 Parsed OR terms: {list(zip(or_terms, or_quoted))}")
            debug(f"🔍 Parsed AND terms: {list(zip(and_terms, and_quoted))}")
            debug(f"🔍 Parsed NOT terms: {list(zip(not_terms, not_quoted))}")
        except Exception as e:
            error(f"⚠️ Error parsing search terms: {e}")
            return

        # If no search terms but we have filters, search for all files and apply filters
        if not or_terms and not and_terms and self.active_filters:
            debug(f"🔍 No search terms but have filters, searching all files")
            or_terms = [""]  # Empty term to match all files
            or_quoted = [False]

        if not or_terms and not and_terms:
            debug("⚠️ No valid search terms found!")
            return

        excluded_folders = []
        total_matches = 0

        # Search each folder and stream results immediately
        for folder in self.search_model.search_folders:
            # Check if search has been cancelled
            if self.should_stop_search or search_id != self.current_search_id:
                debug(f"🛑 Search {search_id} cancelled during folder scan")
                return

            if not folder.exists():
                warning(f"⚠️ Folder doesn't exist: {folder}")
                continue

            debug(f"📂 Searching in: {folder}")
            folder_matches = 0

            try:
                # Use recursive scan and stream results immediately
                for file_path in self.search_model._recursive_scan(
                    str(folder), self.search_model.selected_extensions, excluded_folders
                ):
                    # Check if search has been cancelled during file scanning
                    if self.should_stop_search or search_id != self.current_search_id:
                        debug(f"🛑 Search {search_id} cancelled during file scanning")
                        return

                    full_path = file_path.lower()

                    # Classic search mode logic: OR/AND/NOT matching
                    # OR logic: any OR term must match
                    or_match = (not or_terms) or any(
                        (
                            self.search_model._matches_term(term, full_path, quoted)
                            if term
                            else True
                        )
                        for term, quoted in zip(or_terms, or_quoted)
                    )

                    # AND logic: all AND terms must match
                    and_match = (not and_terms) or all(
                        self.search_model._matches_term(term, full_path, quoted)
                        for term, quoted in zip(and_terms, and_quoted)
                    )

                    # NOT logic: no NOT terms should match
                    not_match = (not not_terms) or not any(
                        self.search_model._matches_term(term, full_path, quoted)
                        for term, quoted in zip(not_terms, not_quoted)
                    )

                    # File matches if: (OR matches) AND (AND matches) AND (NOT doesn't match)
                    if or_match and and_match and not_match:
                        folder_matches += 1
                        total_matches += 1

                        # Get file info
                        file_name = os.path.basename(file_path)

                        # Do expensive processing in background thread
                        library_name = self.file_model.extract_library_info(file_path)
                        file_type = self.file_model.get_file_type_info(file_path)

                        # Add search metadata
                        keywords = self.search_model.get_matched_keywords(
                            file_path, query
                        )
                        keywords_str = " • ".join(keywords) if keywords else ""

                        # Debug print for keywords
                        if keywords:
                            debug(f"[DEBUG] File: {file_name} → Keywords: {keywords}")
                        
                        tags = self.search_model.get_genre_keywords(file_path)
                        tags_str = " • ".join(tags) if tags else ""

                        # Create result with pre-processed metadata
                        result = {
                            "name": file_name,
                            "path": file_path,
                            "library_name": library_name,
                            "file_type": file_type,
                            "keywords": keywords_str,
                            "tags": tags_str,
                            "is_audio": True,
                        }

                        # Apply filters to this result
                        if not self.apply_filters_to_result(result):
                            debug(f"  ❌ Filtered out: {file_name}")
                            continue  # Skip this result if it doesn't pass filters

                        # Stream this result immediately with search ID
                        self.search_queue.put(
                            {
                                "type": "result",
                                "result": result,
                                "query": query,
                                "mode": "simple",
                                "search_id": search_id,
                            }
                        )

                        debug(f"  ✅ Found match: {file_name}")

            except Exception as e:
                error(f"  ⚠️ Cannot search in {folder}: {e}")
                continue

            debug(f"  📊 Folder {folder.name}: {folder_matches} matches")

        debug(f"📊 Dynamic simple search found {total_matches} matching files")

    def _perform_database_search_dynamic(self, query: str, search_id: int):
        """Perform database search with dynamic result streaming"""
        debug(f"🗄️ Dynamic Database Search: {query}")

        # Check if search has been cancelled
        if self.should_stop_search or search_id != self.current_search_id:
            debug(f"🛑 Search {search_id} cancelled before database search")
            return

        try:
            # Use the search model's database search method
            results = self.search_model.database_search(query)

            for result in results:
                # Check if search has been cancelled
                if self.should_stop_search or search_id != self.current_search_id:
                    debug(f"🛑 Search {search_id} cancelled during database search")
                    return

                # Add search metadata
                keywords = self.search_model.get_matched_keywords(result["path"], query)
                keywords_str = " • ".join(keywords) if keywords else ""

                # Debug print for keywords
                if keywords:
                    debug(f"[DEBUG] File: {result['name']} → Keywords: {keywords}")
                
                tags = self.search_model.get_genre_keywords(result['path'])
                tags_str = ' • '.join(tags) if tags else ''
                
                # Create enhanced result with pre-processed metadata
                enhanced_result = {
                    "name": result['name'],
                    "path": result['path'],
                    "library_name": result.get('project') or result.get('library', 'Unknown Library'),
                    "file_type": result.get('file_type', 'File'),
                    "keywords": keywords_str,
                    "tags": tags_str,
                    "vendor": result.get("vendor", "Unknown Vendor"),
                    "instrument": result.get("instrument", ""),
                    "genre": result.get("genre", ""),
                    "is_audio": True,
                }

                # Apply filters to this result
                if not self.apply_filters_to_result(enhanced_result):
                    debug(f"  ❌ Filtered out: {result['name']}")
                    continue  # Skip this result if it doesn't pass filters

                # Stream this result immediately with search ID
                self.search_queue.put(
                    {
                        "type": "result",
                        "result": enhanced_result,
                        "query": query,
                        "mode": "database",
                        "search_id": search_id,
                    }
                )

                debug(f"  ✅ Found match: {result['name']}")

            debug(f"📊 Dynamic database search found {len(results)} matching files")

        except Exception as e:
            error(f"⚠️ Database search error: {e}")
            self.search_queue.put(
                {
                    "type": "error",
                    "query": query,
                    "error": str(e),
                    "search_id": search_id,
                }
            )

    def _perform_ai_search_dynamic(self, query: str, search_id: int):
        """Perform AI search with dynamic result streaming"""
        debug(f"🤖 Dynamic AI Search: {query}")

        # Check if search has been cancelled
        if self.should_stop_search or search_id != self.current_search_id:
            debug(f"🛑 Search {search_id} cancelled before AI search")
            return

        # TODO: Later integrate with patchio.py AI functions
        # For now, return mock results to test UI
        mock_results = [
            {
                "name": f"AI: Epic Drums for '{query}'",
                "path": "/path/to/epic_drums.wav",
                "type": "AI Result",
            },
            {
                "name": f"AI: Cinematic Strings matching '{query}'",
                "path": "/path/to/strings.wav",
                "type": "AI Result",
            },
            {
                "name": f"AI: Dark Bass inspired by '{query}'",
                "path": "/path/to/bass.wav",
                "type": "AI Result",
            },
        ]

        for result in mock_results:
            # Check if search has been cancelled
            if self.should_stop_search or search_id != self.current_search_id:
                debug(f"🛑 Search {search_id} cancelled during AI search")
                return

            # Add metadata
            keywords = self.search_model.get_matched_keywords(result["path"], query)
            result["keywords"] = " • ".join(keywords) if keywords else ""

            # Debug print for keywords
            if keywords:
                debug(f"[DEBUG] File: {result['name']} → Keywords: {keywords}")
            
            tags = self.search_model.get_genre_keywords(result['path'])
            result['tags'] = ' • '.join(tags) if tags else ''
            
            # Apply filters to this result
            if not self.apply_filters_to_result(result):
                debug(f"  ❌ Filtered out AI result: {result['name']}")
                continue  # Skip this result if it doesn't pass filters

            # Stream result immediately with search ID
            self.search_queue.put(
                {
                    "type": "result",
                    "result": result,
                    "query": query,
                    "mode": "ai",
                    "search_id": search_id,
                }
            )

    def _perform_advanced_search_dynamic(self, query: str, search_id: int):
        """Perform advanced search with dynamic result streaming"""
        debug(f"⚙️ Dynamic Advanced Search: {query}")

        # Check if search has been cancelled
        if self.should_stop_search or search_id != self.current_search_id:
            debug(f"🛑 Search {search_id} cancelled before advanced search")
            return

        # TODO: Later integrate with patchio.py advanced search
        # For now, return mock results to test UI
        mock_results = [
            {
                "name": f"Advanced: Complex Pattern for '{query}'",
                "path": "/path/to/pattern.wav",
                "type": "Advanced Result",
            },
            {
                "name": f"Advanced: Filtered Sound matching '{query}'",
                "path": "/path/to/filtered.wav",
                "type": "Advanced Result",
            },
        ]

        for result in mock_results:
            # Check if search has been cancelled
            if self.should_stop_search or search_id != self.current_search_id:
                debug(f"🛑 Search {search_id} cancelled during advanced search")
                return

            # Add metadata
            keywords = self.search_model.get_matched_keywords(result["path"], query)
            result["keywords"] = " • ".join(keywords) if keywords else ""

            # Debug print for keywords
            if keywords:
                debug(f"[DEBUG] File: {result['name']} → Keywords: {keywords}")
            
            tags = self.search_model.get_genre_keywords(result['path'])
            result['tags'] = ' • '.join(tags) if tags else ''
            
            # Apply filters to this result
            if not self.apply_filters_to_result(result):
                debug(f"  ❌ Filtered out advanced result: {result['name']}")
                continue  # Skip this result if it doesn't pass filters

            # Stream result immediately with search ID
            self.search_queue.put(
                {
                    "type": "result",
                    "result": result,
                    "query": query,
                    "mode": "advanced",
                    "search_id": search_id,
                }
            )

    def poll_search_results(self):
        """Poll for search results from background thread with dynamic updates and batching"""
        try:
            import time

            current_time = time.time() * 1000  # Convert to milliseconds

            # Throttle updates to prevent UI freezing
            if current_time - self.last_update_time < self.update_throttle_ms:
                return

            self.last_update_time = current_time

            # Check if search has been cancelled - if so, clear pending results and stop processing
            if self.should_stop_search:
                debug(
                    "🛑 Search cancelled - clearing pending results and stopping processing"
                )
                self.pending_results = []
                return

            # Process results in batches
            results_processed = 0
            while not self.search_queue.empty() and results_processed < self.batch_size:
                result_data = self.search_queue.get_nowait()

                # Check if this result belongs to the current search
                result_search_id = result_data.get("search_id", 0)
                if result_search_id != self.current_search_id:
                    warning(
                        f"🛑 Ignoring result from old search {result_search_id} (current: {self.current_search_id})"
                    )
                    continue

                # Handle different result types
                result_type = result_data.get("type", "unknown")

                if result_type == "clear":
                    # Clear results at start of new search
                    self.main_window.clear_results()
                    self.main_window.show_status_message(
                        f"{SEARCH_RESULTS_LABEL} {result_data.get('query', '')}"
                    )
                    self.pending_results = []  # Clear pending results

                elif result_type == "result":
                    # Add to pending results for batch processing
                    self.pending_results.append(result_data["result"])
                    results_processed += 1

                elif result_type == "complete":
                    # Process any remaining pending results
                    if self.pending_results:
                        self.process_pending_results()

                    # Search completed
                    total_files = sum(
                        lib_data["count"] for lib_data in self.library_nodes.values()
                    )
                    total_libraries = len(self.library_nodes)
                    self.main_window.complete_search_progress(
                        total_files, total_libraries
                    )

                elif result_type == "error":
                    # Search error
                    error_msg = result_data.get("error", "Unknown error")
                    self.main_window.update_status_display(
                        f"❌ Search error: {error_msg}", "error"
                    )

                else:
                    # Handle legacy format for backward compatibility
                    if "error" in result_data:
                        self.main_window.show_error_message(result_data["error"])
                    elif "results" in result_data:
                        self.update_results_display(result_data)

            # Process pending results if we have enough or if it's been a while
            # But only if search hasn't been cancelled
            if not self.should_stop_search and (
                len(self.pending_results) >= self.batch_size
                or (self.pending_results and results_processed == 0)
            ):
                self.process_pending_results()

        except queue.Empty:
            pass

    def process_pending_results(self):
        """Process a batch of results from the pending_results list"""
        if not self.pending_results:
            return

        # Check if search has been cancelled - if so, clear pending results and stop processing
        if self.should_stop_search:
            debug(
                "🛑 Search cancelled - clearing pending results and stopping processing"
            )
            self.pending_results = []
            return

        try:
            debug(f"🔧 Processing batch of {len(self.pending_results)} results")

            # Create tree widget if it doesn't exist yet
            if not self.main_window.results_tree:
                debug("🔧 Creating results tree for first result")
                self.main_window.results_tree = self.main_window.create_tree_widget()

                if not self.main_window.results_tree:
                    warning("⚠️ Could not create results tree")
                    return

                # Setup double-click handler for the new tree
                self.setup_double_click_handler()

                # Initialize library tracking
                self.library_nodes = {}

            # Add individual results to the display
            for result in self.pending_results:
                # Check if search has been cancelled before processing each result
                if self.should_stop_search:
                    debug("🛑 Search cancelled during result processing - stopping")
                    self.pending_results = []
                    return
                self.add_single_result_optimized(result)

            # Update status with current count
            total_files = sum(
                lib_data["count"] for lib_data in self.library_nodes.values()
            )
            total_libraries = len(self.library_nodes)
            self.main_window.update_search_counts(total_files, total_libraries)

            debug(
                f"✅ Processed batch: {total_files} files in {total_libraries} libraries"
            )

            # Clear the pending results list after processing
            self.pending_results = []

            # Perform final UI update after batch processing (much more efficient than per-result updates)
            if self.main_window.results_tree:
                # Auto-resize columns once after batch
                self.main_window.results_tree.resizeColumnToContents(0)
                # Force viewport update once after batch
                self.main_window.results_tree.viewport().update()

            # Update total results processed and adjust performance if needed
            self.total_results_processed += len(self.pending_results)
            self.adjust_performance_for_large_results()

        except Exception as e:
            error(f"⚠️ Error processing pending results: {e}")
            import traceback

            traceback.print_exc()

    def add_single_result_optimized(self, result: Dict[str, Any]):
        """Add a single result to the display with optimized performance (no expensive per-result operations)"""
        try:
            # Use pre-processed data from background thread
            file_path = result.get("path", "")
            file_name = result.get("name", "")
            library_name = result.get("library_name", "Unknown Library")
            file_type = result.get("file_type", "File")

            # Get or create library node
            debug(f"🔍 Processing file: {file_name} -> Library: {library_name}")

            if library_name not in self.library_nodes:
                # Create library node
                library_item = QTreeWidgetItem(self.main_window.results_tree)
                library_item.setText(0, f"📁 {library_name} (1 file)")

                # Use pre-processed file type
                file_type_widget = ResultsTreeBubbleWidget(file_type)
                self.main_window.results_tree.setItemWidget(
                    library_item, 1, file_type_widget
                )
                # Keywords are hidden from UI but still processed
                # Create bubble widget for tags column
                tag_widget = ResultsTreeBubbleWidget(result.get("tags", ""))
                self.main_window.results_tree.setItemWidget(library_item, 2, tag_widget)
                library_item.setExpanded(False)  # Collapsed by default

                # Add tooltips for library items
                # For library items, show the folder path where this library was found
                library_path = os.path.dirname(file_path)
                library_item.setToolTip(
                    0, f"Library: {library_name}\nPath: {library_path}"
                )
                library_item.setToolTip(1, file_type)
                library_item.setToolTip(2, result.get("tags", ""))

                # Store library node
                self.library_nodes[library_name] = {
                    "item": library_item,
                    "count": 1,
                    "keywords": set(),
                    "tags": set(),
                    "file_types": set([file_type]),  # Track file types
                    "files": set(),  # Track added files to prevent duplicates
                }

                # Add keywords and tags to library
                if result.get("keywords"):
                    self.library_nodes[library_name]["keywords"].update(
                        result["keywords"].split(" • ")
                    )
                if result.get("tags"):
                    self.library_nodes[library_name]["tags"].update(
                        result["tags"].split(" • ")
                    )

                # Track this file to prevent duplicates
                self.library_nodes[library_name]["files"].add(file_path)
            else:
                # Update existing library node
                library_data = self.library_nodes[library_name]

                # Check if this file has already been added to this library (shouldn't happen with global tracking, but safety check)
                if file_path in library_data["files"]:
                    return

                library_data["count"] += 1
                library_item = library_data["item"]

                # Update library display
                library_item.setText(
                    0, f"📁 {library_name} ({library_data['count']} files)"
                )

                # Add file type to library (use pre-processed data)
                library_data["file_types"].add(file_type)

                # Add keywords and tags to library
                if result.get("keywords"):
                    library_data["keywords"].update(result["keywords"].split(" • "))
                if result.get("tags"):
                    library_data["tags"].update(result["tags"].split(" • "))

                # Update library file types, keywords and tags
                file_types_str = ", ".join(sorted(library_data["file_types"]))
                library_keywords = " • ".join(sorted(library_data["keywords"]))
                library_tags = " • ".join(sorted(library_data["tags"]))
                file_type_widget = ResultsTreeBubbleWidget(file_types_str)
                self.main_window.results_tree.setItemWidget(
                    library_item, 1, file_type_widget
                )
                # Keywords are hidden from UI but still processed
                # Update bubble widget for library tags
                tag_widget = ResultsTreeBubbleWidget(library_tags)
                self.main_window.results_tree.setItemWidget(library_item, 2, tag_widget)

                # Update tooltips for library items
                library_path = os.path.dirname(file_path)
                library_item.setToolTip(
                    0, f"Library: {library_name}\nPath: {library_path}"
                )
                library_item.setToolTip(1, file_types_str)
                library_item.setToolTip(2, library_tags)

                # Track this file to prevent duplicates
                library_data["files"].add(file_path)

            # Create file item under library
            file_item = QTreeWidgetItem(library_item)

            # Get file icon and name
            file_icon = self.file_model.get_file_icon(file_path)
            file_name = result.get("name", "")

            # Set file item data with icon
            file_item.setText(0, f"{file_icon} {file_name}")

            # Get actual file type from file model
            file_type = self.file_model.get_file_type_info(file_path)
            file_type_widget = ResultsTreeBubbleWidget(file_type)
            self.main_window.results_tree.setItemWidget(file_item, 1, file_type_widget)

            # Keywords are hidden from UI but still processed
            # Create bubble widget for file item tags
            file_tag_widget = ResultsTreeBubbleWidget(result.get("tags", ""))
            self.main_window.results_tree.setItemWidget(file_item, 2, file_tag_widget)

            # Store the full path for later use
            file_item.setData(0, Qt.UserRole, file_path)

            # Add tooltips for file items
            file_item.setToolTip(0, file_path)  # Full file path on filename
            file_item.setToolTip(1, file_type)  # Full file type
            file_item.setToolTip(2, result.get("keywords", ""))  # Full keywords
            file_item.setToolTip(3, result.get("tags", ""))  # Full tags

            # REMOVED: Auto-resize columns if needed - too expensive for large result sets
            # self.main_window.results_tree.resizeColumnToContents(0)

            # Update status with current count
            total_files = sum(
                lib_data["count"] for lib_data in self.library_nodes.values()
            )
            total_libraries = len(self.library_nodes)
            self.main_window.update_search_counts(total_files, total_libraries)

            # REMOVED: Force UI update - too expensive for large result sets
            # self.main_window.results_tree.viewport().update()

        except Exception as e:
            error(f"⚠️ Error adding single result: {e}")
            import traceback

            traceback.print_exc()

    def adjust_performance_for_large_results(self):
        """Dynamically adjust performance parameters for large result sets"""
        if self.total_results_processed >= self.performance_adjustment_threshold:
            # For large result sets, increase batch size and update frequency
            if self.batch_size < 50:
                self.batch_size = min(50, self.batch_size + 5)
                debug(
                    f"🔧 Increased batch size to {self.batch_size} for large result set"
                )

            if self.update_throttle_ms < 200:
                self.update_throttle_ms = min(200, self.update_throttle_ms + 25)
                debug(
                    f"🔧 Increased update throttle to {self.update_throttle_ms}ms for large result set"
                )

            # Reset counter for next adjustment
            self.total_results_processed = 0

    def add_single_result(self, result: Dict[str, Any]):
        """Add a single result to the display immediately with library grouping"""
        try:
            # Create tree widget if it doesn't exist yet
            if not self.main_window.results_tree:
                debug("🔧 Creating results tree for first result")
                self.main_window.results_tree = self.main_window.create_tree_widget()

                if not self.main_window.results_tree:
                    warning("⚠️ Could not create results tree")
                    return

                # Setup double-click handler for the new tree
                self.setup_double_click_handler()

                # Initialize library tracking
                self.library_nodes = {}

            # Use pre-processed data from background thread
            file_path = result.get("path", "")
            file_name = result.get("name", "")
            library_name = result.get("library_name", "Unknown Library")
            file_type = result.get("file_type", "File")

            # Get or create library node
            debug(f"🔍 Processing file: {file_name} -> Library: {library_name}")

            if library_name not in self.library_nodes:
                # Create library node
                library_item = QTreeWidgetItem(self.main_window.results_tree)
                library_item.setText(0, f"📁 {library_name} (1 file)")

                # Use pre-processed file type
                file_type_widget = ResultsTreeBubbleWidget(file_type)
                self.main_window.results_tree.setItemWidget(
                    library_item, 1, file_type_widget
                )
                # Keywords are hidden from UI but still processed
                # Create bubble widget for tags column
                tag_widget = ResultsTreeBubbleWidget(result.get("tags", ""))
                self.main_window.results_tree.setItemWidget(library_item, 2, tag_widget)
                library_item.setExpanded(False)  # Collapsed by default

                # Add tooltips for library items
                # For library items, show the folder path where this library was found
                library_path = os.path.dirname(file_path)
                library_item.setToolTip(
                    0, f"Library: {library_name}\nPath: {library_path}"
                )
                library_item.setToolTip(1, file_type)
                library_item.setToolTip(2, result.get("tags", ""))

                # Store library node
                self.library_nodes[library_name] = {
                    "item": library_item,
                    "count": 1,
                    "keywords": set(),
                    "tags": set(),
                    "file_types": set([file_type]),  # Track file types
                    "files": set(),  # Track added files to prevent duplicates
                }

                # Add keywords and tags to library
                if result.get("keywords"):
                    self.library_nodes[library_name]["keywords"].update(
                        result["keywords"].split(" • ")
                    )
                if result.get("tags"):
                    self.library_nodes[library_name]["tags"].update(
                        result["tags"].split(" • ")
                    )

                # Track this file to prevent duplicates
                self.library_nodes[library_name]["files"].add(file_path)
            else:
                # Update existing library node
                library_data = self.library_nodes[library_name]

                # Check if this file has already been added to this library (shouldn't happen with global tracking, but safety check)
                if file_path in library_data["files"]:
                    return

                library_data["count"] += 1
                library_item = library_data["item"]

                # Update library display
                library_item.setText(
                    0, f"📁 {library_name} ({library_data['count']} files)"
                )

                # Add file type to library (use pre-processed data)
                library_data["file_types"].add(file_type)

                # Add keywords and tags to library
                if result.get("keywords"):
                    library_data["keywords"].update(result["keywords"].split(" • "))
                if result.get("tags"):
                    library_data["tags"].update(result["tags"].split(" • "))

                # Update library file types, keywords and tags
                file_types_str = ", ".join(sorted(library_data["file_types"]))
                library_keywords = " • ".join(sorted(library_data["keywords"]))
                library_tags = " • ".join(sorted(library_data["tags"]))
                file_type_widget = ResultsTreeBubbleWidget(file_types_str)
                self.main_window.results_tree.setItemWidget(
                    library_item, 1, file_type_widget
                )
                # Keywords are hidden from UI but still processed
                # Update bubble widget for library tags
                tag_widget = ResultsTreeBubbleWidget(library_tags)
                self.main_window.results_tree.setItemWidget(library_item, 2, tag_widget)

                # Update tooltips for library items
                library_path = os.path.dirname(file_path)
                library_item.setToolTip(
                    0, f"Library: {library_name}\nPath: {library_path}"
                )
                library_item.setToolTip(1, file_types_str)
                library_item.setToolTip(2, library_keywords)
                library_item.setToolTip(3, library_tags)

                # Track this file to prevent duplicates
                library_data["files"].add(file_path)

            # Create file item under library
            file_item = QTreeWidgetItem(library_item)

            # Get file icon and name
            file_icon = self.file_model.get_file_icon(file_path)
            file_name = result.get("name", "")

            # Set file item data with icon
            file_item.setText(0, f"{file_icon} {file_name}")

            # Get actual file type from file model
            file_type = self.file_model.get_file_type_info(file_path)
            file_type_widget = ResultsTreeBubbleWidget(file_type)
            self.main_window.results_tree.setItemWidget(file_item, 1, file_type_widget)

            # Keywords are hidden from UI but still processed
            # Create bubble widget for file item tags
            file_tag_widget = ResultsTreeBubbleWidget(result.get("tags", ""))
            self.main_window.results_tree.setItemWidget(file_item, 2, file_tag_widget)

            # Store the full path for later use
            file_item.setData(0, Qt.UserRole, file_path)

            # Add tooltips for file items
            file_item.setToolTip(0, file_path)  # Full file path on filename
            file_item.setToolTip(1, file_type)  # Full file type
            file_item.setToolTip(2, result.get("tags", ""))  # Full tags

            # REMOVED: Auto-resize columns if needed - too expensive for large result sets
            # self.main_window.results_tree.resizeColumnToContents(0)

            # Update status with current count
            total_files = sum(
                lib_data["count"] for lib_data in self.library_nodes.values()
            )
            total_libraries = len(self.library_nodes)
            self.main_window.update_search_counts(total_files, total_libraries)

            # REMOVED: Force UI update - too expensive for large result sets
            # self.main_window.results_tree.viewport().update()

        except Exception as e:
            error(f"⚠️ Error adding single result: {e}")
            import traceback

            traceback.print_exc()

    def update_results_display(self, result_data: Dict[str, Any]):
        """Update the results display with new data"""
        query = result_data.get("query", "")
        mode = result_data.get("mode", "simple")
        results = result_data.get("results", {})

        if not results:
            self.main_window.show_status_message(f"No results found for '{query}'")
            return

        # Update the tree with results
        self.populate_results_tree(results)

        # Show status
        total_files = sum(len(lib_data["files"]) for lib_data in results.values())
        self.main_window.show_status_message(
            f"Found {total_files} files in {len(results)} libraries for '{query}'"
        )

    def populate_results_tree(self, results: Dict[str, Dict[str, Any]]):
        """Populate the results tree with data"""
        try:
            # Create tree widget if it doesn't exist
            if not self.main_window.results_tree:
                self.main_window.results_tree = self.main_window.create_tree_widget()

            if not self.main_window.results_tree:
                warning("⚠️ Could not create results tree")
                return

            # Setup double-click handler for the tree
            self.setup_double_click_handler()

            # Clear existing items
            self.main_window.results_tree.clear()

            # Update headers for music production workflow
            self.main_window.results_tree.setHeaderLabels(
                ["File Name", "File Type", "Tags"]
            )

            # Calculate optimal column widths based on actual content
            self.calculate_optimal_column_widths(results)

            # Ensure File Type column has minimum width to prevent truncation
            if self.main_window.results_tree:
                settings = self.file_model.settings
                min_file_type_width = settings.get_setting("MIN_FILE_TYPE_WIDTH") or 120
                current_width = self.main_window.results_tree.columnWidth(1)
                if current_width < min_file_type_width:
                    self.main_window.results_tree.setColumnWidth(1, min_file_type_width)
                    debug(
                        f"🔧 Set File Type column width to minimum: {min_file_type_width}px"
                    )

            # Set header resize modes for 3 columns - professional desktop app approach
            header = self.main_window.results_tree.header()
            header.setStretchLastSection(
                True
            )  # Last column (Tags) stretches to fill remaining space
            header.setSectionResizeMode(
                0, QHeaderView.Interactive
            )  # File Name - user can resize
            header.setSectionResizeMode(
                1, QHeaderView.ResizeToContents
            )  # File Type - auto-resize to content
            header.setSectionResizeMode(
                2, QHeaderView.Stretch
            )  # Tags - stretches to fill remaining space

            # Connect to header resize signal to enforce minimum widths
            header.sectionResized.connect(self.enforce_minimum_column_widths)

            # Enable horizontal scrolling for wide content
            self.main_window.results_tree.setHorizontalScrollMode(
                QTreeWidget.ScrollPerPixel
            )

            # Disable text elision to prevent truncation
            self.main_window.results_tree.setTextElideMode(Qt.ElideNone)

            # Disable word wrap to keep everything on one line
            self.main_window.results_tree.setWordWrap(False)

            debug(f"📊 Populating tree with {len(results)} libraries")

            for library_name, library_data in results.items():
                # Create library item
                library_item = QTreeWidgetItem(self.main_window.results_tree)

                # Set library display with file count
                file_count = len(library_data["files"])
                library_item.setText(0, f"📁 {library_name} ({file_count} files)")
                library_item.setExpanded(False)  # Collapsed by default

                # Set library metadata
                file_types = library_data.get("file_types", set())
                file_type_str = (
                    ", ".join(sorted(file_types)) if file_types else "Library"
                )
                file_type_widget = ResultsTreeBubbleWidget(file_type_str)
                self.main_window.results_tree.setItemWidget(
                    library_item, 1, file_type_widget
                )

                # Extract keywords for the entire library (hidden from UI but still processed)
                library_keywords = self.extract_library_keywords(library_data["files"])

                # Extract tags for the entire library
                library_tags = library_data.get("tags", set())
                tags_str = " • ".join(sorted(library_tags)) if library_tags else ""
                # Create bubble widget for library tags
                tag_widget = ResultsTreeBubbleWidget(tags_str)
                self.main_window.results_tree.setItemWidget(library_item, 2, tag_widget)

                # Add tooltips for library items
                # For library items, show the folder path where this library was found
                # We need to get a sample path from the library data
                sample_path = ""
                if library_data["files"]:
                    sample_path = library_data["files"][0].get("path", "")
                    if sample_path:
                        library_path = os.path.dirname(sample_path)
                        library_item.setToolTip(
                            0, f"Library: {library_name}\nPath: {library_path}"
                        )
                    else:
                        library_item.setToolTip(0, f"Library: {library_name}")
                else:
                    library_item.setToolTip(0, f"Library: {library_name}")

                library_item.setToolTip(1, file_type_str)  # Full file type
                library_item.setToolTip(2, library_keywords)  # Full keywords
                library_item.setToolTip(3, tags_str)  # Full tags

                # Add files under library
                for file_data in library_data["files"]:
                    file_item = QTreeWidgetItem(library_item)

                    # File name (with icon)
                    file_name = file_data.get("name", "Unknown")
                    file_icon = self.file_model.get_file_icon(file_data.get("path", ""))
                    file_item.setText(0, f"{file_icon} {file_name}")

                    # File type
                    file_type = self.file_model.get_file_type_info(
                        file_data.get("path", "")
                    )
                    file_type_widget = ResultsTreeBubbleWidget(file_type)
                    self.main_window.results_tree.setItemWidget(
                        file_item, 1, file_type_widget
                    )

                    # Keywords (matched search terms)
                    keywords = file_data.get("keywords", "")
                    keywords_widget = ResultsTreeBubbleWidget(keywords)
                    self.main_window.results_tree.setItemWidget(
                        file_item, 2, keywords_widget
                    )

                    # Tags (genre keywords)
                    tags = file_data.get("tags", "")
                    # Create bubble widget for file item tags
                    file_tag_widget = ResultsTreeBubbleWidget(tags)
                    self.main_window.results_tree.setItemWidget(
                        file_item, 2, file_tag_widget
                    )

                    # Add tooltips for full content on hover
                    file_path = file_data.get("path", "")
                    file_item.setToolTip(0, file_path)  # Full file path
                    file_item.setToolTip(1, file_type)  # Full file type
                    file_item.setToolTip(2, tags)  # Full tags

                    # Store full path for later use
                    file_item.setData(0, 100, file_data.get("path", ""))

            total_files = sum(len(lib_data["files"]) for lib_data in results.values())
            debug(f"✅ Tree populated with {total_files} files")

            # Final check: Ensure File Type column has minimum width
            if self.main_window.results_tree:
                settings = self.file_model.settings
                min_file_type_width = settings.get_setting("MIN_FILE_TYPE_WIDTH") or 120
                current_width = self.main_window.results_tree.columnWidth(1)
                if current_width < min_file_type_width:
                    self.main_window.results_tree.setColumnWidth(1, min_file_type_width)
                    debug(
                        f"🔧 Final check: Set File Type column width to {min_file_type_width}px"
                    )

        except Exception as e:
            error(f"⚠️ Error populating results tree: {e}")
            import traceback

            traceback.print_exc()

    def extract_library_keywords(self, files: List[Dict[str, Any]]) -> str:
        """Extract keywords that matched files in this library"""
        all_keywords = set()

        for file_result in files:
            keywords = file_result.get("keywords", "")
            if keywords:
                all_keywords.update(keywords.split(" • "))

        return " • ".join(sorted(all_keywords)) if all_keywords else ""

    def format_path_for_display(self, file_path: str) -> str:
        """Format path for display showing last parts"""
        if not file_path:
            return ""

        path_parts = file_path.split("/")
        if len(path_parts) <= 3:
            return file_path

        # Show last 3 parts with ellipsis
        return f".../{'/'.join(path_parts[-3:])}"

    def calculate_optimal_column_widths(self, results: Dict[str, Dict[str, Any]]):
        """Calculate optimal column widths based on actual content"""
        if not results or not self.main_window.results_tree:
            return

        # Sample content for each column
        file_names = []
        file_types = []
        tags_list = []

        # Collect content from all results
        for library_name, library_data in results.items():
            # Add library items
            file_count = len(library_data["files"])
            library_display = f"📁 {library_name} ({file_count} files)"
            file_names.append(library_display)

            file_types_str = ", ".join(sorted(library_data.get("file_types", set())))
            file_types.append(file_types_str if file_types_str else "Library")

            # Library keywords and tags
            library_keywords = self.extract_library_keywords(library_data["files"])
            # Keywords are hidden from UI but still processed for debug

            library_tags = library_data.get("tags", set())
            if library_tags:
                tags_list.append(" • ".join(sorted(library_tags)))

            # Add file items
            for file_data in library_data["files"]:
                file_name = file_data.get("name", "Unknown")
                file_icon = self.file_model.get_file_icon(file_data.get("path", ""))
                file_names.append(f"{file_icon} {file_name}")

                file_type = self.file_model.get_file_type_info(
                    file_data.get("path", "")
                )
                file_types.append(file_type)

                keywords = file_data.get("keywords", "")
                # Keywords are hidden from UI but still processed for debug

                tags = file_data.get("tags", "")
                if tags:
                    tags_list.append(tags)

        # Calculate optimal widths using font metrics
        font_metrics = self.main_window.results_tree.fontMetrics()

        # File Name column - find longest name
        max_file_name_width = 0
        for name in file_names:
            width = font_metrics.horizontalAdvance(name)
            max_file_name_width = max(max_file_name_width, width)

        # File Type column - find longest type
        max_file_type_width = 0
        for file_type in file_types:
            width = font_metrics.horizontalAdvance(file_type)
            max_file_type_width = max(max_file_type_width, width)

        # Tags column - find longest tags
        max_tags_width = 0
        for tags in tags_list:
            width = font_metrics.horizontalAdvance(tags)
            max_tags_width = max(max_tags_width, width)

        # Get settings for padding and max widths
        settings = self.file_model.settings
        file_name_padding = settings.get_setting("FILE_NAME_PADDING") or 40
        file_type_padding = settings.get_setting("FILE_TYPE_PADDING") or 20
        keywords_padding = settings.get_setting("KEYWORDS_PADDING") or 30
        tags_padding = settings.get_setting("TAGS_PADDING") or 30

        max_file_name_width_setting = settings.get_setting("MAX_FILE_NAME_WIDTH") or 400
        max_file_type_width_setting = settings.get_setting("MAX_FILE_TYPE_WIDTH") or 300
        max_keywords_width_setting = settings.get_setting("MAX_KEYWORDS_WIDTH") or 400
        max_tags_width_setting = settings.get_setting("MAX_TAGS_WIDTH") or 500

        # Get minimum width settings
        min_file_name_width = settings.get_setting("MIN_FILE_NAME_WIDTH") or 200
        min_file_type_width = settings.get_setting("MIN_FILE_TYPE_WIDTH") or 120
        min_keywords_width = settings.get_setting("MIN_KEYWORDS_WIDTH") or 150
        min_tags_width = settings.get_setting("MIN_TAGS_WIDTH") or 100

        # Set optimal widths with padding using settings, respecting minimums
        self.main_window.results_tree.setColumnWidth(
            0,
            max(
                min_file_name_width,
                min(
                    max_file_name_width + file_name_padding, max_file_name_width_setting
                ),
            ),
        )
        self.main_window.results_tree.setColumnWidth(
            1,
            max(
                min_file_type_width,
                min(
                    max_file_type_width + file_type_padding, max_file_type_width_setting
                ),
            ),
        )
        self.main_window.results_tree.setColumnWidth(
            2,
            max(
                min_keywords_width,
                min(max_keywords_width + keywords_padding, max_keywords_width_setting),
            ),
        )
        self.main_window.results_tree.setColumnWidth(
            3,
            max(
                min_tags_width,
                min(max_tags_width + tags_padding, max_tags_width_setting),
            ),
        )

        debug("🔧 Optimal column widths calculated:")
        debug(f"  File Name: {self.main_window.results_tree.columnWidth(0)}px")
        debug(f"  File Type: {self.main_window.results_tree.columnWidth(1)}px")
        debug(f"  Keywords: {self.main_window.results_tree.columnWidth(2)}px")
        debug(f"  Tags: {self.main_window.results_tree.columnWidth(3)}px")

    def enforce_minimum_column_widths(self):
        """Enforce minimum column widths to prevent users from making columns too small"""
        if not self.main_window.results_tree:
            return

        settings = self.file_model.settings
        min_file_name_width = settings.get_setting("MIN_FILE_NAME_WIDTH") or 200
        min_file_type_width = settings.get_setting("MIN_FILE_TYPE_WIDTH") or 120
        min_keywords_width = settings.get_setting("MIN_KEYWORDS_WIDTH") or 150
        min_tags_width = settings.get_setting("MIN_TAGS_WIDTH") or 100

        # Check and enforce minimum widths
        if self.main_window.results_tree.columnWidth(0) < min_file_name_width:
            self.main_window.results_tree.setColumnWidth(0, min_file_name_width)
            debug(f"🔧 Enforced minimum File Name width: {min_file_name_width}px")

        if self.main_window.results_tree.columnWidth(1) < min_file_type_width:
            self.main_window.results_tree.setColumnWidth(1, min_file_type_width)
            debug(f"🔧 Enforced minimum File Type width: {min_file_type_width}px")

        if self.main_window.results_tree.columnWidth(2) < min_keywords_width:
            self.main_window.results_tree.setColumnWidth(2, min_keywords_width)
            debug(f"🔧 Enforced minimum Keywords width: {min_keywords_width}px")

        if self.main_window.results_tree.columnWidth(3) < min_tags_width:
            self.main_window.results_tree.setColumnWidth(3, min_tags_width)
            debug(f"🔧 Enforced minimum Tags width: {min_tags_width}px")

    def setup_double_click_handler(self):
        """Setup double-click handler for opening parent folder"""
        if self.main_window.results_tree:
            self.main_window.results_tree.itemDoubleClicked.connect(
                self.on_item_double_clicked
            )

    def on_item_double_clicked(self, item, column):
        """Handle double-click on result item to open parent folder"""
        try:
            # Get the file path from the item data
            file_path = item.data(0, Qt.UserRole)
            if not file_path:
                return

            # Open parent folder and select the file
            self.open_parent_folder_and_select_file(file_path)

        except Exception as e:
            error(f"⚠️ Error handling double-click: {e}")

    def open_parent_folder_and_select_file(self, file_path):
        """Open parent folder and select the file in the system file manager"""
        import subprocess
        import sys

        try:
            if not os.path.exists(file_path):
                warning(f"⚠️ File does not exist: {file_path}")
                return

            if sys.platform == "win32":
                # Windows: Use explorer /select to open folder and select file
                subprocess.run(f'explorer /select,"{file_path}"', shell=True)
            elif sys.platform == "darwin":
                # macOS: Use open -R to reveal file in Finder
                subprocess.run(["open", "-R", file_path])
            else:
                # Linux: Open parent directory
                parent_dir = os.path.dirname(file_path)
                subprocess.run(["xdg-open", parent_dir])

            debug(f"🔍 Opened parent folder for: {os.path.basename(file_path)}")

        except Exception as e:
            error(f"⚠️ Error opening parent folder: {e}")

    def on_filters_changed(self):
        """Handle filter changes - trigger search update with current filters"""
        # Use the same logic as pressing enter - just call on_search_triggered()
        # This ensures consistent behavior between manual search and filter-triggered search
        debug("🔄 Filter changed - triggering search with same logic as manual search")
        self.on_search_triggered()
