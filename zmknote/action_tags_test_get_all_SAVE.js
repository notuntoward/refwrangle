async function getSelectedItemsData(items) {
    if (!items || items.length === 0) {
        alert("No items selected.");
        return;
    }

    // Check if Better BibTeX is installed
    if (!Zotero.BetterBibTeX || !Zotero.BetterBibTeX.KeyManager) {
        alert("⚠️ Warning: The Better BibTeX plugin is not installed or enabled.\n\nThis action expects Better BibTeX to be installed for citation keys and bibliography generation. Please install and enable Better BibTeX before running this action.");
        return;
    }

    let results = [];

    for (let item of items) {
        if (!item.isRegularItem()) continue;

        const itemKey = item.key;
        const itemData = item.toJSON();

        // Citekey from Better BibTeX
        let citekey = '';
        try {
            citekey = Zotero.BetterBibTeX.KeyManager.get(item).citekey || '';
        } catch (e) {
            citekey = '';
        }

        // Tags
        const tags = item.getTags().map(tag => tag.tag);

        // Collections (names)
        const collectionIDs = item.getCollections();
        let collectionNames = [];
        for (let collectionID of collectionIDs) {
            let collectionObj = await Zotero.Collections.getAsync(collectionID);
            collectionNames.push(collectionObj.name);
        }

        // Related items
        const related_items = item.relatedItems || [];

        // Notes
        const noteIDs = item.getNotes();
        let notes = [];
        for (let noteID of noteIDs) {
            let noteItem = await Zotero.Items.getAsync(noteID);
            notes.push(noteItem.getNote());
        }

        // Attachments
        const attachmentIDs = item.getAttachments();
        let attachments = [];
        for (let attachmentID of attachmentIDs) {
            let attachmentItem = await Zotero.Items.getAsync(attachmentID);
            attachments.push({
                title: attachmentItem.getField('title'),
                path: attachmentItem.getLocalFilePath()
            });
        }

        // Bibliography from Better BibTeX API
        let bibliography = '';
        try {
            bibliography = await Zotero.BetterBibTeX.KeyManager.get(item).getBibliography();
        } catch (e) {
            bibliography = '';
        }

        results.push({
            title: itemData.title || '',
            citekey: citekey,
            tags: tags,
            collections: collectionNames,
            exportDate: new Date().toISOString(),
            desktopURI: `zotero://select/library/items/${itemKey}`,
            DOI: itemData.DOI || '',
            url: itemData.url || '',
            abstractNote: itemData.abstractNote || '',
            creators: itemData.creators || [],
            date: itemData.date || new Date().toISOString(),
            itemKey: itemKey,
            itemType: itemData.itemType || '',
            publicationTitle: itemData.publicationTitle || '',
            volume: itemData.volume || '',
            issue: itemData.issue || '',
            publisher: itemData.publisher || '',
            place: itemData.place || '',
            pages: itemData.pages || '',
            ISBN: itemData.ISBN || '',
            allTags: tags,
            relations: related_items,
            bibliography: bibliography,
            notes: notes,
            attachments: attachments
        });
    }

    const jsonString = JSON.stringify(results, null, 2);

    // Save to the specified Windows path
    const filePath = "C:\\Users\\scott\\tmp\\zotero_item_dat.json";
    try {
        Zotero.File.putContents(filePath, jsonString);
        alert(`✅ JSON data successfully saved to:\n${filePath}`);
    } catch (error) {
        console.error(error);
        alert(`❌ Failed to save JSON file:\n${error}`);
    }
}

// Execute the function using the `items` variable provided by Zotero Actions and Tags
getSelectedItemsData(items).catch(err => {
    console.error(err);
    alert(`❌ An error occurred:\n${err}`);
});
