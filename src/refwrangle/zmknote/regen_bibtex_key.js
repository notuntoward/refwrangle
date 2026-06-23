// Regenerate BibTeX keys for all selected items in Zotero.
// Requires the Better BibTeX plugin.
// Will overwrite pinned keys.
// Selected items are passed via the `items` variable by the host plugin.

await Zotero.BetterBibTeX.ready;

if (!items || !items.length) {
  return;
}

// Pass concrete IDs to avoid BBT's internal call that triggers the warning
const ids = Array.isArray(items) ? items.map(i => i.id) : [items.id];
await Zotero.BetterBibTeX.KeyManager.fill(ids, { replace: true });

