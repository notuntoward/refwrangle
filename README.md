# Zotero Obsidian Exporter

A Zotero 7 plugin to create and open notes in Obsidian.

## Prerequisites

1.  **Zotero 7.0 or higher**: This plugin is specifically designed for Zotero 7 and will not work with older versions.
2.  **[Better BibTeX for Zotero (BBT)](https://retorque.re/zotero-better-bibtex/)**: This is required to automatically generate the `citekey` that the plugin uses for filenames and note metadata.
3.  **Obsidian**: The destination for your notes. Must be installed and able to open `obsidian://` links.

## How to Use

Once the plugin is installed, you can use it to create and open notes in Obsidian directly from the Zotero interface.

*   **Create Obsidian Note**: Select one or more items in Zotero and go to `File` -> `Create Obsidian Note`. You can also use the shortcut `Ctrl+Shift+C` (`Cmd+Shift+C` on macOS).
    *   If a note for a selected item already exists, you will be prompted to either **Overwrite** the existing note, **Open** it without making changes, or **Cancel** the action.
*   **Open Obsidian Note**: If a note has already been created for an item, select it and go to `File` -> `Open Obsidian Note`. You can also use the shortcut `Ctrl+Shift+O` (`Cmd+Shift+O` on macOS).

## Building and Installation

You can install this plugin by building the `.xpi` file from the source code.

### 1. Build the Plugin

To build the plugin, run the provided build script from the root directory of the project:

```bash
sh tools/build.sh
```

This command packages the plugin into an `.xpi` file located at `build/dist/zotero-obsidian-exporter.xpi`.

### 2. Install in Zotero

1.  Open Zotero.
2.  Go to `Tools` -> `Add-ons`.
3.  Click the gear icon in the top-right corner of the Add-ons Manager and select `Install Add-on From File...`.
4.  Navigate to the project directory and choose the `build/dist/zotero-obsidian-exporter.xpi` file you just created.
5.  Zotero will prompt you to install the add-on. Click `Install Now`.
6.  Restart Zotero to complete the installation.
