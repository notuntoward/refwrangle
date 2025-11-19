/*
This script creates a new note in Obsidian for each selected Zotero item.
It checks if a note with the same name already exists and prompts the user for action.
*/

// --- CONFIGURATION ---
const OBSIDIAN_VAULT_NAME = "MyVault"; // <--- CHANGE THIS TO YOUR VAULT NAME
const OBSIDIAN_VAULT_PATH = ""; // <--- IMPORTANT: SET THIS to the FULL PATH of your Obsidian vault
                                     // Example for Windows: "C:\Users\YourUser\Documents\Obsidian\MyVault"
                                     // Example for macOS/Linux: "/Users/YourUser/Documents/Obsidian/MyVault"

// --- SCRIPT ---

// Import necessary Zotero and Mozilla components
Components.utils.import("resource://gre/modules/osfile.jsm");
const { classes: Cc, interfaces: Ci, utils: Cu } = Components;

// A simple lock to prevent multiple executions at the same time.
if (typeof Zotero.CreateObsidianNoteLock === 'undefined') {
    Zotero.CreateObsidianNoteLock = { inProgress: false };
}
if (Zotero.CreateObsidianNoteLock.inProgress) {
    Zotero.debug("Create Obsidian Note script is already running.");
    return;
}
Zotero.CreateObsidianNoteLock.inProgress = true;

(async () => {
    try {
        if (!OBSIDIAN_VAULT_PATH) {
            Zotero.alert("The OBSIDIAN_VAULT_PATH variable is not set in the script.", "Configuration Error");
            return;
        }

        // 'items' is provided by Zotero's script execution context
        if (!items || items.length === 0) {
            Zotero.alert("No items selected.", "No Zotero Items Selected");
            return;
        }

        for (const item of items) {
            const itemData = item.toJSON();

            const extraField = item.getField('extra') || '';
            const citekeyMatch = extraField.match(/Citation Key:\s*(.+)/);
            if (!citekeyMatch) {
                Zotero.debug(`Skipping item without a citation key: ${itemData.title}`);
                continue; // Skip items without a citekey
            }
            const citekey = citekeyMatch[1];
            const fileName = `${citekey}.md`;
            const filePath = OS.Path.join(OBSIDIAN_VAULT_PATH, fileName);

            let action = 'create'; // Default action

            const fileExists = await OS.File.exists(filePath);

            if (fileExists) {
                // File exists, prompt user
                const promptService = Cc["@mozilla.org/embedcomp/prompt-service;1"].getService(Ci.nsIPromptService);
                const flags = promptService.BUTTON_TITLE_IS_STRING * promptService.BUTTON_POS_0 +
                              promptService.BUTTON_TITLE_IS_STRING * promptService.BUTTON_POS_1 +
                              promptService.BUTTON_TITLE_IS_STRING * promptService.BUTTON_POS_2;
                
                const button0 = "Overwrite";
                const button1 = "Open";
                const button2 = "Cancel";

                const choice = promptService.select(null, `Note Exists: ${fileName}`,
                    "The note for this item already exists. What would you like to do?",
                    3, [button0, button1, button2], {});

                switch (choice) {
                    case 0: // Overwrite
                        action = 'create';
                        break;
                    case 1: // Open
                        action = 'open';
                        break;
                    case 2: // Cancel
                        action = 'cancel';
                        break;
                }
            }
            
            if (action === 'cancel') {
                Zotero.debug(`User cancelled action for ${fileName}`);
                continue;
            }

            if (action === 'open') {
                const obsidianURI = `obsidian://open?vault=${encodeURIComponent(OBSIDIAN_VAULT_NAME)}&file=${encodeURIComponent(fileName)}`;
                Zotero.Utilities.openURL(obsidianURI);
                continue;
            }

            // Action is 'create' (or overwrite)
            const creators = itemData.creators.map(c => `${c.firstName || ''} ${c.lastName || ''}`.trim()).join(", ");
            const tags = item.getTags().map(tag => tag.tag);

            let notesContent = '';
            const noteIDs = item.getNotes();
            for (const noteID of noteIDs) {
                const noteItem = Zotero.Items.get(noteID);
                if (noteItem) {
                    let noteHTML = noteItem.getNote();
                    // Simple HTML to Markdown conversion
                    let noteMD = noteHTML.replace(/<p>/gi, '').replace(/<\/p>/gi, '\n\n');
                    noteMD = noteMD.replace(/<b>/gi, '**').replace(/<\/b>/gi, '**');
                    noteMD = noteMD.replace(/<i>/gi, '*').replace(/<\/i>/gi, '*');
                    noteMD = noteMD.replace(/<ul>/gi, '').replace(/<\/ul>/gi, '');
                    noteMD = noteMD.replace(/<li>/gi, '* ').replace(/<\/li>/gi, '\n');
                    notesContent += noteMD.trim() + '\n\n';
                }
            }

            const fileContent = `---
citekey: ${citekey}
title: "${itemData.title || ''}"
authors: "${creators}"
date: ${itemData.date || ''}
tags: [${tags.join(', ')}]
zotero_link: zotero://select/library/items/${item.key}
---

# ${itemData.title || ''}

## Abstract
${itemData.abstractNote || ''}

## Notes
${notesContent}
`;

            const encodedContent = encodeURIComponent(fileContent);
            // Use `new` action which also handles overwriting if the file exists.
            const obsidianURI = `obsidian://new?vault=${encodeURIComponent(OBSIDIAN_VAULT_NAME)}&file=${encodeURIComponent(fileName)}&content=${encodedContent}&overwrite`;

            Zotero.Utilities.openURL(obsidianURI);
        }
    } catch (e) {
        Zotero.debug("Error in create_obsidian_note_from_zotero.js: " + e);
        Zotero.alert("An error occurred while creating/opening the Obsidian note(s). Check the debug log.", "Error");
    } finally {
        Zotero.CreateObsidianNoteLock.inProgress = false;
    }
})();
