#!/bin/bash

# Change to the project root directory (parent of build_scripts)
cd "$(dirname "$0")/.."

set -e  # Exit on any error

if [ -z "$1" ]; then
    echo "❌ Usage: ./build_modern.sh <version>"
    exit 1
fi

VERSION="$1"
APP_NAME="PatchIO"
DIST_DIR="builds/dist"
BUILD_DIR="builds/build"
RELEASES_DIR="builds/releases"
APP_PATH="$DIST_DIR/$APP_NAME.app"
UPDATER_SCRIPT="updater/external_updater.py"
UPDATER_BINARY="$DIST_DIR/external_updater"
APP_MANUAL="assets/docs/PatchIO_Manual.pdf"
SIGNING_IDENTITY="Developer ID Application: Shaked Shachar (ZH2BJ5J2HZ)"
PLIST="build_scripts/build_config/custom_info.plist"
ENTITLEMENTS="build_scripts/build_config/entitlements.plist"

# Detect architecture
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    ARCH_SUFFIX="arm64"
elif [ "$ARCH" = "x86_64" ]; then
    ARCH_SUFFIX="intel"
else
    echo "❌ Unsupported architecture: $ARCH"
    exit 1
fi

ZIP_NAME="${APP_NAME}_v${VERSION}_Mac_${ARCH_SUFFIX}.zip"

echo "🏗️  Building for architecture: $ARCH_SUFFIX ($ARCH)"
echo "📦 Output will be: $ZIP_NAME"
echo ""
echo "🔧 Updating version across files..."

# 1. Update patchio_main.py (new entry point)
echo "  → patchio_main.py"
# Note: We'll need to add a version constant to patchio_main.py if needed
# sed -i '' "s/^CURRENT_VERSION = \".*\"/CURRENT_VERSION = \"$VERSION\"/" patchio_main.py

# 2. Update about.txt
echo "  → about.txt"
sed -i '' "s/^Version .*/Version $VERSION/" assets/docs/about.txt

# 3. Update custom_info.plist
echo "  → custom_info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $VERSION" "$PLIST" || echo "⚠️ Could not update CFBundleShortVersionString"
/usr/libexec/PlistBuddy -c "Set :CFBundleVersion $VERSION" "$PLIST" || echo "⚠️ Could not update CFBundleVersion"
/usr/libexec/PlistBuddy -c "Set :CFBundleGetInfoString PatchIO – Patches and Instruments Finder\\nVersion $VERSION\\n© 2025 Shaked Shachar" "$PLIST" || echo "⚠️ Could not update CFBundleGetInfoString"

echo "🔨 Building PatchIO Modern App..."
python3 -m PyInstaller --distpath builds/dist --workpath builds/build --noconfirm Patchio_modern.spec

echo "🔨 Building external_updater binary..."
pyinstaller "$UPDATER_SCRIPT" \
  --onefile \
  --name external_updater \
  --distpath builds/dist \
  --workpath builds/build \
  --codesign-identity "$SIGNING_IDENTITY" \
  --osx-entitlements-file "$ENTITLEMENTS" \
  --specpath updater \
  --noconfirm

# Ensure updater binary exists
if [ ! -f "$UPDATER_BINARY" ]; then
  echo "❌ external_updater build failed"
  exit 1
fi

# Sign updater binary again explicitly
echo "🔏 Signing external_updater binary..."
codesign --deep --force --options runtime --sign "$SIGNING_IDENTITY" "$UPDATER_BINARY"

# Move updater into app bundle
echo "📦 Embedding updater into app bundle..."
cp "$UPDATER_BINARY" "$APP_PATH/Contents/MacOS/external_updater"
chmod +x "$APP_PATH/Contents/MacOS/external_updater"

echo "📄 Copying documentation into app bundle..."
mkdir -p "$DIST_DIR/$APP_NAME.app/Contents/Resources"
cp "$APP_MANUAL" "$DIST_DIR/$APP_NAME.app/Contents/Resources/"

# Clean extended attributes from README / Manual to prevent code signing issues
echo "🧹 Cleaning extended attributes from README..."
xattr -c "$DIST_DIR/$APP_NAME.app/Contents/Resources/$APP_MANUAL"

# Sign app
echo "🔐 Code signing app bundle..."
codesign --deep --force --options runtime --sign "$SIGNING_IDENTITY" "$APP_PATH"

# Notarize updater (optional but recommended)
# echo "🌐 Submitting external_updater for notarization..."
# xcrun notarytool submit "$UPDATER_BINARY" --apple-id "your@apple.com" --team-id "ZH2BJ5J2HZ" --password "your-app-password" --wait
# xcrun stapler staple "$UPDATER_BINARY"

# Create releases directory
mkdir -p "$RELEASES_DIR"

# Zip final app
echo "📁 Creating zip: $ZIP_NAME"
ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$RELEASES_DIR/$ZIP_NAME"

# Build DMG using DMG Canvas
echo ""
echo "💽 Building DMG with DMG Canvas..."
./build_scripts/build_dmg.sh "$VERSION" "$ARCH_SUFFIX"

echo "✅ Build complete: $RELEASES_DIR/$ZIP_NAME" 