async function getSelectedItemsData(items) {
    alert(`entered async function`);

    if (!items || items.length === 0) {
        Zotero.debug("No items selected.");
        return; // Silent failure, no popup
    }
    let results = [];
    for (let item of items) {
        if (!item.isRegularItem()) continue;

        const itemKey = item.key;
        const itemData = item.toJSON();

        // Extract citation key from "extra" field
        let citekey = '';
        const extraField = item.getField('extra') || '';
        const citekeyMatch = extraField.match(/^Citation Key:\s*(.+)$/m);
        if (citekeyMatch) {
            citekey = citekeyMatch[1];
        }

        alert(`just below keymatch, above bibliograpy`);
    
        // Fetch bibliography using Better BibTeX's JSON-RPC API
        let bibliography = '';
        if (citekey) {
            try {
                const response = await fetch("http://localhost:23119/better-bibtex/json-rpc", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    },
                    body: JSON.stringify({
                        jsonrpc: "2.0",
                        method: "item.bibliography",
                        params: [
                            [citekey],
                            { contentType: "text", id: "modern-language-association", locale: "en-US", quickCopy: false }
                        ]
                    })
                });
                const result = await response.json();
                if (result && result.result) {
                    bibliography = result.result;
                }
            } catch (error) {
                Zotero.debug(`Failed to fetch bibliography for citekey ${citekey}: ${error}`);
            }
        }

        // Tags
        const tags = item.getTags().map(tag => tag.tag);

        // Collections (names)
        const collectionIDs = item.getCollections();
        let collectionNames = [];
        for (let collectionID of collectionIDs) {
            let collectionObj = Zotero.Collections.get(collectionID);
            if (collectionObj) {
                collectionNames.push(collectionObj.name);
            }
        }

        alert(`just above notes`);

        // Notes (convert HTML to Markdown)
        const noteIDs = item.getNotes();
        let notes = [];
        for (let noteID of noteIDs) {
            let noteItem = Zotero.Items.get(noteID);
            if (noteItem) {
                const htmlNote = noteItem.getNote();
                notes.push(htmlNote);
                // const markdownNote = htmlToMarkdown(htmlNote);
                // notes.push(markdownNote);
            }
        }

        alert(`done with notes`);

        // Attachments
        const attachmentIDs = item.getAttachments();
        let attachments = [];
        for (let attachmentID of attachmentIDs) {
            let attachmentItem = Zotero.Items.get(attachmentID);
            if (attachmentItem && attachmentItem.isAttachment()) {
                attachments.push({
                    title: attachmentItem.getField('title'),
                    path: attachmentItem.getFilePath() || '',
                    url: attachmentItem.getField('url') || ''
                });
            }
        }

        results.push({
            title: itemData.title || '',
            citekey: citekey,
            bibliography: bibliography,
            tags: tags,
            collections: collectionNames,
            exportDate: new Date().toLocaleString(),
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
            notes: notes,
            attachments: attachments
        });
    }

    const jsonString = JSON.stringify(results, null, 2);

    // For debugging, save to the specified Windows path
    const filePath = "C:\\Users\\scott\\tmp\\zotero_item_dat.json";
    try {
        Zotero.File.putContents(filePath, jsonString);
    } catch (error) {
        console.error(error);
    }

    try {
        await fetch("http://localhost:5050", { // Send JSON to webhook listener
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: jsonString
        });
    } catch (error) {
        Zotero.debug(`Failed to send data to webhook listener on port 5050: ${error}`);
    }
}

function htmlToMarkdown(html) {
    // Handle blockquotes separately to preserve inner formatting
    html = html.replace(/<blockquote>([\s\S]*?)<\/blockquote>/g, (match, content) => {
        // Convert inner content recursively to handle nested formatting
        const innerMarkdown = htmlToMarkdown(content.trim());
        // Add '> ' at the beginning of each line
        return innerMarkdown.split('\n').map(line => '> ' + line).join('\n');
    });

    return html
        // Convert <h1> to <h6> to Markdown headers
        .replace(/<h1>(.*?)<\/h1>/g, '# $1')
        .replace(/<h2>(.*?)<\/h2>/g, '## $1')
        .replace(/<h3>(.*?)<\/h3>/g, '### $1')
        .replace(/<h4>(.*?)<\/h4>/g, '#### $1')
        .replace(/<h5>(.*?)<\/h5>/g, '##### $1')
        .replace(/<h6>(.*?)<\/h6>/g, '###### $1')
        // Convert <strong> and <em> to bold and italics
        .replace(/<strong>(.*?)<\/strong>/g, '**$1**')
        .replace(/<em>(.*?)<\/em>/g, '*$1*')
        // Convert unordered list items
        .replace(/<ul>/g, '')
        .replace(/<\/ul>/g, '')
        .replace(/<li>(.*?)<\/li>/g, '- $1')
        // Convert paragraphs and line breaks
        .replace(/<p>(.*?)<\/p>/g, '$1\n')
        .replace(/<br\s*\/?>/g, '\n')
        // Convert standard web links to Markdown format
        .replace(/<a\s+href="(https?:\/\/.*?)">(.*?)<\/a>/g, '[$2]($1)')
        // Convert Zotero item links to Markdown format
        .replace(/<a\s+href="(zotero:\/\/select\/library\/items\/.*?)">(.*?)<\/a>/g, '[$2]($1)')
        // Convert HTML highlighting (any background color) to Obsidian Markdown highlighting
        .replace(/<span style="background-color:\s*[^;]+;">(.*?)<\/span>/g, '==$1==')
        // Remove any remaining HTML tags
        .replace(/<\/?[^>]+(>|$)/g, '')
        // Trim extra spaces and lines
        .trim();
}


getSelectedItemsData(items);
