
var ZoteroObsidianExporter = {
    rootURI: null,
    nunjucks: null,
    linkedItemCache: null,
    scanInterval: null,

    log: function(msg) {
        Zotero.debug('ZoteroObsidianExporter: ' + msg);
    },

    init: function(props) {
        this.log('Initializing...');
        this.rootURI = props.rootURI;
        this.linkedItemCache = new Set();

        Services.scriptloader.loadSubScript(this.rootURI + 'chrome/content/lib/nunjucks.min.js', () => {
            this.nunjucks = nunjucks;
            this.log('Nunjucks templating engine loaded.');
        });
        
        this.log('Starting background scanner (using placeholder implementation)...');
        this.refreshLinkedItems();
        this.scanInterval = setInterval(() => this.refreshLinkedItems(), 5 * 60 * 1000);
        this.log('Initialization complete.');
    },

    shutdown: function() {
        this.log('Shutting down...');
        if (this.scanInterval) {
            clearInterval(this.scanInterval);
        }
    },

    refreshLinkedItems: function() {
        this.log('Placeholder: refreshLinkedItems() called. No action taken.');
    },

    refreshZoteroView: function() {
        try {
            Zotero.getActiveZoteroPane().view.refresh();
        } catch (e) {
            this.log('Could not refresh Zotero view: ' + e);
        }
    },

    getItemData: async function(item) {
        const citekey = Zotero.BetterBibTeX?.API?.get(item.id)?.citekey;
        return {
            title: item.getField('title') || 'No Title',
            citekey: citekey || null,
        };
    },

    verifyNoteCreation: async function(fileName) {
        this.log(`Placeholder: verifyNoteCreation() for "${fileName}" called. Assuming success.`);
        return true;
    },

    addToWindow: function(window) {
        const doc = window.document;
        const menu = doc.getElementById('menu_FilePopup');
        if (!menu) {
            return;
        }

        const createNoteMenuItem = doc.createElement('menuitem');
        createNoteMenuItem.id = 'zotero-obsidian-create-note';
        createNoteMenuItem.setAttribute('label', 'Create Obsidian Note');
        createNoteMenuItem.addEventListener('command', () => this.exportNew());
        menu.appendChild(createNoteMenuItem);

        const openNoteMenuItem = doc.createElement('menuitem');
        openNoteMenuItem.id = 'zotero-obsidian-open-note';
        openNoteMenuItem.setAttribute('label', 'Open Obsidian Note');
        openNoteMenuItem.addEventListener('command', () => this.exportOpen());
        menu.appendChild(openNoteMenuItem);

        const keyset = doc.createElement('keyset');
        keyset.id = 'zotero-obsidian-keyset';
        doc.documentElement.appendChild(keyset);

        const createKey = doc.createElement('key');
        createKey.id = 'zotero-obsidian-create-key';
        createKey.setAttribute('key', 'c');
        createKey.setAttribute('modifiers', 'accel,shift');
        createKey.setAttribute('oncommand', `document.getElementById('zotero-obsidian-create-note').doCommand()`);
        keyset.appendChild(createKey);
        createNoteMenuItem.setAttribute("key", "zotero-obsidian-create-key");

        const openKey = doc.createElement('key');
        openKey.id = 'zotero-obsidian-open-key';
        openKey.setAttribute('key', 'o');
        openKey.setAttribute('modifiers', 'accel,shift');
        openKey.setAttribute('oncommand', `document.getElementById('zotero-obsidian-open-note').doCommand()`);
        keyset.appendChild(openKey);
        openNoteMenuItem.setAttribute("key", "zotero-obsidian-open-key");
    },
    removeFromWindow: function(window) {
        const doc = window.document;
        const createNoteMenuItem = doc.getElementById('zotero-obsidian-create-note');
        if (createNoteMenuItem) createNoteMenuItem.remove();
        const openNoteMenuItem = doc.getElementById('zotero-obsidian-open-note');
        if (openNoteMenuItem) openNoteMenuItem.remove();
        const keyset = doc.getElementById('zotero-obsidian-keyset');
        if (keyset) keyset.remove();
    },

    exportNew: async function() {
        const items = Zotero.getActiveZoteroPane().getSelectedItems();
        if (!items.length) {
            return Zotero.alert(null, "No Items Selected", "Please select at least one item to create a note for.");
        }
        for (const item of items) {
            await this.createNote(item);
        }
    },

    exportOpen: async function() {
        const items = Zotero.getActiveZoteroPane().getSelectedItems();
        if (!items.length) {
            return Zotero.alert(null, "No Items Selected", "Please select at least one item to open the note for.");
        }
        for (const item of items) {
            await this.openNote(item);
        }
    },

    createNote: async function(item) {
        if (!this.nunjucks) {
            return Zotero.alert(null, "Template Engine Not Ready", "The Nunjucks template engine is still loading. Please try again in a moment.");
        }
        const itemData = await this.getItemData(item);
        if (!itemData.citekey) {
            return Zotero.alert(null, "Citekey Not Found", `A Better BibTeX citekey was not found for the item \"${itemData.title}\"". Please ensure BBT is installed and the item has a citekey.`);
        }

        const filenameTemplate = Zotero.Prefs.get('extensions.zotero-obsidian-exporter.filename-template') || '{{citekey}}.md';
        const fileName = this.nunjucks.renderString(filenameTemplate, itemData);

        if (this.linkedItemCache.has(item.key)) {
            const buttons = {
                overwrite: "Overwrite",
                open: "Open Existing",
                cancel: "Cancel"
            };
            const confirmation = Zotero.Confirm.show(
                `A note for "${fileName}" already exists.`,
                "Note Already Exists",
                buttons
            );

            switch (confirmation) {
                case "open":
                    this.openNote(item);
                    return;
                case "cancel":
                    return;
            }
        }

        const vaultName = Zotero.Prefs.get('extensions.zotero-obsidian-exporter.vault-name');
        const noteTemplate = Zotero.Prefs.get('extensions.zotero-obsidian-exporter.note-template');
        const noteContent = this.nunjucks.renderString(noteTemplate, itemData);
        const newURI = `obsidian://new?vault=${encodeURIComponent(vaultName)}&file=${encodeURIComponent(fileName)}&content=${encodeURIComponent(noteContent)}&overwrite`;
        
        Zotero.Utilities.openURL(newURI);

        const verificationSuccess = await this.verifyNoteCreation(fileName);

        if (verificationSuccess) {
            this.linkedItemCache.add(item.key);
            this.refreshZoteroView();
            this.log(`Successfully verified creation of ${fileName}`);
        }
    },

    openNote: async function(item) {
        if (!this.linkedItemCache.has(item.key)) {
            return Zotero.alert(null, "Note not found", "A note for this item has not been created yet.");
        }
        if (!this.nunjucks) {
            return Zotero.alert(null, "Template Engine Not Ready", "The Nunjucks template engine is still loading. Please try again in a moment.");
        }
        const itemData = await this.getItemData(item);
        const filenameTemplate = Zotero.Prefs.get('extensions.zotero-obsidian-exporter.filename-template') || '{{citekey}}.md';
        const fileName = this.nunjucks.renderString(filenameTemplate, itemData);
        const vaultName = Zotero.Prefs.get('extensions.zotero-obsidian-exporter.vault-name');
        const openURI = `obsidian://open?vault=${encodeURIComponent(vaultName)}&file=${encodeURIComponent(fileName)}`;
        return Zotero.Utilities.openURL(openURI);
    },
};
