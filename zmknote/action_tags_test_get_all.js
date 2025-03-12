async function getSelectedItemsData(items) {
    // Ensure items are passed to the script
    if (!items || items.length === 0) {
        Zotero.debug("No items selected.");
        return; 
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

        // Notes (convert HTML to Markdown)
        const noteIDs = item.getNotes();
        let notes = [];
        for (let noteID of noteIDs) {
            let noteItem = Zotero.Items.get(noteID);
            if (noteItem) {
                const htmlNote = noteItem.getNote();
                // TODO: figure out why internal links to zotero notes don't work
                const markdownNote = htmlToMarkdown(htmlNote);
                notes.push(markdownNote);
            }
        }

        // Attachments
        const attachmentIDs = item.getAttachments();
        let attachments = [];
        for (let attachmentID of attachmentIDs) {
            let attachmentItem = Zotero.Items.get(attachmentID);
            if (attachmentItem && attachmentItem.isAttachment()) {
                attachments.push({
                    title: attachmentItem.getField('title'),
                    path: attachmentItem.getFilePath() || '', // Get file path if available
                    url: attachmentItem.getField('url') || '' // Include URL if available
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
    try {
        const filePathString = "C:\\Users\\scott\\tmp\\zotero_item_dat.json";
        
        const file = Components.classes["@mozilla.org/file/local;1"]
                                .createInstance(Components.interfaces.nsIFile);
        
        file.initWithPath(filePathString);

        if (!file.parent.exists()) {
            file.parent.create(Components.interfaces.nsIFile.DIRECTORY_TYPE, 0o777);
        }

        Zotero.File.putContents(file, jsonString);
        
    } catch (error) {
      Zotero.debug(error);
    }

    // webhook output
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
      const innerMarkdown = htmlToMarkdown(content.trim());
      return innerMarkdown.split('\n').map(line => '> ' + line).join('\n');
    });
  
    // Convert Zotero internal links correctly to Markdown with citekey
    html = html.replace(/<a[^>]+href="zotero:\/\/select\/library\/items\/([^"]+)"[^>]*>(.*?)<\/a>/g,
      (match, itemKey, originalLinkText) => {
        const linkedItem = Zotero.Items.getByLibraryAndKey(Zotero.Libraries.userLibraryID, itemKey);
        let citekey = originalLinkText; // Default to original link text
        if (linkedItem) {
          const extraField = linkedItem.getField('extra') || '';
          const citekeyMatch = extraField.match(/^Citation Key:\s*(.+)$/m);
          if (citekeyMatch && citekeyMatch[1]) {
            citekey = citekeyMatch[1]; // Use the extracted citation key if available
          }
        }
        return `[${citekey}](zotero://select/library/items/${itemKey})`;
      }
    );
  
    // Convert standard web links correctly without extra attributes
    html = html.replace(/<a[^>]+href="([^"]+)"[^>]*>(.*?)<\/a>/g, '[$2]($1)');
  
    return html
      .replace(/<h1>(.*?)<\/h1>/g, '# $1')
      .replace(/<h2>(.*?)<\/h2>/g, '## $1')
      .replace(/<h3>(.*?)<\/h3>/g, '### $1')
      .replace(/<h4>(.*?)<\/h4>/g, '#### $1')
      .replace(/<h5>(.*?)<\/h5>/g, '##### $1')
      .replace(/<h6>(.*?)<\/h6>/g, '###### $1')
      .replace(/<(b|strong)>(.*?)<\/\1>/g, '**$2**')
      .replace(/<(i|em)>(.*?)<\/\1>/g, '*$2*')
      .replace(/<ul>/g, '')
      .replace(/<\/ul>/g, '')
      .replace(/<li>(.*?)<\/li>/g, '- $1')
      .replace(/<p>(.*?)<\/p>/g, '$1\n')
      .replace(/<br\s*\/?>/gi, '\n')
      // Convert highlights to Obsidian Markdown highlighting
      .replace(/<span[^>]*?style="background-color:[^"]*"[^>]*>(.*?)<\/span>/gi, '==$1==')
      // Remove any remaining HTML tags
      .replace(/<\/?[^>]+(>|$)/g, '')
      .trim();
  }
  
  


getSelectedItemsData(items);
