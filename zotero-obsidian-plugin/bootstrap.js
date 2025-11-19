var ZoteroObsidianExporter;

function log(msg) { Zotero.debug(`ZoteroObsidianExporter: ${msg}`); }

async function install() { 
    log("Installed");
    Services.prefs.setCharPref('extensions.zotero-obsidian-exporter.create-note-shortcut', 'control+shift+c');
    Services.prefs.setCharPref('extensions.zotero-obsidian-exporter.open-note-shortcut', 'control+shift+o');
}

async function startup({ id, version, rootURI }) {
    log("Starting");
    const majorVersion = Zotero.version.split('.')[0];
    if (majorVersion < 6) {
        const chromeHandle = Zotero.getMainWindow().QueryInterface(Components.interfaces.nsIInterfaceRequestor)
            .getInterface(Components.interfaces.nsIWebNavigation)
            .QueryInterface(Components.interfaces.nsIDocShellTreeItem)
            .rootTreeItem
            .QueryInterface(Components.interfaces.nsIInterfaceRequestor)
            .getInterface(Components.interfaces.nsIDOMWindow).chrome;
        if (chromeHandle.ZoteroObsidianExporter) {
            chromeHandle.ZoteroObsidianExporter.shutdown();
            delete chromeHandle.ZoteroObsidianExporter;
        }
    }

    Services.scriptloader.loadSubScript(rootURI + 'zotero-obsidian-exporter.js');
    ZoteroObsidianExporter = new ZoteroObsidianExporter(rootURI);
    ZoteroObsidianExporter.init();

    addMenuItems();
}

function shutdown() {
    log("Shutting down");
    ZoteroObsidianExporter.shutdown();
    const majorVersion = Zotero.version.split('.')[0];
    if (majorVersion < 6) {
        const chromeHandle = Zotero.getMainWindow().QueryInterface(Components.interfaces.nsIInterfaceRequestor)
            .getInterface(Components.interfaces.nsIWebNavigation)
            .QueryInterface(Components.interfaces.nsIDocShellTreeItem)
            .rootTreeItem
            .QueryInterface(Components.interfaces.nsIInterfaceRequestor)
            .getInterface(Components.interfaces.nsIDOMWindow).chrome;
        delete chromeHandle.ZoteroObsidianExporter;
    }
}

function uninstall() { log("Uninstalled"); }

function addMenuItems() {
    const menu = Zotero.getMainWindow().document.getElementById('menu_FilePopup');
    
    const createNoteMenuItem = Zotero.getMainWindow().document.createElement('menuitem');
    createNoteMenuItem.id = 'zotero-obsidian-create-note';
    createNoteMenuItem.setAttribute('label', 'Create Obsidian Note');
    createNoteMenuItem.addEventListener('command', onMenuItemCommand);
    menu.appendChild(createNoteMenuItem);

    const openNoteMenuItem = Zotero.getMainWindow().document.createElement('menuitem');
    openNoteMenuItem.id = 'zotero-obsidian-open-note';
    openNoteMenuItem.setAttribute('label', 'Open Obsidian Note');
    openNoteMenuItem.addEventListener('command', onMenuItemCommand);
    menu.appendChild(openNoteMenuItem);

    const keyset = Zotero.getMainWindow().document.createElement('keyset');
    keyset.id = 'zotero-obsidian-keyset';
    Zotero.getMainWindow().document.documentElement.appendChild(keyset);

    const createKey = Zotero.getMainWindow().document.createElement('key');
    createKey.id = 'zotero-obsidian-create-key';
    createKey.setAttribute('key', 'c');
    createKey.setAttribute('modifiers', 'accel,shift');
    createKey.setAttribute('oncommand', "document.getElementById('zotero-obsidian-create-note').doCommand()");
    keyset.appendChild(createKey);

    const openKey = Zotero.getMainWindow().document.createElement('key');
    openKey.id = 'zotero-obsidian-open-key';
    openKey.setAttribute('key', 'o');
    openKey.setAttribute('modifiers', 'accel,shift');
    openKey.setAttribute('oncommand', "document.getElementById('zotero-obsidian-open-note').doCommand()");
    keyset.appendChild(openKey);

    createNoteMenuItem.setAttribute("key", "zotero-obsidian-create-key");
    openNoteMenuItem.setAttribute("key", "zotero-obsidian-open-key");
}

function onMenuItemCommand(event) {
    if (event.target.id === 'zotero-obsidian-create-note') {
        ZoteroObsidianExporter.exportNew();
    } else if (event.target.id === 'zotero-obsidian-open-note') {
        ZoteroObsidianExporter.exportOpen();
    }
}
