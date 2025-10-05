#!/bin/bash
set -e  # exit if any command fails

# ========== USER CONFIG ==========
ZIP_FILE="/Users/shaked/Desktop/Patchio App/_Current version/1.1.5/PatchIO_v1.1.5_Mac_arm64.zip"  # already contains signed App
APP_BUNDLE="/Users/shaked/Desktop/Patchio App/_Current version/1.1.5/dist/PatchIO.app"
DMG_PATH="/Users/shaked/Desktop/Patchio App/_Current version/1.1.5/PatchIO_v1.1.5_Mac_arm64.dmg"
SIGNED_DMG="/Users/shaked/Desktop/Patchio App/_Current version/1.1.5/PatchIO_v1.1.5_Mac_arm64_signed.dmg"

APPLE_ID="shaked5sha@gmail.com"
TEAM_ID="ZH2BJ5J2HZ"
APP_PASSWORD="ctju-xmgm-yyis-ggmc"
# ==================================

# ✅ Check if app is already notarized before submitting ZIP
echo "🔍 Checking if .app is already notarized..."
if spctl --assess --type execute --verbose=4 "$APP_BUNDLE" 2>&1 | grep -q "source=Notarized Developer ID"; then
  echo "✅ .app already notarized. Skipping ZIP submission."
else
  echo "☁️ 1️⃣ Submitting ZIP for notarization..."
  xcrun notarytool submit "$ZIP_FILE" \
    --apple-id "$APPLE_ID" \
    --team-id "$TEAM_ID" \
    --password "$APP_PASSWORD" \
    --wait
  echo "✔️ ZIP successfully notarized"

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

echo ""
if [ -f "$DMG_PATH" ]; then
  echo "💽 4️⃣ Notarizing and stapling ticket to .dmg..."

  # ✅ Check if DMG is already stapled
  if xcrun stapler validate "$DMG_PATH" &>/dev/null; then
    echo "✅ .dmg already notarized and stapled. Skipping."
  else
    xcrun notarytool submit "$DMG_PATH" \
      --apple-id "$APPLE_ID" \
      --team-id "$TEAM_ID" \
      --password "$APP_PASSWORD" \
      --wait

    cp "$DMG_PATH" "$SIGNED_DMG"
    xcrun stapler staple "$SIGNED_DMG"
    echo "✅ .dmg has stapled ticket"
  fi
else
  echo "ℹ️ No DMG detected; skipping DMG stapling"
fi

echo ""
echo "🎉 All done! PatchIO is notarized, stapled, and ready for distribution."
