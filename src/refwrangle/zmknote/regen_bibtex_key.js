// Regenerate BibTeX keys for all selected items in Zotero.
// Requires the Better BibTeX plugin.
// Selected items are passed via the `items` variable by the host plugin.
//
// For each item:
//   - BBT generates a proposed key (NOT written to Zotero)
//   - A system-modal dialog appears (autoraise-safe) with the proposed key
//   - Enter / OK writes the key to Zotero's citationKey field
//   - Escape / Cancel leaves the key unchanged and stops iteration;
//     keys already saved in previous iterations remain saved
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

  await item.reload();
  const oldKey = item.getField('citationKey') || '';

  // `propose()` is synchronous and returns a string (or falsy if no key).
  // It computes a candidate key without touching Zotero's database.
  const proposedKey = Zotero.BetterBibTeX.KeyManager.propose(item) || '';

  // Show the proposed key in a modal prompt; the field is pre-selected so
  // typing replaces it, and arrow keys move the cursor.
  const keyRef = { value: proposedKey };
  const accepted = Services.prompt.prompt(
    null,
    'Edit Citation Key',
    `${item.getField('title')}\n\nProposed key:`,
    keyRef,
    null,
    {}
  );

  if (!accepted) {
    // Cancel / Escape: leave the existing key unchanged, stop iterating.
    break;
  }

  // Only write back if the user actually changed something.
  const finalKey = keyRef.value;
  if (finalKey && finalKey !== oldKey) {
    item.setField('citationKey', finalKey);
    await item.saveTx({ skipDateModifiedUpdate: true });
  }

  // Give BBT's background scheduler a moment to breathe before
  // showing the next prompt, otherwise the notifier-driven
  // auto-fill can delay or starve the event loop.
  await Zotero.Promise.delay(100);
}
