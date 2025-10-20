#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
import appdirs
from utils.logger import debug, info, warning, error, critical

# Setup logging to user config dir
config_dir = appdirs.user_config_dir("PatchIO", "PatchIO")
os.makedirs(config_dir, exist_ok=True)
UPDATER_LOG_FILE = os.path.join(config_dir, "patchIO_updater.log")

def log(msg):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    full_msg = f"{timestamp} {msg}"
    with open(UPDATER_LOG_FILE, "a") as f:
        f.write(full_msg + "\n")
    debug(full_msg)

def wait_for_app_to_close(app_path):
    while os.path.exists(app_path + "/Contents/MacOS/PatchIO"):
        try:
            subprocess.check_output(["pgrep", "-f", app_path])
            time.sleep(1)
        except subprocess.CalledProcessError:
            break  # process not found

def delete_app_with_admin(app_path):
    log(f"Attempting to delete {app_path} with admin privileges...")
    try:
        escaped_path = app_path.replace('"', '\\"')  # escape any quotes in path
        script = f'do shell script "rm -rf \\"{escaped_path}\\"" with administrator privileges'
        subprocess.run(["osascript", "-e", script], check=True)
        log("Deletion via AppleScript succeeded.")
    except subprocess.CalledProcessError as e:
        log(f"Admin delete failed: {e}")
        sys.exit(1)

def main():
    try:
        if len(sys.argv) != 3:
            log("Usage: external_updater <path_to_new_app> <path_to_old_app>")
            sys.exit(1)

        new_app_path = sys.argv[1]
        old_app_path = sys.argv[2]

        log(f"Waiting for {old_app_path} to close...")
        wait_for_app_to_close(old_app_path)

        log(f"Replacing old app at {old_app_path} with {new_app_path}...")
        if os.path.exists(old_app_path):
            try:
                shutil.rmtree(old_app_path)
            except Exception as e:
                log(f"Standard delete failed: {e}")
                delete_app_with_admin(old_app_path)

        shutil.move(new_app_path, old_app_path)
        log("New app moved into place successfully.")
        time.sleep(1.5)  # Give macOS a moment to settle

        # Remove macOS Gatekeeper quarantine flags
        subprocess.run(["xattr", "-dr", "com.apple.quarantine", old_app_path])
        binary_path = os.path.join(old_app_path, "Contents", "MacOS", "PatchIO")
        subprocess.run(["chmod", "+x", binary_path])

        log("Launching updated app...")
        # subprocess.run([
        #     "open", "-a", old_app_path,
        #     "--args", "--from-updater"
        # ])
        binary_path = os.path.join(old_app_path, "Contents", "MacOS", "PatchIO")
        subprocess.Popen([binary_path])

    except Exception as e:
        log(f"ERROR: {e}")
        raise

if __name__ == "__main__":
    main()
