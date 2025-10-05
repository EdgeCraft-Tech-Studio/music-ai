#!/bin/bash
set -e

# This script makes your .app, .zip, or .dmg behave like it was just downloaded from the internet by a user for the first time

# ========== INPUT ==========
if [ -z "$1" ]; then
  echo "❌ Usage: $0 /path/to/file.{app|zip|dmg}"
  exit 1
fi

INPUT_PATH="$1"
FILENAME=$(basename "$INPUT_PATH")
EXT="${FILENAME##*.}"
NAME="${FILENAME%.*}"

# ========== CONFIG ==========
APP_NAME="PatchIO.app"                     # Adjust if needed
TEMP_DIR="/tmp/patchio_first_time"
MOUNT_DIR="/Volumes/PatchIOTest"
OUTPUT_DMG="${INPUT_PATH%.*}_first_time.dmg"
# ============================

# ========== CODE SIGN / NOTARIZATION CHECK ==========
echo "🔍 Checking code signature and notarization status..."

case "$EXT" in
  app)
    spctl_output=$(spctl --assess --type execute --verbose=4 "$INPUT_PATH" 2>&1 || true)
    stapler_output=$(xcrun stapler validate "$INPUT_PATH" 2>&1 || true)
    ;;
  zip)
    unzip -qq "$INPUT_PATH" -d "$TEMP_DIR-check"
    APP_EXTRACTED="$TEMP_DIR-check/$APP_NAME"
    spctl_output=$(spctl --assess --type execute --verbose=4 "$APP_EXTRACTED" 2>&1 || true)
    stapler_output=$(xcrun stapler validate "$APP_EXTRACTED" 2>&1 || true)
    rm -rf "$TEMP_DIR-check"
    ;;
  dmg)
    hdiutil attach "$INPUT_PATH" -mountpoint "$MOUNT_DIR" -nobrowse -quiet
    spctl_output=$(spctl --assess --type execute --verbose=4 "$MOUNT_DIR/$APP_NAME" 2>&1 || true)
    stapler_output=$(xcrun stapler validate "$INPUT_PATH" 2>&1 || true)
    hdiutil detach "$MOUNT_DIR" -quiet
    ;;
  *)
    echo "❌ Unsupported file type: .$EXT"
    exit 1
    ;;
esac

# ========== SUMMARY PRINT ==========
if echo "$spctl_output" | grep -q "accepted"; then
  if echo "$spctl_output" | grep -q "source=Notarized Developer ID"; then
    if echo "$stapler_output" | grep -q "The validate action worked!"; then
      echo "✅ App is codesigned, notarized, and stapled."
    else
      echo "⚠️ App is codesigned and notarized, but NOT stapled."
    fi
  else
    echo "⚠️ App is codesigned but NOT notarized."
  fi
else
  echo "❌ App is NOT codesigned properly."
fi

# ========== CLEAN TEMP ==========
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"

# ========== HANDLE FILE TYPES ==========
if [ "$EXT" = "dmg" ]; then
  echo "📦 Detaching any existing mount..."
  hdiutil detach "$MOUNT_DIR" &>/dev/null || true

  echo "📦 Mounting original DMG..."
  hdiutil attach "$INPUT_PATH" -mountpoint "$MOUNT_DIR" -nobrowse -quiet

  echo "🛠  Copying contents to temp directory..."
  cp -R "$MOUNT_DIR"/* "$TEMP_DIR"

  echo "📤 Unmounting..."
  hdiutil detach "$MOUNT_DIR" -quiet

elif [ "$EXT" = "zip" ]; then
  echo "🧩 Unzipping .zip..."
  unzip -q "$INPUT_PATH" -d "$TEMP_DIR"

elif [ "$EXT" = "app" ]; then
  echo "🛠  Copying .app to temp directory..."
  cp -R "$INPUT_PATH" "$TEMP_DIR/"
fi

# ========== QUARANTINE & PACKAGE ==========
echo "🚩 Applying quarantine flag to app..."
xattr -r -w com.apple.quarantine "0081;662e6c31;Safari;" "$TEMP_DIR/$APP_NAME"

echo "💽 Creating first-time DMG..."
hdiutil create -volname "PatchIO" -srcfolder "$TEMP_DIR" -format UDZO -quiet "$OUTPUT_DMG"

echo "✅ Created: $OUTPUT_DMG"
echo "🧪 You can now double-click it to test as a first-time user."
