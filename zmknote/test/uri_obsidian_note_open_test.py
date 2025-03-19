"""Tests the Obsidian Advanced URI plugin's ability to open a note in a new tab."""

import subprocess
import urllib.parse
import os

def open_obsidian_note(vault_name, note_path, new_tab=True):
    """
    Opens a specific note in Obsidian on Windows.
    
    Args:
        vault_name: Name of the Obsidian vault
        note_path: Path to the note (without .md extension)
        new_tab: Whether to open in a new tab (requires Advanced URI plugin)
    """
    # URL encode the parameters
    vault = urllib.parse.quote(vault_name)
    file_path = urllib.parse.quote(note_path)
    
    if new_tab:
        # Advanced URI plugin syntax to open in new tab
        uri = f"obsidian://adv-uri?vault={vault}&filepath={file_path}&newpane=true"
    else:
        # Standard Obsidian URI
        uri = f"obsidian://open?vault={vault}&file={file_path}"
    
    # For Windows, use os.system with quotes to handle special characters like &
    os.system(f'start "" "{uri}"')

# Example usage
open_obsidian_note("Obsidian Share Vault", "lit/lit_notes/Coursera24SQLVsNoSQLdiffExplain", new_tab=True)
# open_obsidian_note("Obsidian Share Vault", "All Tasks Summary", new_tab=True)
