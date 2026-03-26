"""For opening a note in a new obsidian tab.

NOTE: It won't open the note in a NEW tab unless Obsidian's Advanced URI plugin is installed and has the right options.  
Without that, it will back off to the default obsidian URI mechanism, which REUSES an existing tab."""

import os
import json
import shutil
import urllib.parse
import subprocess
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

    # Stage 2: Does the binary respond?
    try:
        result = subprocess.run(
            ["obsidian", "version"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            status["binary_responds"] = False
            status["failure_reason"] = "binary_broken"
            return status
        status["binary_responds"] = True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        status["binary_responds"] = False
        status["failure_reason"] = "binary_broken"
        return status

    # Stage 3: Is the CLI enabled in Settings and the vault reachable?
    vault_name = vault_path.name
    try:
        result = subprocess.run(
            ["obsidian", f"vault={vault_name}", "status"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            status["cli_enabled"] = True
            status["obsidian_running"] = True
        else:
            status["cli_enabled"] = False
            combined = (result.stdout + result.stderr).lower()
            if "not running" in combined or "not open" in combined:
                status["obsidian_running"] = False
                status["failure_reason"] = "obsidian_not_running"
            else:
                status["obsidian_running"] = True
                status["failure_reason"] = "cli_disabled"
    except subprocess.TimeoutExpired:
        status["cli_enabled"] = False
        status["obsidian_running"] = False
        status["failure_reason"] = "obsidian_not_running"

    return status


def open_note_via_cli(note_path: str, vault_path: Path) -> dict:
    """
    Opens an existing Obsidian note in a new tab using the Obsidian CLI.
    Does not depend on Obsidian's file watcher — uses Obsidian's internal API.

    note_path: vault-relative path WITH .md extension,
               e.g. "lit/lit_notes/Smith24someTitle.md"
    vault_path: full Path to the vault root (same convention as open_obsidian_note())

    Returns a dict with keys:
        success:       bool
        cli_output:    str — stdout from CLI call
        error:         str or None — stderr or exception message
    """
    vault_name = vault_path.name
    result_dict = {"success": False, "cli_output": "", "error": None}
    try:
        result = subprocess.run(
            ["obsidian", f"vault={vault_name}", "open",
             f"path={note_path}", "newtab"],
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
    
def open_obsidian_note(note_path: str, vault_path: Path | str | None = None, new_tab: bool = True) -> dict:
    """ Opens an Obsidian note in a new tab, if possible and requested.
          note_path: internal obsidian path from the vault root to the note (without .md)
          vault_path: Full path to the vault directory (Path object or string)
          new_tab: Whether to open in a new tab (requires Obsidian's Advanced URI plugin, 
                   with its "Open file without write in new pane" option enabled)
    
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
    
    is_installed, is_enabled = check_advanced_uri_plugin(vault_path)
    status["advanced_uri_plugin_installed"] = is_installed
    status["advanced_uri_plugin_enabled"] = is_enabled
    
    if is_installed and is_enabled:
        newpane_enabled = check_newpane_setting(vault_path)
        status["plugin_newpane_setting_enabled"] = newpane_enabled
        status["new_tab_possible"] = new_tab and newpane_enabled
    else:
        status["new_tab_possible"] = False
    
    if new_tab and status["new_tab_possible"]:
        status["method_used"] = "advanced-uri"
    else:
        status["method_used"] = "standard"
    
    try:
        vault_name_quoted = urllib.parse.quote(vault_name)
        note_path_quoted = urllib.parse.quote(note_path)
        
        if status["method_used"] == "advanced-uri":
            uri = f"obsidian://adv-uri?vault={vault_name_quoted}&filepath={note_path_quoted}&newpane=true"
        else:  # standard
            uri = f"obsidian://open?vault={vault_name_quoted}&file={note_path_quoted}"
        
        status["uri_used"] = uri
    except Exception as e:
        print(f"Error building URI: {e}")
    
    if status["note_found"] and status["uri_used"]:
        try:
            uri = status["uri_used"]
            if os.name == 'nt':  # Windows
                # Use subprocess for more reliable execution than os.system
                subprocess.run(
                    ['cmd', '/c', 'start', '', uri],
                    shell=False,
                    check=False,
                    capture_output=True
                )
            elif os.name == 'posix':  # macOS or Linux
                if Path('/proc/version').exists() and 'microsoft' in Path('/proc/version').read_text().lower():
                    subprocess.run(['cmd.exe', '/c', 'start', '', uri]) # it's Linux but WSL
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