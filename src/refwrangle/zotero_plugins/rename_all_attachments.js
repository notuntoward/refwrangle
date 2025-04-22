/**
 * Bulk rename of attachment titles
 * @author thalient-ai
 * @usage 
 * @link https://github.com/windingwind/zotero-actions-tags/discussions/380
 * @see https://github.com/windingwind/zotero-actions-tags/discussions/380
 *
 * SO bugfixed version, 3/2025 (https://www.perplexity.ai/search/the-javascript-below-runs-in-t-v21lwgaqQCeBqvQLl8mrgg?0=d#9)
 * - fix to avoid error popup
 * - Improved error logging by using Zotero.log() instead of Zotero.logError(), which allows for specifying log levels.
 * - if a rename could duplicate filenames e.g. if it contained two .pdf files, then refuses to rename, and jiggles a bit.  The user will have to rename by hand.
 */

const Zotero = require("Zotero");

// Function to process renaming of each attachment
async function processRenaming(attachment, processedAttachmentIds) {
    if (!attachment || processedAttachmentIds.has(attachment.id)) {
        return { renamed: 0, errors: 0 };
    }

    if (attachment.attachmentLinkMode === Zotero.Attachments.LINK_MODE_LINKED_URL) {
        Zotero.log(`Cannot rename linked URL attachment ${attachment.id}.`, 'warning');
        return { renamed: 0, errors: 1 };
    }

    if (!attachment.parentItemID) {
        Zotero.log(`Attachment ${attachment.id} does not have a parent item.`, 'warning');
        return { renamed: 0, errors: 1 };
    }

    const parentItem = await Zotero.Items.getAsync(attachment.parentItemID);
    if (!parentItem) {
        Zotero.log(`No parent item found for attachment ${attachment.id}.`, 'warning');
        return { renamed: 0, errors: 1 };
    }

    const currentPath = await attachment.getFilePathAsync();
    if (!currentPath) {
        Zotero.log(`No local file path available for attachment ${attachment.id}.`, 'warning');
        return { renamed: 0, errors: 1 };
    }

    // Generate new filename based on parent item and attachment title
    const newName = Zotero.Attachments.getFileBaseNameFromItem(parentItem, { 
        attachmentTitle: attachment.getField("title") 
    });
    
    const currentName = currentPath.split(/(\\|\/)/g).pop(); // Extract current filename from path
    const extension = currentName.includes('.') ? currentName.split('.').pop() : ''; // Extract file extension
    const finalName = extension ? `${newName}.${extension}` : newName;

    if (newName !== currentName.replace(`.${extension}`, "")) {
        try {
            await attachment.renameAttachmentFile(finalName); // Rename file on disk
            attachment.setField('title', newName); // Update title in Zotero database
            await attachment.saveTx(); // Save changes to database
            processedAttachmentIds.add(attachment.id);
            return { renamed: 1, errors: 0 };
        } catch (error) {
            Zotero.log(`Error renaming attachment ${attachment.id}: ${error.message}`, 'error');
            return { renamed: 0, errors: 1 };
        }
    }

    return { renamed: 0, errors: 0 };
}

// Main execution block
(async () => {
    if (!items && !item) {
        Zotero.log("[Rename Attachments] No item or items array provided.", 'warning');
        return;
    }

    let targetItems = items || [item];
    let totalRenamed = 0;
    let totalErrors = 0;
    let processedAttachmentIds = new Set();

    for (const currentItem of targetItems) {
        const attachments = currentItem.itemType === 'attachment' 
            ? [currentItem] 
            : await Zotero.Items.getAsync(currentItem.getAttachments());
        
        for (const attachment of attachments) {
            const result = await processRenaming(attachment, processedAttachmentIds);
            totalRenamed += result.renamed;
            totalErrors += result.errors;
        }
    }

    if (totalRenamed > 0 || totalErrors > 0) {
        let message = `Successfully renamed ${totalRenamed} attachment${totalRenamed !== 1 ? 's' : ''}`;
        if (totalErrors > 0) {
            message += `. Errors encountered: ${totalErrors}`;
        }
        
        // Log success message instead of showing a popup or causing interruptions
        Zotero.log(`[Rename Attachments] ${message}`, 'info');
    }
})();
