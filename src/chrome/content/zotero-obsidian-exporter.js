var ZoteroObsidianExporter = {
    log: function(msg) {
        Zotero.debug('ZoteroObsidianExporter: ' + msg);
    },

    init: function(props) {
        this.log('Plugin skeleton initialized successfully.');
        // All complex initialization logic has been removed to isolate the installation issue.
        // We will add back functionality once we confirm the plugin can be installed.
    },

    shutdown: function() {
        this.log('Plugin shut down.');
    },

    addToWindow: function(window) {
        this.log('Adding UI to window...');
        const doc = window.document;
        const menu = doc.getElementById('menu_FilePopup');
        if (!menu) {
            this.log('Could not find File menu. UI will not be added.');
            return;
        }

        const createNoteMenuItem = doc.createElement('menuitem');
        createNoteMenuItem.id = 'zotero-obsidian-create-note';
        createNoteMenuItem.setAttribute('label', 'Create Obsidian Note (placeholder)');
        menu.appendChild(createNoteMenuItem);
        this.log('UI added to window.');
    },

    removeFromWindow: function(window) {
        this.log('Removing UI from window...');
        const doc = window.document;
        const createNoteMenuItem = doc.getElementById('zotero-obsidian-create-note');
        if (createNoteMenuItem) {
            createNoteMenuItem.remove();
            this.log('UI removed from window.');
        }
    }
};