#!/bin/bash

# This script is used to build the zotero-markdb-connect plugin.
# It creates a xpi file that can be installed in Zotero.

# The name of the plugin.
PLUGIN_NAME="zotero-markdb-connect"

# The version of the plugin.
PLUGIN_VERSION="0.1.0"

# The directory where the plugin is located.
PLUGIN_DIR="src"

# The name of the xpi file.
XPI_FILE="${PLUGIN_NAME}-${PLUGIN_VERSION}.xpi"

# Create the xpi file.
zip -r "${XPI_FILE}" "${PLUGIN_DIR}/bootstrap.js" "${PLUGIN_DIR}/manifest.json" "${PLUGIN_DIR}/lib/"

# Move the xpi file to the build directory.
mkdir -p "build"

mv "${XPI_FILE}" "build"

# Print a message to the console.
echo "Successfully created ${XPI_FILE} in the build directory."
