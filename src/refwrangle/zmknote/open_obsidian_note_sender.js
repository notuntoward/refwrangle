/* This is the zotero side of a webhook interface between zotero items and a python webhook message receiver, 
which opens one or more obsidian literature notes. The job here is to get and send the necessary item data.

The companion python script for this one is zotero_to_obsidian_note_receiver_test.py */

// The webhook sending port, match the Python side's LISTEN_PORT
const SEND_PORT = 5050;

// this ID tells the receiver who sent the message (and what to do wih it)
const SENDER_ID_OPEN_OBSIDIAN_NOTE  = 'open_obsidian_note'

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
        selectedItems.push(item);      // Single item selected
    } else if (items && items.length > 0) {
         selectedItems = items;        // Multiple items selected
    } else {
        Zotero.alert(null, "Error", "No item selected.");
        Zotero.ZoteroWebhookLock.inProgress = false;
        return;
    }
    
    // Put item in JSON
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
        itemDataArray.push(citekey)
    }
    
    // Only send if we have at least one valid item
    if (itemDataArray.length > 0) {
        // Send data to webhook (once!)
        sendToWebhook(itemDataArray, Zotero.ZoteroWebhookLock.requestId);
    } else {
        Zotero.alert(null, "Error", "No valid items with citekeys found.");
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
    
    const payload = {sender_id: SENDER_ID_OPEN_OBSIDIAN_NOTE,
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