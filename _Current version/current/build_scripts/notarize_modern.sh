#!/bin/bash

# Change to the directory where this script is located
cd "$(dirname "$0")"

set -e  # exit if any command fails

# ========== VERSION VALIDATION ==========
if [ -z "$1" ]; then
    echo "❌ Usage: ./notarize_modern.sh <version> [architecture]"
    echo "💡 Examples:"
    echo "   ./notarize_modern.sh 1.2.0          # Notarize all found architectures"
    echo "   ./notarize_modern.sh 1.2.0 all      # Notarize all found architectures"
    echo "   ./notarize_modern.sh 1.2.0 arm64    # Notarize arm64 only"
    echo "   ./notarize_modern.sh 1.2.0 intel    # Notarize intel only"
    exit 1
fi

VERSION="$1"
ARCHITECTURE="${2:-all}"  # Default to "all" if no second parameter

echo "🏷️  Notarizing version: $VERSION"
echo "🏗️  Architecture mode: $ARCHITECTURE"

# ========== CONFIGURATION ==========
APPLE_ID="shaked5sha@gmail.com"
TEAM_ID="ZH2BJ5J2HZ"
APP_PASSWORD="ctju-xmgm-yyis-ggmc"

# ========== VALIDATE FILES EXIST ==========
RELEASES_DIR="builds/releases"
APP_BUNDLE="builds/dist/PatchIO.app"

# Auto-detect architecture from existing files
ZIP_FILES=()
NOTARIZED_ZIPS=()
DMG_FILES=()
SIGNED_DMGS=()

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

# Check for ZIP files with specified architectures (including _notarized versions)
for arch in "${ARCHS_TO_CHECK[@]}"; do
    # Look for both regular and _notarized versions
    for zip_pattern in "builds/releases/PatchIO_v${VERSION}_Mac_${arch}.zip" "builds/releases/PatchIO_v${VERSION}_Mac_${arch}_notarized.zip"; do
        if [ -f "$zip_pattern" ]; then
            ZIP_FILES+=("$zip_pattern")
            echo "✅ Found ZIP: $zip_pattern"
            break  # Only add the first one found
        fi
    done
done

# Check for DMG files with specified architectures (including _notarized versions)
for arch in "${ARCHS_TO_CHECK[@]}"; do
    # Look for both regular and _notarized versions
    for dmg_pattern in "builds/releases/PatchIO_v${VERSION}_Mac_${arch}.dmg" "builds/releases/PatchIO_v${VERSION}_Mac_${arch}_notarized.dmg"; do
        if [ -f "$dmg_pattern" ]; then
            DMG_FILES+=("$dmg_pattern")
            # Always set the target as _notarized version
            SIGNED_DMGS+=("builds/releases/PatchIO_v${VERSION}_Mac_${arch}_notarized.dmg")
            echo "✅ Found DMG: $dmg_pattern"
            break  # Only add the first one found
        fi
    done
done

echo "📁 Looking for files:"
echo "   - App: $APP_BUNDLE"
if [ ${#ZIP_FILES[@]} -gt 0 ]; then
    echo "   - ZIP files (${#ZIP_FILES[@]} found):"
    for zip in "${ZIP_FILES[@]}"; do
        echo "     • $zip"
    done
else
    echo "   - ZIP: Not found"
fi
if [ ${#DMG_FILES[@]} -gt 0 ]; then
    echo "   - DMG files (${#DMG_FILES[@]} found):"
    for dmg in "${DMG_FILES[@]}"; do
        echo "     • $dmg"
    done
else
    echo "   - DMG: Not found"
fi

# ========== VALIDATION ==========
echo ""
echo "🔍 Validating files exist..."

if [ ! -d "$APP_BUNDLE" ]; then
    echo "❌ App bundle not found at $APP_BUNDLE"
    echo "🔍 Please run: ./build_modern.sh $VERSION"
    exit 1
fi
echo "✅ App bundle found"

if [ ${#ZIP_FILES[@]} -eq 0 ]; then
    echo "❌ No ZIP files found for version $VERSION"
    echo "🔍 Please run: ./build_modern.sh $VERSION"
    exit 1
fi
echo "✅ Found ${#ZIP_FILES[@]} ZIP file(s)"

if [ ${#DMG_FILES[@]} -gt 0 ]; then
    echo "✅ Found ${#DMG_FILES[@]} DMG file(s)"
else
    echo "ℹ️ No DMG files found (optional)"
fi

# ========== NOTARIZATION PROCESS ==========
echo ""
echo "🔍 Checking if .app is already notarized..."

# Check if app is already notarized
if spctl --assess --type execute --verbose=4 "$APP_BUNDLE" 2>&1 | grep -q "source=Notarized Developer ID"; then
    echo "✅ .app already notarized. Skipping ZIP submissions."
    APP_ALREADY_NOTARIZED=true
else
    echo "☁️ 1️⃣ Submitting ZIP files for notarization..."
    APP_ALREADY_NOTARIZED=false
fi

# Notarize all ZIP files
for zip_file in "${ZIP_FILES[@]}"; do
    echo ""
    echo "📦 Processing ZIP: $(basename "$zip_file")"
    
    if [ "$APP_ALREADY_NOTARIZED" = false ]; then
        echo "☁️ Submitting for notarization..."
        if xcrun notarytool submit "$zip_file" \
            --apple-id "$APPLE_ID" \
            --team-id "$TEAM_ID" \
            --password "$APP_PASSWORD" \
            --wait; then
            echo "✔️ ZIP successfully notarized"
            
            # Rename to add _notarized suffix
            zip_dir=$(dirname "$zip_file")
            zip_name=$(basename "$zip_file" .zip)
            notarized_zip="$zip_dir/${zip_name}_notarized.zip"
            mv "$zip_file" "$notarized_zip"
            NOTARIZED_ZIPS+=("$notarized_zip")
            echo "✅ Renamed to: $(basename "$notarized_zip")"
        else
            echo "❌ ZIP notarization failed"
            exit 1
        fi
    else
        echo "ℹ️ Skipping (app already notarized)"
    fi
done

# Staple tickets to app bundle (only once)
if [ "$APP_ALREADY_NOTARIZED" = false ]; then
    echo ""
    echo "📌 2️⃣ Stapling ticket to your .app..."
    xcrun stapler staple "$APP_BUNDLE"
    echo "✔️ .app has stapled ticket"
fi

echo ""
echo "🔍 3️⃣ Verifying Gatekeeper acceptance..."
if spctl --assess --type execute --verbose=4 "$APP_BUNDLE"; then
    echo "✅ App is notarized and accepted!"
else
    echo "❌ Gatekeeper still rejects the app"
fi

# ========== DMG NOTARIZATION ==========
echo ""
if [ ${#DMG_FILES[@]} -gt 0 ]; then
    echo "💽 4️⃣ Notarizing and stapling tickets to DMG files..."
    
    for i in "${!DMG_FILES[@]}"; do
        dmg_file="${DMG_FILES[$i]}"
        signed_dmg="${SIGNED_DMGS[$i]}"
        
        echo ""
        echo "📦 Processing DMG: $(basename "$dmg_file")"
        
        # Check if DMG is already stapled
        if xcrun stapler validate "$dmg_file" &>/dev/null; then
            echo "✅ .dmg already notarized and stapled. Skipping."
        else
            echo "☁️ Submitting DMG for notarization..."
            xcrun notarytool submit "$dmg_file" \
                --apple-id "$APPLE_ID" \
                --team-id "$TEAM_ID" \
                --password "$APP_PASSWORD" \
                --wait

            echo "📌 Stapling ticket to DMG..."
            cp "$dmg_file" "$signed_dmg"
            xcrun stapler staple "$signed_dmg"
            echo "✅ .dmg has stapled ticket"
            
            # Verify the notarized DMG is valid
            if xcrun stapler validate "$signed_dmg" &>/dev/null; then
                echo "✅ Notarized DMG verified successfully"
                
                # Remove original DMG file only if notarized version is valid
                # Only remove if original doesn't already have _notarized suffix
                dmg_name=$(basename "$dmg_file" .dmg)
                if [[ "$dmg_name" != *"_notarized" ]]; then
                    rm "$dmg_file"
                    echo "🗑️ Removed original DMG: $(basename "$dmg_file")"
                fi
            else
                echo "❌ Notarized DMG validation failed"
                exit 1
            fi
        fi
    done
else
    echo "ℹ️ No DMG files found; skipping DMG stapling"
    echo "💡 To create a DMG, you can use the make_first_time_dmg.sh script"
fi

echo ""
echo "🎉 All done! PatchIO is notarized, stapled, and ready for distribution."
echo "📁 Files location:"
echo "   - App: $APP_BUNDLE"
if [ ${#NOTARIZED_ZIPS[@]} -gt 0 ]; then
    echo "   - Notarized ZIP files:"
    for notarized_zip in "${NOTARIZED_ZIPS[@]}"; do
        if [ -f "$notarized_zip" ]; then
            echo "     • $notarized_zip"
        fi
    done
else
    echo "   - ZIP files:"
    for zip in "${ZIP_FILES[@]}"; do
        echo "     • $zip"
    done
fi
if [ ${#SIGNED_DMGS[@]} -gt 0 ]; then
    echo "   - Notarized DMG files:"
    for signed_dmg in "${SIGNED_DMGS[@]}"; do
        if [ -f "$signed_dmg" ]; then
            echo "     • $signed_dmg"
        fi
    done
fi 