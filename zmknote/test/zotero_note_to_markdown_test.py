"""Uses the obsidian content generating functions in the webhook listener to create obsidian stuff, based on file input, rather than having to rely on a webhook."""

from bs4 import BeautifulSoup
import json
from urllib.parse import unquote
import pathlib as pl
import sys

import zotero_to_obsidian_note_listener as zol

# Define paths and credentials
refwrangle_dir = pl.Path('~/ref/refwrangle').expanduser()
sys.path.append(str(refwrangle_dir))
import refwrangle as rfw  # Import your custom refwrangle module


if __name__ == '__main__':

    # Test with a sample JSON fed to a webhook listener. Assume it's for a zotero entry.
    test_dat_dir = pl.Path(r"C:\Users\scott\OneDrive\share\ref\refwrangle\zmknote\dat")
    #test_json_input_file = test_dat_dir / "zotero_item_date_YK4TVDBM.json"
    #test_json_input_file = test_dat_dir / "zotero_item_date_LWXDDZCG.json"
    test_json_input_file = pl.Path(r"C:\Users\scott\tmp\zotero_item_dat.json")
    data = json.loads(test_json_input_file.read_text(encoding="utf-8"))

    if isinstance(data, list):
        #item_jsons = [dict(item) for item in data]  # Convert each top-level element into a dict
        # assume it's a single zotero item, so only one json in the list
        note_html = data[0]['notes'][0]
        #print("REMOVED DIV REMOVAL")
        #note_html = "\n".join(note_html.splitlines()[1:]) # remove mystery <div> @ top
    else:
        raise ValueError('expected a list')

        
    #obsidian_md = zotero_note_html_to_md(note_html)
    obsidian_md = zol.zotero_note_html_to_md(note_html)

    # Save the result to a file to avoid tab/space confusion
    outfile = pl.Path(r"C:\Users\scott\OneDrive\share\ref\obsidian\Obsidian Share Vault\Scratch Space\zotero_to_obsidian_note_output.md")
    with open(outfile, "w", encoding="utf-8") as f:
        f.write(obsidian_md)

    print(f"Conversion complete! Output saved to {outfile}")

    # Also print to console for reference
    print("\n--- CONVERTED OUTPUT ---\n")
    print(obsidian_md)
