/* A test of a flask webhook interface with zotero, with dialog buttons that popup if the file the 
listener wants to generate already exists.  The only way to do this in a decent way in python was to
popup the dialog in a browser, unfortunately.

The companion python script for this is  multikey_listener_test.py */

// Configuration constant to match Python's LISTEN_PORT
const SEND_PORT = 5050;

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

// Set processing lock
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
    
    // Process all selected items
    let itemDataArray = [];
    for (let selectedItem of selectedItems) {
        let extraField = selectedItem.getField('extra');
        let citationKeyMatch = extraField.match(/Citation Key:\s*(.+)/);
        if (!citationKeyMatch) {
            Zotero.debug("Citation key not found for one of the selected items.");
            continue;
        }
    
        let citationKey = citationKeyMatch[1];
        let zoteroItemKey = selectedItem.key;
    
        // Add item data to array
        itemDataArray.push({
            zoteroItemKey: zoteroItemKey,
            citationKey: citationKey
        });
    }
    
    // Only send if we have at least one valid item
    if (itemDataArray.length > 0) {
        // Send data to webhook (once!)
        sendToWebhook(itemDataArray, Zotero.ZoteroWebhookLock.requestId);
    } else {
        Zotero.alert(null, "Error", "No valid items with citation keys found.");
        Zotero.ZoteroWebhookLock.inProgress = false;
    }
} catch (e) {
    Zotero.debug("Error in webhook script: " + e);
    Zotero.ZoteroWebhookLock.inProgress = false;
}

// Function to send data to webhook using fetch()
function sendToWebhook(itemDataArray, requestId) {
    // Use the SEND_PORT constant instead of hardcoding the port number
    const webhookUrl = `http://localhost:${SEND_PORT}/webhook`;
    
    Zotero.debug(`Sending webhook request ${requestId} with ${itemDataArray.length} items`);

    fetch(webhookUrl, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-Request-ID": requestId
        },
        body: JSON.stringify(itemDataArray)
    })
    .then(response => {
        if (response.ok) {
            Zotero.debug(`Webhook response: ${response.statusText}`);
        } else {
            Zotero.debug(`Webhook error status: ${response.status}`);
        }
        // Release lock after request completes
        Zotero.ZoteroWebhookLock.inProgress = false;
    })
    .catch(error => {
        Zotero.debug(`Webhook error: ${error.message}`);
        // Release lock if request fails
        Zotero.ZoteroWebhookLock.inProgress = false;
    });
}
