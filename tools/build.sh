#!/bin/bash

# Define source and destination
SRC_DIR="src"
DIST_FILE="build/dist/zotero-obsidian-exporter.xpi"
PROJECT_ROOT=$(pwd)

# List of files to include in the XPI
FILES_TO_INCLUDE=(
  "manifest.json"
  "bootstrap.js"
  "chrome.manifest"
  "chrome/content/lib/nunjucks.min.js"
  "chrome/content/zotero-obsidian-exporter.js"
  "chrome/skin/default/icons/icon.png"
)

# Ensure the dist directory exists
mkdir -p "$(dirname "$DIST_FILE")"

# Create a temporary directory for packaging
TMP_DIR=$(mktemp -d)

# Copy only the specified files to the temporary directory
for file in "${FILES_TO_INCLUDE[@]}"; do
  if [ -f "$SRC_DIR/$file" ]; then
    mkdir -p "$TMP_DIR/$(dirname "$file")"
    cp "$SRC_DIR/$file" "$TMP_DIR/$file"
  else
    echo "Warning: Source file not found, skipping: $SRC_DIR/$file"
  fi
done

# Navigate to the temporary directory and create the zip file
echo "Creating XPI file..."
(cd "$TMP_DIR" && zip -r "$PROJECT_ROOT/$DIST_FILE" . -x "*.DS_Store")

# Clean up the temporary directory
rm -rf "$TMP_DIR"

echo "Successfully built $DIST_FILE"
