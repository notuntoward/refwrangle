/* This is the zotero side of a webhook interface between zotero items and a python webhook message receiver, 
which writes one or more obsidian literature notes. The job here is to get and send the necessary item data.

The companion python script for this one is zotero_to_obsidian_note_receiver_test.py */

// The webhook sending port, match the Python side's LISTEN_PORT
const SEND_PORT = 5050;

// this ID tells the receiver who sent the message (and what to do wih it)
const SENDER_ID_ZOTERO_TO_OBSIDIAN_NOTE  = 'zotero_to_obsidian_note'

// how long the webhook interface will wait before a zotero popup error
// s/b a fair amount longer than python's RECEIVER_BUTTON_WAIT_SECS  
const RECEIVER_RESPONSE_WAIT_TIMEOUT_SECS = 60 // seconds

// the name of the script receiving the webhook message, and writing the lit note
const RECEIVER_PROGRAM_NAME = "'zotero_to_obsidian_note_receiver'"

// Global request tracking
if (typeof Zotero.ZoteroWebhookLock === 'undefined') {
    Zotero.ZoteroWebhookLock = {
        inProgress: false,
        requestId: null,
        lastRequestTime: 0
    };
}

// Ensure the script uses `item` or `items` variables passed by Zotero
// Prevent duplicate processing using a global lock mechanism
if (Zotero.ZoteroWebhookLock.inProgress) {
    Zotero.debug("Already processing a webhook request, ignoring duplicate call");
    return;
}

// Additional time-based throttling
const now = Date.now();
if (now - Zotero.ZoteroWebhookLock.lastRequestTime < 1000) {
    Zotero.debug("Request too soon after previous request, ignoring to prevent duplicates");
    return;
}

// Set processing lock, again to avoid duplicates, which were a stubborn problem.
Zotero.ZoteroWebhookLock.inProgress = true;
Zotero.ZoteroWebhookLock.lastRequestTime = now;
Zotero.ZoteroWebhookLock.requestId = Math.random().toString(36).substring(2, 10);

try {
    // Collect all selected items into an array
    let selectedItems = [];
    if (item) {
        // Single item selected
        selectedItems.push(item);
    } else if (items && items.length > 0) {
        // Multiple items selected
        selectedItems = items;
    } else {
        Zotero.alert(null, "Error", "No item selected.");
        Zotero.ZoteroWebhookLock.inProgress = false;
        return;
    }
    
    // Put item data into a JSON message strucure

    let itemDataArray = [];
    for (let item of selectedItems) {
        let itemkey = item.key; // zotero item key

        const extraField = item.getField('extra') || '';
        let citekeyMatch = extraField.match(/Citation Key:\s*(.+)/);
        if (!citekeyMatch) {
            Zotero.debug(`Better Bibtex Citation Key not found in 'extra' field of selected zotero item key: ${itemkey}`);
            continue;
        }
        let citekey = citekeyMatch[1];
    
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
                    
                    // Remove URLs (http://, https://)
                    bibliography = bibliography.replace(/https?:\/\/\S+/g, '');
                    
                    // Remove other URLs (www.something.com style)
                    bibliography = bibliography.replace(/www\.\S+/g, '');
                    
                    // Remove DOIs (doi.org pattern)
                    bibliography = bibliography.replace(/doi\.org\/\S+/g, '');
                    
                    // Remove trailing commas and spaces before a period
                    bibliography = bibliography.replace(/,\s*\./g, '.');
                    
                    // Remove trailing comma at end of string and replace with period
                    bibliography = bibliography.replace(/,\s*$/g, '.');
                    
                    // Remove orphaned commas
                    bibliography = bibliography.replace(/,\s+,/g, ',');
                    bibliography = bibliography.replace(/,\s*\./g, '.');
                    
                    // Clean up multiple spaces
                    bibliography = bibliography.replace(/\s+/g, ' ').trim();
                }
            } catch (error) {
                Zotero.debug(`Failed to fetch bibliography for citekey ${citekey}: ${error}`);
            }
        }

        // item tags: for now.  Obsidian will store separately from its own tags.
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

        // item notes (they're in html)
        const noteIDs = item.getNotes();
        let notes = [];
        for (let noteID of noteIDs) {
            let noteItem = Zotero.Items.get(noteID);
            if (noteItem) {
                const htmlNote = noteItem.getNote();
				notes.push(htmlNote);
            }
        }

        // item attachments
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

        // load this item's payload structure
        const itemData = item.toJSON();
        itemDataArray.push({
            title: itemData.title || '',
            citekey: citekey,
            bibliography: bibliography,
            tags: tags,
            collections: collectionNames,
            exportDate: new Date().toLocaleString(),
            desktopURI: `zotero://select/library/items/${itemkey}`,
            DOI: itemData.DOI || '',
            url: itemData.url || '',
            abstractNote: itemData.abstractNote || '',
            creators: itemData.creators || [],
            date: itemData.date || new Date().toISOString(),
            itemkey: itemkey,
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
    
    // Only send if we have at least one valid item
    if (itemDataArray.length > 0) {
        // Send data to webhook (once!)
        sendToWebhook(itemDataArray, Zotero.ZoteroWebhookLock.requestId);
    } else {
        Zotero.alert(null, "Error", "No valid items with citkeys found.");
        Zotero.ZoteroWebhookLock.inProgress = false;
    }
} catch (e) {
    Zotero.debug("Error in webhook script: " + e);
    Zotero.ZoteroWebhookLock.inProgress = false;
}

function sendToWebhook(itemDataArray, requestId) {
    const webhookUrl = `http://localhost:${SEND_PORT}/webhook`;
    Zotero.debug(`Sending webhook request ${requestId} with ${itemDataArray.length} items`);

    let timeoutId = null;
    let requestCompleted = false;
    
    timeoutId = setTimeout(function() {
        if (!requestCompleted) {
            Zotero.debug(`Webhook request timed out after ${RECEIVER_RESPONSE_WAIT_TIMEOUT_SECS} seconds`);
            Zotero.alert(null, "Webhook Warning", `The receiving server did not respond within ${RECEIVER_RESPONSE_WAIT_TIMEOUT_SECS} seconds (timeout). Is ${RECEIVER_PROGRAM_NAME} running?`);
            Zotero.ZoteroWebhookLock.inProgress = false;
        }
    }, RECEIVER_RESPONSE_WAIT_TIMEOUT_SECS * 1000);
    
    const payload = {sender_id: SENDER_ID_ZOTERO_TO_OBSIDIAN_NOTE,
                     data: itemDataArray};

    fetch(webhookUrl, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-Request-ID": requestId
        },
        body: JSON.stringify(payload)
    })
    .then(response => {
        requestCompleted = true;
        clearTimeout(timeoutId);
        if (response.ok) {
            Zotero.debug(`Webhook response: ${response.statusText}`);
        } else {
            Zotero.debug(`Webhook error status: ${response.status}`);
            Zotero.alert(null, "Webhook Warning", `The webhook receiver responded with an error. Is ${RECEIVER_PROGRAM_NAME} running? : ${response.status} ${response.statusText}`);
        }
        Zotero.ZoteroWebhookLock.inProgress = false;
    })
    .catch(error => {
        requestCompleted = true;
        clearTimeout(timeoutId);
        Zotero.debug(`Webhook error: ${error.message}`);
        Zotero.alert(null, "Webhook Warning", `The receiving server did not respond. Is ${RECEIVER_PROGRAM_NAME} running? : ${error.message}`);
        Zotero.ZoteroWebhookLock.inProgress = false;
    });
}