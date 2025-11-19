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

        // ACTION: Create or Overwrite
        const noteTemplate = await this.getPref('note-template');
        const noteContent = this.nunjucks.renderString(noteTemplate, itemData);
        const newURI = `obsidian://new?vault=${encodeURIComponent(vaultName)}&file=${encodeURIComponent(fileName)}&content=${encodeURIComponent(noteContent)}&overwrite`;
        
        Zotero.Utilities.openURL(newURI);

        // --- VERIFICATION STEP ---
        const verificationSuccess = await this.verifyNoteCreation(fileName);

        if (verificationSuccess) {
            this.linkedItemCache.add(item.key);
            this.refreshZoteroView();
            log(`Successfully verified creation of ${fileName}`);
        } else {
            Zotero.alert(null, "Creation Not Verified", `The plugin attempted to create '${fileName}', but could not verify its existence. Please check your Obsidian vault.`);
            log(`Could not verify creation of ${fileName}`);
        }
    }

    async verifyNoteCreation(fileName) {
        const vaultPath = await this.getPref('vault-path');
        if (!vaultPath) return false;

        const filePath = OS.Path.join(vaultPath, fileName);
        const maxRetries = 5;
        const delay = 500; // ms to wait between checks

        for (let i = 0; i < maxRetries; i++) {
            await Zotero.Promise.delay(delay);
            try {
                if (await OS.File.exists(filePath)) {
                    const stat = await OS.File.stat(filePath);
                    if (stat.size > 0) {
                        return true; // File exists and has content.
                    }
                    // File exists but is empty, loop again to give Obsidian more time to write.
                }
            } catch (e) {
                // OS.File.exists can throw if path is invalid, but we proceed.
                 log(`Verification check ${i+1} failed: ${e.message}`);
            }
        }
        return false; // File was not found or was empty after all retries.
    }
    
    // ... (rest of the functions are unchanged) ...

    async refreshLinkedItems() {
        log("Scanning vault for linked notes...");
        const vaultPath = await this.getPref('vault-path');
        if (!vaultPath) { return; }

        this.linkedItemCache.clear();
        let iterator;
        try {
            iterator = new OS.File.DirectoryIterator(vaultPath);
            await iterator.forEach(async (entry) => {
                if (entry.isDir || !entry.name.endsWith('.md')) return;
                const match = entry.name.match(/^([a-zA-Z0-9_]+)/);
                if (!match) return;
                const itemKey = await this.findItemKeyByCitekey(match[1]);
                if (itemKey) this.linkedItemCache.add(itemKey);
            });
        } catch(e) {
            log(`Error scanning vault: ${e}`);
        } finally {
            if (iterator) iterator.close();
        }
        log(`Scan complete. Found ${this.linkedItemCache.size} linked notes.`);
        this.refreshZoteroView();
    }

    async findItemKeyByCitekey(citekey) {
        const sds = new Zotero.Search();
        sds.libraryID = Zotero.Libraries.userLibraryID;
        sds.addCondition('extra', 'contains', `Citation Key: ${citekey}`);
        const ids = await sds.search();
        return ids.length ? Zotero.Items.get(ids[0]).key : null;
    }

    refreshZoteroView() {
        Zotero.getActiveZoteroPane().view.refresh();
    }

    async getPref(pref) {
        const isSynced = pref !== 'vault-path';
        return Zotero.Prefs.get(`extensions.zotero-obsidian-exporter.${pref}`, isSynced);
    }

    async isObsidianAvailable() {
        try {
            const protocolService = Cc["@mozilla.org/uriloader/external-protocol-service;1"].getService(Ci.nsIExternalProtocolService);
            return protocolService.externalProtocolHandlerExists('obsidian');
        } catch (e) { return false; }
    }

    promptUserForAction(fileName) {
        const ps = Cc["@mozilla.org/embedcomp/prompt-service;1"].getService(Ci.nsIPromptService);
        return ps.select(null, `Note Exists: ${fileName}`, "What would you like to do?", 3, ["Overwrite", "Open", "Cancel"], {});
    }

    async getItemData(item) {
        const itemData = item.toJSON();
        let data = { ...itemData, creators: item.getCreators().map(c => `${c.firstName|| ''} ${c.lastName || ''}`.trim()).join(", "), tags: item.getTags().map(t => t.tag), zotero_link: `zotero://select/library/items/${item.key}` };
        const extra = item.getField('extra') || '';
        const citekeyMatch = extra.match(/Citation Key:\s*(.+)/);
        data.citekey = citekeyMatch ? citekeyMatch[1] : null;
        data.notes = (await Promise.all(item.getNotes().map(id => Zotero.Items.get(id).getNote()))).map(note => this.htmlToMarkdown(note)).join('\n\n');
        return data;
    }
    
    htmlToMarkdown(html) {
        return html.replace(/<[^>]+>/g, '');
    }
};