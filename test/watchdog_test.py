"""Tests of the watchdog library.  It works."""

# %%
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

refwrangle_dir = Path('~/ref/refwrangle').expanduser()
import sys
sys.path.append(str(refwrangle_dir))
import basic_relink as br

(WATCH_DIR := Path(r"C:\Users\scott\tmp\watchpad")).mkdir(parents=True, exist_ok=True)
(DEST_DIR := Path(r"C:\Users\scott\OneDrive\share\ref\obsidian\Obsidian Share Vault\Scratch Space")).mkdir(parents=True, exist_ok=True)

class PerplexExportRelinker(FileSystemEventHandler):
    """When a new file arrives in the WATCH_DIR, change the footnotes to URL, obsidian or zotero links.
    Save the result to DEST_DIR.  If save was successful, cleans out the WATCH_DIR.  This is expecting
    Perplexity export .md files: special handling of chrome download-in-progress file extension, which
    can trigger the handler before the file is fully downloaded."""
    
    def on_moved(self, event: 'DirMovedEvent | FileMovedEvent') -> None:
        """Once file is fully downloaded to WATCH_DIR (no longer .crdownload), relink and move to DEST_DIR"""
        if not getattr(event, 'is_directory', False) and not event.dest_path.endswith('.crdownload'):
            in_file: Path = Path(event.dest_path if hasattr(event, 'dest_path') else event.src_path)
            out_file: Path = DEST_DIR / in_file.name
            print(f"Relinking new file:\n"
                  f"       {str(in_file)}\n"
                  f"  ---> {str(out_file)}")
            if in_file.exists():
                try:
                    br.perplex_to_obs_note_file(in_file, out_file)
                except Exception as e:
                    print(f"Failed to read or write: {e}")
                    return
            if out_file.exists():
                time.sleep(1)  # small delay avoids chrome error msg   
                print(f'Cleaning out {str(WATCH_DIR)}')            
                for file in WATCH_DIR.rglob('*'):
                    if file.is_file():
                        file.unlink()
                            
if __name__ == "__main__":
    event_handler = PerplexExportRelinker()
    observer = Observer()
    observer.schedule(event_handler, str(WATCH_DIR), recursive=False)
    observer.start()

    print(f'Watching Perplexy Export Dir: {WATCH_DIR}  ...')
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()