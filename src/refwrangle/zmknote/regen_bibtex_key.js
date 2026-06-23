// Regenerate BibTeX keys for all selected items in Zotero.
// Requires the Better BibTeX plugin.
// Selected items are passed via the `items` variable by the host plugin.
//
// For each item:
//   - BBT regenerates the citation key
//   - A system-modal dialog appears (autoraise-safe) with the key pre-filled
//   - Enter / OK saves the key (whether edited or accepted as-is)
//   - Escape / Cancel stops iteration; the current regenerated key is kept
//     and any keys saved in previous iterations remain saved
//
// The prompt uses a null parent (system-modal) so Windows autoraise
// does not bury it behind another window.

if (!Zotero.BetterBibTeX) {
  Zotero.warn('Better BibTeX is not installed. Cannot regenerate keys.');
  return;
}

await Zotero.BetterBibTeX.ready;

// Normalize to an array — Actions & Tags may pass a single item or an array
const selectedItems = Array.isArray(items) ? items : (items ? [items] : []);
if (!selectedItems.length) {
  return;
}

for (const item of selectedItems) {
  if (!item.isRegularItem()) continue;

  // Regenerate via BBT (writes into Zotero's citationKey field)
  await Zotero.BetterBibTeX.KeyManager.fill([item.id], { replace: true });
  await item.reload();

  const key = item.getField('citationKey') || '';

  // System-modal prompt (parent=null keeps it above autoraising windows)
  const keyRef = { value: key };
  const accepted = Services.prompt.prompt(
    null,
    'Edit Citation Key',
    `${item.getField('title')}\n\nCitation key:`,
    keyRef,
    null,
    {}
  );

  // Cancel / Escape → stop processing further items
  if (!accepted) {
    break;
  }

  // Save only if the user changed the key
  if (keyRef.value !== key) {
    item.setField('citationKey', keyRef.value);
    await item.saveTx();
  }
}
