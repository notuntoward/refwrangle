Cu.import("resource://gre/modules/osfile.jsm");

function log(msg) { Zotero.debug(`ZoteroObsidianExporter: ${msg}`); }

this.ZoteroObsidianExporter = class {

    constructor(rootURI) {
        this.rootURI = rootURI;
        this.nunjucks = null;
        this.linkedItemCache = new Set();
        this.scanInterval = null;
        Services.scriptloader.loadSubScript(this.rootURI + 'lib/nunjucks.min.js');
        this.nunjucks = nunjucks;
    }

    async init() {
        log("Initializing background scanner...");
        await this.refreshLinkedItems();
        this.scanInterval = setInterval(() => this.refreshLinkedItems(), 5 * 60 * 1000);
    }

    shutdown() {
        if (this.scanInterval) clearInterval(this.scanInterval);
    }

    async export() {
        if (!(await this.isObsidianAvailable())) {
            return Zotero.alert(null, "Obsidian Not Detected", "The plugin could not detect that Obsidian is installed and configured to handle obsidian:// links. Please ensure Obsidian is installed and has been run at least once.");
        }
        const items = Zotero.getActiveZoteroPane().getSelectedItems();
        if (!items.length) {
            return Zotero.alert(null, "No Items Selected", "Please select at least one item to export.");
        }
        for (const item of items) {
            await this.processItem(item);
        }
    }

    async exportNew() {
        const items = Zotero.getActiveZoteroPane().getSelectedItems();
        if (!items.length) {
            return Zotero.alert(null, "No Items Selected", "Please select at least one item to create a note for.");
        }
        for (const item of items) {
            await this.createNote(item);
        }
    }

    async exportOpen() {
        const items = Zotero.getActiveZoteroPane().getSelectedItems();
        if (!items.length) {
            return Zotero.alert(null, "No Items Selected", "Please select at least one item to open the note for.");
        }
        for (const item of items) {
            await this.openNote(item);
        }
    }

    async createNote(item) {
        const itemData = await this.getItemData(item);
        if (!itemData.citekey) {
            return Zotero.alert(null, "Citekey Not Found", `A Better BibTeX citekey was not found for the item \"${itemData.title}\". Please ensure BBT is installed and the item has a citekey.`);
        }

        const filenameTemplate = await this.getPref('filename-template') || '{{citekey}}.md';
        const fileName = this.nunjucks.renderString(filenameTemplate, itemData);

        const vaultName = await this.getPref('vault-name');
        const noteTemplate = await this.getPref('note-template');
        const noteContent = this.nunjucks.renderString(noteTemplate, itemData);
        const newURI = `obsidian://new?vault=${encodeURIComponent(vaultName)}&file=${encodeURIComponent(fileName)}&content=${encodeURIComponent(noteContent)}&overwrite`;
        
        Zotero.Utilities.openURL(newURI);

        const verificationSuccess = await this.verifyNoteCreation(fileName);

        if (verificationSuccess) {
            this.linkedItemCache.add(item.key);
            this.refreshZoteroView();
            log(`Successfully verified creation of ${fileName}`);
        }
    }

    async openNote(item) {
        if (!this.linkedItemCache.has(item.key)) {
            return Zotero.alert(null, "Note not found", "A note for this item has not been created yet.");
        }
        const itemData = await this.getItemData(item);
        const filenameTemplate = await this.getPref('filename-template') || '{{citekey}}.md';
        const fileName = this.nunjucks.renderString(filenameTemplate, itemData);
        const vaultName = await this.getPref('vault-name');
        const openURI = `obsidian://open?vault=${encodeURIComponent(vaultName)}&file=${encodeURIComponent(fileName)}`;
        return Zotero.Utilities.openURL(openURI);
    }

    async processItem(item) {
        const itemData = await this.getItemData(item);
        if (!itemData.citekey) {
            return Zotero.alert(null, "Citekey Not Found", `A Better BibTeX citekey was not found for the item "${itemData.title}". Please ensure BBT is installed and the item has a citekey.`);
        }

        const filenameTemplate = await this.getPref('filename-template') || '{{citekey}}.md';
        const fileName = this.nunjucks.renderString(filenameTemplate, itemData);

        let action = 'create';
        if (this.linkedItemCache.has(item.key)) {
            const choice = this.promptUserForAction(fileName);
            action = ['create', 'open', 'cancel'][choice];
        }

        if (action === 'cancel') return;

        const vaultName = await this.getPref('vault-name');
        if (action === 'open') {
            const openURI = `obsidian://open?vault=${encodeURIComponent(vaultName)}&file=${encodeURIComponent(fileName)}`;
            return Zotero.Utilities.openURL(openURI);
        }

        const noteTemplate = await this.getPref('note-template');
        const noteContent = this.nunjucks.renderString(noteTemplate, itemData);
        const newURI = `obsidian://new?vault=${encodeURIComponent(vaultName)}&file=${encodeURIComponent(fileName)}&content=${encodeURIComponent(noteContent)}&overwrite`;
        
        Zotero.Utilities.openURL(newURI);

        const verificationSuccess = await this.verifyNoteCreation(fileName);

        if (verificationSuccess) {
            this.linkedItemCache.add(item.key);
            this.refreshZoteroView();
            log(`Successfully verified creation of ${fileName}`);
        } else {
//... existing code
