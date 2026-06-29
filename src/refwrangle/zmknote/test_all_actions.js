// test_all_actions.js — smoke-test runner for every .js action script.
//
// SAFETY — read before running in your Zotero:
//
// Every `eval` of a real action script used to run under the *live* Zotero
// environment.  The previous "source loads without syntax errors" evals only
// stubbed `require`, leaving Zotero, Services.prompt, items, item, and fetch
// real.  If items were selected in Zotero when the test was run, the regen
// script would actually propose keys and pop up edit dialogs for them; the
// sender scripts would flip Zotero.ZoteroWebhookLock on the real Zotero,
// fire a real Zotero.alert("No item selected"), and (if the Python receiver
// was running and real items had citekeys) make a real websocket fetch to
// localhost:5050.
//
// All evals are now routed through `evalInSandbox(src, ...)`, which:
//   • Replaces Zotero/Services.prompt/items/item/fetch with no-op stubs
//     for the duration of the eval.
//   • Restores every global in a `finally` block, even on throw.
//   • Passes `items` and `item` as empty / null so scripts see no selection.
//
// The behavioural regen tests use an additional layer (runScript) that
// injects mock-items and controls what Services.prompt.prompt() returns.
// In both layers, Zotero.BetterBibTeX.KeyManager.propose returns stub
// keys and item.saveTx() is a no-op resolved Promise — no database writes.
//
// The **only** real Zotero calls made by this test are:
//   • Services.prompt.confirm() — the "Continue?" gate at the top.
//   • Services.prompt.alert()   — the final results popup.
//
// If still unsure, back up your Zotero profile before running.

(async function () {

  // ==========================================================================
  // Self-locate: derive the action-script directory from the eval stack.
  // The test file can be dropped alongside the actions on any machine.
  // ==========================================================================
  function scriptDirectory() {
    const stackLine = (new Error()).stack.split('\n')[1] || '';
    const raw = stackLine.split('@')[0].trim();
    const cleaned = raw
      .replace('jar:file://', '')        // packaged Zotero extensions
      .replace(/\/test_all_actions\.js$/, '')
      .replace(/\\test_all_actions\.js$/, '')
      .replace(/test_all_actions\.js$/, '');
    return OS.Path.dirname(OS.Path.normalize(cleaned));
  }

  const SCRIPT_DIR = scriptDirectory();

  // ---------------------------------------------------------------------------
  // Safety gate
  // ---------------------------------------------------------------------------
  const OK = Services.prompt.confirm(
    null,
    'Action Scripts Smoke Test',
    'This will `eval` every .js action script in this folder.\n\n' +
    'Every eval runs inside a full sandbox: Zotero, Services.prompt,\n' +
    'items, item, and fetch are all replaced with no-op stubs — no\n' +
    'Zotero data is written and no network requests are made.\n\n' +
    'The only Zotero calls this test itself makes are this confirm\n' +
    'dialog and the final results alert.\n\n' +
    'If unsure, back up your Zotero profile first.\n\n' +
    'Continue?'
  );
  if (!OK) return;

  // ==========================================================================
  // Path resolution
  // ==========================================================================
  function scriptPath(name) {
    return OS.Path.join(SCRIPT_DIR, name + '.js');
  }
  function readSource(name) {
    const p = scriptPath(name);
    return OS.File.exists(p) ? IOUtils.readUTF8(p) : null;
  }

  const SCRIPT_NAMES = [
    'regen_bibtex_key',
    'toggle_left_pane',
    'toggle_right_pane',
    'open_obsidian_note_sender',
    'new_obsidian_note_sender',
  ];

  const sources = {};
  SCRIPT_NAMES.forEach(name => { sources[name] = readSource(name); });

  // ==========================================================================
  // Shared mocks
  // ==========================================================================
  function makeItem(overrides = {}) {
    const fields = Object.assign(
      { citationKey: 'Smith2024test', title: 'Test Item', extra: '' },
      overrides._fields || {}
    );
    const item = Object.assign({
      id: 12345,
      key: 'FAKEYKEY',
      libraryID: 1,
      itemType: 'journalArticle',
      deleted: false,
      getField:       function(n) { return fields[n] ?? ''; },
      setField:       function(n,v) { fields[n] = v; },
      saveTx:         function()  { return Promise.resolve(); },
      isRegularItem:  () => true,
      isAttachment:   () => false,
      reload:         function()  { return Promise.resolve(); },
      getTags:        () => [],
      getCollections: () => [],
      getNotes:       () => [],
      getAttachments: () => [],
      toJSON: function() {
        return {
          title: fields.title, DOI: '', url: '', abstractNote: '',
          creators: [], date: '2024-01-01', itemType: this.itemType,
          publicationTitle: '', volume: '', issue: '',
          publisher: '', place: '', pages: '', ISBN: '',
        };
      },
    }, overrides);
    item._fields = fields;
    return item;
  }

  // ==========================================================================
  // Report machinery
  // ==========================================================================
  const results = [];
  const ordered = [];   // async tests queued here; awaited in order

  function pass(script, label)         { results.push({ ok: true,  script, label }); }
  function fail(script, label, detail) { results.push({ ok: false, script, label, detail: String(detail) }); }

  function test(script, label, fn) {
    try {
      const result = fn();
      if (result && typeof result.then === 'function') {
        ordered.push(result);
        result.then(() => pass(script, label), err => fail(script, label, err));
      } else {
        pass(script, label);
      }
    } catch (err) {
      fail(script, label, err);
    }
  }

  // ==========================================================================
  // Sandbox eval — the core safety primitive.
  //
  // Replaces every global that a Zotero action script might read or write:
  //   Zotero         — stub object (no DB access, no network)
  //   Services.prompt— three noop dialogs
  //   items / item   — empty / null (script sees no selection)
  //   fetch          — rejected Promise (receiver not reachable)
  //   require        — returns a stub proxy (for toggle scripts)
  //
  // All of them are restored in a finally block, even on error or throw.
  // ==========================================================================
  function evalInSandbox(src, extraStubs = {}) {
    const real = {
      Zotero:        globalThis.Zotero,
      Services:      Services,
      item:          (typeof item  !== 'undefined') ? item  : undefined,
      items:         (typeof items !== 'undefined') ? items : undefined,
      fetch:         globalThis.fetch,
      require:       (typeof require !== 'undefined') ? require : undefined,
    };

    const stubZotero = Object.assign({
      BetterBibTeX: null,   // scripts must guard against this
      warn:    () => {},
      debug:   () => {},
      log:     () => {},
      alert:   (p, t, m) => { Services.prompt.alert(p, t, m); },   // forward to stubbed prompt
      Promise: { delay: () => Promise.resolve() },
      Collections: { get: () => ({ name: 'Stub Collection' }) },
      Items:       { get: () => makeItem() },
      File: {
        pathToFile: p => ({ path: p, exists: () => false, create: () => {},
                           copyTo: () => {}, QueryInterface: () => {} }),
        putContents: () => {},
      },
    }, extraStubs.Zotero || {});

    const stubPrompt = Object.assign({
      alert:   (p, t, m) => {},
      confirm: (p, t, m) => true,
      prompt:  ()       => false,
    }, extraStubs.prompt || {});

    const stubFetch = (url, opts) =>
      Promise.reject(new Error('sandboxed fetch stub — receiver not reachable'));

    const stubRequire = (mod) =>
      new Proxy(function(){}, {
        get: () => new Proxy({}, { get: () => () => {} }),
      });

  // Install the Zotero stub and the per-eval prompt stub.
  globalThis.Zotero = stubZotero;
  const realPrompt  = Services.prompt;
  Services.prompt   = stubPrompt;
  globalThis.item   = extraStubs.item   !== undefined ? extraStubs.item   : null;
  globalThis.items  = extraStubs.items  !== undefined ? extraStubs.items  : [];
  globalThis.fetch  = extraStubs.fetch  !== undefined ? extraStubs.fetch  : stubFetch;
  globalThis.require = stubRequire;

  try {
    // eslint-disable-next-line no-eval
    return (0, eval)(src);
  } finally {
    // Restore real globals — even if the script threw.
    Services.prompt = realPrompt;
    try { globalThis.Zotero = real.Zotero; } catch(_) {}
    try {
      globalThis.fetch = real.fetch;
      if (real.item  === undefined) { delete globalThis.item;  }
      else                          { globalThis.item  = real.item;  }
      if (real.items === undefined) { delete globalThis.items; }
      else                          { globalThis.items = real.items; }
      if (real.require === undefined) { delete globalThis.require; }
      else                            { globalThis.require = real.require; }
    } catch(_) { /* best-effort restore */ }
  }
  }

  // ==========================================================================
  // 1.  REGEN BIBTEX KEY
  // ==========================================================================
  {
    const name = 'regen_bibtex_key';

    if (!sources[name]) { fail(name, 'source file exists', 'not found'); }
    else {
      const src = sources[name];

      test(name, 'source file exists', () => {});

      // Sandbox eval: no selection, no real Zotero.  Even if items were
      // selected in Zotero when the test runs, nothing happens.
      test(name, 'source loads without syntax errors', () => {
        evalInSandbox(src);
      });

      test(name, 'uses KeyManager.propose (not fill)', () => {
        if (!src.includes('KeyManager.propose')) throw 'KeyManager.propose absent';
        if (src.includes('KeyManager.fill'))    throw 'still uses KeyManager.fill';
      });

      test(name, 'passes concrete IDs, not "selected"', () => {
        if (src.includes("'selected'"))
          throw "still passes 'selected'";
      });

      test(name, 'guards against missing BBT plugin', () => {
        if (!src.includes('.BetterBibTeX'))
          throw 'no BetterBibTeX guard';
      });

      test(name, 'uses Services.prompt.prompt (not ZoteroPane)', () => {
        if (!src.includes('Services.prompt.prompt')) throw 'no prompt call';
        if (src.includes('ZoteroPane'))              throw 'still uses ZoteroPane';
      });

      test(name, 'skips save when key is unchanged', () => {
        if (!src.includes('finalKey !== oldKey'))
          throw 'no change-detection guard';
      });

      test(name, 'yields between iterations', () => {
        if (!src.includes('Promise.delay'))
          throw 'no inter-item yield';
      });

      // ---- Behavioural tests: custom Zotero stub, controlled prompt --------
      let seq = 0;

      async function runScript(itemList, BetterBibTeXStub, promptReturns) {
        const ZoteroStub = {
          BetterBibTeX: BetterBibTeXStub,
          warn:    () => {},
          debug:   () => {},
          log:     () => {},
          alert:   (p, t, m) => { Services.prompt.alert(p, t, m); },
          Promise: { delay: () => Promise.resolve() },
          Collections: { get: () => ({ name: 'Stub Collection' }) },
          Items:       { get: () => makeItem() },
        };
        const promptStub = { prompt: () => promptReturns() };

        const _Zotero           = Zotero;
        const _Services_prompt  = Services.prompt;
        const _items            = (typeof items !== 'undefined') ? items : undefined;
        const _item             = (typeof item  !== 'undefined') ? item  : undefined;
        const _fetch            = globalThis.fetch;
        const _require          = (typeof require !== 'undefined') ? require : undefined;

        Zotero             = ZoteroStub;
        Services.prompt    = promptStub;
        globalThis.item    = (itemList && itemList.length) ? itemList[0] : null;
        globalThis.items   = Array.isArray(itemList) ? itemList : [];
        globalThis.fetch   = (url) => Promise.reject(new Error('sandboxed fetch'));
        globalThis.require = (mod) =>
          new Proxy(function(){}, {
            get: () => new Proxy({}, { get: () => () => {} }),
          });
        try {
          await (0, eval)(src);
        } finally {
          Services.prompt = _Services_prompt;
          Zotero          = _Zotero;
          try {
            globalThis.fetch  = _fetch;
            if (_item  === undefined) delete globalThis.item;
            else                      globalThis.item  = _item;
            if (_items === undefined) delete globalThis.items;
            else                      globalThis.items = _items;
            if (_require === undefined) delete globalThis.require;
            else                        globalThis.require = _require;
          } catch(_) { /* read-only global; best-effort restore */ }
        }
      }

      test(name, 'returns silently when BBT not installed', async () => {
        const ZoteroStub = { warn: () => {}, debug: () => {} };
        await runScript([makeItem()], ZoteroStub, () => false);
      });

      test(name, 'handles empty selection without error', async () => {
        await runScript([], {
          ready: Promise.resolve(), KeyManager: {},
        }, () => false);
      });

      test(name, 'single item: proposed key saved on OK', async () => {
        seq = 0;
        const item = makeItem({ _fields: { citationKey: 'OldKey', title: 'X' } });
        await runScript([item], {
          ready:      Promise.resolve(),
          KeyManager: { propose: () => `ProposedKey${++seq}` },
        }, () => true);
        if (item._fields.citationKey !== 'ProposedKey1')
          throw `expected ProposedKey1, got "${item._fields.citationKey}"`;
      });

      test(name, 'multi-item: all keys saved when OK', async () => {
        seq = 0;
        const items = [
          makeItem({ id: 1, _fields: { citationKey: 'A', title: 'A' } }),
          makeItem({ id: 2, _fields: { citationKey: 'B', title: 'B' } }),
          makeItem({ id: 3, _fields: { citationKey: 'C', title: 'C' } }),
        ];
        await runScript(items, {
          ready:      Promise.resolve(),
          KeyManager: { propose: () => `Key${++seq}` },
        }, () => true);
        ['Key1','Key2','Key3'].forEach((exp, i) => {
          if (items[i]._fields.citationKey !== exp)
            throw `item ${i}: expected ${exp}, got "${items[i]._fields.citationKey}"`;
        });
      });

      test(name, 'Cancel on 2nd stops; 1st saved; 2nd,3rd untouched', async () => {
        seq = 0;
        let calls = 0;
        const items = [
          makeItem({ id: 1, _fields: { citationKey: 'A', title: 'A' } }),
          makeItem({ id: 2, _fields: { citationKey: 'B', title: 'B' } }),
          makeItem({ id: 3, _fields: { citationKey: 'C', title: 'C' } }),
        ];
        await runScript(items, {
          ready:      Promise.resolve(),
          KeyManager: { propose: () => `Key${++seq}` },
        }, () => (++calls === 1));   // 1st OK, rest Cancel
        if (items[0]._fields.citationKey !== 'Key1')
          throw `item 0 expected Key1, got "${items[0]._fields.citationKey}"`;
        if (items[1]._fields.citationKey !== 'B')
          throw `item 1 should stay B, got "${items[1]._fields.citationKey}"`;
        if (items[2]._fields.citationKey !== 'C')
          throw `item 2 should stay C, got "${items[2]._fields.citationKey}"`;
      });

      test(name, 'Cancel restores original key (no write)', async () => {
        seq = 0;
        const item = makeItem({ _fields: { citationKey: 'OriginalKey', title: 'X' } });
        await runScript([item], {
          ready:      Promise.resolve(),
          KeyManager: { propose: () => `NewProposed${++seq}` },
        }, () => false);
        if (item._fields.citationKey !== 'OriginalKey')
          throw `expected OriginalKey, got "${item._fields.citationKey}"`;
      });
    }
  }

  // ==========================================================================
  // 2.  TOGGLE PANES  (structural — DOM actions not mocked beyond require stub)
  // ==========================================================================
  {
    const toggleNames = ['toggle_left_pane', 'toggle_right_pane'];
    toggleNames.forEach(name => {
      if (!sources[name]) { fail(name, 'source file exists', 'not found'); return; }
      const src = sources[name];

      test(name, 'source file exists', () => {});

      // Sandbox eval — no selection, no real Zotero.
      test(name, 'source loads without syntax errors', () => {
        evalInSandbox(src);
      });

      test(name, 'returns early when an item is supplied', () => {
        if (!src.includes('if (item)')) throw 'no item guard';
      });

      test(name, 'toggles splitter state', () => {
        if (!src.includes('state'))       throw 'no state reference';
        if (!src.includes('collapsed'))   throw 'no collapsed state';
      });

      test(name, 'branches on library-tab vs reader-tab', () => {
        if (!src.includes('Zotero_Tabs.selectedType'))
          throw 'no Zotero_Tabs.selectedType branch';
      });

      test(name, 'uses document.querySelector', () => {
        if (!src.includes('document.querySelector'))
          throw 'no document.querySelector';
      });
    });
  }

  // ==========================================================================
  // 3.  OPEN OBSIDIAN NOTE SENDER
  // ==========================================================================
  {
    const name = 'open_obsidian_note_sender';
    if (!sources[name]) { fail(name, 'source file exists', 'not found'); }
    else {
      const src = sources[name];

      test(name, 'source file exists', () => {});

      // Sandbox eval — no items, no fetch, no real Zotero.
      test(name, 'source loads without syntax errors', () => {
        evalInSandbox(src);
      });

      test(name, 'has ZoteroWebhookLock guard', () => {
        if (!src.includes('ZoteroWebhookLock') || !src.includes('inProgress'))
          throw 'no dedup guard';
      });

      test(name, 'uses SENDER_ID_OPEN_OBSIDIAN_NOTE', () => {
        if (!src.includes("'open_obsidian_note'"))
          throw 'missing sender id';
      });

      test(name, 'sends plain citekeys (not full item objects)', () => {
        if (!src.includes('itemDataArray.push(citekey)'))
          throw 'wrong payload shape';
      });

      test(name, 'warns when webhook times out', () => {
        if (!src.includes('did not respond'))
          throw 'no timeout warning';
      });

      test(name, 'falls back to extra-field citekey pre-8.0', () => {
        if (!/extra/i.test(src)) throw 'no extra field fallback';
      });

      test(name, 'uses fetch() for webhook POST', () => {
        if (!src.includes('fetch(')) throw 'no fetch call';
      });

      test(name, 'payload includes sender_id', () => {
        if (!src.includes('sender_id')) throw 'no sender_id in payload';
      });

      test(name, 'clears lock on all exit paths (catch block)', () => {
        if (!/catch\s*[\s(]*\)?\s*\{[^}]*inProgress\s*=\s*false/s.test(src))
          throw 'lock not cleared in catch';
      });
    }
  }

  // ==========================================================================
  // 4.  NEW OBSIDIAN NOTE SENDER
  // ==========================================================================
  {
    const name = 'new_obsidian_note_sender';
    if (!sources[name]) { fail(name, 'source file exists', 'not found'); }
    else {
      const src = sources[name];

      test(name, 'source file exists', () => {});

      // Sandbox eval — no items, no fetch, no real Zotero.
      test(name, 'source loads without syntax errors', () => {
        evalInSandbox(src);
      });

      test(name, 'has ZoteroWebhookLock guard', () => {
        if (!src.includes('ZoteroWebhookLock') || !src.includes('inProgress'))
          throw 'no dedup guard';
      });

      test(name, 'uses SENDER_ID_NEW_OBSIDIAN_NOTE', () => {
        if (!src.includes("'new_obsidian_note_from_zotero'"))
          throw 'missing sender id';
      });

      test(name, 'defines validateCitationKey function', () => {
        if (!/function\s+validateCitationKey\s*\(/.test(src))
          throw 'no validateCitationKey definition';
      });

      test(name, 'validates before sending (invalid-key popup flow)', () => {
        if (!src.includes('validateCitationKey(citekey)'))
          throw 'no validation call';
        if (!src.includes('Invalid Citation Key'))
          throw 'no invalid-key popup title';
      });

      test(name, 'fetches bibliography via BBT JSON-RPC', () => {
        if (!src.includes('item.bibliography')) throw 'no bibliography RPC call';
        if (!src.includes('item.citationkey'))  throw 'no citekey RPC call';
      });

      test(name, 'falls back to libraryID:itemKey when citekey lookup empty', () => {
        if (!src.includes('libItemId')) throw 'no libItemId fallback';
      });

      test(name, 'has timedOut race-guard in sendToWebhook', () => {
        if (!/timedOut\s*=\s*true/.test(src))
          throw 'no timedOut flag';
      });

      test(name, 'sends full item payload (not just citekeys)', () => {
        const fields = ['citekey:', 'bibliography:', 'tags:', 'creators:', 'notes:'];
        for (const f of fields) {
          if (!src.includes(f)) throw `payload missing "${f}"`;
        }
      });

      test(name, 'deduplicates invalid-citekey popups per run (5 s window)', () => {
        if (!src.includes('shownPopupCitekeys')) throw 'no popup dedup';
        if (!src.includes('5000'))                throw 'no 5 s expiry on dedup map';
      });
    }
  }

  // ==========================================================================
  // Await all queued async behavioural tests, then display the report.
  // ==========================================================================
  for (const p of ordered) { try { await p; } catch (_) { /* failure already recorded */ } }

  if (results.length === 0) {
    Services.prompt.alert(null, 'Smoke Test',
      'No results collected. SCRIPT_DIR could not be resolved.\n\n' +
      'SCRIPT_DIR = ' + SCRIPT_DIR);
    return;
  }

  const passCount = results.filter(r => r.ok).length;
  const failCount = results.filter(r => !r.ok).length;
  const lines = results.map(r =>
    (r.ok ? '[PASS] ' : '[FAIL] ') + r.script + ' — ' + r.label +
    (r.detail ? '\n        ' + r.detail : '')
  );
  const summary =
    'ACTION SCRIPT SMOKE-TEST RESULTS\n' +
    '─'.repeat(48) + '\n\n' +
    lines.join('\n') +
    '\n\n' +
    `Total: ${results.length}   Passed: ${passCount}   Failed: ${failCount}`;

  Services.prompt.alert(null, 'Action Scripts Smoke Test', summary);
})();
