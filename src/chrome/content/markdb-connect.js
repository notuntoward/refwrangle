
var MarkDBConnect = (() => {
  var __defProp = Object.defineProperty;
  var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __hasOwnProp = Object.prototype.hasOwnProperty;
  var __export = (target, all) => {
    for (var name in all)
      __defProp(target, name, { get: all[name], enumerable: true });
  };
  var __copyProps = (to, from, except, desc) => {
    if (from && typeof from === "object" || typeof from === "function") {
      for (let key of __getOwnPropNames(from))
        if (!__hasOwnProp.call(to, key) && key !== except)
          __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
    }
    return to;
  };
  var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

  // MarkDB-Connect.ts
  var MarkDBConnect_exports = {};
  __export(MarkDBConnect_exports, {
    startup: () => startup
  });
  var Zotero2 = window.Zotero;
  var PromptFactory = class {
    constructor(promptService) {
      this.promptService = promptService;
    }
    confirm(title, text) {
      const confirmed = this.promptService.confirm(null, title, text);
      return confirmed;
    }
  };
  var Notifier = class {
    constructor(notifierID, window) {
      this.notifierID = notifierID;
      this.window = window;
    }
    async anounce(message, progress) {
      let notifier = this.window.document.getElementById(this.notifierID);
      if (!notifier) {
        const ZoteroPane = this.window.ZoteroPane;
        notifier = ZoteroPane.createProgressNotifier(message);
        notifier.id = this.notifierID;
      }
      notifier.setText(message);
      if (progress) {
        notifier.setProgress(progress);
      }
    }
    close() {
      const notifier = this.window.document.getElementById(this.notifierID);
      if (notifier) {
        notifier.close();
      }
    }
  };
  var startup = ({ id, version, rootURI }) => {
    log("Starting MarkDB-Connect");
    const window = Zotero2.getMainWindow();
    const prompt = new PromptFactory(window.Services.prompt);
    const notifier = new Notifier("markdb-connect-notifier", window);
    Services.scriptloader.loadSubScript(rootURI + "lib/sql-wasm.js");
    const dbPath = Zotero2.getProfileDirectory().path + "/markdb-connect.sqlite";
    log("Initializing DB at " + dbPath);
    let db;
    let query_res;
    const load = async () => {
      const SQL = await initSqlJs({
        locateFile: (file) => `${rootURI}lib/${file}`
      });
      let db_exists = await Zotero2.File.exists(dbPath);
      if (db_exists) {
        log("DB exists, loading.");
        const filecontents = await Zotero2.File.getContentsAsync(dbPath);
        db = new SQL.Database(filecontents);
      } else {
        log("DB does not exist, creating.");
        db = new SQL.Database();
        const data = db.export();
        await Zotero2.File.putContentsAsync(dbPath, data);
      }
      query_res = db.exec(
        "CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT)"
      );
      log(query_res);
    };
    load();
    const save = async () => {
      const data = db.export();
      await Zotero2.File.putContentsAsync(dbPath, data);
      log("DB saved.");
    };
    const main = async (a) => {
      log(a);
      notifier.anounce(
        "MarkDB-Connect: Starting export, this may take a while..."
      );
      const items = await Zotero2.Items.getAll(
        Zotero2.getLibraryID(),
        true,
        false,
        true
      );
      let i = 0;
      for (const item of items) {
        const file = item.getAttachments(false, true).find((id) => {
          const attachment = Zotero2.Items.get(id);
          return attachment.attachmentContentType === "application/pdf";
        });
        i++;
        if (file) {
          const file_item = Zotero2.Items.get(file);
          const meta = {
            item: item,
            file: file_item,
            path: file_item.getFilePath()
          };
          notifier.anounce(`MarkDB-Connect: Processing ${i}/${items.length} items.`, i / items.length * 100);
          const key = item.getField("key");
          const value = JSON.stringify(meta, null, 2);
          const stmt = db.prepare(
            "INSERT OR REPLACE INTO kv (key, value) VALUES (?, ?)"
          );
          stmt.bind([key, value]);
          stmt.step();
          stmt.free();
        }
      }
      await save();
      notifier.close();
      prompt.confirm("MarkDB-Connect", "Export finished.");
    };
    const menuitem = createHElement("menuitem");
    menuitem.setAttribute("label", "MarkDB-Connect: Sync Library");
    menuitem.addEventListener("command", main);
    const menupopup = window.document.getElementById("menu_FilePopup");
    menupopup.appendChild(menuitem);
    function log(msg) {
      Zotero2.debug("MarkDB-Connect: " + msg);
    }
    function createHElement(type) {
      return window.document.createXULElement(type);
    }
  };
  return __toCommonJS(MarkDBConnect_exports);
})();
