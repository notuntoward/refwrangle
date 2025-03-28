"""Tests of the watchdog library.  It works."""

# %%
import sys
import time
from pathlib import Path
from typing import Union

from watchdog.events import FileSystemEventHandler, FileCreatedEvent, DirCreatedEvent, FileModifiedEvent, DirModifiedEvent
from watchdog.observers import Observer
from icecream import ic

# Add refwrangle_dir to sys.path for importing basic_relink
refwrangle_dir = Path("~/ref/refwrangle").expanduser()
sys.path.append(str(refwrangle_dir))
import basic_relink as br  # pylint: disable=import-error

# Input files to be relinked are expected here
WATCH_DIR = Path(r"C:\Users\scott\tmp\watchpad")
# Relinked output files are put here
DEST_DIR = Path(r"C:\Users\scott\OneDrive\share\ref\obsidian\Obsidian Share Vault\Scratch Space")

class PerplexExportRelinker(FileSystemEventHandler):
    """When a new file arrives in the self.watch_dir, change the footnotes to URL, obsidian or zotero links.
    Save the result to self.dest_dir. If save was successful, cleans out the self.watch_dir. This is expecting
    Perplexity export .md files: special handling of chrome download-in-progress file extension, which
    can trigger the handler before the file is fully downloaded."""

    def __init__(self, watch_dir: Union[str, Path] = WATCH_DIR, dest_dir: Union[str, Path] = DEST_DIR, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.watch_dir: Path = Path(watch_dir)
        self.watch_dir.mkdir(exist_ok=True)
        self.dest_dir: Path = Path(dest_dir)
        self.processing = False

    def relink_file(self, in_file: Path) -> None:
        """Relink and move the file to the destination directory."""
        
        if self.processing:
            # Try to avoid disruptions due to multiple calls for same file, while already working on it.
            return

        self.processing = True

        out_file = self.dest_dir / in_file.name
        if in_file.exists():
            try:
                self.dest_dir.mkdir(parents=True, exist_ok=True)
                br.perplex_to_obs_note_file(in_file, out_file)
                print(f"Relinking new file:\n"
                    f" {in_file}\n"
                    f" ---> {out_file}")
            except Exception as e:
                print(f"Failed to read, relink, or write: {e}")
                self.processing = False
                return

            # Clear out watch_dir after successful relinking to new location
            time.sleep(1)  # Small delay avoids Chrome error messages
            print(f'Cleaning out all of {self.watch_dir}')
            for file in self.watch_dir.rglob('*'):
                if file.is_file():
                    try:
                        file.unlink()
                    except Exception as e:
                        print(f"Failed to delete file {file}: {e}")

        self.processing = False

    def on_created(self, event: Union[DirCreatedEvent, FileCreatedEvent]) -> None:
        """When a new file is created."""
        if not event.is_directory:
            file_path = Path(str(event.src_path))
            if file_path.suffix != '.crdownload':
                # it's not a tmp file written by chrome browsers while still downloading.
                self.relink_file(file_path)

                            
if __name__ == "__main__":
    perplexity_relinker = PerplexExportRelinker()
    observer = Observer()
    observer.schedule(perplexity_relinker, str(perplexity_relinker.watch_dir), recursive=False)
    observer.start()

    print(f'Watching Perplexy Export Dir: {perplexity_relinker.watch_dir}  ...')
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()