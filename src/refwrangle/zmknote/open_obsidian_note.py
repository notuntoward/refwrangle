"""For opening an Obsidian note in Obsidian.

Three strategies are supported (tried in order by the caller):
  1. Obsidian CLI (preferred for new notes) — doesn't require any plugin and is
     immune to file-watcher / OneDrive lag.
  2. Advanced URI plugin, open mode — used when a note is already open and needs
     to be focused without duplication:
       • new_tab=True  + newpane setting on  → obsidian://adv-uri?…&newpane=true
       • new_tab=False + plugin installed    → obsidian://adv-uri?…  (focus existing tab)
  3. Standard obsidian:// URI — fallback when the Advanced URI plugin is absent."""

import os
import json
import shutil
import subprocess
import time
import urllib.parse
from pathlib import Path

def check_advanced_uri_plugin(vault_path: Path) -> tuple[bool, bool]:
    """ Checks if the Advanced URI plugin is installed and enabled.
        vault_path: Path to the Obsidian vault, including the vault name itself
        
        Return: tuple: (is_installed, is_enabled)"""

    plugin_id = "obsidian-advanced-uri"
    
    plugins_dir = vault_path / ".obsidian" / "plugins"
    community_plugins_file = vault_path / ".obsidian" / "community-plugins.json"
    
    plugin_dir = plugins_dir / plugin_id
    is_installed = plugin_dir.is_dir()
    
    is_enabled = False
    if is_installed and community_plugins_file.exists():
        try:
            with community_plugins_file.open('r') as f:
                enabled_plugins = json.load(f)
                is_enabled = plugin_id in enabled_plugins
        except Exception as e:
            print(f"Error reading community plugins file: {e}")
    
    return is_installed, is_enabled

def check_newpane_setting(vault_path: Path) -> bool:
    """Checks if the "Open file without write in new pane" option is enabled.
        vault_path: Path to the Obsidian vault, including the vault name itself
        
        Return: bool: True if the setting is enabled, False otherwise"""
        
    plugin_data_path = vault_path / ".obsidian" / "plugins" / "obsidian-advanced-uri" / "data.json"
    
    if not plugin_data_path.exists():
        print(f"Advanced URI plugin data file not found at: {plugin_data_path}")
        return False
    
    try:
        with plugin_data_path.open('r') as f:
            plugin_data = json.load(f)
            
        return plugin_data.get("openFileWithoutWriteInNewPane", False)
            
    except Exception as e:
        print(f"Error reading Advanced URI plugin settings: {e}")
        return False


def _normalize_vault_path(path: str) -> str:
    """Normalize a vault-relative path for comparison.
    
    Converts backslashes to forward slashes and strips leading/trailing slashes.
    """
    return path.replace("\\", "/").strip("/")


def is_note_open_in_obsidian(note_path: str, vault_path: Path) -> bool:
    """Check whether a note is already open in Obsidian by reading workspace.json.
    
    Args:
        note_path: vault-relative path to the note (e.g. "lit/lit_notes/Note.md")
        vault_path: full path to the vault root
        
    Returns:
        True if the note appears as an open leaf in Obsidian's workspace file.
    """
    workspace_file = vault_path / ".obsidian" / "workspace.json"
    if not workspace_file.exists():
        return False

    target = _normalize_vault_path(note_path)
    try:
        with workspace_file.open("r", encoding="utf-8") as f:
            workspace = json.load(f)
    except Exception:
        return False

    def _search(node):
        if isinstance(node, dict):
            if node.get("type") == "leaf":
                state = node.get("state") or {}
                if isinstance(state, dict):
                    inner_state = state.get("state") or {}
                    if isinstance(inner_state, dict):
                        open_file = inner_state.get("file")
                        if open_file and _normalize_vault_path(open_file) == target:
                            return True
            for value in node.values():
                if _search(value):
                    return True
        elif isinstance(node, list):
            for item in node:
                if _search(item):
                    return True
        return False

    return _search(workspace.get("workspace", workspace))


def check_obsidian_cli_available(vault_path: Path) -> dict:
    """
    Checks whether the Obsidian CLI is installed, reachable, and enabled in Settings.
    vault_path: full Path to the vault root (same as used elsewhere in this module).

    Returns a dict with keys:
        binary_on_path:      bool — CLI executable found via PATH
        binary_responds:     bool or None — 'obsidian version' succeeded
        cli_enabled:         bool or None — vault status command succeeded
        obsidian_running:    bool or None — whether Obsidian process appears to be running
        failure_reason:      str or None — one of: 'not_on_path', 'binary_broken',
                                           'obsidian_not_running', 'cli_disabled', None
    """
    status: dict[str, bool | str | None] = {
        "binary_on_path": False,
        "binary_responds": None,
        "cli_enabled": None,
        "obsidian_running": None,
        "failure_reason": None,
    }

    # Stage 1: Is the binary on PATH?
    if shutil.which("obsidian") is None:
        status["failure_reason"] = "not_on_path"
        return status
    status["binary_on_path"] = True

    # Stage 2: Probe version as a quick liveness check. Some Obsidian builds
    # (e.g. 1.12.x) return non-zero here even when the CLI is registered and
    # works for actual vault commands, so this is advisory only — we do not
    # fail the whole check on it.
    version_probe_ok = False
    try:
        result = subprocess.run(
            ["obsidian", "version"],
            capture_output=True, text=True, timeout=10
        )
        version_probe_ok = result.returncode == 0
    except Exception:
        version_probe_ok = False

    # Stage 3: The authoritative test is whether the CLI can talk to Obsidian
    # about the target vault.
    vault_name = vault_path.name
    try:
        result = subprocess.run(
            ["obsidian", f"vault={vault_name}", "status"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            status["binary_responds"] = True
            status["cli_enabled"] = True
            status["obsidian_running"] = True
            return status

        combined = (result.stdout + result.stderr).lower()
        status["binary_responds"] = True  # the binary itself responded

        if "not running" in combined or "not open" in combined:
            status["obsidian_running"] = False
            status["cli_enabled"] = False
            status["failure_reason"] = "obsidian_not_running"
        else:
            # Obsidian is running but the vault status command failed. This
            # usually means the CLI is disabled in Settings or the vault is not
            # loaded; in either case the CLI is not usable for this vault.
            status["obsidian_running"] = True
            status["cli_enabled"] = False
            status["failure_reason"] = "cli_disabled"
        return status
    except subprocess.TimeoutExpired:
        # Vault status timed out. If the version probe also failed, the CLI
        # binary itself is likely broken; otherwise Obsidian is not responding.
        status["binary_responds"] = version_probe_ok
        status["obsidian_running"] = False
        status["cli_enabled"] = False
        status["failure_reason"] = "obsidian_not_running" if version_probe_ok else "binary_broken"
        return status
    except Exception:
        status["binary_responds"] = version_probe_ok
        status["cli_enabled"] = False
        status["failure_reason"] = "binary_broken" if not version_probe_ok else "cli_disabled"
        return status



def open_note_via_cli(note_path: str, vault_path: Path, new_tab: bool = True, timeout: float = 10.0, interval: float = 1.5) -> dict:
    """
    Opens an existing Obsidian note using the Obsidian CLI.
    Waits for the vault to be ready before attempting to open.
    Does not depend on Obsidian's file watcher — uses Obsidian's internal API.

    note_path: vault-relative path WITH .md extension,
                e.g. "lit/lit_notes/Smith24someTitle.md"
    vault_path: full Path to the vault root (same convention as open_obsidian_note())
    new_tab:   If True (default), open in a new tab.
                If False, reuse the existing tab if the note is already open;
                otherwise open in the most-recently-used pane.
    timeout:   Maximum seconds to wait for vault readiness (default 10)
    interval:  Seconds to wait between status polls (default 1.5)

    Returns a dict with keys:
        success:       bool
        cli_output:    str — stdout from CLI call
        error:         str or None — stderr or exception message
    """
    vault_name = vault_path.name
    result_dict = {"success": False, "cli_output": "", "error": None}
    
    # Wait for vault to be ready. If status reports the vault as not open but
    # it is registered in Obsidian, try to open it via the CLI first.
    deadline = time.time() + timeout
    vault_ready = False
    vault_open_attempted = False
    while time.time() < deadline:
        try:
            status_result = subprocess.run(
                ["obsidian", f"vault={vault_name}", "status"],
                capture_output=True, text=True, timeout=10
            )
            if status_result.returncode == 0:
                vault_ready = True
                break
            # Vault exists but is not open — try to open it (only once)
            if not vault_open_attempted:
                vault_open_attempted = True
                try:
                    subprocess.run(
                        ["obsidian", f"vault={vault_name}", "open"],
                        capture_output=True, text=True, timeout=10
                    )
                except Exception:
                    pass
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass
        time.sleep(interval)
    
    if not vault_ready:
        result_dict["error"] = "Timed out waiting for vault to be ready"
        return result_dict
    
    # Vault is ready, try to open the note
    try:
        cmd = ["obsidian", f"vault={vault_name}", "open", f"path={note_path}"]
        if new_tab:
            cmd.append("newtab")
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=10
        )
        result_dict["cli_output"] = result.stdout.strip()
        if result.returncode == 0:
            result_dict["success"] = True
        else:
            result_dict["error"] = result.stderr.strip() or result.stdout.strip()
    except subprocess.TimeoutExpired:
        result_dict["error"] = "CLI open timed out"
    except Exception as e:
        result_dict["error"] = str(e)
    
    return result_dict
    
def open_obsidian_note(
    note_path: str,
    vault_path: Path | str | None = None,
    new_tab: bool = True,
    prefer_uri: bool = False,
) -> dict:
    """ Opens an Obsidian note in a new tab, if possible and requested.
          note_path: internal obsidian path from the vault root to the note (without .md)
          vault_path: Full path to the vault directory (Path object or string)
          new_tab: Whether to open in a new tab (requires Obsidian's Advanced URI plugin, 
                    with its "Open file without write in new pane" option enabled)
          prefer_uri: If True, skip the CLI entirely and use the Advanced URI /
                    standard obsidian:// URI method. The raw Obsidian CLI `open`
                    command does not search existing tabs for the target file —
                    it opens/reuses the most-recently-used pane regardless of
                    whether the file is already displayed elsewhere, which can
                    produce a duplicate tab. The Advanced URI plugin (without
                    `newpane`) explicitly searches leaves for the file and
                    focuses it, so it is the reliable way to "focus if already
                    open, otherwise open in place" without duplicating tabs.
      
          Returns: dict: Status information about the operation (see comments)"""
    
    status = {"vault_found": False,          # vault_path works
              "note_found": None,            # note_path works
              "advanced_uri_plugin_installed": None,      # plugin installed
              "advanced_uri_plugin_enabled": None,        # enabled
              "plugin_newpane_setting_enabled": None, # plugin option enabled
              "new_tab_requested": new_tab,  # From function parameter
              "new_tab_possible": None,      # if new tab could be done
              "method_used": None,           # URI type used to open note
              "uri_used": ""}                # actually used URI
    
    if vault_path is None:
        raise ValueError("vault_path must be provided")
    
    vault_path = vault_path if isinstance(vault_path, Path) else Path(vault_path)
    vault_name = vault_path.name
    status["vault_found"] = vault_path.exists()
    
    if not status["vault_found"]:
        status["note_found"] = False
        status["method_used"] = "none"
        return status
    
    print(f'{note_path=}')
    if not note_path.endswith('.md'):
        note_path += '.md'
    status["note_found"] = (vault_path / note_path).exists()
    
    # If vault is found, try the CLI method first if available and responsive
    # (unless the caller explicitly asked to skip it via prefer_uri — see the
    # prefer_uri docstring above for why CLI is unsuitable for focus-if-open).
    # We try CLI even if note doesn't exist on disk yet, as CLI can create/open new notes.
    # We try CLI whenever the binary is available and responsive (binary_on_path and binary_responds),
    # regardless of whether the specific vault's CLI is enabled, since the act of opening a note
    # might cause the vault to open.
    if status["vault_found"] and not prefer_uri:
        cli_status = check_obsidian_cli_available(vault_path)
        if cli_status["binary_on_path"] and cli_status["binary_responds"]:
            # Check if the vault is already open
            vault_already_open = False
            try:
                status_result = subprocess.run(
                    ["obsidian", f"vault={vault_name}", "status"],
                    capture_output=True, text=True, timeout=10
                )
                vault_already_open = status_result.returncode == 0
            except Exception:
                pass
            
            if vault_already_open:
                # Try to open via CLI (only when vault is already open)
                cli_result = open_note_via_cli(note_path, vault_path, new_tab)
                if cli_result["success"]:
                    # Build a status dict for CLI success
                    status["method_used"] = "cli"
                    status["cli_output"] = cli_result["cli_output"]
                    status["error"] = cli_result["error"]
                    status["uri_used"] = ""  # No URI used in CLI method
                    # CLI's "newtab" flag reliably adds a new tab when requested,
                    # so treat success as fulfilling the new_tab request.
                    status["new_tab_possible"] = True if new_tab else None
                    return status
                # If CLI method fails, fall through to URI method below
    
    # If we get here, either vault not found, CLI not available/responsive, 
    # vault not open, or CLI method failed.
    # Proceed with URI method (original logic)
    # Reset URI-specific status fields
    status["advanced_uri_plugin_installed"] = None
    status["advanced_uri_plugin_enabled"] = None
    status["plugin_newpane_setting_enabled"] = None
    status["new_tab_possible"] = None
    status["method_used"] = None
    status["uri_used"] = ""
    
    if status["vault_found"] and status["note_found"]:
        is_installed, is_enabled = check_advanced_uri_plugin(vault_path)
        status["advanced_uri_plugin_installed"] = is_installed
        status["advanced_uri_plugin_enabled"] = is_enabled
        
        if is_installed and is_enabled:
            newpane_enabled = check_newpane_setting(vault_path)
            status["plugin_newpane_setting_enabled"] = newpane_enabled
            status["new_tab_possible"] = new_tab and newpane_enabled
            if new_tab and newpane_enabled:
                status["method_used"] = "advanced-uri-newtab"
            else:
                # Plugin present but new_tab=False or newpane setting off:
                # use Advanced URI without newpane — this focuses the existing tab
                # if the file is already open, which obsidian://open does NOT do.
                status["method_used"] = "advanced-uri-focus"
        else:
            status["new_tab_possible"] = False
            status["method_used"] = "standard"
        
        try:
            vault_name_quoted = urllib.parse.quote(vault_name)
            # Advanced URI plugin's `filepath` parameter requires the path separators
            # to be encoded as %2F — use safe='' to encode forward slashes.
            note_path_quoted_filepath = urllib.parse.quote(note_path, safe='')
            # Standard obsidian:// `file` parameter accepts unencoded slashes.
            note_path_quoted_file = urllib.parse.quote(note_path)
            
            if status["method_used"] == "advanced-uri-newtab":
                uri = f"obsidian://adv-uri?vault={vault_name_quoted}&filepath={note_path_quoted_filepath}&newpane=true"
            elif status["method_used"] == "advanced-uri-focus":
                # Focuses the existing open tab for this file, or opens in the current pane.
                # Does NOT create a duplicate tab.
                uri = f"obsidian://adv-uri?vault={vault_name_quoted}&filepath={note_path_quoted_filepath}"
            else:  # standard — fallback when Advanced URI plugin is not installed
                uri = f"obsidian://open?vault={vault_name_quoted}&file={note_path_quoted_file}"
            
            status["uri_used"] = uri
        except Exception as e:
            print(f"Error building URI: {e}")
        
        if status["note_found"] and status["uri_used"]:
            try:
                uri = status["uri_used"]
                print(f'Firing URI ({status["method_used"]}): {uri}')
                if os.name == 'nt':  # Windows
                    # os.startfile is the most reliable way to open a custom URI
                    # handler on Windows — it goes through the ShellExecute API
                    # directly, which is what Explorer uses and avoids the
                    # intermediate cmd.exe process that can silently drop the call.
                    os.startfile(uri)
                elif os.name == 'posix':  # macOS or Linux
                    if Path('/proc/version').exists() and 'microsoft' in Path('/proc/version').read_text().lower():
                        subprocess.run(['cmd.exe', '/c', 'start', '', uri], capture_output=True, check=False)  # it's Linux but WSL
                    elif Path('/System').exists():  # macOS
                        subprocess.run(['open', uri])
                    else:  # Linux
                        subprocess.run(['xdg-open', uri])
            except Exception as e:
                print(f"Error opening URI: {e}")
    
    return status

if __name__ == "__main__":
    # Tests
    from icecream import ic

    # Option 1: Provide just the vault path (name is extracted automatically)
    # Open several notes so can verify that new tab for each note works
    vault_path = Path(r"C:\Users\scott\OneDrive\share\ref\obsidian\Obsidian Share Vault")
    status = open_obsidian_note( "lit/lit_notes/Coursera24SQLVsNoSQLdiffExplain", vault_path=vault_path, new_tab=True)
    status = open_obsidian_note( "lit/lit_notes/Atrioc25teslaBacklashBiblical", vault_path=vault_path, new_tab=True)
    
    # Option 2: Provide both vault path and explicit name (if folder name differs from vault name)
    # vault_path = Path("C:/Users/YourName/Documents/ObsidianVaults/Shared")
    # result = open_obsidian_note("All Tasks Summary", new_tab=True, vault_path=vault_path, vault_name="Obsidian Share Vault")    
    good_note_path = "lit/lit_notes/Coursera24SQLVsNoSQLdiffExplain"
    good_vault_path = Path(r"C:\Users\scott\OneDrive\share\ref\obsidian\Obsidian Share Vault")
    
    # test bad path cases
    note_path, vault_path = "DOES NOT EXIST", "BAD_PATH"
    status = open_obsidian_note(note_path, vault_path=vault_path, new_tab=True)
    ic(status)

    # a prototype for caller error handling
    if not (status['note_found'] and  status['vault_found'] and status["uri_used"] != ""):
        error_message = f'Note, Vault or URI problem: {status=}'
    elif status['new_tab_requested'] and status['new_tab_possible'] is not True:
        error_message = f'Could not make new note tab: {status=}'
    else:
        error_message = ''
    
    ic(error_message)