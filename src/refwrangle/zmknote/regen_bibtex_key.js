// Regenerate BibTeX keys for all selected items in Zotero.
// Requires the Better BibTeX. plugin.
// Will overwrite pinned keys.

// Regenerate BibTeX key for selected items (Better BibTeX)
await Zotero.BetterBibTeX.ready;

const items = Zotero.getActiveZoteroPane().getSelectedItems();
if (!items.length) {
  return;
}

for (const item of items) {
  if (!item.isRegularItem()) continue;

  // Remove any pinned citation key from the Extra field
  const extra = item.getField('extra') || '';
  const newExtra = extra
    .split('\n')
    .filter(line => !/^citation key\s*:/i.test(line))
    .join('\n')
    .trim();
  item.setField('extra', newExtra);
  await item.saveTx();
}

// Now trigger BBT to regenerate keys for selected items
Zotero.BetterBibTeX.KeyManager.refresh('selected', true);
