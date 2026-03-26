/* This is the zotero side of a webhook interface between zotero items and a python webhook message receiver, 
which writes one or more obsidian literature notes. The job here is to get and send the necessary item data.

The companion python script for this one is zotero_to_obsidian_note_receiver.py */

// The webhook sendtoing port, match the Python side's LISTEN_PORT
const SEND_PORT = 5050;

// this ID tells the receiver who sent the message (and what to do wih it)
const SENDER_ID_NEW_OBSIDIAN_NOTE  = 'new_obsidian_note_from_zotero'

// how long the webhook interface will wait before a zotero popup error
// s/b a fair amount longer than python's RECEIVER_BUTTON_WAIT_SECS  
const RECEIVER_RESPONSE_WAIT_TIMEOUT_SECS = 60 // seconds

// the name of the script receiving the webhook message, and writing the lit note
const RECEIVER_PROGRAM_NAME = "'zotero_to_obsidian_note_receiver'"

/**
 * Validates a citation key for use as a filename across Windows, macOS, and Linux.
 * Returns an object with 'valid' boolean and 'reason' string if invalid.
 * 
 * @param {string} citekey - The citation key to validate
 * @returns {{valid: boolean, reason: string|null}}
 */
function validateCitationKey(citekey) {
    if (!citekey || typeof citekey !== 'string') {
        return { valid: false, reason: 'Citation key is empty or not a string' };
    }
    
    // Check for empty string
    if (citekey.trim() === '') {
        return { valid: false, reason: 'Citation key is empty' };
    }
    
    // Characters invalid on Windows (most restrictive)
    // Windows forbids: < > : " / \ | ? * and control chars (0-31)
    const windowsInvalidChars = /[<>:"\/\\|?*\x00-\x1F]/;
    if (windowsInvalidChars.test(citekey)) {
        const invalidChars = citekey.match(/[<>:"\/\\|?*\x00-\x1F]/g);
        const uniqueChars = [...new Set(invalidChars)].map(c => {
            if (c === '\x00') return 'NULL';
            if (c === '\t') return 'TAB';
            if (c === '\n') return 'NEWLINE';
            if (c === '\r') return 'CR';
            return `'${c}'`;
        });
        return { 
            valid: false, 
            reason: `Contains invalid character(s): ${uniqueChars.join(', ')}. These characters cannot be used in filenames on Windows.` 
        };
    }
    
    // macOS forbids: : (colon is path separator in HFS+/APFS legacy)
    // Note: already checked in Windows invalid chars above, but kept for clarity
    
    // Linux forbids: / (path separator)
    // Note: already checked in Windows invalid chars above, but kept for clarity
    
    // Windows reserved names (CON, PRN, AUX, NUL, COM1-COM9, LPT1-LPT9)
    const reservedNames = /^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$/i;
    if (reservedNames.test(citekey)) {
        return { valid: false, reason: `'${citekey}' is a reserved Windows device name and cannot be used as a filename` };
    }
    
    // Check for leading/trailing spaces or periods (Windows issue)
    if (citekey !== citekey.trim()) {
        return { valid: false, reason: 'Citation key has leading or trailing spaces' };
    }
    if (citekey.endsWith('.')) {
        return { valid: false, reason: 'Citation key ends with a period, which is not allowed in Windows filenames' };
    }
    
    // Check maximum filename length (Windows limit is 255 characters)
    // Adding 3 for ".md" extension
    if (citekey.length + 3 > 255) {
        return { valid: false, reason: `Citation key is too long (${citekey.length} chars). Maximum is 252 characters (to allow for .md extension).` };
    }
    
    return { valid: true, reason: null };
}

// Global request tracking
if (typeof Zotero.ZoteroWebhookLock === 'undefined') {
    Zotero.ZoteroWebhookLock = {
        inProgress: false,
        requestId: null,
        lastRequestTime: 0,
        shownPopupCitekeys: {}  // Track which citation keys we've already shown popups for
    };
}

// Clear popup tracking from any previous run that's more than 5 seconds old
const currentTime = Date.now();
if (currentTime - Zotero.ZoteroWebhookLock.lastRequestTime > 5000) {
    Zotero.ZoteroWebhookLock.shownPopupCitekeys = {};
}

Zotero.debug("=== NEW_OBSIDIAN_NOTE_SENDER SCRIPT STARTING ===");
Zotero.debug(`Lock state: inProgress=${Zotero.ZoteroWebhookLock.inProgress}, lastRequestTime=${Zotero.ZoteroWebhookLock.lastRequestTime}`);

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

Zotero.debug("Passed throttling checks, proceeding with script");

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

        // Try Zotero 8.0+ native citationKey field first
        let citekey = item.getField('citationKey');

        // Fallback to parsing 'extra' field for pre-8.0 items
        if (!citekey) {
            const extraField = item.getField('extra') || '';
            let citekeyMatch = extraField.match(/Citation Key:\s*(.+)/);
            if (citekeyMatch) {
                citekey = citekeyMatch[1];
            }
        }

        if (!citekey) {
            Zotero.debug(`Citation Key not found for zotero item key: ${itemkey}`);
            continue;
        }

        Zotero.debug(`Found citation key "${citekey}" for item ${itemkey}`);

        // Validate citation key as a valid filename
        const validation = validateCitationKey(citekey);
        Zotero.debug(`Validation result for "${citekey}": valid=${validation.valid}, reason=${validation.reason}`);
        
        if (!validation.valid) {
            // Check if we've already shown a popup for this citation key (prevents duplicates)
            const popupKey = `popup_${citekey}`;
            if (Zotero.ZoteroWebhookLock.shownPopupCitekeys[popupKey]) {
                Zotero.debug(`Skipping duplicate popup for citation key "${citekey}"`);
                continue;
            }
            
            Zotero.debug(`Invalid citation key "${citekey}": ${validation.reason} - SHOWING POPUP NOW`);
            
            // Mark this citation key as having shown a popup (expires after 5 seconds)
            Zotero.ZoteroWebhookLock.shownPopupCitekeys[popupKey] = true;
            setTimeout(() => {
                delete Zotero.ZoteroWebhookLock.shownPopupCitekeys[popupKey];
            }, 5000);
            
            Zotero.alert(null, "Invalid Citation Key", 
                `The citation key "${citekey}" is not valid.\n\nReason: ${validation.reason}\n\n` +
                `Please edit the citation key in Zotero to remove any invalid characters before creating a note.`);
            Zotero.debug(`Popup shown for invalid citation key "${citekey}"`);
            continue;
        }

        // Fetch bibliography using Better BibTeX's JSON-RPC API.
        // Strategy: Try citekey-based lookup first (works for most item types, e.g.
        // journalArticle, newspaperArticle), then fall back to libraryID:itemKey
        // format (needed for videoRecording / YouTube in Zotero 8+).
        //
        // In Zotero 8, item.getField('citationKey') returns the native key, but BBT's
        // KeyManager may have indexed a different form of the key (e.g. from a prior
        // 'extra' field migration).  We first ask BBT which citekey it knows for this
        // item via item.citationkey, then use that confirmed key for item.bibliography.
        // Without this step, BBT silently returns an RPC error ("zero matches") and
        // bibliography ends up empty.
        let bibliography = '';
        if (citekey) {
            try {
                const libItemId = `${item.libraryID}:${itemkey}`;

                // Step 1: resolve the citekey that BBT actually has indexed for this item
                let bbtCitekey = citekey;
                try {
                    const ckResponse = await fetch("http://localhost:23119/better-bibtex/json-rpc", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "Accept": "application/json"
                        },
                        body: JSON.stringify({
                            jsonrpc: "2.0",
                            method: "item.citationkey",
                            params: [[libItemId]]
                        })
                    });
                    const ckResult = await ckResponse.json();
                    if (ckResult && ckResult.result) {
                        // result shape: { "libraryID:itemKey": "citekey" }
                        const ckValue = Object.values(ckResult.result)[0];
                        if (ckValue) {
                            bbtCitekey = ckValue;
                            Zotero.debug(`BBT resolved citekey for ${itemkey}: ${bbtCitekey}`);
                        }
                    } else if (ckResult && ckResult.error) {
                        Zotero.debug(`BBT item.citationkey error for ${itemkey}: ${JSON.stringify(ckResult.error)}`);
                    }
                } catch (ckError) {
                    Zotero.debug(`item.citationkey lookup failed, falling back to original citekey: ${ckError}`);
                }

                // Step 2: fetch the bibliography using the confirmed BBT citekey
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
                            [bbtCitekey],
                            { contentType: "text", id: "modern-language-association", locale: "en-US", quickCopy: false }
                        ]
                    })
                });

                const result = await response.json();
                if (result && result.result) {
                    bibliography = result.result;
                    Zotero.debug(`BBT bibliography (via citekey) for "${bbtCitekey}": "${bibliography.substring(0, 80)}"`);
                } else if (result && result.error) {
                    // Log the actual RPC error so it appears in Zotero debug output
                    Zotero.debug(`BBT item.bibliography RPC error for citekey "${bbtCitekey}": ${JSON.stringify(result.error)}`);
                }

                // Step 3 (fallback): for item types like videoRecording (YouTube) where the
                // citekey-based lookup returns empty in Zotero 8, retry using the
                // libraryID:itemKey identifier directly.  BBT's item.bibliography accepts
                // both formats; the direct key bypasses BBT's citekey index entirely.
                if (!bibliography) {
                    Zotero.debug(`Citekey lookup returned empty for "${bbtCitekey}"; retrying via libraryID:itemKey "${libItemId}"`);
                    const libBibResp = await fetch("http://localhost:23119/better-bibtex/json-rpc", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "Accept": "application/json"
                        },
                        body: JSON.stringify({
                            jsonrpc: "2.0",
                            method: "item.bibliography",
                            params: [
                                [libItemId],
                                { contentType: "text", id: "modern-language-association", locale: "en-US", quickCopy: false }
                            ]
                        })
                    });
                    const libBibResult = await libBibResp.json();
                    if (libBibResult && libBibResult.result) {
                        bibliography = libBibResult.result;
                        Zotero.debug(`BBT bibliography (via libItemId fallback) for "${libItemId}": "${bibliography.substring(0, 80)}"`);
                    } else if (libBibResult && libBibResult.error) {
                        Zotero.debug(`BBT item.bibliography RPC error (libItemId fallback) for "${libItemId}": ${JSON.stringify(libBibResult.error)}`);
                    }
                }

                if (bibliography) {
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
        // Only show generic error if we didn't already show a specific invalid citekey error
        // Check if we've shown any popup for invalid citekeys (more reliable than hadInvalidCitekey flag)
        const shownAnyPopup = Object.keys(Zotero.ZoteroWebhookLock.shownPopupCitekeys).length > 0;
        if (!shownAnyPopup) {
            Zotero.alert(null, "Error", "No valid items with citation keys found.");
        }
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
    // timedOut tracks whether the timeout already fired so the response (if late) is ignored
    let timedOut = false;
    
    timeoutId = setTimeout(function() {
        if (!requestCompleted) {
            timedOut = true;
            Zotero.debug(`Webhook request timed out after ${RECEIVER_RESPONSE_WAIT_TIMEOUT_SECS} seconds`);
            Zotero.alert(null, "Webhook Warning", `The receiving server did not respond within ${RECEIVER_RESPONSE_WAIT_TIMEOUT_SECS} seconds (timeout). Is ${RECEIVER_PROGRAM_NAME} running?`);
            Zotero.ZoteroWebhookLock.inProgress = false;
        }
    }, RECEIVER_RESPONSE_WAIT_TIMEOUT_SECS * 1000);
    
    const payload = {sender_id: SENDER_ID_NEW_OBSIDIAN_NOTE,
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
        if (timedOut) {
            // Late response after timeout — ignore it silently to prevent processing a stale request
            Zotero.debug(`Ignoring late webhook response (request already timed out)`);
            return;
        }
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
        if (timedOut) {
            // Error after timeout — ignore silently
            Zotero.debug(`Ignoring late webhook error (request already timed out): ${error.message}`);
            return;
        }
        Zotero.debug(`Webhook error: ${error.message}`);
        Zotero.alert(null, "Webhook Warning", `The receiving server did not respond. Is ${RECEIVER_PROGRAM_NAME} running? : ${error.message}`);
        Zotero.ZoteroWebhookLock.inProgress = false;
    });
}
