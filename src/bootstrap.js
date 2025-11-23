const {
    classes: Cc,
    interfaces: Ci,
    utils: Cu,
    results: Cr
} = Components;

Cu.import('resource://gre/modules/Services.jsm');

var ZoteroObsidianExporter;

function log(msg) {
    Zotero.debug('ZoteroObsidianExporter: ' + msg);
}

var zoteroReady = new Promise(resolve => {
    if (Zotero.initializationComplete) {
        resolve();
    } else {
        let notifier = {
            observe: (subject, topic) => {
                if (topic === 'zotero-initialization-complete') {
                    Zotero.Notifier.removeObserver(notifierID);
                    resolve();
                }
            }
        };
        let notifierID = Zotero.Notifier.registerObserver(notifier, ['zotero-initialization-complete']);
    }
});

async function install() {
    await zoteroReady;
    log('Installed');
}

async function startup({
    id,
    version,
    rootURI
}) {
    await zoteroReady;
    log('Starting');

    Services.scriptloader.loadSubScript('chrome://zotero-obsidian-exporter/content/zotero-obsidian-exporter.js', () => {
        ZoteroObsidianExporter.init({
            id,
            version,
            rootURI
        });
    });
}

function onMainWindowLoad({
    window
}) {
    ZoteroObsidianExporter.addToWindow(window);
}

function onMainWindowUnload({
    window
}) {
    ZoteroObsidianExporter.removeFromWindow(window);
}

async function shutdown() {
    await zoteroReady;
    if (ZoteroObsidianExporter) {
        log('Shutting down');
        ZoteroObsidianExporter.shutdown();
        ZoteroObsidianExporter = undefined;
    }
}

async function uninstall() {
    await zoteroReady;
    log('Uninstalled');
}
