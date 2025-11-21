import zipfile
import os

# The directory containing the add-on files
source_dir = 'zotero-obsidian-plugin'

# The name of the output XPI file
xpi_name = 'zotero-obsidian-exporter.xpi'

with zipfile.ZipFile(xpi_name, 'w', zipfile.ZIP_DEFLATED) as xpi:
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            # The path of the file to be added to the zip
            file_path = os.path.join(root, file)
            # The path of the file within the zip (relative to the source_dir)
            archive_path = os.path.relpath(file_path, source_dir)
            xpi.write(file_path, archive_path)

print(f"Successfully created {xpi_name}")
