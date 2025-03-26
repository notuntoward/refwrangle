"""Tests of the watchdog library.  It works.
TODO: delete files from watch_dir after completion, otherwise, they'll accumulate
TODO: what to do if there are more than one files there anyway?"""
# %%
import time
import sys
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from icecream import ic

refwrangle_dir = Path('~/ref/refwrangle').expanduser() # can't reliably get dir of your .ipynb 
sys.path.append(str(refwrangle_dir))
import refwrangle as rfw
import basic_relink as br

(WATCH_DIR := Path(r"C:\Users\scott\tmp\watchpad")).mkdir(parents=True, exist_ok=True)
(DEST_DIR := Path(r"C:\Users\scott\OneDrive\share\ref\obsidian\Obsidian Share Vault\Scratch Space")).mkdir(parents=True, exist_ok=True)

class PerplexExportRelinker(FileSystemEventHandler):
    """When a new file arrives in the WATCH_DIR, change the footnotes to URL, obsidian or zotero links.
    Save the result to DEST_DIR."""
    
    def on_created(self, event):
        if not event.is_directory:
            #print(f"New file created: {event.src_path}")
            
            in_file = Path(event.src_path)
            out_file = DEST_DIR / Path(event.src_path).name
            ic(in_file, in_file.exists(), out_file)
            br.perplex_to_obs_note_file(in_file, out_file)

if __name__ == "__main__":
    event_handler = PerplexExportRelinker()
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIR, recursive=False)
    observer.start()

    print(f'Watching Perplexy Export Dir: {WATCH_DIR}  ...')
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()