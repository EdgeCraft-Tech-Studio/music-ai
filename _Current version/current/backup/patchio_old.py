import os
import sys
import subprocess
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, ttk
from PIL import Image, ImageTk  # pip install pillow
import shlex
import json
import threading
import queue
import time
import re
import ctypes
import platform
import appdirs
from appdirs import site_data_dir
import tkinter.messagebox as messagebox
import traceback
import logging
import datetime
import shutil
from openai import OpenAI
import socket
from Crypto.Cipher import AES
import base64
import requests
import tkinter.font as tkfont
from collections import defaultdict
from pathlib import Path
import tempfile

folder_keyword_map = defaultdict(set)

def format_modification_date(folder_path):
    """Format folder modification date in macOS default format with time"""
    try:
        if os.path.exists(folder_path):
            mtime = os.path.getmtime(folder_path)
            dt = datetime.datetime.fromtimestamp(mtime)
            # Use macOS format with date and time: "15 Jan 2024 at 16:35"
            return dt.strftime("%d %b %Y at %H:%M")
        else:
            return ""
    except (OSError, ValueError):
        return ""

### DEMO settings ###
def get_demo_file_path():
    system = platform.system()

    if system == "Windows":
        base = os.getenv("APPDATA") or str(Path.home())
        path = Path(base) / "PatchIO" / ".patchIO_demo.json"
    elif system == "Darwin":
        path = Path.home() / "Library" / "Application Support" / "PatchIO" / ".patchIO_demo.json"

    path.parent.mkdir(parents=True, exist_ok=True)

    # Windows: Set hidden attribute if file exists and not already hidden
    if system == "Windows" and path.exists():
        try:
            FILE_ATTRIBUTE_HIDDEN = 0x02
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
            if not attrs & FILE_ATTRIBUTE_HIDDEN:
                ctypes.windll.kernel32.SetFileAttributesW(str(path), attrs | FILE_ATTRIBUTE_HIDDEN)
        except Exception as e:
            print(f"⚠️ Failed to hide file: {e}")

    return str(path)

# Use this:
DEMO_FILE = get_demo_file_path()
DEMO_DURATION_DAYS = 30
DEMO_MODE = True  # set to False to skip all this logic
DEMO_TOKEN_LIMIT = 40000  # Max tokens per demo license
demo_label = None  # Will be initialized later

### AI ###
AI_AVAILABLE = True

# General Settings
APP_NAME = "PatchIO"
APP_AUTHOR = None  # No author or company name
MANUAL_NAME = f"{APP_NAME}_Manual.pdf"

### DRIVE FILES IDs ###
SYSTEM_MESSAGE_DRIVE_ID = "1W-upMhKyQjqYKnXQReO6xhYQUVMNqURS" # ID of system_message.txt file on Drive
API_KEY_FILE_ID = "1lBtKmwOXK6J8BySnecdrI6QSrFkCWETL" # ID of API KEY
GPT_SETTINGS_FILE_ID = "18J6bRUaQnygUv4twjLKZB8EdDQw59PPE"
AES_KEY = b'NahaPatchio12345'

### DOCUMENTATION PATH ###
def get_doc_path():
    if getattr(sys, 'frozen', False):
        # App is frozen (running from .app bundle)
        base_path = os.path.dirname(sys.executable)
        return os.path.abspath(os.path.join(base_path, '..', 'Resources', MANUAL_NAME))
    else:
        # Development / unfrozen mode
        return os.path.abspath(MANUAL_NAME)

DOC_PATH = get_doc_path()

all_items = []  # global list to store all item iids (populate once after you fill the tree)

APP_PATH = "/Applications/PatchIO.app"
CURRENT_VERSION = "--help"
VERSION_FILE_ID = "1pAIrEaregd4l8D0OCK1aoy49AzYVZPUF"
VERSION_URL = f"https://drive.google.com/uc?export=download&id={VERSION_FILE_ID}"


def get_os_zip_url(lines):
    system = platform.system()
    machine = platform.machine()

    try:
        if system == "Darwin":
            if machine == "arm64":
                return lines[1].strip()  # macOS ARM
            elif machine == "x86_64":
                return lines[2].strip()  # macOS Intel
            else:
                return None
        elif system == "Windows":
            return lines[3].strip()  # Windows
        else:
            return None
    except IndexError:
        # Fallback for old version.txt files with only 2 lines
        return lines[1].strip()

def check_for_updates(silent=False):
    def worker():
        try:
            resp = requests.get(VERSION_URL)
            resp.raise_for_status()
            lines = resp.text.strip().splitlines()
            latest_version = lines[0].strip()

            zip_url = get_os_zip_url(lines)
            if not zip_url:
                if not silent:
                    messagebox.showerror("Update Error", f"Unsupported OS/Architecture: {platform.system()} {platform.machine()}")
                return

            if latest_version > CURRENT_VERSION:
                if not messagebox.askyesno("Update Available", f"New version {latest_version} available.\nInstall now?"):
                    return

                tmpdir = tempfile.mkdtemp()
                zip_path = os.path.join(tmpdir, "update.zip")

                with requests.get(zip_url, stream=True) as r:
                    r.raise_for_status()
                    with open(zip_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)

                subprocess.run(["unzip", "-q", zip_path, "-d", tmpdir], check=True)

                # Detect extracted .app directory
                new_app_path = None
                for item in os.listdir(tmpdir):
                    if item.endswith(".app"):
                        new_app_path = os.path.join(tmpdir, item)
                        break

                if not new_app_path or not os.path.exists(new_app_path):
                    messagebox.showerror("Update Error", "Update failed: PatchIO.app not found in ZIP.")
                    return

                # Ensure correct updater path
                if getattr(sys, 'frozen', False):
                    base_dir = os.path.abspath(os.path.join(os.path.dirname(sys.executable), '..', 'MacOS'))
                else:
                    base_dir = os.path.dirname(__file__)

                updater_path = os.path.join(base_dir, "external_updater")

                if not os.path.exists(updater_path):
                    messagebox.showerror("Update Error", f"Updater not found at {updater_path}")
                    return

                # Launch updater with correct args
                try:
                    subprocess.Popen([updater_path, new_app_path, APP_PATH])
                except Exception as e:
                    messagebox.showerror("Launch Error", f"Failed to launch updater:\n{e}")

                messagebox.showinfo("Restarting", "PatchIO will now close and restart to apply the update.")
                time.sleep(2)  # let updater settle before app exits
                os._exit(0)

            else:
                if not silent:
                    messagebox.showinfo("Up to Date", f"You are already running the latest version: {CURRENT_VERSION}")

        except Exception as e:
            if not silent:
                messagebox.showerror("Update Error", f"Failed to check or install update:\n{e}")

    threading.Thread(target=worker, daemon=True).start()




# detect dark mode for changing color of custom-colored texts
def is_dark_mode():
    system = platform.system()

    if system == "Darwin":  # macOS
        try:
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True,
                text=True,
            )
            # If output contains "Dark", dark mode is enabled
            return "Dark" in result.stdout
        except Exception:
            return False

    elif system == "Windows":
        try:
            import winreg
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return value == 0  # 0 means dark mode, 1 means light mode
        except Exception:
            return False

    else:
        # For Linux or other OSes, no standard way, assume light mode
        return False

IS_DARK_MODE = is_dark_mode()

# Encrypt JSON DEMO file
def save_obfuscated_json(filepath, data_dict):
    json_str = json.dumps(data_dict)
    encoded = base64.b64encode(json_str.encode("utf-8"))
    with open(filepath, "wb") as f:
        f.write(encoded)

# Decode JSON DEMO file
def load_obfuscated_json(filepath):
    try:
        with open(filepath, "rb") as f:
            encoded = f.read()
        decoded = base64.b64decode(encoded).decode("utf-8")
        return json.loads(decoded)
    except Exception:
        return None

def check_demo_validity():
    if not DEMO_MODE:
        return True

    now = datetime.datetime.now()
    data = get_demo_data()

    if "start_time" not in data:
        data["start_time"] = now.isoformat()
        data["tokens_used"] = 0
        save_demo_data(data)
        return True

    try:
        start_time = datetime.datetime.fromisoformat(data["start_time"])
        if now > start_time + datetime.timedelta(days=DEMO_DURATION_DAYS):
            return False
    except Exception:
        return False

    return True


def get_demo_days_remaining():
    """Return how many demo days are left."""
    if not os.path.exists(DEMO_FILE):
        return DEMO_DURATION_DAYS

    data = load_obfuscated_json(DEMO_FILE)
    if not data:
        return 0

    try:
        start_time = datetime.datetime.fromisoformat(data["start_time"])
        now = datetime.datetime.now()
        elapsed = (now - start_time).days
        return max(0, DEMO_DURATION_DAYS - elapsed)
    except Exception:
        return 0

def get_demo_data():
    try:
        with open(DEMO_FILE, "rb") as f:
            obfuscated = f.read()
            decoded = base64.b64decode(obfuscated).decode("utf-8")
            return json.loads(decoded)
    except Exception:
        return {}

def save_demo_data(data):
    try:
        encoded = base64.b64encode(json.dumps(data).encode("utf-8"))
        with open(DEMO_FILE, "wb") as f:
            f.write(encoded)
    except Exception:
        pass

def get_demo_tokens_used():
    data = get_demo_data()
    return int(data.get("tokens_used", 0))

def update_demo_tokens_used(additional_tokens):
    data = get_demo_data()
    data["tokens_used"] = int(data.get("tokens_used", 0)) + additional_tokens
    save_demo_data(data)


if DEMO_MODE and not check_demo_validity():
    from tkinter import messagebox
    messagebox.showwarning("Demo Expired", f"Your {DEMO_DURATION_DAYS}-day demo has expired.\n"
                        "To extend your trial or upgrade, please contact the creator: info@shaked-music.com"
                    )
    exit()


# Cache API key
_cached_api_key = None

# Util: Unpad PKCS#7
def unpad(s):
    return s[:-ord(s[-1:])]

# Load & Decrypt API key
def load_encrypted_api_key_from_drive(file_id, aes_key):
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        encrypted_base64 = response.text.strip()
        encrypted_bytes = base64.b64decode(encrypted_base64)

        cipher = AES.new(aes_key, AES.MODE_ECB)
        decrypted = cipher.decrypt(encrypted_bytes)
        api_key = unpad(decrypted).decode("utf-8")
        return api_key
    except Exception as e:
        print(f"Error loading/decrypting API key: {e}")
        return None

# Cached access
def get_cached_api_key():
    global _cached_api_key
    if _cached_api_key is None:
        _cached_api_key = load_encrypted_api_key_from_drive(API_KEY_FILE_ID, AES_KEY)
    return _cached_api_key

# Use the API key
api_key = get_cached_api_key()
if api_key:
    print("Succesfully loaded API key.")
    client = OpenAI(api_key=api_key)
else:
    print("Failed to load API key.")


MAX_FOLDER_ENTRIES = 8  # <-- change this to adjust max folders allowed
MAX_EXCLUDED_FOLDERS = 8  # Limit to 8 excluded folders

# Get the directory for configuration files (cross-platform)
config_dir = appdirs.user_config_dir(APP_NAME, APP_AUTHOR)

# Create the directory if it doesn't exist
os.makedirs(config_dir, exist_ok=True)

# Set the path to the settings file
SETTINGS_FILE = os.path.join(config_dir, "patchIO_settings.json")
LOG_FILE = os.path.join(config_dir, "patchIO_logs.log")

# ALL DEFAULT SETTINGS
DEFAULT_SETTINGS = {
    "last_folders": [],
    "extensions": {},  # extension dict like {".wav": True}
    "excluded_folders": [],
    "cubase_key_command": "shift+f12",
    "shown_key_command_warning": False
}

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    # Merge missing defaults
                    for key, default_value in DEFAULT_SETTINGS.items():
                        if key not in data:
                            data[key] = default_value
                    return data
        except Exception:
            pass  # fallback to default
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)

# Configure logging globally
logging.basicConfig(
    filename=LOG_FILE,
    filemode="a",  # Append mode
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

last_prompt = None
last_result = None
cached_gpt_settings = None
cached_system_prompt = None

searching = False
ai_search_in_progress = False

def load_system_prompt_from_drive(file_id):
    global AI_AVAILABLE
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return {
            "role": "system",
            "content": response.text.strip()
        }
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        msg = "AI feature disabled due to error:\n" + str(e)
        print(msg)
        messagebox.showerror("AI Connection Error", msg)
        AI_AVAILABLE = False

    except Exception as e:
        print(f"Unexpected error loading system prompt: {e}")
        AI_AVAILABLE = False
        print("AI feature disabled due to error:", e)

    # Fallback if any error occurs
    return {
        "role": "system",
        "content": "Error: Could not load system message."
    }

def get_cached_system_prompt():
    global cached_system_prompt
    if cached_system_prompt is None:
        print(f"[DEBUG] System Message (prompt) isn't loaded yet. Fetching it from Google Drive")
        cached_system_prompt = load_system_prompt_from_drive(SYSTEM_MESSAGE_DRIVE_ID)
    return cached_system_prompt

def load_gpt_settings_from_drive(file_id):
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        settings = json.loads(response.text.strip())
        return settings
    except Exception as e:
        msg = f"Error loading GPT settings: {e}"
        print(msg)
        messagebox.showerror("GPT Settings Load Error", msg)
        return None

def get_cached_gpt_settings():
    global cached_gpt_settings
    if cached_gpt_settings is None:
        print(f"[DEBUG] GPT Settings file isn't loaded yet. Fetching it from Google Drive")
        cached_gpt_settings = load_gpt_settings_from_drive(GPT_SETTINGS_FILE_ID)
    return cached_gpt_settings

# Preload GPT files from Google Drive
def preload_gpt_files():

    def load():
        global cached_system_prompt, cached_gpt_settings, AI_AVAILABLE
        try:
            cached_system_prompt = load_system_prompt_from_drive(SYSTEM_MESSAGE_DRIVE_ID)
            cached_gpt_settings = load_gpt_settings_from_drive(GPT_SETTINGS_FILE_ID)
            print("GPT files (message and settings) preloaded.")
        except Exception as e:
            AI_AVAILABLE = False
            print("Failed to preload GPT files (message and settings):", e)

    threading.Thread(target=load, daemon=True).start()

def get_matched_keywords(name, or_terms, and_terms):
    name_lc = name.lower()
    matches = []
    for token in (or_terms + and_terms):
        token = token.strip('"').lower()
        if token and token in name_lc:
            matches.append(token)
    return matches


def call_gpt_api_to_generate_keywords(prompt, root, or_entry, and_entry, not_entry, search_button=None, callback=None,
                                      results_count_label=None):
    global last_prompt, last_result

    # Don't re-send query for same prompt
    if prompt == last_prompt:
        # Reuse previous result
        if callback:
            callback(last_result)
        return

    def parse_ai_lines(text):
        result = {"or": [], "and": [], "not": []}
        current = None

        for line in text.strip().splitlines():
            if ':' in line:
                key, rest = line.split(':', 1)
                key = key.strip().lower()
                if key in result:
                    current = key
                    tokens = re.findall(r'"[^"]+"|\S+', rest.strip())
                    result[current] = tokens
            elif current:
                tokens = re.findall(r'"[^"]+"|\S+', line.strip())
                result[current].extend(tokens)

        return result

    def worker():
        global searching, ai_search_in_progress
        text = ""

        try:
            system_message = get_cached_system_prompt()
            user_message = {"role": "user", "content": prompt}
            gpt_settings = get_cached_gpt_settings()
            if gpt_settings:
                response = client.chat.completions.create(
                    model=gpt_settings.get("model", "gpt-4o"),
                    messages=[system_message, user_message],
                    max_tokens=gpt_settings.get("max_tokens", 400),
                    temperature=gpt_settings.get("temperature", 0.2),
                    top_p=gpt_settings.get("top_p", 1.0)
                )
            else:
                print("Could not load GPT settings.")

            # Track token usage for demo limit
            if DEMO_MODE:
                try:
                    usage = response.usage  # this is a dot-access object
                    tokens_used = usage.total_tokens or (
                            (usage.prompt_tokens or 0) + (usage.completion_tokens or 0)
                    )
                    update_demo_tokens_used(tokens_used)
                    if demo_label:
                        remaining = get_demo_days_remaining()
                        tokens_used = get_demo_tokens_used()
                        demo_label.config(
                            text=f"🧪 {DEMO_DURATION_DAYS}-day demo – {remaining} days remaining, {tokens_used}/{DEMO_TOKEN_LIMIT} GPT tokens used"
                        )
                except Exception as e:
                    messagebox.showwarning("AI Tokens Read Error", f"Could not track GPT tokens: {e}")

            text = response.choices[0].message.content.strip()

            print("GPT Original Output:", text)
            # Safety net: enforce 3 lines, and cap each list at 40 items max
            def truncate_keywords(line):
                if ":" not in line:
                    return line
                key, values = line.split(":", 1)
                raw_tokens = re.findall(r'"[^"]+"|\S+', values.strip())
                clean_tokens = []
                for token in raw_tokens:
                    token = token.strip()
                    if token.startswith('"') and token.endswith('"'):
                        token = token.rstrip(",")
                    elif '"' in token:
                        continue  # malformed
                    else:
                        token = token.rstrip(",")

                    clean_tokens.append(token)
                    if len(clean_tokens) == 40:
                        break

                # Join and remove multiple spaces
                joined = " ".join(clean_tokens)
                joined = re.sub(r"\s{2,}", " ", joined)

                return f"{key.strip().lower()}: {joined}"

            lines = text.splitlines()
            cleaned_lines = [truncate_keywords(line) for line in lines if line.strip()]
            while len(cleaned_lines) < 3:
                cleaned_lines.append("and: " if len(cleaned_lines) == 1 else "not: ")

            text = "\n".join(cleaned_lines)

            # Validate GPT response format
            print("GPT Cleaned Output:", text)
            is_valid, error_msg = validate_gpt_output(text)
            if not text.lower().startswith("or:") or "and:" not in text.lower() or "not:" not in text.lower():
                messagebox.showerror("AI Format Error",
                                     f"The AI output is missing one of the required lines.\n\nRaw output:\n{text}")
                return

            # Proceed to use parsed...
            data = parse_ai_lines(text)
            if not any(data.values()):
                messagebox.showwarning("No Keywords", "The AI did not return any keywords. Try rephrasing your prompt.")
                search_button.config(text="Search", state="normal", style="TButton")
                searching = False
                ai_search_in_progress = False
                if results_count_label:
                    results_count_label.config(text="")
                return

            or_keywords = data.get("or", [])
            and_keywords = data.get("and", [])
            not_keywords = data.get("not", [])

            def update_ui():
                or_entry.delete("1.0", tk.END)
                or_entry.insert(tk.END, "\n".join(or_keywords))

                and_entry.delete("1.0", tk.END)
                and_entry.insert(tk.END, "\n".join(and_keywords))

                not_entry.delete("1.0", tk.END)
                not_entry.insert(tk.END, "\n".join(not_keywords))

                if search_button:
                    search_button.config(state="normal")

                if callback:
                    callback(text)

            root.after(0, update_ui)

        except Exception as e:
            def report_error(e):
                messagebox.showerror("AI Search Error", f"Failed to get AI keywords:\n{e}")
                global searching, stop_search_flag
                searching = False
                stop_search_flag = False
                if search_button:
                    search_button.config(state="normal")
                if callback:
                    callback("")

            root.after(0, report_error(e))

    threading.Thread(target=worker, daemon=True).start()

# protect against weird GPT response
def validate_gpt_output(response_text):
    lines = response_text.strip().splitlines()
    keys_found = {"or": 0, "and": 0, "not": 0}

    for line in lines:
        l = line.lower().strip()
        if l.startswith("or:"):
            keys_found["or"] += 1
        elif l.startswith("and:"):
            keys_found["and"] += 1
        elif l.startswith("not:"):
            keys_found["not"] += 1

    # All keys must appear exactly once
    missing = [key for key, count in keys_found.items() if count == 0]
    if missing:
        return False, f"GPT output is missing section(s): {', '.join(missing)}"
    if any(count > 1 for count in keys_found.values()):
        return False, "GPT output has duplicate section(s)"

    return True, ""

def check_internet(host="8.8.8.8", port=53, timeout=2):
    """
    Checks internet connectivity by trying to open a socket to a DNS server.
    Returns True if internet is available, False otherwise.
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except Exception:
        return False

def log_error(message):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"[{timestamp}] {message}"

        # Write to log file
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(full_message + "\n")

        # Also print to console
        print(message)

    except Exception:
        pass  # Silently ignore logging errors

stop_search_event = threading.Event()

search_thread = None
stop_search_flag = False
# Track open settings windows to prevent duplicates
extensions_window_ref = None
excluded_window_ref = None

# recursive scan is a fast scan for files
def recursive_scan(folder, selected_extensions, excluded_folders):
    selected_extensions_lower = tuple(ext.lower() for ext in selected_extensions)
    try:
        for entry in os.scandir(folder):
            if stop_search_flag:
                break

            entry_path = os.path.normcase(os.path.abspath(entry.path))

            if entry.is_dir(follow_symlinks=False):
                # Use normalized path comparison instead of os.path.samefile()
                if any(entry_path == ex or entry_path.startswith(ex + os.sep) for ex in excluded_folders):
                    log_error(f"[DEBUG] Skipping excluded folder: {entry_path}")
                    continue

                yield from recursive_scan(entry.path, selected_extensions, excluded_folders)

            elif entry.is_file(follow_symlinks=False):
                if entry.name.lower().endswith(selected_extensions_lower):
                    yield entry.path

    except PermissionError as e:
        log_error(f"PermissionError accessing '{folder}': {e}")
    except Exception as e:
        log_error(f"Unexpected error accessing '{folder}': {traceback.format_exc()}")


def load_last_folders():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                log_error(f"[DEBUG] Loaded settings from JSON: {data}")  # DEBUG

                # Check if data is a dictionary and contains 'last_folders'
                if isinstance(data, dict):
                    last_folders = data.get("last_folders", [])
                    return last_folders
                else:
                    log_error("[DEBUG] JSON data is not in expected dictionary format.")
        except json.JSONDecodeError as e:
            log_error(f"[ERROR] Invalid JSON format:\n{traceback.format_exc()}")
            messagebox.showerror("Settings Error", "Your settings file appears to be corrupted.\n"
                                                   "PatchIO will reset it to default. Your corrupted settings will be backed up.")
            # back up
            backup_path = SETTINGS_FILE + ".corrupt"
            shutil.copyfile(SETTINGS_FILE, backup_path)
            # Optionally reset the file
            create_default_settings_file()
        except Exception as e:
            log_error(f"Unexpected error: {traceback.format_exc()}")
    else:
        log_error(f"[DEBUG] Settings file not found: {SETTINGS_FILE}")
    return []  # Return an empty list if no data or an error occurred


def save_last_folders():
    try:
        # Extract the folder paths and strip any whitespace, keeping only non-empty values.
        folders = [entry.get().strip() for _, entry in folder_entries if entry.get().strip()]

        # Load the current settings to preserve other data
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings_data = json.load(f)
        else:
            settings_data = {}

        # Update only the "last_folders" part of the settings
        settings_data["last_folders"] = folders

        # Save the updated settings back to the file
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings_data, f, indent=2)

        log_error("[DEBUG] Saved last folders to JSON.")

    except Exception as e:
        log_error(f"Could not save last folders:\n{traceback.format_exc()}")


def load_last_extensions():
    default_exts = {ext: True for ext in all_extensions}

    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                log_error(f"[DEBUG] Loaded settings from JSON: {data}")

                if isinstance(data, dict):
                    extensions = data.get("extensions")
                    if extensions and isinstance(extensions, dict):
                        return extensions
                    else:
                        # Add default extensions if missing or invalid
                        data["extensions"] = default_exts
                        with open(SETTINGS_FILE, "w", encoding="utf-8") as fw:
                            json.dump(data, fw, indent=2)
                        log_error("[DEBUG] Added default extensions to settings file.")
                        return default_exts
                else:
                    log_error("[ERROR] JSON structure is invalid. Expected a dictionary.")
        except json.JSONDecodeError:
            log_error(f"[ERROR] Invalid JSON format:\n{traceback.format_exc()}")
            messagebox.showerror("Settings Error", "Your settings file appears to be corrupted.\n"
                                                   "PatchIO will reset it to default. Your corrupted settings will be backed up.")
            shutil.copyfile(SETTINGS_FILE, SETTINGS_FILE + ".corrupt")
            create_default_settings_file()
            return default_exts
        except Exception:
            log_error(f"[ERROR] Could not load extensions:\n{traceback.format_exc()}")
    else:
        log_error(f"[DEBUG] {SETTINGS_FILE} not found. Creating default file.")
        create_default_settings_file()
        return default_exts

    return default_exts

def load_cubase_key_command():
    default_key = "shift+f1"

    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                log_error(f"[DEBUG] Loaded settings from JSON: {data}")

                if isinstance(data, dict):
                    key_cmd = data.get("cubase_key_command", default_key)
                    if isinstance(key_cmd, str):
                        return key_cmd
                    else:
                        log_error("[WARN] Invalid type for 'cubase_key_command'. Resetting to default.")
                        data["cubase_key_command"] = default_key
                        with open(SETTINGS_FILE, "w", encoding="utf-8") as fw:
                            json.dump(data, fw, indent=2)
                        return default_key

        except json.JSONDecodeError:
            log_error(f"[ERROR] Invalid JSON format in settings:\n{traceback.format_exc()}")
            messagebox.showerror("Settings Error", "Your settings file appears to be corrupted.\n"
                                                   "PatchIO will reset it to default. A backup will be created.")
            shutil.copyfile(SETTINGS_FILE, SETTINGS_FILE + ".corrupt")
            create_default_settings_file()
            return default_key
        except Exception:
            log_error(f"[ERROR] Failed to load cubase_key_command:\n{traceback.format_exc()}")
    else:
        log_error(f"[DEBUG] {SETTINGS_FILE} not found. Creating default file.")
        create_default_settings_file()
        return default_key

    return default_key


def save_cubase_key_command(new_key):
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    data["cubase_key_command"] = new_key.strip()
                    with open(SETTINGS_FILE, "w", encoding="utf-8") as fw:
                        json.dump(data, fw, indent=2)
                    log_error("[DEBUG] Saved cubase_key_command.")
        else:
            log_error(f"[ERROR] {SETTINGS_FILE} not found.")
    except Exception:
        log_error(f"[ERROR] Could not save cubase_key_command:\n{traceback.format_exc()}")


def create_default_settings_file():
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_SETTINGS, f, indent=2)
        log_error("[DEBUG] Created default settings file.")
    except Exception:
        log_error(f"[ERROR] Failed to create default settings file:\n{traceback.format_exc()}")

def save_last_extensions(extensions):
    try:
        # Save the updated extensions to the settings file
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    data["extensions"] = extensions
                    with open(SETTINGS_FILE, "w", encoding="utf-8") as f_out:
                        json.dump(data, f_out, indent=2)
                    log_error("[DEBUG] Extensions saved.")
        else:
            log_error(f"[ERROR] {SETTINGS_FILE} not found.")
    except Exception as e:
        log_error(f"[ERROR] Could not save extensions: \n{traceback.format_exc()}")

def enable_undo_redo(text_widget):
    text_widget.config(undo=True)

    def undo(event):
        try:
            text_widget.edit_undo()
        except tk.TclError:
            pass
        return "break"

    def redo(event):
        try:
            text_widget.edit_redo()
        except tk.TclError:
            pass
        return "break"

    text_widget.bind("<Control-z>", undo)         # Undo Windows/Linux
    text_widget.bind("<Control-y>", redo)         # Redo Windows/Linux
    text_widget.bind("<Command-z>", undo)         # Undo macOS
    text_widget.bind("<Command-Shift-Z>", redo)   # Redo macOS

result_queue = queue.Queue()

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False
    log_error(f"[ERROR] tkinterdnd2 not installed — drag & drop disabled.\n{traceback.format_exc()}")

icon_path = resource_path("pistachio.png")

def show_about():
    about_file = resource_path("about.txt")
    about_text = "PatchIO – Patches and Instruments Finder\nVersion 1.0.0\n© 2025 Shaked Shachar\n"
    try:
        with open(about_file, "r", encoding="utf-8") as f:
            about_text = f.read()
    except Exception as e:
        log_error(f"[ERROR] Could not read about.txt: \n{traceback.format_exc()}")
    messagebox.showinfo("About PatchIO", about_text)

def focus_next_widget(event):
    event.widget.tk_focusNext().focus_set()
    return "break"  # prevent inserting tab character

def focus_prev_widget(event):
    event.widget.tk_focusPrev().focus_set()
    return "break"  # prevent inserting tab character

def expand_plural_phrases(terms, quoted_flags):
    """
    For every quoted multi-word phrase, add plural form by pluralizing only the last word.
    Returns updated (terms, quoted_flags) lists.
    """
    plural_terms = []
    plural_quoted = []

    for term, quoted in zip(terms, quoted_flags):
        plural_terms.append(term)
        plural_quoted.append(quoted)

        if quoted and ' ' in term:
            words = term.split(' ')
            last_word = words[-1]

            # Naive pluralization for last word:
            if last_word.endswith('s'):
                plural_last = last_word  # already plural, skip
            elif last_word.endswith('y'):
                plural_last = last_word[:-1] + 'ies'
            else:
                plural_last = last_word + 's'

            if plural_last != last_word:
                plural_phrase = ' '.join(words[:-1] + [plural_last])
                plural_terms.append(plural_phrase)
                plural_quoted.append(True)  # plural form stays quoted

    return plural_terms, plural_quoted


def parse_terms(input_str):
    """
    Parse the input string into terms and detect which were quoted.
    Returns a tuple (terms, quoted_flags)
    """
    pattern = r'"([^"]+)"|(\S+)'
    matches = re.findall(pattern, input_str)
    terms = []
    quoted_flags = []
    for quoted, unquoted in matches:
        if quoted:
            terms.append(quoted)
            quoted_flags.append(True)
        else:
            terms.append(unquoted)
            quoted_flags.append(False)
    return terms, quoted_flags

def matches_term(term, text, quoted):
    term = term.lower()
    text = text.lower()

    if quoted:
        if ' ' in term:
            return term in text
        else:
            # Match whole word or surrounded by non-alphanumeric characters
            pattern = r'(?:^|[^a-zA-Z0-9])' + re.escape(term) + r'(?:[^a-zA-Z0-9]|$)'
            return re.search(pattern, text) is not None
    else:
        return term in text

def reveal_in_explorer(path):
    path = os.path.normpath(path)
    folder = os.path.dirname(path)
    file_exists = os.path.exists(path)

    if file_exists:
        try:
            # Now, open folder and select the file inside the opened folder
            subprocess.run(f'explorer /select,"{path}"', shell=True)
        except Exception as e:
            log_error(f"[ERROR] ShellExecute fallback due to:\n{traceback.format_exc()}")
            subprocess.run(f'explorer /select,"{path}"', shell=True)
    else:
        os.startfile(folder)


# def open_extensions_window():
#     global extensions_window_ref
#
#     if extensions_window_ref and extensions_window_ref.winfo_exists():
#         extensions_window_ref.lift()
#         extensions_window_ref.focus_force()
#         return
#
#     # Load extensions before creating window to calculate size
#     extensions_data = load_last_extensions()
#     extension_count = len(extensions_data)
#     checkbox_height_px = 35  # estimated height per checkbox
#     base_height = 170        # space for padding, buttons, label, etc.
#     total_height = base_height + checkbox_height_px * extension_count
#     total_height = max(total_height, 300)  # fallback minimum
#
#     window_width = 300
#     window_geometry = f"{window_width}x{total_height}"
#
#     extensions_window_ref = tk.Toplevel(root)
#     extensions_window_ref.title("Search Settings – File Extensions")
#     extensions_window_ref.geometry(window_geometry)
#     extensions_window_ref.minsize(window_width, total_height)
#     extensions_window_ref.transient(root)
#     extensions_window_ref.grab_set()
#
#     def on_close():
#         global extensions_window_ref
#         if extensions_window_ref is not None:
#             extensions_window_ref.destroy()
#             extensions_window_ref = None
#
#     extensions_window_ref.protocol("WM_DELETE_WINDOW", on_close)
#
#     label = ttk.Label(extensions_window_ref, text="Select file extensions to include in search:")
#     label.pack(pady=10)
#
#     checkbox_frame = tk.Frame(extensions_window_ref)
#     checkbox_frame.pack(pady=5, fill=tk.BOTH, expand=True)
#
#     canvas = tk.Canvas(checkbox_frame)
#     canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
#
#     inner_frame = tk.Frame(canvas)
#     canvas.create_window((0, 0), window=inner_frame, anchor='nw')
#
#     scrollbar = ttk.Scrollbar(checkbox_frame, orient=tk.VERTICAL, command=canvas.yview)
#     scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
#     canvas.configure(yscrollcommand=scrollbar.set)
#
#     def on_configure(event):
#         canvas.configure(scrollregion=canvas.bbox("all"))
#
#     inner_frame.bind("<Configure>", on_configure)
#
#     extension_vars.clear()
#
#     def on_extension_change():
#         updated_extensions = {ext: var.get() for ext, var in extension_vars.items()}
#         save_last_extensions(updated_extensions)
#
#     for ext, is_checked in extensions_data.items():
#         var = tk.BooleanVar(value=is_checked)
#         extension_vars[ext] = var
#         cb = ttk.Checkbutton(inner_frame, text=ext, variable=var, command=on_extension_change)
#         cb.pack(anchor='w', padx=10, pady=4)
#         cb.configure(takefocus=0)
#
#     def select_all():
#         for var in extension_vars.values():
#             var.set(True)
#         on_extension_change()
#
#     def deselect_all():
#         for var in extension_vars.values():
#             var.set(False)
#         on_extension_change()
#
#     btn_frame = tk.Frame(extensions_window_ref)
#     btn_frame.pack(pady=10)
#
#     ttk.Button(btn_frame, text="Select All", command=select_all).pack(side=tk.LEFT, padx=5)
#     ttk.Button(btn_frame, text="Deselect All", command=deselect_all).pack(side=tk.LEFT, padx=5)
#
#     ttk.Button(extensions_window_ref, text="Close", command=on_close).pack(pady=(5, 10))

# Tooltip for explaining AI feature
class ModernToolTip:
    def __init__(self, widget, text, bg="#222", fg="#fff"):
        self.widget = widget
        self.text = text
        self.bg = bg
        self.fg = fg
        self.tip_window = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x, y, _, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 20
        y += self.widget.winfo_rooty() + cy + 20

        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            tw, text=self.text, justify='left',
            background=self.bg, foreground=self.fg,
            relief="solid", borderwidth=1,
            font=("", 14), padx=8, pady=4,
            wraplength=260
        )
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

def open_documentation():

    if not os.path.exists(DOC_PATH):
        print(f"ERROR: {DOC_PATH} not found")
        messagebox.showerror("Error", "Documentation file not found.")
        return

    try:
        if platform.system() == "Darwin":  # macOS
            subprocess.call(["open", DOC_PATH])
        elif platform.system() == "Windows":
            os.startfile(DOC_PATH)
        else:  # Linux
            subprocess.call(["xdg-open", DOC_PATH])
    except Exception as e:
        messagebox.showerror("Error", f"Failed to open documentation:\n{e}")


def build_ui(root):
    # Style
    global style, AI_AVAILABLE
    style = ttk.Style()

    # get default colors of OS
    bg_color = style.lookup("TFrame", "background")
    fg_color = style.lookup("TLabel", "foreground")

    # Define your custom styles here:
    style.configure("Default.TButton")
    style.configure("Stop.TButton", foreground="gray50")  # foreground color
    # Define a custom style for the heading label
    style.configure(
        "Heading.TLabel",
        font=("Ariel", 22, "bold")
    )
    style.configure("My.TCheckbutton", padding=(5, 3), focuscolor="")  # (left/right, top/bottom)
    # Set global default font
    default_font = tkfont.nametofont("TkDefaultFont")
    default_font.configure(size=14)

    global plus_button, minus_button, plus_btn, folder_entries, excluded_folder_entries  # ensure access
    plus_button = None
    plus_btn = None
    minus_button = None
    folder_entries = []
    excluded_folder_entries = []

    global demo_label
    if DEMO_MODE:
        remaining = get_demo_days_remaining()
        tokens_used = get_demo_tokens_used()
        tokens_left = DEMO_TOKEN_LIMIT - tokens_used
        percent_used = min(round(tokens_used / DEMO_TOKEN_LIMIT * 100, 1), 100)
        print(f"percent_used: {tokens_used} / {DEMO_TOKEN_LIMIT} * 100 = {percent_used}")

        if percent_used >= 90:
            token_status = f"        ⚠️ You've used {percent_used}% out of your tokens!"
        else:
            token_status = ""

        demo_label_text_color = "#d45500" if not is_dark_mode() else "#ffb84d"
        # - Light mode: dark burnt orange (#b34700)
        # - Dark mode: soft glowing orange (#ffb84d)

        demo_label = ttk.Label(
            root,
            text=f"🧪 {DEMO_DURATION_DAYS}-day demo – {remaining} days remaining   |   {tokens_used}/{DEMO_TOKEN_LIMIT} AI tokens used"
                 f"{token_status}",
            foreground=demo_label_text_color,
            font=("", 12, "italic")
        )
        demo_label.pack(side="bottom", pady=(5, 5))

    # Check for internet connection
    if not check_internet():
        AI_AVAILABLE = False
        messagebox.showwarning(
            "Internet Required for AI",
            "AI search requires an active internet connection.\n"
            "Please reconnect and restart the app."
        )

    def create_styled_text_box(parent, height=7):
        frame = ttk.Frame(parent)

        text_widget = tk.Text(
            frame,
            height=height,
            wrap=tk.WORD,
            padx=10,
            pady=10,
            bd=0,
            relief="flat",
            font="TkDefaultFont"
        )

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)

        # Use grid inside frame for better layout control
        text_widget.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Allow expansion
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        return text_widget, frame

    def load_excluded_folders():
        if os.path.exists(SETTINGS_FILE):
            try:
                log_error(f"[DEBUG] Loading excluded folders from {SETTINGS_FILE}...")
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    excluded_folders = data.get("excluded_folders", [])
                    log_error(f"[DEBUG] Excluded folders loaded: {excluded_folders}")
                    return excluded_folders
            except json.JSONDecodeError as e:
                log_error(f"[ERROR] Invalid JSON format:\n{traceback.format_exc()}")
                messagebox.showerror("Settings Error", "Your settings file appears to be corrupted.\n"
                                                       "PatchIO will reset it to default. Your corrupted settings will be backed up.")
                # back up
                backup_path = SETTINGS_FILE + ".corrupt"
                shutil.copyfile(SETTINGS_FILE, backup_path)
                # Optionally reset the file
                create_default_settings_file()
            except Exception as e:
                log_error(f"[ERROR] Failed to load excluded folders:\n{traceback.format_exc()}")
        else:
            log_error(f"[DEBUG] {SETTINGS_FILE} does not exist. Returning empty list.")
        return []

    def save_excluded_folders():
        try:
            # Filter out invalid or empty entries
            folders = [e.get().strip() for _, e in excluded_folder_entries if e.winfo_exists() and e.get().strip()]

            # Log the excluded folders for debugging
            log_error(f"[DEBUG] Saving excluded folders: {folders}")

            # Load the existing settings file, if it exists
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {}

            # Update the excluded_folders section
            data["excluded_folders"] = folders

            # Save the updated data back to the settings file
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            log_error(f"[DEBUG] Excluded folders saved successfully.")
        except Exception as e:
            log_error(f"[ERROR] Failed to save excluded folders:\n{traceback.format_exc()}")

    def on_entry_change(event=None):
        save_excluded_folders()

    # append logs to log box in UI
    def append_log(log_widget, message):
        log_box.delete("1.0", tk.END) # clear first
        log_widget.insert(tk.END, message + "\n")
        log_widget.see(tk.END)

    def update_plus_button_state_for_excluded(plus_button):
        # Debug print to ensure the correct number of entries is being checked
        print(f"Number of entries (plus func): {len(excluded_folder_entries)}")

        # Check if plus_button is initialized
        if plus_button is None:
            print("Error: 'plus_button' is not initialized.")
            return

        # Disable the plus button if the max number of entries has been reached
        if len(excluded_folder_entries) >= MAX_EXCLUDED_FOLDERS:
            plus_button.state(['disabled'])
            print("Plus button disabled.")
        else:
            # Enable the plus button if there are fewer than the max allowed entries
            plus_button.state(['!disabled'])
            print("Plus button enabled.")

    def update_remove_buttons_visibility_for_excluded():
        # Check the length of excluded_folder_entries
        print(f"Number of entries: {len(excluded_folder_entries)}")

        if len(excluded_folder_entries) <= 1:
            # If only one folder entry, hide the remove button
            print("Hiding remove buttons")
            for row_frame, entry in excluded_folder_entries:
                # Ensure row_frame is still a valid widget before accessing it
                if row_frame.winfo_exists():
                    for widget in row_frame.winfo_children():
                        if isinstance(widget, ttk.Button) and widget['text'] == '–':
                            widget.pack_forget()  # Hide the button
        else:
            # Show the remove buttons for multiple entries
            print("Showing remove buttons")
            for row_frame, entry in excluded_folder_entries:
                # Ensure row_frame is still a valid widget before accessing it
                if row_frame.winfo_exists():
                    for widget in row_frame.winfo_children():
                        if isinstance(widget, ttk.Button) and widget['text'] == '–':
                            widget.pack(side=tk.LEFT, padx=(5, 0))  # Show the button

    def add_excluded_field(inner_frame, path="", plus_button=None):
        if len(excluded_folder_entries) >= MAX_EXCLUDED_FOLDERS:
            return  # Prevent adding more than the maximum allowed folders

        row_frame = ttk.Frame(inner_frame)
        row_frame.pack(pady=(2, 3), anchor='w')

        entry = ttk.Entry(row_frame, width=60)
        entry.insert(0, path)
        entry.pack(side=tk.LEFT)
        entry.bind("<KeyRelease>", on_entry_change)

        def browse_entry(e=entry):
            selected = filedialog.askdirectory()
            if selected:
                e.delete(0, tk.END)
                e.insert(0, selected)
                save_excluded_folders()

        browse_btn = ttk.Button(row_frame, text="Browse", command=browse_entry)
        browse_btn.pack(side=tk.LEFT, padx=(5, 0))

        if DND_AVAILABLE:
            entry.drop_target_register(DND_FILES)

            def drop(event, entry=entry):
                paths = root.tk.splitlist(event.data)
                if paths:
                    folder = paths[0].strip("{}")
                    if os.path.isdir(folder):
                        entry.delete(0, tk.END)
                        entry.insert(0, folder)
                        save_excluded_folders()  # <-- This ensures saving on drop
                return 'break'

            entry.dnd_bind('<<Drop>>', drop)

        def remove_entry():
            row_frame.destroy()
            excluded_folder_entries.remove((row_frame, entry))
            save_excluded_folders()
            update_remove_buttons_visibility_for_excluded()  # Update visibility after removing a folder
            update_plus_button_state_for_excluded(plus_button)  # Update plus button state after removal

        # Remove button ("–") will be hidden if there's only 1 entry
        remove_btn = ttk.Button(row_frame, text="–", width=2, command=remove_entry)
        remove_btn.pack(side=tk.LEFT, padx=(5, 0))

        excluded_folder_entries.append((row_frame, entry))

        update_remove_buttons_visibility_for_excluded()  # Update visibility after adding a folder
        update_plus_button_state_for_excluded(plus_button)  # Update plus button state after adding a folder

    def open_preferences_window():
        pref = tk.Toplevel(root)
        pref.title("Preferences")
        pref.geometry("850x500")
        pref.minsize(850, 500)
        pref.transient(root)
        pref.grab_set()

        notebook = ttk.Notebook(pref)
        notebook.pack(fill="both", expand=True)

        folders_tab = ttk.Frame(notebook)
        extensions_tab = ttk.Frame(notebook)
        key_commands_tab = ttk.Frame(notebook)

        notebook.add(folders_tab, text="Excluded Folders")
        notebook.add(extensions_tab, text="File Types")
        notebook.add(key_commands_tab, text="Key Commands")

        def clear_entry_focus(event):
            pref.focus_force()

        notebook.bind("<<NotebookTabChanged>>", clear_entry_focus)

        # === EXCLUDED FOLDERS TAB ===
        excluded_folder_entries.clear()

        excluded_frame = ttk.Frame(folders_tab, padding=20)
        excluded_frame.pack(fill=tk.BOTH, expand=True)

        label = ttk.Label(excluded_frame, text="Folder(s) to exclude from search:")
        label.pack(anchor='center')

        inner_frame = ttk.Frame(excluded_frame)
        inner_frame.pack()

        def add_and_save(path=""):
            add_excluded_field(inner_frame, path, plus_button=plus_btn)
            save_excluded_folders()

        plus_btn = ttk.Button(excluded_frame, text="+", width=2, command=lambda: add_and_save())
        plus_btn.pack(pady=10)

        existing = load_excluded_folders()
        for path in existing or [""]:
            add_excluded_field(inner_frame, path, plus_button=plus_btn)

        update_plus_button_state_for_excluded(plus_btn)
        update_remove_buttons_visibility_for_excluded()

        # === EXTENSIONS TAB ===
        extension_frame = ttk.Frame(extensions_tab, padding=20)
        extension_frame.pack(fill="both", expand=True)

        extensions_data = load_last_extensions()
        extension_vars = {}

        def on_extension_toggle():
            updated_dict = {ext: var.get() for ext, var in extension_vars.items()}
            save_last_extensions(updated_dict)
            update_all_group_states()

        # First: create individual extension BooleanVars
        for ext in sorted(extensions_data):
            var = tk.BooleanVar(value=extensions_data.get(ext, True))
            extension_vars[ext] = var

        group_vars = {}
        group_labels = {}

        def update_group_state(group_name):
            states = [extension_vars[ext].get() for ext in EXT_GROUPS[group_name] if ext in extension_vars]
            label_widget = group_labels.get(group_name)

            if not states:
                group_vars[group_name].set(False)
                if label_widget:
                    label_widget.config(state="disabled", text=group_name)
                return

            is_all_on = all(states)
            group_vars[group_name].set(is_all_on)
            if label_widget:
                label_widget.config(state="normal", text=group_name)

        def update_all_group_states():
            for group in EXT_GROUPS:
                update_group_state(group)

        # Show each group as its own top-level checkbox
        for group, ext_list in EXT_GROUPS.items():
            group_var = tk.BooleanVar()
            group_vars[group] = group_var

            def make_toggle_fn(group_name=group):
                def toggle():
                    val = group_vars[group_name].get()
                    for ext in EXT_GROUPS[group_name]:
                        if ext in extension_vars:
                            extension_vars[ext].set(bool(val))
                    on_extension_toggle()

                return toggle

            label = ttk.Checkbutton(
                extension_frame,
                text=group,
                variable=group_var,
                onvalue=True,
                offvalue=False,
                command=make_toggle_fn(group_name=group)
            )
            label.pack(anchor="w", pady=(5, 0))
            group_labels[group] = label

            if not any(ext in extension_vars for ext in ext_list):
                label.config(state="disabled")

        # Handle ungrouped extensions — show each as its own group-style checkbox
        ungrouped_exts = [ext for ext in extension_vars if not any(ext in lst for lst in EXT_GROUPS.values())]
        if ungrouped_exts:
            for ext in sorted(ungrouped_exts):
                group_var = tk.BooleanVar(value=extension_vars[ext].get())
                group_vars[ext] = group_var

                def make_ungrouped_fn(ext_name=ext):
                    def toggle():
                        extension_vars[ext_name].set(group_vars[ext_name].get())
                        on_extension_toggle()

                    return toggle

                cb = ttk.Checkbutton(
                    extension_frame,
                    text=ext,
                    variable=group_var,
                    onvalue=True,
                    offvalue=False,
                    command=make_ungrouped_fn()
                )
                cb.pack(anchor="w", pady=(5, 0))

        # Initial update
        update_all_group_states()

        # === KEY COMMANDS TAB ===
        key_frame = ttk.Frame(key_commands_tab, padding=20)
        key_frame.pack(fill="both", expand=True)

        key_var = tk.StringVar(value=load_cubase_key_command())

        ttk.Label(key_frame, text="Key Command to Add Kontakt Instrument Track in Cubase:").pack(anchor="w",
                                                                                                       pady=(10, 4))
        entry = ttk.Entry(key_frame, textvariable=key_var, width=30)
        entry.pack(anchor="w")
        entry.bind("<KeyRelease>", lambda e: save_cubase_key_command(key_var.get()))

    menu_bar = tk.Menu(root)
    help_menu = tk.Menu(menu_bar, tearoff=0)
    help_menu.add_command(label="About", command=show_about)
    help_menu.add_command(label="Documentation", command=open_documentation)
    help_menu.add_command(label="Check for Updates", command=check_for_updates)
    menu_bar.add_cascade(label="Help", menu=help_menu)

    # --- Settings Menu ---
    settings_menu = tk.Menu(menu_bar, tearoff=0)
    # settings_menu.add_command(label="File Extensions", command=open_extensions_window)
    # settings_menu.add_command(label="Excluded Folders", command=open_excluded_folders_window)
    settings_menu.add_command(label="Preferences", command=open_preferences_window)
    menu_bar.add_cascade(label="Settings", menu=settings_menu)

    root.config(menu=menu_bar)

    frame = tk.Frame(root, padx=20, pady=20)
    frame.pack(fill=tk.BOTH, expand=True)

    header_frame = tk.Frame(frame)
    header_frame.pack(pady=(0, 15))

    try:
        if os.path.exists(icon_path):
            img = Image.open(icon_path)
            img = img.resize((32, 32), Image.LANCZOS)
            icon_img = ImageTk.PhotoImage(img)
            icon_label = ttk.Label(header_frame, image=icon_img)
            icon_label.image = icon_img
            icon_label.pack(side=tk.LEFT, padx=(0, 8))
    except Exception:
        log_error(f"[ERROR] Failed to load icon:\n{traceback.format_exc()}")

    # Create the label with the custom style
    header_label = ttk.Label(header_frame, text="PatchIO – Patches and Instruments Finder", style="Heading.TLabel")
    header_label.pack(side=tk.LEFT)

    folder_label = ttk.Label(frame, text="Folder(s) to search (browse or drag & drop folders here):")
    folder_label.pack(anchor='center')

    folders_frame = tk.Frame(frame)
    folders_frame.pack()

    def on_folder_entry_change(event=None):
        save_last_folders()

    def update_plus_button_state():
        if plus_button is None:
            return
        if len(folder_entries) >= MAX_FOLDER_ENTRIES:
            plus_button.state(['disabled'])
        else:
            plus_button.state(['!disabled'])

    def update_remove_buttons_visibility():
        # Show minus buttons only if more than 1 folder entry
        show = len(folder_entries) > 1

        for row_frame, entry in folder_entries:
            # Find the remove button in the row_frame
            remove_btn = None
            for widget in row_frame.winfo_children():
                if isinstance(widget, ttk.Button) and widget['text'] == '–':
                    remove_btn = widget
                    break

            # Show or hide the remove button
            if remove_btn:
                if show:
                    remove_btn.pack(side=tk.LEFT, padx=(5, 0))  # Show button
                else:
                    remove_btn.pack_forget()  # Hide button

    def add_folder_field(folder_path=""):
        if len(folder_entries) >= MAX_FOLDER_ENTRIES:
            return

        row_frame = ttk.Frame(folders_frame)
        row_frame.pack(pady=(2, 3), anchor='w')

        entry = ttk.Entry(row_frame, width=60)
        entry.insert(0, folder_path)
        entry.pack(side=tk.LEFT)
        entry.bind("<KeyRelease>", on_folder_entry_change)

        def browse_this_entry(e=entry):
            folder_selected = filedialog.askdirectory()
            if folder_selected:
                e.delete(0, tk.END)
                e.insert(0, folder_selected)
                save_last_folders()

        browse_btn = ttk.Button(row_frame, text="Browse", command=browse_this_entry)
        browse_btn.pack(side=tk.LEFT, padx=(5, 0))

        if DND_AVAILABLE:
            entry.drop_target_register(DND_FILES)

            def drop(event, entry=entry):
                paths = root.tk.splitlist(event.data)
                if paths:
                    folder = paths[0].strip("{}")
                    if os.path.isdir(folder):
                        entry.delete(0, tk.END)
                        entry.insert(0, folder)
                        save_last_folders()  # <-- This ensures saving on drop
                return 'break'

            entry.dnd_bind('<<Drop>>', drop)

        def remove_this_field():
            row_frame.destroy()
            folder_entries.remove((row_frame, entry))  # Remove everything together
            save_last_folders()
            update_plus_button_state()
            update_remove_buttons_visibility()

        remove_btn = ttk.Button(row_frame, text="–", width=2, command=remove_this_field)
        remove_btn.pack(side=tk.LEFT, padx=(5, 0))

        folder_entries.append((row_frame, entry))  # Store all elements

        update_plus_button_state()
        update_remove_buttons_visibility()

    # Clear existing folder entries just in case
    for row_frame, entry in folder_entries:
        row_frame.destroy()
    folder_entries.clear()

    last_folders = load_last_folders()
    log_error(f"[DEBUG] last_folders after loading: {last_folders}")
    if last_folders:
        for _ in last_folders:
            add_folder_field()
        for i, folder_path in enumerate(last_folders):
            _, entry = folder_entries[i]
            entry.delete(0, tk.END)
            entry.insert(0, folder_path)
    else:
        add_folder_field()

    # Ensure all current entries are bound to save on focus loss
    for _, entry in folder_entries:
        entry.bind("<KeyRelease>", on_folder_entry_change)

    # "+" button below all entries
    buttons_frame = ttk.Frame(frame)
    buttons_frame.pack(pady=(5, 10))

    plus_button = ttk.Button(buttons_frame, text="+", width=2, command=add_folder_field)
    plus_button.pack(side=tk.LEFT)

    update_plus_button_state()
    update_remove_buttons_visibility()

    load_last_extensions()  # Load the last extensions state when the app starts

    buttons_frame = tk.Frame(frame)
    buttons_frame.pack(pady=(0, 10))

    _ai_call_after_id = None

    frame = ttk.Frame(root)
    frame.pack(fill=tk.BOTH, expand=True)

    # Label + toggle frame (includes label, radio buttons, and text box)
    label_toggle_frame = ttk.Frame(frame)
    label_toggle_frame.pack(fill='x', pady=(10, 5), padx=15)

    # Then: label + radio buttons in same row
    top_controls_frame = ttk.Frame(label_toggle_frame)
    top_controls_frame.pack(fill='x', pady=(0, 6))  # Add 6 pixels below

    keywords_label = ttk.Label(top_controls_frame,
                               text="Enter keywords (Use quotes for exact matches, comma or space separated):")
    keywords_label.pack(side=tk.LEFT, anchor='w')

    search_mode_var = tk.StringVar(value="ai") # initialize with AI mode as default
    search_mode_frame = ttk.Frame(top_controls_frame)
    search_mode_frame.pack(side=tk.RIGHT)

    radio_buttons = {}  # key = mode name, value = Radiobutton widget

    for text, mode in [("AI Search", "ai"), ("Simple", "simple"), ("Advanced", "advanced")]:
        rb = ttk.Radiobutton(search_mode_frame, text=text, variable=search_mode_var, value=mode)
        rb.pack(side="left", padx=5)
        radio_buttons[mode] = rb

    tooltip_text = (
        "Type any scene, genre, or mood — AI will suggest matching instruments and sounds.\n"
        "It automatically fills the 'Advanced' tab with smart keyword filters for your search."
    )

    ModernToolTip(radio_buttons['ai'],
                  tooltip_text,
                  bg="#222" if IS_DARK_MODE else "#ffffe0",
                  fg="#f8f8f8" if IS_DARK_MODE else "#000000"
                  )

    # Keyword mode content container
    search_input_holder = ttk.Frame(label_toggle_frame)
    search_input_holder.pack(fill="both", expand=True)

    search_box_holder = ttk.Frame(search_input_holder)
    search_box_holder.pack(fill="both", expand=True)

    # Simple Keywords Box
    #simple_keywords_entry = ScrolledText(search_input_holder,height=10, wrap=tk.WORD, padx=10, pady=10, bd=0)
    simple_keywords_entry, simple_scroll_frame = create_styled_text_box(search_box_holder, height=10)
    simple_scroll_frame.pack(fill="both", expand=True)
    enable_undo_redo(simple_keywords_entry)
    simple_keywords_entry.bind("<Return>", on_enter_press)
    simple_keywords_entry.bind("<Shift-Return>", on_shift_enter_press)

    # AI Keywords Box
    #ai_search_entry = ScrolledText(search_input_holder,height=10, wrap=tk.WORD, padx=10, pady=10, bd=0)
    ai_search_entry, ai_search_entry_frame = create_styled_text_box(search_box_holder, height=10)
    ai_search_entry_frame.pack(fill="both", expand=True)
    default_fg = ai_search_entry.cget("fg")  # store whatever the current theme uses
    default_font = ai_search_entry.cget("font")
    enable_undo_redo(ai_search_entry)
    ai_search_entry.bind("<Return>", on_enter_press)
    ai_search_entry.bind("<Shift-Return>", on_shift_enter_press)
    placeholder_text = "Try: quirky bassoon, warm piano, festive Christmas instruments"
    placeholder_active = [True]

    ai_search_entry.insert("1.0", placeholder_text)
    ai_search_entry.configure(fg="#888888")

    def clear_placeholder_if_active():
        if placeholder_active[0]:
            ai_search_entry.delete("1.0", tk.END)
            ai_search_entry.configure(fg=default_fg, font=default_font)
            placeholder_active[0] = False

    def on_focus_in(event):
        clear_placeholder_if_active()

    def on_keypress(event):
        clear_placeholder_if_active()

    def on_focus_out(event):
        current = ai_search_entry.get("1.0", "end-1c").strip()
        if not current:
            ai_search_entry.insert("1.0", placeholder_text)
            ai_search_entry.configure(fg="#888888")
            placeholder_active[0] = True

    ai_search_entry.bind("<FocusIn>", on_focus_in)
    ai_search_entry.bind("<KeyPress>", on_keypress)
    ai_search_entry.bind("<FocusOut>", on_focus_out)

    # Advanced Frame with keyword blocks
    advanced_frame = ttk.Frame(search_box_holder)

    def make_keyword_block(parent, label_text):
        block = ttk.Frame(parent, padding=(10, 0))
        block.grid_propagate(False)  # important when using .grid()

        label = ttk.Label(block, text=label_text)
        label.pack(anchor='w', pady=(0, 4))

        # Frame to contain text + scrollbar
        box, box_frame = create_styled_text_box(block, height=7)
        box_frame.pack(fill='both', expand=True)

        # Make sure the box_frame itself expands inside the block
        block.rowconfigure(0, weight=1)
        block.columnconfigure(0, weight=1)

        enable_undo_redo(box)
        box.bind("<Return>", on_enter_press)
        box.bind("<Shift-Return>", on_shift_enter_press)

        return box, block, box_frame

    keywords_or_entry, or_block, _ = make_keyword_block(advanced_frame, "Any of these words (OR):")
    keywords_and_entry, and_block, _ = make_keyword_block(advanced_frame, "All of these words (AND):")
    keywords_not_entry, not_block, _ = make_keyword_block(advanced_frame, "None of these words (NOT):")

    advanced_frame.columnconfigure((0, 1, 2), weight=1)
    or_block.grid(row=0, column=0, padx=5, sticky='nsew')
    and_block.grid(row=0, column=1, padx=5, sticky='nsew')
    not_block.grid(row=0, column=2, padx=5, sticky='nsew')
    advanced_frame.rowconfigure(0, weight=1)  # allow row 0 to expand

    # Add tab functionality to all text boxes in advanced tab
    for entry in [keywords_or_entry, keywords_and_entry, keywords_not_entry]:
        entry.bind("<Tab>", focus_next_widget)
        entry.bind("<Shift-Tab>", focus_prev_widget)

    advanced_frame.columnconfigure((0,1,2), weight=1)
    advanced_shown = tk.BooleanVar(value=False)

    # Function to switch visible search input
    def on_search_mode_change(*args):
        mode = search_mode_var.get()

        # Clear current contents
        simple_scroll_frame.pack_forget()
        ai_search_entry_frame.pack_forget()
        advanced_frame.pack_forget()

        if mode == "simple":
            simple_scroll_frame.pack(fill="both", expand=True)
            keywords_label.config(text="Enter keywords (Use quotes for exact matches, comma or space separated):")
            advanced_shown.set(False)

        elif mode == "ai":
            ai_search_entry_frame.pack(fill="both", expand=True)
            keywords_label.config(
                text="Describe any sound, mood, instrument or idea — I'll help you find the right patch.")
            advanced_shown.set(False)

        elif mode == "advanced":
            advanced_frame.pack(fill="both", expand=True)
            keywords_label.config(text="Enter keywords (Use quotes for exact matches, comma or space separated):")
            advanced_shown.set(True)

    # Watch for mode changes
    search_mode_var.trace_add("write", on_search_mode_change)

    # Initial UI mode setup (show "simple" box by default)
    on_search_mode_change()

    advanced_frame.columnconfigure((0, 1, 2), weight=1)

    # Continue with search button, results box etc. below this

    # Now define search_in_folder inside build_ui to access those variables directly:
    def on_search_button_click():
        global searching, stop_search_flag, ai_search_in_progress
        if searching:
            stop_search_flag = True
            return  # Let poll_results detect and stop

        ai_search_in_progress = False
        search_button.config(text="Stop", style="Stop.TButton")

        mode = search_mode_var.get()
        log_box.delete("1.0", tk.END)
        results_tree.delete(*results_tree.get_children())
        
        # Reset sort indicators
        sort_reverse[0] = False
        results_tree.heading("last modified", text="Last Modified")

        if mode == "ai":
            prompt = ai_search_entry.get("1.0", tk.END).strip()
            if not prompt:
                messagebox.showwarning("Input needed", "Please enter a prompt for AI search.")
                return
            if placeholder_active[0] or not prompt:
                append_log(log_box, "Please enter a search prompt.\n")
                search_button.config(text="Search", state="normal", style="TButton")  # ← make sure it's enabled again
                searching = False
                ai_search_in_progress = False
                results_count_label.config(text="")
                return

            # Check internet before calling GPT
            if not check_internet():
                messagebox.showerror(
                    "No Internet Connection",
                    "AI search requires an active internet connection.\n"
                    "Please reconnect and try again."
                )
                search_button.config(text="Search", state="normal", style="TButton")  # ← make sure it's enabled again
                searching = False
                ai_search_in_progress = False
                results_count_label.config(text="")
                return

            searching = True
            stop_search_flag = False
            ai_search_in_progress = True
            results_count_label.config(text="Searching...")
            search_button.config(text="Stop", style="Stop.TButton")

            text = ai_search_entry.get("1.0", "end-1c").strip()
            if text == placeholder_text or not text:
                append_log(log_box, "Please enter a search prompt.\n")
                search_button.config(text="Search", style="TButton")
                searching = False
                results_count_label.config(text="")
                return

            if DEMO_MODE:
                if not check_demo_validity():
                    messagebox.showwarning("Demo Expired", f"Your {DEMO_DURATION_DAYS}-day demo has expired.")
                    return

                tokens_used = get_demo_tokens_used()
                if tokens_used >= DEMO_TOKEN_LIMIT:
                    messagebox.showwarning(
                        "AI Token Limit Reached",
                        f"You've reached the AI usage limit for this demo license ({tokens_used}/{DEMO_TOKEN_LIMIT} tokens).\n"
                        "To extend your trial or upgrade, please contact the creator: info@shaked-music.com"
                    )
                    search_button.config(text="Search", style="TButton")
                    searching = False
                    results_count_label.config(text="")
                    return

            threading.Thread(
                target=call_gpt_api_to_generate_keywords,
                args=(
                    text,
                    root,
                    keywords_or_entry,
                    keywords_and_entry,
                    keywords_not_entry,
                    search_button,
                    on_gpt_keywords_ready,
                    results_count_label,
                ),
                daemon=True
            ).start()

        else:
            # Parse keywords from UI depending on mode
            if advanced_shown.get():
                or_raw = keywords_or_entry.get("1.0", tk.END).strip().lower()
                and_raw = keywords_and_entry.get("1.0", tk.END).strip().lower()
                not_raw = keywords_not_entry.get("1.0", tk.END).strip().lower()

                try:
                    or_terms, or_quoted = parse_terms(or_raw) if or_raw else ([], [])
                    and_terms, and_quoted = parse_terms(and_raw) if and_raw else ([], [])
                    not_terms, not_quoted = parse_terms(not_raw) if not_raw else ([], [])

                    # Apply plural expansions only to multi-word quoted phrases
                    or_terms, or_quoted = expand_plural_phrases(or_terms, or_quoted)
                    and_terms, and_quoted = expand_plural_phrases(and_terms, and_quoted)
                    not_terms, not_quoted = expand_plural_phrases(not_terms, not_quoted)

                except Exception as e:
                    print(f"Error:{e}")

                    overlap_terms = set(not_terms) & (set(or_terms) | set(and_terms))
                    if overlap_terms:
                        overlap_list = ", ".join(f"'{term}'" for term in overlap_terms)
                        messagebox.showwarning(
                            "Keyword Conflict",
                            f"The following words appear both in NOT and OR/AND boxes: {overlap_list}.\n"
                            "Please remove them from either the NOT box or the OR/AND boxes."
                        )
                        search_button.config(text="Search", state="normal", style="TButton")
                        searching = False
                        stop_search_flag = False
                        results_count_label.config(text="")
                        return

                except Exception as e:
                    append_log(log_box, f"Error parsing keywords: {e}\n")
                    log_error(f"Error parsing keywords:\n{traceback.format_exc()}")
                    search_button.config(text="Search")
                    searching = False
                    results_count_label.config(text="")
                    return

                if not (or_terms or and_terms or not_terms):
                    append_log(log_box, "Please enter at least one keyword in OR, AND or NOT boxes.\n")
                    search_button.config(text="Search", style="TButton", state="normal")
                    searching = False
                    stop_search_flag = False
                    results_count_label.config(text="")
                    return

            else: # simple mode
                simple_raw = simple_keywords_entry.get("1.0", tk.END).strip().lower()
                try:
                    or_terms, or_quoted = parse_terms(simple_raw)
                    # Expand plural forms only for quoted phrases with multiple words
                    or_terms, or_quoted = expand_plural_phrases(or_terms, or_quoted)
                except Exception as e:
                    append_log(log_box, f"Error parsing keywords: {e}\n")
                    log_error(f"Error parsing keywords:\n{traceback.format_exc()}")
                    search_button.config(text="Search")
                    searching = False
                    results_count_label.config(text="")
                    return

                if not or_terms:
                    append_log(log_box, "Please enter at least one keyword.\n")
                    search_button.config(text="Search", state="normal", style="TButton")
                    searching = False
                    stop_search_flag = False
                    results_count_label.config(text="")
                    return

                and_terms, and_quoted = [], []
                not_terms, not_quoted = [], []

            # Now start the actual search with parsed keywords
            search_button.config(text="Stop", style="Stop.TButton")
            searching = True
            stop_search_flag = False
            results_count_label.config(text="Searching...")
            search_for_folder(or_terms, and_terms, not_terms, or_quoted, and_quoted, not_quoted)

    def on_gpt_keywords_ready(gpt_output):
        global searching, ai_search_in_progress, stop_search_flag

        if stop_search_flag:
            append_log(log_box, "Search was canceled before file scan began.\n")
            searching = False
            ai_search_in_progress = False
            results_count_label.config(text="")
            search_button.config(text="Search", style="TButton")
            return

        ai_search_in_progress = False  # GPT finished
        try:
            is_valid, error_msg = validate_gpt_output(gpt_output)
            if not is_valid:
                messagebox.showerror("Invalid AI Output", f"The AI response was not usable:\n\n{error_msg}")
                search_button.config(state="normal", text="Search")
                searching = False
                ai_search_in_progress = False
                stop_search_flag = False
                results_count_label.config(text="")
                return

            lines = gpt_output.strip().splitlines()
            or_line = lines[0][3:].strip()
            and_line = lines[1][4:].strip()
            not_line = lines[2][4:].strip()

            keywords_or_entry.delete("1.0", tk.END)
            keywords_or_entry.insert(tk.END, or_line)

            keywords_and_entry.delete("1.0", tk.END)
            keywords_and_entry.insert(tk.END, and_line)

            keywords_not_entry.delete("1.0", tk.END)
            keywords_not_entry.insert(tk.END, not_line)

            append_log(log_box, "AI keywords generated and populated into Advanced mode.\n")

            search_button.config(state="normal", text="Search")

            # Make sure advanced mode is on before searching
            advanced_shown.set(True)

            # Allow UI to update, then trigger search_for_folder with parsed terms
            root.update_idletasks()  # force UI refresh

            # Parse the terms from the text boxes again to pass to search_for_folder
            or_terms, or_quoted = parse_terms(keywords_or_entry.get("1.0", tk.END))
            and_terms, and_quoted = parse_terms(keywords_and_entry.get("1.0", tk.END))
            not_terms, not_quoted = parse_terms(keywords_not_entry.get("1.0", tk.END))

            # Apply plural expansions only for quoted multi-word phrases
            or_terms, or_quoted = expand_plural_phrases(or_terms, or_quoted)
            and_terms, and_quoted = expand_plural_phrases(and_terms, and_quoted)
            not_terms, not_quoted = expand_plural_phrases(not_terms, not_quoted)

            # Trigger search shortly after to avoid race conditions
            root.after(100,
                       lambda: search_for_folder(or_terms, and_terms, not_terms, or_quoted, and_quoted, not_quoted))

        except Exception as e:
            messagebox.showerror("Error", f"Failed to process GPT keywords: {e}")
            search_button.config(state="normal", text="Search")

    def search_for_folder(or_terms, and_terms, not_terms, or_quoted, and_quoted, not_quoted):
        global search_thread, searching, stop_search_flagm, ai_search_in_progress
        result_count = [0]  # mutable counter
        stop_search_flag = False

        # Load excluded folders and normalize paths
        excluded_folders = load_excluded_folders()
        excluded_folders = [os.path.normcase(os.path.abspath(f)) for f in excluded_folders]
        print(f"Excluded folders after normalization: {excluded_folders}")  # Debug
        log_error(f"[DEBUG] Error parsing keywords:\n{traceback.format_exc()}")

        # Get selected folders, validate and normalize
        selected_folders = [entry.get().strip() for _, entry in folder_entries if
                            entry.get().strip() and os.path.isdir(entry.get().strip())]

        selected_folders = [os.path.abspath(folder) for folder in selected_folders]
        print(f"[DEBUG] Selected folders after normalization: {selected_folders}")  # Debug
        if not selected_folders:
            append_log(log_box, "Please enter at least one valid folder path.\n")
            search_button.config(text="Search", state="normal", style="TButton")  # ← make sure it's enabled again
            searching = False
            ai_search_in_progress = False
            results_count_label.config(text="")
            return

        # Filter out selected folders that are excluded
        selected_folders = [
            folder for folder in selected_folders
            if not any(
                folder == excluded or
                os.path.commonpath([folder, excluded]) == excluded
                for excluded in excluded_folders
            )
        ]

        if not selected_folders:
            append_log(log_box, "All selected folders are excluded.\n")
            searching = False
            stop_search_flag = False
            search_button.config(text="Search", style="TButton")
            return

        # Log mode info
        if advanced_shown.get():
            append_log(log_box, f"Searching in {len(selected_folders)} folder(s) (Advanced mode: OR + AND + NOT)\n")
        else:
            append_log(log_box, f"Searching in {len(selected_folders)} folder(s) (Simple OR mode)\n")

        # Clear previous results in UI
        for item in results_tree.get_children():
            results_tree.delete(item)
        
        # Reset sort indicators
        sort_reverse[0] = False
        results_tree.heading("last modified", text="Last Modified")

        for folder in selected_folders:
            log_box.insert(tk.END, f"• {folder}\n")
        log_box.insert(tk.END, "\n")

        # Load extensions selected
        extensions_data = load_last_extensions()
        selected_extensions = tuple(ext for ext, is_checked in extensions_data.items() if is_checked)
        if not selected_extensions:
            append_log(log_box, "No extensions selected. Please select at least one extension in the Settings menu.\n")
            return

        seen_folders = {}
        matches_found = [False]
        total_threads = len(selected_folders)
        finished_threads = [0]

        searching = True
        search_button.config(text="Stop", style="Stop.TButton")

        while not result_queue.empty():
            result_queue.get_nowait()

        def normalize_path(path):
            return os.path.normpath(path).lower()

        def is_folder_excluded(folder, excluded_folders):
            normalized_folder = normalize_path(folder)

            for excluded_folder in excluded_folders:
                normalized_excluded = normalize_path(excluded_folder)

                if normalized_folder == normalized_excluded:
                    return True

                if normalized_folder.startswith(normalized_excluded + os.sep):
                    return True

            return False

        def is_subfolder_of(folder, excluded_folder):
            folder = os.path.normpath(folder).lower()
            excluded_folder = os.path.normpath(excluded_folder).lower()

            if folder == excluded_folder:
                return True

            if folder.startswith(excluded_folder + os.sep):
                return True

            return False

        def threaded_search(folder):
            is_advanced = advanced_shown.get()

            if is_folder_excluded(folder, excluded_folders):
                return

            for file_path in recursive_scan(folder, selected_extensions, excluded_folders):
                if stop_search_flag:
                    break

                full_path = file_path.lower()

                if any(
                        full_path.startswith(excluded.lower())
                        and is_subfolder_of(full_path, excluded.lower())
                        for excluded in excluded_folders
                ):
                    continue

                if is_advanced:
                    or_match = not or_terms or any(
                        matches_term(term, full_path, quoted)
                        for term, quoted in zip(or_terms, or_quoted)
                    )
                    if not or_match:
                        continue

                    if and_terms:
                        and_match = all(
                            matches_term(term, full_path, quoted)
                            for term, quoted in zip(and_terms, and_quoted)
                        )
                        if not and_match:
                            continue

                    if not_terms:
                        not_match = any(
                            matches_term(term, full_path, quoted)
                            for term, quoted in zip(not_terms, not_quoted)
                        )
                        if not_match:
                            continue

                    result_queue.put(file_path)

                else:
                    if any(matches_term(term, full_path, quoted) for term, quoted in zip(or_terms, or_quoted)):
                        result_queue.put(file_path)

            result_queue.put(None)  # Signal thread finished

        base_folders = selected_folders[:]
        normalized_base_folders = [os.path.normpath(os.path.abspath(f)).lower() for f in base_folders]

        def run_threads():
            threads = []
            for folder in selected_folders:
                t = threading.Thread(target=threaded_search, args=(folder,), daemon=True)
                threads.append(t)
                t.start()
            for t in threads:
                t.join()

        def extract_library_root(path):
            """
            Attempts to extract a 'library root' identifier from a file path.
            E.g., /Samples/Spitfire Audio - Symphonic Woodwinds/Instruments/... -> Spitfire Audio - Symphonic Woodwinds
            """
            parts = os.path.normpath(path).split(os.sep)
            try:
                # Find "Samples" or "Libraries", then return the next component as library name
                for i, part in enumerate(parts):
                    if part.lower() in ["samples", "libraries"] and i + 1 < len(parts):
                        return parts[i + 1]
            except Exception:
                pass
            # Fallback to second-to-last folder (like "Splice Sounds" or vendor folder)
            return parts[-2] if len(parts) >= 2 else parts[-1]

        matched_paths = []

        def poll_results(keywords):
            seen_folders.clear()
            library_nodes = {}

            def get_library_key(path):
                parts = os.path.normpath(path).split(os.sep)
                generic_dirs = {
                    "samples", "instruments", "presets", "audio", "multis", "articulations",
                    "data", "patches", "files", "programs", "kits", "output", "sounds"
                }
                for i in range(len(parts) - 1, 1, -1):
                    if parts[i].lower() not in generic_dirs:
                        return os.sep.join(parts[:i + 1])
                return os.sep.join(parts[-3:]) if len(parts) >= 3 else path

            def insert_path_live(full_path, or_terms, and_terms):
                global all_items
                parent = os.path.dirname(full_path)
                lib_root = get_library_key(parent)
                lib_name = os.path.basename(lib_root.rstrip(os.sep)) or lib_root

                # Track matched keywords for this path
                matches = get_matched_keywords(full_path, or_terms, and_terms)
                if matches:
                    path = os.path.normpath(full_path)
                    normalized_lib_root = os.path.normpath(lib_root).lower()

                    # ✅ Make sure lib_root is included!
                    folder_keyword_map[normalized_lib_root].update(matches)

                    while True:
                        folder_keyword_map[path].update(matches)
                        parent = os.path.dirname(path)
                        if parent == path:
                            break
                        path = parent

                if lib_root not in library_nodes:
                    result_count[0] += 1
                    results_count_label.config(
                        text=f"Found {result_count[0]} result{'s' if result_count[0] != 1 else ''}"
                    )
                    normalized_lib_root = os.path.normpath(lib_root).lower()
                    matched_terms = folder_keyword_map.get(normalized_lib_root, set())
                    keyword_hint = f"  ⟶ [{', '.join(sorted(matched_terms))}]" if matched_terms else ""
                    # tag = "has_keywords" if matched_terms else ""
                    # matched_terms is a set or list of keywords for this item (can be empty)
                    tags = tuple(matched_terms) if matched_terms else ()
                    # Add modification date for folders
                    mod_date = format_modification_date(lib_root)
                    lib_node = results_tree.insert(
                        "", "end",
                        text=f"📁 {lib_name}{keyword_hint}",
                        values=(mod_date,),
                        tags=tags,
                        open=False
                    )
                    library_nodes[lib_root] = lib_node
                    #all_items = results_tree.get_children("")
                else:
                    lib_node = library_nodes[lib_root]

                rel_path = os.path.relpath(full_path, lib_root)
                insert_path_recursive(results_tree, lib_node, rel_path, full_path, or_terms, and_terms)

            try:
                while not result_queue.empty() and not stop_search_flag:
                    item = result_queue.get_nowait()

                    if item is None:
                        finished_threads[0] += 1
                        if finished_threads[0] == total_threads:
                            finish_search(results_count_label)
                            return
                        continue

                    if os.path.exists(item):
                        matches_found[0] = True
                        insert_path_live(item, keywords['or'], keywords['and'])

                if stop_search_flag:
                    finish_search(results_count_label)
                else:
                    root.after(50, lambda: poll_results(keywords))
            except queue.Empty:
                if stop_search_flag:
                    finish_search(results_count_label)
                else:
                    root.after(50, lambda: poll_results(keywords))


        def finish_search(results_count_label=None):
            global searching, stop_search_flag
            if not searching:
                return
            searching = False
            stop_search_flag = False
            search_button.config(text="Search", style="TButton")
            # If results count label haven't found samples (it says "Searching..." then initialize it
            if results_count_label.cget("text") == "Searching...":
                results_count_label.config(text="")

            if matches_found[0]:
                stop_search_flag = False
                return

            # If no matches, distinguish between true finish and cancellation
            if stop_search_flag:
                append_log(log_box, "Search cancelled — here's what we've found so far.\n")
            else:
                append_log(log_box, "No matching files found.\n")


            stop_search_flag = False

        search_thread = threading.Thread(target=run_threads, daemon=True)
        search_thread.start()

        folder_keyword_map.clear()
        poll_results({"or": or_terms, "and": and_terms})

    global search_button
    search_button = ttk.Button(frame, text="Search", width=15, command=on_search_button_click)
    search_button.pack(pady=(0, 5))

    def copy_selected_path():
        selected_item = results_tree.selection()
        if selected_item:
            full_path = item_id_to_path.get(selected_item[0], None)
            if full_path:
                root.clipboard_clear()
                root.clipboard_append(full_path)
                root.update()


    def open_parent_folder_from_menu():
        open_parent_folder_internal(menu=True)

    def open_parent_folder(event=None):
        open_parent_folder_internal()

    def open_parent_folder_internal(menu=False):
        item_id = results_tree.selection()
        if not item_id:
            return
        file_path = item_id_to_path.get(item_id[0], None)
        if not file_path:
            return

        if os.path.isfile(file_path):
            if sys.platform == "win32":
                reveal_in_explorer(file_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", "-R", file_path])
            else:
                subprocess.run(["xdg-open", os.path.dirname(file_path)])
        elif os.path.isdir(file_path) and menu:
            # Open the folder directly
            if sys.platform == "win32":
                os.startfile(file_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", file_path])
            else:
                subprocess.run(["xdg-open", file_path])
        else:
            pass # don't open folders on double click, only through menu

    def create_kontakt_track_and_load_patch():
        settings = load_settings()
        if not settings.get("shown_key_command_warning", False):
            messagebox.showinfo(
                "Cubase Key Command Setup",
                "To use this feature, please add a key command in Cubase for:\n\n"
                "Add Track → Instrument\n\n"
                "See the PatchIO manual for further instructions.\n"
                "You can ignore this message if you've already set it up."
            )
            settings["shown_key_command_warning"] = True
            save_settings(settings)
        selected_item = results_tree.selection()
        if selected_item:
            file_path = item_id_to_path.get(selected_item[0], None)
            if file_path:
                patch_name = get_selected_patch_basename()
                try:
                    from cubase_utils import create_kontakt_track_from_patch, load_patch_into_kontakt
                    key_command = load_cubase_key_command()
                    # Step 1: Create the track
                    success = create_kontakt_track_from_patch(patch_name, key_command)
                    if not success:
                        print("⛔ Aborting. Failed to create track.")
                        return  # Exit early if track wasn't created
                    # Step 2: Load patch into visible Kontakt instrument
                    load_patch_into_kontakt(file_path)
                except Exception as e:
                    print(f"⚠️ Track creation or drag error: {e}")

    def replace_kontakt_instrument():
        selected_item = results_tree.selection()
        if selected_item:
            file_path = item_id_to_path.get(selected_item[0], None)
            if file_path:
                try:
                    from cubase_utils import load_patch_into_kontakt
                    load_patch_into_kontakt(file_path, reset_before_load=True)
                except Exception as e:
                    print(f"⚠️ Replace instrument error: {e}")

    # --- Tree Menu ---
    context_menu = tk.Menu(root, tearoff=0)
    context_menu.add_command(label="Copy Full Path", command=lambda: copy_selected_path())
    context_menu.add_command(label="Open File Location", command=open_parent_folder_from_menu)
    context_menu.add_command(
        label="Create a new Kontakt instrument track in DAW",
        command=create_kontakt_track_and_load_patch,
        state="normal" if platform.system() == "Darwin" else "disabled"
    )
    context_menu.add_command(
        label="Replace Kontakt instrument in DAW",
        command=replace_kontakt_instrument,
        state="normal" if platform.system() == "Darwin" else "disabled"
    )

    def on_right_click(event):
        row_id = results_tree.identify_row(event.y)
        if not row_id:
            return

        results_tree.selection_set(row_id)

        # Get selected file path
        file_path = item_id_to_path.get(row_id, "")

        # Rebuild the menu dynamically
        context_menu = tk.Menu(root, tearoff=0)
        context_menu.add_command(label="Copy Full Path", command=copy_selected_path)
        context_menu.add_command(label="Open File Location", command=open_parent_folder_from_menu)

        valid_exts = [".nki", ".nksn", ".nkm"]
        if any(file_path.lower().endswith(ext) for ext in valid_exts):
            context_menu.add_command(label="Create a new Kontakt instrument track in DAW", command=create_kontakt_track_and_load_patch)
            context_menu.add_command(label="Replace Kontakt instrument track in DAW",
                                     command=replace_kontakt_instrument)
        context_menu.post(event.x_root, event.y_root)

    def get_selected_patch_basename():
        selected_item = results_tree.selection()
        if selected_item:
            filename = results_tree.item(selected_item[0], "text")

            # Remove any leading non-alphanumeric characters (emoji, icons, punctuation)
            cleaned = re.sub(r"^[^\w]+", "", filename).strip()  # strip icons & leading spaces

            return os.path.splitext(cleaned)[0]
        return ""



    # Results Treeview (single)
    results_frame = ttk.Frame(frame)
    results_frame.pack(fill=tk.BOTH, expand=True)

    def create_filter_entry():
        filter_entry = tk.Entry(results_frame, borderwidth=0, relief='flat')  # or your container
        #filter_entry.pack(fill='x', padx=10, pady=5)
        filter_entry.pack(side=tk.TOP, fill='x', padx=10, pady=5)
        width = ai_search_entry.winfo_width()
        filter_entry.config(width=width)
        #filter_entry.pack(fill="both", expand=True)
        default_fg = filter_entry.cget("fg")  # store whatever the current theme uses
        default_font = filter_entry.cget("font")

        placeholder_text = "Filter results"
        placeholder_active = [True]

        filter_entry.insert(0, placeholder_text)
        filter_entry.configure(fg="#888888")

        def clear_placeholder_if_active():
            if placeholder_active[0]:
                filter_entry.delete(0, tk.END)
                filter_entry.configure(fg=default_fg, font=default_font)
                placeholder_active[0] = False

        def on_focus_in(event):
            clear_placeholder_if_active()

        def on_keypress(event):
            clear_placeholder_if_active()

        def on_focus_out(event):
            current = filter_entry.get().strip()
            if not current:
                filter_entry.insert(0, placeholder_text)
                filter_entry.configure(fg="#888888")
                placeholder_active[0] = True

        filter_entry.bind("<FocusIn>", on_focus_in)
        filter_entry.bind("<KeyPress>", on_keypress)
        filter_entry.bind("<FocusOut>", on_focus_out)

        return filter_entry

    filter_entry = create_filter_entry()
    
    # Configure TreeView with Modified column for folders
    results_tree = ttk.Treeview(results_frame, columns=("last modified",), show="tree headings", height=20)
    
    # Sorting state
    sort_reverse = [False]  # Track sort direction (False = ascending, True = descending)
    
    def sort_folders_by_date():
        """Sort top-level folders by modification date"""
        # Get all top-level items (folders only)
        folder_items = results_tree.get_children("")
        if len(folder_items) <= 1:
            # Not enough folders to sort, just update header
            results_tree.heading("last modified", text="Last Modified ▲")
            return
        
        # Collect folder data for sorting
        folder_data = []
        for item in folder_items:
            # Get the date string from values
            values = results_tree.item(item, "values")
            date_str = values[0] if values else ""
            try:
                # Parse the date string for proper sorting
                if date_str:
                    dt = datetime.datetime.strptime(date_str, "%d %b %Y at %H:%M")
                    sort_key = dt.timestamp()
                else:
                    sort_key = 0  # Empty dates go to bottom
            except ValueError:
                sort_key = 0
            folder_data.append((sort_key, item))
        
        # Toggle sort direction
        sort_reverse[0] = not sort_reverse[0]
        
        # Sort the folders
        folder_data.sort(reverse=sort_reverse[0])
        
        # Rearrange folders in TreeView
        for index, (_, item) in enumerate(folder_data):
            results_tree.move(item, "", index)
        
        # Update column heading with sort indicator
        if sort_reverse[0]:
            results_tree.heading("last modified", text="Last Modified ▼")
        else:
            results_tree.heading("last modified", text="Last Modified ▲")
    
    # Configure columns with sorting
    results_tree.heading("#0", text="Name", anchor="w")
    results_tree.heading("last modified", text="Last Modified", anchor="w", command=sort_folders_by_date)
    
    # Set column widths
    results_tree.column("#0", width=400, minwidth=200)
    results_tree.column("last modified", width=150, minwidth=100, anchor="w")
    # results_tree.column("path", width=0, stretch=False)
    # results_tree.tag_configure(
    #     "has_keywords",
    #     foreground="#55aaff" if IS_DARK_MODE else "#1a4b7a",
    #     font=("TkDefaultFont", 14, "italic")
    # )
    results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    results_tree.bind("<Button-3>", on_right_click)  # This works on Windows & Linux
    results_tree.bind("<Button-2>", on_right_click)  # Add this for macOS
    results_tree.bind("<Double-1>", open_parent_folder) # Double click

    def simple_filter(event=None):
        filter_text = filter_entry.get().lower().strip()

        for iid in all_items:  # use your full list of all inserted items
            item_tags = results_tree.item(iid, "tags") or ()
            item_text = results_tree.item(iid, "text").lower()
            tags_text = " ".join(item_tags).lower()

            if filter_text == "" or filter_text in item_text or filter_text in tags_text:
                results_tree.reattach(iid, "", "end")  # show
            else:
                results_tree.detach(iid)  # hide

    filter_entry.bind("<KeyRelease>", simple_filter)


    results_count_label = ttk.Label(frame, text="")
    results_count_label.pack(pady=(2, 10))

    # AI Loading Spinner (initially hidden)
    ai_spinner = ttk.Label(root, text="⏳ Asking AI...", font=("TkDefaultFont", 10, "italic"), foreground="#888")
    ai_spinner.pack(pady=(4, 2))
    ai_spinner.pack_forget()  # Hide initially

    scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=results_tree.yview)
    results_tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Mapping from TreeView item ID to full path
    item_id_to_path = {}

    def insert_path_recursive(tree, parent_node, relative_path, full_path, or_terms=None, and_terms=None):
        global all_items
        parts = relative_path.split(os.sep)
        if len(parts) == 1:
            # It's a file
            mod_date = format_modification_date(full_path)
            item_id = tree.insert(parent_node, "end", text=f"\U0001F4C4 {parts[0]}", values=(mod_date,))
            item_id_to_path[item_id] = full_path
            all_items = tree.get_children("")
        else:
            folder = parts[0]
            rest = os.sep.join(parts[1:])
            children = tree.get_children(parent_node)
            folder_node = None
            for child in children:
                item_text = tree.item(child, "text")
                item_name = item_text[2:] if item_text.startswith(("\U0001F4C1 ", "\U0001F4C2 ")) else item_text
                if item_name == folder:
                    folder_node = child
                    break

            if folder_node is None:
                folder_path = os.path.join(os.path.dirname(full_path), folder)
                match_keywords = get_matched_keywords(folder_path, or_terms or [], and_terms or [])
                match_str = f" ({', '.join(match_keywords)})" if match_keywords else ""
                folder_display = f"\U0001F4C1 {folder}{match_str}"
                parent_values = tree.item(parent_node, "values")
                parent_path = item_id_to_path.get(parent_node, "") if parent_node else ""
                folder_path = os.path.normpath(os.path.join(parent_path, folder)).lower()
                matched_terms = folder_keyword_map.get(folder_path, set())
                keyword_hint = "  [" + ", ".join(sorted(matched_terms)) + "]" if matched_terms else ""
                mod_date = format_modification_date(os.path.join(parent_path, folder))
                folder_full_path = os.path.join(parent_path, folder)
                folder_node = tree.insert(
                    parent_node,
                    "end",
                    text=f"\U0001F4C1 {folder}{keyword_hint}",
                    values=(mod_date,),
                    open=False
                )
                item_id_to_path[folder_node] = folder_full_path

            insert_path_recursive(tree, folder_node, rest, full_path, or_terms, and_terms)

    log_box, log_box_frame = create_styled_text_box(frame, height=6)
    log_box_frame.pack(fill="both", expand=True)
    enable_undo_redo(log_box)

    if IS_DARK_MODE:
        style.configure("Treeview", foreground="white", background="#222222", fieldbackground="#222222")
    else:
        style.configure("Treeview", foreground="black", background="white", fieldbackground="white")

    root.update_idletasks()

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    min_width = root.winfo_reqwidth()
    min_height = root.winfo_reqheight()

    # Clamp height to fit inside screen (leave room for taskbar/menu bar)
    safe_min_height = min(min_height, screen_height - 100)
    safe_min_width = min(min_width, screen_width)

    # Apply clamped min size
    root.minsize(safe_min_width, safe_min_height)

    preload_gpt_files() # preload the GPT settings and message

    # if AI connection errors occur, just disable the feature
    if not AI_AVAILABLE:
        radio_buttons["ai"].config(state="disabled")  # disable AI button
        search_mode_var.set("simple")  # select Simple mode by default


if DND_AVAILABLE:
    root = TkinterDnD.Tk()
else:
    root = tk.Tk()

root.title("PatchIO – Patches and Instruments Finder")

root.after(1000, lambda: check_for_updates(silent=True))

def on_enter_press(event):
    search_button.invoke()  # Trigger the search
    return "break"  # Prevent newline

def on_shift_enter_press(event):
    widget = event.widget  # The widget that received the event
    widget.insert(tk.INSERT, "\n")  # Insert newline at cursor position
    return "break"  # Prevent default behavior

# Detect platform
current_platform = platform.system().lower()

# Set toggle button width dynamically based on the platform
if current_platform == 'windows':
    button_width = 10  # Suitable width for Windows
elif current_platform == 'darwin':  # macOS
    button_width = 7  # Suitable width for Mac
else:
    button_width = 7  # Default for other platforms

# Define the supported file extensions and associated tkinter BooleanVars
all_extensions = [".wav", ".nki", ".preset", ".aif", ".nkm", ".nksn", ".nkx", ".ytil", ".db", ".zmulti",
                  ".otarc", ".oib", ".fxp", ".cst", ".exs", "prt_omn"]
EXT_GROUPS = {
    "Native Instruments - Kontakt": [".nki", ".nkm", ".nksn", ".nkx"],
    "Spectrasonics - Omnisphere": [".db", "prt_omn"],
    "Spitfire Audio": [".zmulti"],
    "Best Service - Engine": [".ytil"],
    "Orchestral Tools - Sine Player": [".otarc"],
    "East West - Opus Player": [".oib", ".preset"],
    "Logic Pro": [".exs", ".cst"],
    "VST plugins": [".fxp"],  # .db used in some UVI soundbanks
    "WAV Samples (Splice and other downloaded WAV files)": [".wav"],
    "AIF samples (mostly used by Logic Pro)": [".aif"]
}
# Note for dev: added support for Engine libraries, Omnisphere, Spitfire Labs, Sine Player

def sync_extensions_with_json(available_extensions):
    log_error(f"[DEBUG] Syncing extensions with available list.")

    try:
        settings = load_settings()
        log_error("[DEBUG] Settings loaded successfully.")
    except Exception as e:
        log_error(f"[ERROR] Failed to load settings:\n{traceback.format_exc()}")
        settings = {
            "last_folders": [],
            "extensions": {},
            "excluded_folders": [],
            "cubase_key_command": ""
        }

    settings.setdefault("extensions", {})

    # Add new extensions from available_extensions if missing
    for ext in available_extensions:
        if ext not in settings["extensions"]:
            settings["extensions"][ext] = True
            log_error(f"[DEBUG] Added new extension: {ext} (set to True)")

    # Remove extensions from settings that are not in available_extensions anymore
    to_remove = [ext for ext in settings["extensions"] if ext not in available_extensions]
    for ext in to_remove:
        del settings["extensions"][ext]
        log_error(f"[DEBUG] Removed extension no longer available: {ext}")

    save_settings(settings)



# sync any new extensions with existing JSON file
sync_extensions_with_json(all_extensions)

extension_vars = {ext: tk.BooleanVar(value=True) for ext in all_extensions}

default_width = 1100
default_height = 1000
min_width = 800
min_height = 700
bottom_reserved = 180  # Always leave this space clear

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

available_height = screen_height - bottom_reserved
available_width = screen_width - 100  # some horizontal margin

window_height = min(default_height, available_height)
window_width = min(default_width, available_width)

root.minsize(min_width, min_height)

x = (screen_width - window_width) // 2
y = max(0, (screen_height - bottom_reserved - window_height) // 2)

root.geometry(f"{window_width}x{window_height}+{x}+{y}")
root.maxsize(available_width, available_height)  # ✅ hard limit
root.resizable(True, False)


# # Limit height to fit screen if needed
# window_height = min(default_height, available_height)
# window_width = default_width  # You can also limit this if needed
#
# # Apply minimum size
# root.minsize(min_width, min_height)
#
# # Center the window
# x = (screen_width // 2) - (window_width // 2)
# y = (screen_height // 2) - (window_height // 2)
#
# # Set size and position
# root.geometry(f"{window_width}x{window_height}+{x}+{y}")



try:
    if os.path.exists(icon_path):
        img = Image.open(icon_path)
        icon = ImageTk.PhotoImage(img)
        root.iconphoto(False, icon)
except Exception as e:
    log_error(f"[ERROR] Failed to set window icon:\n{traceback.format_exc()}")

build_ui(root)

def on_closing():
    # no need to save extensions / folders since they're saved real-time
    root.destroy()  # Close the application


root.protocol("WM_DELETE_WINDOW", on_closing)

root.mainloop()
