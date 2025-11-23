# Zotero Obsidian Exporter

This Zotero plugin exports items to Obsidian, creating individual notes from your Zotero library using a powerful and customizable templating system.

## Features

- **Live Status Indicator**: A column in Zotero displays a mark (⚫) next to items that already have a note in Obsidian. This status updates automatically.
- **One-Click Export**: Export selected Zotero items to Obsidian with a single click.
- **Customizable Templates**: Use Nunjucks (a Jinja2-like language) to define the exact content and structure of your notes.
- **Smart File Handling**: The plugin checks if a note already exists and prompts you to Overwrite, Open, or Cancel.
- **Machine-Specific Configuration**: Your Obsidian vault path is stored locally, allowing you to sync your Zotero setup across different operating systems without issue.
- **Built-in Template Validation**: A validator is included in the preferences to help you catch syntax errors in your templates instantly.

## Prerequisites

1.  **Zotero 6.0 or higher**
2.  **[Better BibTeX for Zotero (BBT)](https://retorque.re/zotero-better-bibtex/)**: This is required to automatically generate the `citekey` that the plugin uses for filenames and metadata.
3.  **Obsidian**: The destination for your notes. Must be installed and able to open `obsidian://` links.

---

## Installation

To install the plugin, you first need to package it as an `.xpi` file.

### 1. Create the `.xpi` file

You can do this from the command line. Navigate to the root directory of this project and run the following command:

```bash
cd zotero-obsidian-plugin
zip -r ../zotero-obsidian-exporter.xpi ./*
cd ..
```

This will create a file named `zotero-obsidian-exporter.xpi` in the project's root directory.

### 2. Install in Zotero

1.  Open Zotero.
2.  Go to `Tools` -> `Add-ons`.
3.  Click the gear icon in the top-right corner and select `Install Add-on From File...`.
4.  Choose the `zotero-obsidian-exporter.xpi` file you just created.
5.  Follow the prompts to install the plugin and then restart Zotero.

---

## Configuration

Once installed, you must configure the plugin before first use:

1.  In Zotero, go to `Tools` -> `Zotero Obsidian Exporter Settings`.
2.  A preferences window will open. Fill out the following fields:
    *   **Vault Name**: The exact name of your Obsidian vault.
    *   **Vault Full Path (Local)**: The full, absolute path to your Obsidian vault on your current machine. This setting is **not synced** across computers.
    *   **Filename Template**: The Nunjucks template for the note's filename. The default is `{{citekey}}.md`.
    *   **Note Content Template**: The main Nunjucks template for your note's content.
3.  Click the `Validate Template` button to check for syntax errors in your content template.
4.  Close the window to save the settings.

---

## How to Use

1.  In Zotero, select one or more items you wish to export.
2.  Go to `File` -> `Export to Obsidian Note`.
3.  To update the linked status column for all items, go to `Tools` -> `Refresh Obsidian Note Links`.

---

## Troubleshooting

### What happens if Obsidian isn't installed or available?

The plugin communicates with Obsidian using `obsidian://` URLs. If Obsidian is not installed or if your operating system has not registered it as the handler for this URL scheme, the export will fail.

**Solution:** Ensure you have installed Obsidian on your machine. If you have just installed it, try running it at least once to ensure it has registered the `obsidian://` URL handler with the operating system. The plugin will warn you on first export if it cannot detect Obsidian.

### What happens if Better BibTeX (BBT) is not installed?

If BBT is not installed or an item does not have a citekey, the plugin cannot link it to a note file.

**Solution:** Ensure you have the Better BibTeX plugin installed in Zotero and that your items have been assigned a citekey. The plugin will warn you if it cannot find a citekey for an item you are trying to export.
