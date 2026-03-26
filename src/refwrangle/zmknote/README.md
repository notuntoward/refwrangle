# zmknote — Zotero → Obsidian Note Pipeline

This folder contains the scripts that create Obsidian literature notes from
selected Zotero items, and open existing notes in Obsidian.

---

## Overview

```
Zotero (Actions & Tags plugin)
    ↓  trigger hotkey
    ↓  run sender script (JS)
    ↓  HTTP webhook POST → localhost:5050
    ↓
zotero_to_obsidian_note_receiver.py  (Python, always running)
    ↓  writes Markdown note to Obsidian vault
    ↓  opens / focuses the note in Obsidian
```

### Two workflows

| Hotkey | Sender script | Action |
|--------|---------------|--------|
| `Ctrl+N` | `new_obsidian_note_sender.js` | Create a new literature note (or overwrite an existing one after confirmation) |
| `Ctrl+O` | `open_obsidian_note_sender.js` | Open / focus an existing literature note |

---

## Scripts

### `zotero_to_obsidian_note_receiver.py`
The always-running Python webhook server (port 5050). Receives item data from
Zotero, renders a Jinja2 Markdown template, writes the note to the Obsidian
vault, and opens/focuses the note.

- **Start it**: `uv run zotero_to_obsidian_note_receiver.py`
  (or double-click `StartZoteroToObsidian.bat`)
- **Logs to**: `zotero_item_receiver.log` in this directory

### `open_obsidian_note.py`
Low-level note-opening utilities used by the receiver. Supports two strategies:
1. **Obsidian CLI** (preferred — immune to file-watcher/OneDrive lag)
2. **Advanced URI plugin** — `obsidian://adv-uri?…` for new-tab and tab-focus

### `new_obsidian_note_sender.js`  ← paste into Zotero Actions & Tags
Runs inside Zotero when the "New Obsidian Note" hotkey fires. Collects the
selected item(s), fetches the bibliography from Better BibTeX, validates the
citation key, and sends the full item payload to the receiver via webhook.

### `open_obsidian_note_sender.js`  ← paste into Zotero Actions & Tags
Runs inside Zotero when the "Open Obsidian Note" hotkey fires. Sends the
citation key(s) of the selected item(s) to the receiver, which uses the
Advanced URI plugin to focus the already-open note tab (no duplicate tabs).

### `open_obsidian_note_sender.js` vs `new_obsidian_note_sender.js`
The two sender scripts share a `ZoteroWebhookLock` global to prevent duplicate
webhook calls. They use a different `sender_id` to tell the receiver which
action to take.

### `StartZoteroToObsidian.bat`
Windows batch file that starts the receiver in the background. Double-click
to launch.

### `zotero_to_obsidian_note_receiver_installer.py`
One-time setup script. Installs Python dependencies and registers the receiver.

---

## Installation

### Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.12+ | via `uv` (recommended) or system Python |
| `uv` | `pip install uv` — or see https://docs.astral.sh/uv/getting-started/installation/ |
| Node.js 18+ | only needed to run the JS test suite (`npm test`); not needed to use the scripts. Download from https://nodejs.org |
| Zotero 8+ | with **Actions and Tags** plugin and **Better BibTeX** plugin |
| Obsidian | with **Advanced URI** plugin installed and enabled |
| Obsidian CLI | v1.12.4+. Install: download a **fresh Obsidian installer** (in-app update is NOT sufficient) → Settings → General → enable "Command line interface" → click "Register CLI" |

### First-time setup

```
# 1. Clone / download the repo, then install all Python dependencies
#    (uv reads pyproject.toml automatically — no need to list packages)
cd path/to/refwrangle
uv sync

# 2. Edit zotero_to_obsidian_note_receiver.py to set your vault path:
#    OS_PATH_TO_VAULT_ROOT = Path(r"C:\Users\you\...\YourVaultName")

# 3. Start the receiver — two options (pick one):

#    Option A: run directly with uv (no build step, always uses latest source)
uv run src/refwrangle/zmknote/zotero_to_obsidian_note_receiver.py

#    Option B: build a standalone Windows .exe (no Python required to run it)
cd src/refwrangle/zmknote
uv run pyinstaller --runtime-tmpdir=. \
    --hidden-import win32timezone \
    --exclude-module PyQt5 \
    --exclude-module PySide6 \
    --onefile \
    zotero_to_obsidian_note_receiver.py
# This creates dist/zotero_to_obsidian_note_receiver.exe
# pyinstaller is already a project dependency (installed by uv sync)
```

> **Option A vs Option B**: `uv run` is easier to update (just edit the .py file and restart).
> The `.exe` is useful if Python/uv are not available on the target machine.
> `StartZoteroToObsidian.bat` can run either version — edit it to choose.

### Register sender scripts in Zotero

1. Open Zotero → Tools → Actions and Tags
2. Create a new rule for "New Obsidian Note":
   - **Shortcut**: `Ctrl+N`
   - **Script**: paste the full contents of `new_obsidian_note_sender.js`
3. Create a new rule for "Open Obsidian Note":
   - **Shortcut**: `Ctrl+O`
   - **Script**: paste the full contents of `open_obsidian_note_sender.js`
4. Save both rules

> **Important**: the Actions and Tags plugin stores script content inline in
> Zotero's preferences database. When you update either `.js` file, you must
> paste the new content into the plugin's rule editor again.

---

## Running the tests

### Automated regression tests (run before every commit)

**Python** (50 tests):
```
uv run pytest                    # from the repo root (src/refwrangle/zmknote/test/ is auto-discovered)
# or:
uv run pytest test/test_regression.py -v
```

**JavaScript** (49 tests, requires Node.js):
```
cd path/to/zmknote
npm install    # one-time
npm test
```

See [`test/README.md`](test/README.md) for details on what each test covers.

### Manual / integration tests

Scripts that require a live Zotero + Obsidian setup live in [`test_manual/`](test_manual/).
See [`test_manual/README.md`](test_manual/README.md).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| "Nothing happens" when triggering hotkey | Script not saved in Actions & Tags plugin | Re-paste the `.js` file content into the plugin rule |
| Receiver not reached | Server not started | Run `uv run zotero_to_obsidian_note_receiver.py` first |
| "Obsidian CLI Disabled" popup | CLI not enabled in Obsidian settings | Settings → General → enable "Command line interface" |
| "Obsidian CLI Not Found" popup | Fresh Obsidian installer required | Download installer (not in-app update), then Settings → General → "Register CLI" |
| Note tab not focused after overwrite | Advanced URI plugin not installed/enabled | Install and enable in Obsidian Community Plugins |
| Bibliography empty | Better BibTeX not running | Open Zotero, ensure BBT plugin is active |
