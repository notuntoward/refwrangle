import zipfile
import os

with zipfile.ZipFile('zotero-obsidian-exporter.xpi', 'w', zipfile.ZIP_DEFLATED) as xpi:
    xpi.write('zotero-obsidian-plugin/README.md', 'README.md')
    xpi.write('zotero-obsidian-plugin/bootstrap.js', 'bootstrap.js')
    xpi.write('zotero-obsidian-plugin/zotero-obsidian-exporter.js', 'zotero-obsidian-exporter.js')
    xpi.write('zotero-obsidian-plugin/icons/icon-16.png', 'icons/icon-16.png')
    xpi.write('zotero-obsidian-plugin/icons/icon-48.png', 'icons/icon-48.png')
    xpi.write('zotero-obsidian-plugin/lib/nunjucks.min.js', 'lib/nunjucks.min.js')
    xpi.write('manifest.json', 'manifest.json')