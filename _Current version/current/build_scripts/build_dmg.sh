#!/bin/bash

# Change to the project root directory (parent of build_scripts)
cd "$(dirname "$0")/.."

set -e  # Exit on any error

# ========== USAGE ==========
if [ -z "$1" ]; then
    echo "❌ Usage: ./build_dmg.sh <version> [architecture]"
    echo "💡 Examples:"
    echo "   ./build_dmg.sh 1.2.0          # Build DMG for all found architectures"
    echo "   ./build_dmg.sh 1.2.0 all      # Build DMG for all found architectures"
    echo "   ./build_dmg.sh 1.2.0 arm64    # Build DMG for arm64 only"
    echo "   ./build_dmg.sh 1.2.0 intel    # Build DMG for intel only"
    exit 1
fi

VERSION="$1"
ARCHITECTURE="${2:-all}"  # Default to "all" if no second parameter

echo "💽 Building DMG for version: $VERSION"
echo "🏗️  Architecture mode: $ARCHITECTURE"

# ========== CONFIGURATION ==========
APP_NAME="PatchIO"
DIST_DIR="builds/dist"
RELEASES_DIR="builds/releases"
DMG_CANVAS_PROJECT="build_scripts/build_config/PatchIO DMG Project.dmgcanvas"
SIGNING_IDENTITY="Developer ID Application: Shaked Shachar (ZH2BJ5J2HZ)"

# Determine which architectures to check based on parameter
if [ "$ARCHITECTURE" = "all" ]; then
    ARCHS_TO_CHECK=("arm64" "intel")
elif [ "$ARCHITECTURE" = "arm64" ]; then
    ARCHS_TO_CHECK=("arm64")
elif [ "$ARCHITECTURE" = "intel" ]; then
    ARCHS_TO_CHECK=("intel")
else
    echo "❌ Invalid architecture: $ARCHITECTURE"
    echo "💡 Valid options: all, arm64, intel"
    exit 1
fi

# ========== VALIDATION ==========
echo ""
echo "🔍 Validating files exist..."

# Check if DMG Canvas command-line tool is available
if ! command -v dmgcanvas &> /dev/null; then
    echo "❌ DMG Canvas command-line tool not found"
    echo "💡 Please install DMG Canvas command-line tool"
    echo "💡 You can find it in the DMG Canvas app: Help > Install Command Line Tool"
    exit 1
fi
echo "✅ DMG Canvas command-line tool found"

# Check if DMG Canvas project exists
if [ ! -d "$DMG_CANVAS_PROJECT" ]; then
    echo "❌ DMG Canvas project not found at $DMG_CANVAS_PROJECT"
    exit 1
fi
echo "✅ DMG Canvas project found"

# Check if at least one app bundle exists
APP_BUNDLE="$DIST_DIR/$APP_NAME.app"
if [ ! -d "$APP_BUNDLE" ]; then
    echo "❌ App bundle not found at $APP_BUNDLE"
    echo "🔍 Please run: ./build_modern.sh $VERSION first"
    exit 1
fi
echo "✅ App bundle found"

# ========== DMG BUILDING ==========
echo ""
echo "💽 Building DMG files with DMG Canvas..."

# Create releases directory
mkdir -p "$RELEASES_DIR"

# Build DMGs for each architecture (only if app exists)
for arch in "${ARCHS_TO_CHECK[@]}"; do
    echo ""
    echo "💽 Building DMG for $arch architecture..."
    
    # Define output DMG name
    OUTPUT_DMG="$RELEASES_DIR/${APP_NAME}_v${VERSION}_Mac_${arch}.dmg"
    
    # Check if app bundle exists for this architecture
    # For now, we use the same app bundle for all architectures
    # In the future, you could have separate app bundles per architecture
    if [ -d "$APP_BUNDLE" ]; then
        echo "🎨 Using DMG Canvas project: $DMG_CANVAS_PROJECT"
        echo "📦 Output DMG: $OUTPUT_DMG"
        
        # Build DMG using DMG Canvas
        dmgcanvas "$DMG_CANVAS_PROJECT" "$OUTPUT_DMG"
        
        if [ $? -eq 0 ]; then
            echo "✅ DMG built successfully: $OUTPUT_DMG"
            echo "✅ DMG already code signed by DMG Canvas"
            
        else
            echo "❌ Failed to build DMG with DMG Canvas"
            echo "💡 Please check your DMG Canvas project configuration"
            exit 1
        fi
    else
        echo "⚠️ App bundle not found for $arch architecture, skipping DMG build"
    fi
done

echo ""
echo "🎉 DMG building complete!"
echo "📁 DMG files location:"
for arch in "${ARCHS_TO_CHECK[@]}"; do
    potential_dmg="$RELEASES_DIR/${APP_NAME}_v${VERSION}_Mac_${arch}.dmg"
    if [ -f "$potential_dmg" ]; then
        echo "   • $potential_dmg"
    fi
done 