import time
import platform
import subprocess
import pyautogui
import pyperclip
import tkinter as tk
from tkinter import ttk

CUBASE_VERSIONS = ["Cubase 14", "Cubase 13", "Cubase 12"]
APP_NAME = "PatchIO"

def focus_any_cubase():
    if platform.system() != "Darwin":
        print("⚠️ focus_any_cubase is only supported on macOS.")
        return False

    for app_name in CUBASE_VERSIONS:
        script = f'''
        tell application "System Events"
            set isRunning to (count of (every process whose name is "{app_name}")) > 0
            if isRunning then
                set frontmost of process "{app_name}" to true
                return "{app_name}"
            end if
        end tell
        '''
        try:
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            focused_app = result.stdout.strip()
            if focused_app in CUBASE_VERSIONS:
                print(f"✅ Focused {focused_app}")
                return True
        except Exception as e:
            print(f"⚠️ Failed checking {app_name}: {e}")

    # Only show this if user action likely triggered it
    show_floating_error("PatchIO",
                        f"Cubase is not open. Please open a Cubase project to use this feature.")
    return False

def show_floating_error(title="PatchIO", message=""):
    import textwrap

    # Estimate height dynamically based on visual line count (preserving \n)
    max_width = 500
    wrap_len = int(max_width * 0.12)  # rough char-to-pixel ratio

    # Count existing line breaks and estimated wrapped lines
    visual_lines = 0
    for line in message.splitlines():
        wrapped_lines = textwrap.wrap(line, width=wrap_len)
        visual_lines += max(1, len(wrapped_lines))  # at least one line per input line

    window_height = 150 + (visual_lines * 20)

    err_win = tk.Toplevel()
    err_win.title(title)
    err_win.geometry(f"540x{window_height}")
    err_win.attributes("-topmost", True)
    err_win.lift()
    err_win.grab_set()
    err_win.focus_force()
    err_win.resizable(False, False)

    # Ensure stays above Cubase: slight delay + raise again
    err_win.after(300, lambda: err_win.attributes("-topmost", True))
    err_win.after(350, err_win.lift)
    err_win.after(400, err_win.focus_force)

    # Center the window
    err_win.update_idletasks()
    x = (err_win.winfo_screenwidth() // 2) - 250
    y = (err_win.winfo_screenheight() // 2) - (window_height // 2)
    err_win.geometry(f"+{x}+{y}")

    frame = ttk.Frame(err_win, padding=20)
    frame.pack(expand=True, fill="both")

    # Message
    label_msg = ttk.Label(
        frame,
        text=message,
        wraplength=500,
        justify="left",
        anchor="w"
    )
    label_msg.pack(pady=(10, 10), anchor="w")

    # OK button
    ok_btn = ttk.Button(frame, text="OK", command=err_win.destroy)
    ok_btn.pack(pady=(10, 0))

    err_win.wait_window()


def sanitize_key_command(raw_input):
    """
    Cleans and validates a raw key command string like 'Shift + F1'.
    Returns a lowercase list of valid keys, or None if invalid.
    """
    key_combo = raw_input.strip().lower().replace(' ', '')  # 'Shift + F1' → 'shift+f1'
    parts = key_combo.split('+')

    valid_keys = set(pyautogui.KEYBOARD_KEYS)

    if all(part in valid_keys for part in parts):
        return parts
    else:
        print(f"⚠️ Invalid or unsupported key combo: {key_combo}")
        return None

def send_key_command(raw_key_combo):
    keys = sanitize_key_command(raw_key_combo)
    if not keys or len(keys) < 1:
        print(f"⚠️ Invalid or empty key combo: {raw_key_combo}")
        return False

    key = keys[-1]
    modifiers = keys[:-1]

    keycode = keycode_for(key)
    if keycode is None:
        print(f"⚠️ Unsupported key: {key}")
        return False

    modifier_str = ', '.join(f'{mod} down' for mod in modifiers)

    script = f'''
    tell application "System Events"
        key code {keycode} using {{{modifier_str}}}
    end tell
    '''

    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"🎹 Sent key command via AppleScript: {raw_key_combo}")
        return True
    else:
        print(f"❌ AppleScript error: {result.stderr.strip()}")
        return False

def keycode_for(key):
    key = key.lower()
    keycodes = {
        'a': 0, 'b': 11, 'c': 8, 'd': 2, 'e': 14, 'f': 3,
        'g': 5, 'h': 4, 'i': 34, 'j': 38, 'k': 40, 'l': 37,
        'm': 46, 'n': 45, 'o': 31, 'p': 35, 'q': 12, 'r': 15,
        's': 1, 't': 17, 'u': 32, 'v': 9, 'w': 13, 'x': 7,
        'y': 16, 'z': 6,
        'return': 36, 'enter': 76, 'tab': 48, 'space': 49,
        'escape': 53,
        'f1': 122, 'f2': 120, 'f3': 99, 'f4': 118,
        'f5': 96, 'f6': 97, 'f7': 98, 'f8': 100,
        'f9': 101, 'f10': 109, 'f11': 103, 'f12': 111
    }
    return keycodes.get(key, 0)  # default to 0 = 'a'

def wait_for_add_track_window(timeout=5):
    print("🔍 Starting wait_for_add_track_window (timeout=10)...")
    start = time.time()
    while time.time() - start < timeout:
        # Try supported Cubase versions
        for version in CUBASE_VERSIONS:
            script = f'''
            tell application "System Events"
                tell process "{version}"
                    repeat with w in windows
                        if name of w is "Add Track" then
                            set pos to position of w
                            return (item 1 of pos as string) & "," & (item 2 of pos as string)
                        end if
                    end repeat
                end tell
            end tell
            '''
            try:
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True,
                    timeout=1  # ← this enforces a quick exit
                )
            except subprocess.TimeoutExpired:
                print(f"⏱️ AppleScript timed out for {version}")
                continue
            if result.returncode == 0 and result.stdout.strip():
                print(f"✅ Found Add Track window in {version}")
                return result.stdout.strip()
        time.sleep(0.2)
    print("⛔ Aborting. Timed out waiting for Add Track window.")
    return None

def set_track_name_with_dropdown_and_osascript(track_name, dropdown_offset_x=309, dropdown_offset_y=156, name_offset_x=253, name_offset_y=279):
    found_pos = None
    found_pos = wait_for_add_track_window(timeout=2)

    if not found_pos:
        print("❌ Couldn't find Add Track window in any Cubase version.")
        show_floating_error(
            "PatchIO",
            "PatchIO couldn't locate Cubase's 'Add Track' window.\n\n"
            "Please make sure that:\n"
            "• A Cubase project is currently open\n"
            "• You've assigned a key command for 'Add Track → Instrument' in Cubase\n"
            "• The same key command is entered in PatchIO settings\n\n"
            "See the manual for setup instructions."
        )
        return False  # ❗️ Add this line to indicate failure


    try:
        x_str, y_str = found_pos.split(",")
        base_x, base_y = int(x_str), int(y_str)
        dropdown_x = base_x + dropdown_offset_x
        dropdown_y = base_y + dropdown_offset_y
        name_x = base_x + name_offset_x
        name_y = base_y + name_offset_y
    except Exception as e:
        print(f"⚠️ Failed to parse window position: {e}")
        return

    # --- Step 1: Insert Kontakt 8 as plugin ---
    pyautogui.click(dropdown_x, dropdown_y)
    time.sleep(0.2)
    pyperclip.copy("Kontakt 8")
    time.sleep(0.1)
    pyautogui.hotkey("command", "v")
    time.sleep(0.3)
    pyautogui.press("return")
    time.sleep(0.3)

    # --- Step 2: Set track name ---
    print(f"📋 Trying to type track name: {track_name} at {name_x}, {name_y}")
    pyautogui.click(name_x, name_y)
    time.sleep(0.2)
    pyperclip.copy(track_name)
    pyautogui.hotkey("command", "v")
    time.sleep(0.5)
    pyautogui.press("return")

    # After successfully setting name
    return True  # ❗️ Add this to indicate success


def open_accessibility_settings():
    if platform.system() != "Darwin":
        return  # Only applies to macOS

    try:
        # Get macOS major and minor version
        result = subprocess.run(["sw_vers", "-productVersion"], capture_output=True, text=True)
        version = result.stdout.strip()
        major, minor, *_ = map(int, version.split("."))

        # Ventura (13) and later → System Settings
        # Older versions → System Preferences (but same URL works)
        subprocess.run([
            "open",
            "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
        ])

        # Show user guidance via AppleScript dialog
        applescript = '''
        display dialog "To enable PatchIO’s 'Open Track in DAW' feature, you must grant Accessibility access.\\n\\nThis allows PatchIO to control Cubase and load Kontakt patches automatically.\\n\\n1. Click the lock icon to make changes.\\n2. Press the ➕ button.\\n3. In the Applications folder, select 'PatchIO' and click Open.\\n4. Ensure the checkbox next to 'PatchIO' is enabled.\\n\\nThis is only needed once." buttons {"OK"} default button "OK" with icon caution with title "Enable Accessibility Access"
        '''
        subprocess.run(["osascript", "-e", applescript])
    except Exception as e:
        print(f"⚠️ Failed to open accessibility settings: {e}")

def create_kontakt_track_from_patch(patch_name, key_command):
    if not focus_any_cubase():
        print("⛔ Cubase is not open. Aborting...")
        return False

    if not send_key_command(key_command):
        if platform.system() == "Darwin":
            show_floating_error("PatchIO", f"PatchIO couldn't trigger the Cubase key command '{key_command}'.\n\n"
                                           f"Please make sure:\n"
                                           f"• The key command is set correctly in Cubase\n"
                                           f"• PatchIO is enabled in System Settings → Privacy & Security → Accessibility")
            open_accessibility_settings()
        else:
            show_floating_error("PatchIO", f"Could not trigger Cubase key command '{key_command}'. "
                                       f"Make sure it's mapped correctly in Cubase and {APP_NAME} settings and try again.")
        return False

    time.sleep(1.0)  # Give time for dialog to open

    success = set_track_name_with_dropdown_and_osascript(patch_name)
    return success  # Return whether it succeeded

def get_kontakt_window_position():

    for version in CUBASE_VERSIONS:
        script = f'''
        tell application "System Events"
            tell process "{version}"
                repeat with w in windows
                    if name of w contains "Kontakt" then
                        set pos to position of w
                        return (item 1 of pos as string) & "," & (item 2 of pos as string)
                    end if
                end repeat
            end tell
        end tell
        '''
        try:
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                x_str, y_str = result.stdout.strip().split(",")
                print(f"🎹 Kontakt window found in {version}")
                return int(x_str), int(y_str)
        except Exception as e:
            print(f"⚠️ Error checking {version}: {e}")

    print("❌ Couldn't find Kontakt window.")
    return None

def wait_for_kontakt_window(timeout=5):
    print(f"🔍 Waiting for Kontakt window (timeout={timeout})...")
    start = time.time()
    while time.time() - start < timeout:
        pos = get_kontakt_window_position()
        if pos is not None:
            print(f"✅ Kontakt window found at {pos}")
            return pos
        time.sleep(0.2)
    print("⛔ Aborting. Timed out waiting for Kontakt window.")
    show_floating_error(
        "PatchIO",
        "PatchIO couldn't detect the Kontakt window in Cubase.\n\n"
        "Please make sure Kontakt is loaded into a track and visible."
    )
    return None


def load_patch_into_kontakt(file_path, reset_before_load=False):

    if not focus_any_cubase():
        print("⛔ Cubase is not open. Aborting...")
        return
    time.sleep(0.5)

    pos = wait_for_kontakt_window(timeout=5)
    if pos is None:
        return  # Already printed and showed error

    # Copy full file path to clipboard
    try:
        subprocess.run("pbcopy", text=True, input=file_path)
    except Exception as e:
        print(f"⚠️ Failed to copy path: {e}")
        return

    win_x, win_y = get_kontakt_window_position()
    if win_x is None:
        return


    # Use your confirmed offsets
    file_menu_x = win_x + 176
    file_menu_y = win_y + 66

    reset_multi_x = win_x + 211
    reset_multi_y = win_y + 252

    load_option_x = win_x + 181
    load_option_y = win_y + 116

    if reset_before_load:
        # Step 1: Open File menu and reset multi
        pyautogui.moveTo(file_menu_x, file_menu_y)
        time.sleep(0.2)
        pyautogui.click()
        time.sleep(0.4)

        pyautogui.moveTo(reset_multi_x, reset_multi_y)
        time.sleep(0.2)
        pyautogui.click()
        time.sleep(0.8)
        pyautogui.press("return")  # Confirm reset

    # Step 3: Open File menu again
    pyautogui.moveTo(file_menu_x, file_menu_y)
    time.sleep(0.1)
    pyautogui.click()
    time.sleep(0.1)

    # Step 4: Click "Load..." menu item
    pyautogui.moveTo(load_option_x, load_option_y)
    time.sleep(0.2)
    pyautogui.click()
    time.sleep(1.2)  # Let file dialog open

    # Open "Go to Folder" dialog
    pyautogui.hotkey('command', 'shift', 'g')
    time.sleep(0.3)

    # Step 5: Paste file path and press return twice (first to select, second to load)
    pyautogui.hotkey('command', 'v')
    time.sleep(0.4)
    pyautogui.press("return")  # Select the file
    time.sleep(0.4)
    pyautogui.press("return")  # Confirm to load

def get_kontakt_window_position():
    def get_cubase_process_name(possible_versions=["Cubase 14", "Cubase 13", "Cubase 12"]):
        for version in possible_versions:
            script = f'''
            tell application "System Events"
                if exists process "{version}" then
                    return "{version}"
                end if
            end tell
            '''
            try:
                result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
                name = result.stdout.strip()
                if name:
                    return name
            except Exception as e:
                print(f"⚠️ Error checking for {version}: {e}")
        print("❌ No supported Cubase version running.")
        return None

    cubase_process = get_cubase_process_name()
    if not cubase_process:
        return None

    script = f'''
    tell application "System Events"
        tell process "{cubase_process}"
            repeat with w in windows
                if name of w contains "Kontakt" then
                    set pos to position of w
                    return (item 1 of pos as string) & "," & (item 2 of pos as string)
                end if
            end repeat
        end tell
    end tell
    '''
    try:
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            x_str, y_str = result.stdout.strip().split(",")
            x, y = int(x_str), int(y_str)
            print(f"🎹 Kontakt window position: ({x}, {y})")
            return x, y
        else:
            print("❌ Couldn't find Kontakt window.")
            return None
    except Exception as e:
        print(f"⚠️ Error retrieving Kontakt window position: {e}")
        return None


def list_all_cubase_windows():
    script = '''
    tell application "System Events"
        tell process "{app_name}"
            set windowNames to {}
            repeat with w in windows
                set end of windowNames to name of w
            end repeat
            return windowNames as string
        end tell
    end tell
    '''
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    print("🪟 Open Cubase Windows:\n" + result.stdout.strip())

## coordinates testing
# list_all_cubase_windows()
# get_kontakt_window_position()