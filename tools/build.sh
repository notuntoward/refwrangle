#!/bin/bash

# Read configuration from .build file
BUILD_CONFIG="build/.build"

if [ ! -f "$BUILD_CONFIG" ]; then
    echo "Build configuration file not found!" C
    exit 1
fi

# Extract values using a simple parser
DIST=$(grep '"dist"' $BUILD_CONFIG | sed 's/.*: "\(.*\)",/\1/')
ROOT=$(grep '"root"' $BUILD_CONFIG | sed 's/.*: "\(.*\)",/\1/')
FILES=$(grep -E '"(bootstrap.js|chrome.manifest|manifest.json|chrome/.*)"' $BUILD_CONFIG | sed 's/.*"\(.*\)".*/\1/')

# Get the absolute path to the project root
PROJECT_ROOT=$(pwd)

# Create a temporary directory for packaging
TMP_DIR=$(mktemp -d)

# Copy files to the temporary directory
for file in $FILES; do
    # Check if the source file exists before copying
    if [ -f "$ROOT/$file" ]; then
        mkdir -p "$TMP_DIR/$(dirname "$file")"
        cp "$ROOT/$file" "$TMP_DIR/$file"
    else
        echo "Warning: Source file not found, skipping: $ROOT/$file"
    fi

done

# Create the XPI file
(cd "$TMP_DIR" && zip -r "$PROJECT_ROOT/$DIST" .)

# Clean up the temporary directory
rm -rf "$TMP_DIR"

echo "Successfully built $DIST"
