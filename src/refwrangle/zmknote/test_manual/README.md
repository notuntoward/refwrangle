# Manual / Integration Tests

These scripts require a live Zotero instance, an Obsidian vault, or other
external services. They are NOT run automatically before commits.

Run them by hand when testing end-to-end integration.

| File | What it tests |
|------|--------------|
| `multikey_listener_test.py` | Flask webhook listener prototype with browser-based dialogs |
| `multikey_sender_test.js` | Companion JS sender for the multikey listener test |
| `action_tags_test.js` | Action & Tags plugin script smoke test |
| `action_tags_run_python_test.js` | Runs a Python script from Action & Tags |
| `test-zotero-script.js` | Zotero script sandbox / scratch test |
| `zotero_note_to_markdown_test.py` | HTML→Markdown conversion test (requires a Zotero JSON input file) |
| `zotero_note_to_markdown_test.ipynb` | Jupyter notebook version of the above |
| `zotero_to_obsidian_note_pyzotero.py` | pyzotero API integration test (requires Zotero running) |
| `zotero_webhook_listener_test.py` | Webhook listener integration test |

## Automated tests are in `../test/`

See [`../test/README.md`](../test/README.md) for tests that run automatically.
