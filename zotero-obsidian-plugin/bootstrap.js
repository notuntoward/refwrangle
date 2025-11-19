const { classes: Cc, interfaces: Ci, utils: Cu } = Components;
Cu.import("resource://gre/modules/Services.jsm");

var ZoteroObsidianExporter;
const LINK_COLUMN_ID = 'zotero-obsidian-link-column';

function log(msg) {
    Zotero.debug(`ZoteroObsidianExporter: ${msg}`);
}

async function install() {
    log("Installed");
}

async function startup({ id, version, rootURI }) {
    log("Starting");

    // Load main plugin logic
    if (!ZoteroObsidianExporter) {
        const scope = {};
        Services.scriptloader.loadSubScript(rootURI + 'zotero-obsidian-exporter.js', scope);
        ZoteroObsidianExporter = new scope.ZoteroObsidianExporter(rootURI);
    }

    // Add UI elements
    addMenuItems();
    addLinkColumn();

    // Start the background scanner
    await ZoteroObsidianExporter.init();
}

function addMenuItems() {
    const menu = Zotero.getMainWindow().document.getElementById('menu_FilePopup');
    let menuItem = Zotero.getMainWindow().document.createElement('menuitem');
    menuItem.setAttribute('id', 'zotero-obsidian-export-item');
    menuItem.setAttribute('label', 'Export to Obsidian Note');
    menuItem.addEventListener('command', () => ZoteroObsidianExporter.export());
    menu.appendChild(menuItem);

    const toolsMenu = Zotero.getMainWindow().document.getElementById('menu_ToolsPopup');
    let toolsMenuItem = Zotero.getMainWindow().document.createElement('menuitem');
    toolsMenuItem.setAttribute('id', 'zotero-obsidian-refresh-item');
    toolsMenuItem.setAttribute('label', 'Refresh Obsidian Note Links');
    toolsMenuItem.addEventListener('command', () => ZoteroObsidianExporter.refreshLinkedItems());
    toolsMenu.appendChild(toolsMenuItem);

    toolsMenuItem = Zotero.getMainWindow().document.createElement('menuitem');
    toolsMenuItem.setAttribute('id', 'zotero-obsidian-settings-item');
    toolsMenuItem.setAttribute('label', 'Zotero Obsidian Exporter Settings');
    toolsMenuItem.addEventListener('command', () => {
        Zotero.getMainWindow().openDialog(
            ZoteroObsidianExporter.rootURI + 'preferences.xhtml',
            'zotero-obsidian-exporter-prefs',
            'chrome,titlebar,centerscreen'
        );
    });
    toolsMenu.appendChild(toolsMenuItem);
}

function addLinkColumn() {
    const Zotero_Build = Zotero.version.split('.')[0];
    const columnSpec = Zotero_Build < 7
      ? `<treecol id="${LINK_COLUMN_ID}" label="⚫" flex="1" Zotero:sortable="true" Zotero:plugin="zotero-obsidian-exporter"/>`
      : `<treecol id="${LINK_COLUMN_ID}" label="⚫" flex="1" sortable="true" plugin="zotero-obsidian-exporter"/>`;
  
    Zotero.getMainWindow().document.getElementById('zotero-items-tree').appendChild(Zotero.getMainWindow().document.createXULElement(columnSpec));

    // Column handler
    const linkColumn = {
        dataStore: {},
        getCellText: function(row, col) {
            const item = Zotero.Items.get(Zotero.getActiveZoteroPane().getSortedItems()[row].id);
            return ZoteroObsidianExporter.linkedItemCache.has(item.key) ? "⚫" : "";
        },
        getRowClass: function() {},
        getImageSrc: function() {},
        isEditable: () => false,
        zoteroColumn: Zotero.Columns.get(LINK_COLUMN_ID)
    };
    
    Zotero.getActiveZoteroPane().setColumnHandler(LINK_COLUMN_ID, linkColumn);
}

function shutdown() {
    log("Shutting down");
    // Remove UI elements
    const ids = ['zotero-obsidian-export-item', 'zotero-obsidian-refresh-item', 'zotero-obsidian-settings-item', LINK_COLUMN_ID];
    for (const id of ids) {
        const elem = Zotero.getMainWindow().document.getElementById(id);
        if (elem) elem.remove();
    }

    ZoteroObsidianExporter = undefined;
}

function uninstall() {
    log("Uninstalled");
}
