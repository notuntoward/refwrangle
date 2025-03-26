"""Tests of the watchdog library.  It works."""

# %%
import sys
import time
from pathlib import Path

from watchdog.events import (DirMovedEvent, FileMovedEvent,
                             FileSystemEventHandler)
from watchdog.observers import Observer

refwrangle_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(refwrangle_dir))

import basic_relink as br  # pylint: disable=import-error

WATCH_DIR = Path(r"C:\Users\scott\tmp\watchpad")
DEST_DIR = Path(r"C:\Users\scott\OneDrive\share\ref\obsidian\Obsidian Share Vault\Scratch Space")

class PerplexExportRelinker(FileSystemEventHandler):
    """When a new file arrives in the WATCH_DIR, change the footnotes to URL, obsidian or zotero links.
    Save the result to self.dest_dir.  If save was successful, cleans out the WATCH_DIR.  This is expecting
    Perplexity export .md files: special handling of chrome download-in-progress file extension, which
    can trigger the handler before the file is fully downloaded."""
    
    def __init__(self, watch_dir=WATCH_DIR, dest_dir=DEST_DIR, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.watch_dir = Path(watch_dir)
        self.watch_dir.mkdir(exist_ok=True)
        self.dest_dir = Path(dest_dir)
    
    def on_moved(self, event: 'DirMovedEvent | FileMovedEvent') -> None:
        """Once file is fully downloaded to self.watch_dir (no longer .crdownload), relink and move to self.dest_dir"""
        if not getattr(event, 'is_directory', False) and not (event.dest_path.decode('utf-8') if isinstance(event.dest_path, bytes) else event.dest_path).endswith('.crdownload'):
            in_file: Path = Path(str(event.dest_path.decode('utf-8')) if isinstance(event.dest_path, bytes) else str(event.dest_path) if hasattr(event, 'dest_path') else str(event.src_path))
            out_file: Path = self.dest_dir / in_file.name
            print(f"Relinking new file:\n"
                  f"       {str(in_file)}\n"
                  f"  ---> {str(out_file)}")
            
            if in_file.exists():
                try:
                    self.dest_dir.mkdir(parents=True, exist_ok=True)
                    br.perplex_to_obs_note_file(in_file, out_file)
                except Exception as e:
                    print(f"Failed to read or write: {e}")
                    return
            if out_file.exists():
                time.sleep(1)  # small delay avoids chrome error msg   
                print(f'Cleaning out {str(self.watch_dir)}')            
                for file in self.watch_dir.rglob('*'):
                    if file.is_file():
                        file.unlink()
                            
if __name__ == "__main__":
    event_handler = PerplexExportRelinker()
    observer = Observer()
    observer.schedule(event_handler, str(event_handler.watch_dir), recursive=False)
    observer.start()

    print(f'Watching Perplexy Export Dir: {event_handler.watch_dir}  ...')
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
# %%
