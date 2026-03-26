# Automated Regression Tests

These tests run automatically before every commit and in CI. They require no
live Zotero, Obsidian, or network connection.

## Python tests (pytest)

```
uv run pytest test/ -v
```

File: `test_regression.py`

Covers:
- `validate_filepath()` — Windows-invalid chars, reserved names, length limits
- `open_obsidian_note()` — URI construction modes (new-tab, focus-existing, fallback)
- `check_obsidian_cli_available()` — 3-stage CLI health check, including unexpected exceptions
- `open_note_via_cli()` — `new_tab` parameter wiring, error propagation
- `ask_overwrite_popup()` — return value contract (never returns the removed `"open"` value)
- Startup block structure — `threading.Thread` present before `serve()` (non-blocking check)

## JavaScript tests (Vitest)

```
npm test
```

File: `test_sender_scripts.test.js`

Covers:
- `validateCitationKey()` in `new_obsidian_note_sender.js` — all input types, all
  Windows-forbidden characters, reserved names, length, control-char labelling scheme
- Structural checks for both sender scripts — key functions/guards still present,
  old regression patterns absent

## When to run

Run both suites before committing changes to any of:
- `new_obsidian_note_sender.js`
- `open_obsidian_note_sender.js`
- `open_obsidian_note.py`
- `zotero_to_obsidian_note_receiver.py`
