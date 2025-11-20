
var ZoteroObsidianExporter;
var windowObserver;

function log(msg) {
  Zotero.debug(`ZoteroObsidianExporter: ${msg}`);
}

function addWindow(window) {
    const doc = window.document;
    const menu = doc.getElementById('menu_FilePopup');
    if (!menu) {
        return;
    }

    const createNoteMenuItem = doc.createElement('menuitem');
    createNoteMenuItem.id = 'zotero-obsidian-create-note';
    createNoteMenuItem.setAttribute('label', 'Create Obsidian Note');
    createNoteMenuItem.addEventListener('command', () => ZoteroObsidianExporter.exportNew());
    menu.appendChild(createNoteMenuItem);

    const openNoteMenuItem = doc.createElement('menuitem');
    openNoteMenuItem.id = 'zotero-obsidian-open-note';
    openNoteMenuItem.setAttribute('label', 'Open Obsidian Note');
    openNoteMenuItem.addEventListener('command', () => ZoteroObsidianExporter.exportOpen());
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
}

function removeWindow(window) {
    const doc = window.document;
    const createNoteMenuItem = doc.getElementById('zotero-obsidian-create-note');
    if (createNoteMenuItem) createNoteMenuItem.remove();
    const openNoteMenuItem = doc.getElementById('zotero-obsidian-open-note');
    if (openNoteMenuItem) openNoteMenuItem.remove();
    const keyset = doc.getElementById('zotero-obsidian-keyset');
    if (keyset) keyset.remove();
}

async function install() {
  log('Installed');
  Services.prefs.setCharPref('extensions.zotero-obsidian-exporter.create-note-shortcut', 'control+shift+c');
  Services.prefs.setCharPref('extensions.zotero-obsidian-exporter.open-note-shortcut', 'control+shift+o');
}

async function startup({ id, version, rootURI }) {
  log('Starting');

  Services.scriptloader.loadSubScript(rootURI + 'zotero-obsidian-exporter.js');
  
  ZoteroObsidianExporter = new ZoteroObsidianExporter(rootURI);
  ZoteroObsidianExporter.init();

  windowObserver = {
    observe(subject, topic) {
      if (topic === 'domwindowopened') {
        const window = subject.window;
        if (window.ZoteroPane) {
          addWindow(window);
        }
      }
    }
  };

  Services.ww.registerNotification(windowObserver);

  for (const win of Zotero.getMainWindows()) {
    addWindow(win);
  }
}

function shutdown() {
  log('Shutting down');

  if (windowObserver) {
    Services.ww.unregisterNotification(windowObserver);
  }

  for (const win of Zotero.getMainWindows()) {
    removeWindow(win);
  }

  if (ZoteroObsidianExporter) {
    ZoteroObsidianExporter.shutdown();
    ZoteroObsidianExporter = undefined;
  }
}

function uninstall() {
  log('Uninstalled');
  Services.prefs.clearUserPref('extensions.zotero-obsidian-exporter.create-note-shortcut');
  Services.prefs.clearUserPref('extensions.zotero-obsidian-exporter.open-note-shortcut');
}
