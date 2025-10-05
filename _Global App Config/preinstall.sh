#!/bin/bash

APP_NAME="PatchIO.app"
INSTALL_PATH="/Applications/$APP_NAME"

echo "Running preinstall script..."

if [ -d "$INSTALL_PATH" ]; then
    echo "Removing existing app at $INSTALL_PATH"
    rm -rf "$INSTALL_PATH"
else
    echo "No existing app found at $INSTALL_PATH"
fi

exit 0