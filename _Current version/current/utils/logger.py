#!/usr/bin/env python3
"""
PatchIO Logger - Enhanced version with proper log levels
Provides both custom log functions and standard Python logging
"""

import os
import logging
from datetime import datetime
from typing import Optional

class PatchIOLogger:
    """Enhanced logger with proper log levels"""
    
    def __init__(self, log_file_path: str, log_level: str = "ERROR"):
        self.log_file = log_file_path
        self.log_level = getattr(logging, log_level.upper())
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration with proper levels"""
        try:
            # Configure standard Python logging
            logging.basicConfig(
                filename=self.log_file,
                filemode="a",  # Append mode
                level=self.log_level,
                format="%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        except Exception as e:
            print(f"⚠️ Error setting up logging: {e}")
    
    def _write_to_log(self, level: str, message: str):
        """Write message to log file and console"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            full_message = f"[{timestamp}] [{level}] {message}"
            
            # Write to log file
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(full_message + "\n")
            
            # Also print to console (identical to original)
            print(message)
            
        except Exception:
            pass  # Silently ignore logging errors (identical to original)
    
    def debug(self, message: str):
        """Log debug message - can be turned off by setting log level to INFO or higher"""
        if self.log_level <= logging.DEBUG:
            self._write_to_log("DEBUG", message)
    
    def info(self, message: str):
        """Log info message"""
        if self.log_level <= logging.INFO:
            self._write_to_log("INFO", message)
    
    def warning(self, message: str):
        """Log warning message"""
        if self.log_level <= logging.WARNING:
            self._write_to_log("WARNING", message)
    
    def error(self, message: str):
        """Log error message"""
        if self.log_level <= logging.ERROR:
            self._write_to_log("ERROR", message)
    
    def critical(self, message: str):
        """Log critical message"""
        if self.log_level <= logging.CRITICAL:
            self._write_to_log("CRITICAL", message)
    
    # Removed log_error method - use error() instead
    # def log_error(self, message: str):
    #     """
    #     Custom log_error function identical to original patchio_old.py
    #     Always logs regardless of level (for backward compatibility)
    #     """
    #     self._write_to_log("ERROR", message)

# Global logger instance (will be initialized in main)
_logger: Optional[PatchIOLogger] = None

def get_logger() -> PatchIOLogger:
    """Get the global logger instance"""
    global _logger
    if _logger is None:
        raise RuntimeError("Logger not initialized. Call setup_logger() first.")
    return _logger

def setup_logger(log_file_path: str, log_level: str = "ERROR") -> PatchIOLogger:
    """Setup the global logger instance"""
    global _logger
    _logger = PatchIOLogger(log_file_path, log_level)
    return _logger

def _safe_logger_call(func_name: str, message: str):
    """Safely call logger function, fall back to print if not initialized"""
    try:
        logger = get_logger()
        getattr(logger, func_name)(message)
    except RuntimeError:
        # Logger not initialized, fall back to print
        print(message)

# Removed log_error function - use error() instead
# def log_error(message: str):
#     """Global log_error function identical to original"""
#     _safe_logger_call('log_error', message)

def debug(message: str):
    """Global debug function - can be turned off"""
    _safe_logger_call('debug', message)

def info(message: str):
    """Global info function"""
    _safe_logger_call('info', message)

def warning(message: str):
    """Global warning function"""
    _safe_logger_call('warning', message)

def error(message: str):
    """Global error function"""
    _safe_logger_call('error', message)

def critical(message: str):
    """Global critical function"""
    _safe_logger_call('critical', message) 