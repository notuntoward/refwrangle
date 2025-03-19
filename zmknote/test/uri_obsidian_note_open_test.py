"""Tests the Obsidian Advanced URI plugin's ability to open a note in a new tab.

It works!

NOTE: When the advanced URI plugin is installed and has the right options, this will open each note in a new tab.
Without that, it will back off to the default obsidian URI, which will reuse an existing for the new note."""

import json
import urllib.parse
import subprocess
from pathlib import Path

def check_advanced_uri_plugin(vault_path: Path) -> tuple[bool, bool]:
    """ Checks if the Advanced URI plugin is installed and enabled.
        vault_path: Path to the Obsidian vault, including the vault name itself
        
        Return: tuple: (is_installed, is_enabled)"""
    # Plugin ID for Advanced URI
    plugin_id = "obsidian-advanced-uri"
    
    # Path to plugins directory and community plugins list
    plugins_dir = vault_path / ".obsidian" / "plugins"
    community_plugins_file = vault_path / ".obsidian" / "community-plugins.json"
    
    # Check if plugin directory exists (installed)
    plugin_dir = plugins_dir / plugin_id
    is_installed = plugin_dir.is_dir()
    
    # Check if plugin is enabled
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
        
        Return: bbool: True if the setting is enabled, False otherwise"""
        
    # Path to Advanced URI plugin's data.json file
    plugin_data_path = vault_path / ".obsidian" / "plugins" / "obsidian-advanced-uri" / "data.json"
    
    # Check if the file exists
    if not plugin_data_path.exists():
        print(f"Advanced URI plugin data file not found at: {plugin_data_path}")
        return False
    
    # Read and parse the plugin's data.json file
    try:
        with plugin_data_path.open('r') as f:
            plugin_data = json.load(f)
            
        # Check if the openFileWithoutWriteInNewPane setting is enabled
        return plugin_data.get("openFileWithoutWriteInNewPane", False)
            
    except Exception as e:
        print(f"Error reading Advanced URI plugin settings: {e}")
        return False

def find_vault_path(vault_name: str) -> Path | None:
    """Attempts to find the path to an Obsidian vault based on its name.
        vault_name: Name of the Obsidian vault
        
    Returns: Path: Path to the vault if found, None otherwise """
    
    home = Path.home()
    # Try common Obsidian vault locations
    possible_locations = [
        home / "Documents" / vault_name,
        home / vault_name,
        home / "Obsidian Vaults" / vault_name
    ]
    
    for loc in possible_locations:
        if loc.exists():
            return loc
    
    return None

def open_obsidian_note(note_path: str, vault_path: Path | str | None = None, new_tab: bool = True, vault_name: str | None = None):
    """ Opens a specific note in Obsidian, with fallback to standard URI if Advanced URI plugin isn't available.
        note_path: internal obsidian path from the vault root to the note (without .md extension)
        vault_path: Full path to the vault directory (Path object or string)
        new_tab: Whether to open in a new tab (requires Advanced URI plugin 
                 with option "Open file without write in new pane enabled" )
        vault_name: Optional override for vault name (if different from the bottom directory in the vault_path)
    
        Returns: dict: Status information about the operation """
        
    result = {
        "success": True,
        "new_tab_requested": new_tab,
        "new_tab_possible": False,
        "plugin_installed": False,
        "plugin_enabled": False,
        "newpane_setting_enabled": False,
        "method_used": "standard",
        "vault_found": False,
        "uri_used": ""
    }
    
    # Convert vault_path to Path object if it's a string
    if vault_path and isinstance(vault_path, str):
        vault_path = Path(vault_path)
    
    # Determine vault name and path
    if vault_path:
        # Extract vault name from path if not explicitly provided
        if not vault_name:
            vault_name = vault_path.name
        result["vault_found"] = vault_path.exists()
    elif vault_name:
        # Try to find vault path from name
        vault_path = find_vault_path(vault_name)
        result["vault_found"] = vault_path is not None
    else:
        raise ValueError("Either vault_path or vault_name must be provided")
    
    # Only check for Advanced URI plugin if new_tab is requested
    if new_tab and vault_path and result["vault_found"]:
        # Check if Advanced URI plugin is installed and enabled
        is_installed, is_enabled = check_advanced_uri_plugin(vault_path)
        result["plugin_installed"] = is_installed
        result["plugin_enabled"] = is_enabled
        
        # Check if newpane setting is enabled
        if is_installed and is_enabled:
            newpane_enabled = check_newpane_setting(vault_path)
            result["newpane_setting_enabled"] = newpane_enabled
            
            # Determine if new tab is possible
            result["new_tab_possible"] = is_installed and is_enabled and newpane_enabled
    
    # URL encode the parameters
    vault = urllib.parse.quote(vault_name)
    file_name = urllib.parse.quote(note_path)
    
    # Determine which URI to use
    if new_tab and result["new_tab_possible"]:
        # Advanced URI plugin syntax to open in new tab
        uri = f"obsidian://adv-uri?vault={vault}&filepath={file_name}&newpane=true"
        result["method_used"] = "advanced-uri"
        
        # Print informative message
        print("Using Advanced URI to open note in new tab")
        print(f"Advanced URI plugin installed: {result['plugin_installed']}")
        print(f"Advanced URI plugin enabled: {result['plugin_enabled']}")
        print(f"'Open file without write in new pane' enabled: {result['newpane_setting_enabled']}")
    else:
        # Standard Obsidian URI
        uri = f"obsidian://open?vault={vault}&file={file_name}"
        result["method_used"] = "standard"
        
        # Print informative message
        if new_tab and not result["new_tab_possible"]:
            print("Warning: Cannot open in new tab due to missing requirements.")
            if not result["vault_found"]:
                print("  - Vault path not found")
            elif not result["plugin_installed"]:
                print("  - Advanced URI plugin not installed")
            elif not result["plugin_enabled"]:
                print("  - Advanced URI plugin not enabled")
            elif not result["newpane_setting_enabled"]:
                print("  - 'Open file without write in new pane' setting not enabled")
            print("Falling back to standard Obsidian URI (note will open in current tab)")
        else:
            print("Using standard Obsidian URI to open note")
    
    # Store the URI used
    result["uri_used"] = uri
    
    # Open the URI using the appropriate method based on OS
    try:
        import os
        if os.name == 'nt':  # Windows
            os.system(f'start "" "{uri}"')
        elif os.name == 'posix':  # macOS or Linux
            if Path('/proc/version').exists() and 'microsoft' in Path('/proc/version').read_text().lower():
                # WSL detection
                os.system(f'cmd.exe /c start "" "{uri}"')
            elif Path('/System').exists():  # macOS
                subprocess.run(['open', uri])
            else:  # Linux
                subprocess.run(['xdg-open', uri])
    except Exception as e:
        print(f"Error opening URI: {e}")
        result["success"] = False
    
    return result

def explain_result():
    

# Example usage
if __name__ == "__main__":
    # Both of these formats are supported
    
    # Option 1: Provide just the vault path (name is extracted automatically)
    # open several notes so can verify that new tab for each note works
    
    vault_path = Path(r"C:\Users\scott\OneDrive\share\ref\obsidian\Obsidian Share Vault")
    result = open_obsidian_note("All Tasks Summary", vault_path=vault_path, new_tab=True)
    result = open_obsidian_note( "lit/lit_notes/Coursera24SQLVsNoSQLdiffExplain", vault_path=vault_path, new_tab=True)
    result = open_obsidian_note( "lit/lit_notes/Atrioc25teslaBacklashBiblical", vault_path=vault_path, new_tab=True)
    
    # Option 2: Provide both vault path and explicit name (if folder name differs from vault name)
    # vault_path = Path("C:/Users/YourName/Documents/ObsidianVaults/Shared")
    # result = open_obsidian_note("All Tasks Summary", new_tab=True, vault_path=vault_path, vault_name="Obsidian Share Vault")    

    # It won't open a note at all if this isn't true
    import icecream
    ic(result['success'])
    # and won't make a new tab for each note if this isn't true
    ic(result['new_tab_possible'])
    # reasons for it not to be possible are if any of these are false
    new_tab_required_tube['plugin_installed','plugin_enabled']
    ic(result['plugin_installed'], result['plugin_enabled'], )
    
    new_tab_required_tube = ['plugin_installed','plugin_enabled']

{'success': True,
 'new_tab_requested': True,
 'new_tab_possible': True,
 'plugin_installed': True,
 'plugin_enabled': True,
 'newpane_setting_enabled': True,
 'method_used': 'advanced-uri',
 'vault_found': True,
 'uri_used':    
