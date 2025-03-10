// attempt to make lit note from zotero actions & tags plugin using nunjucks
// but it says it can't import nunjucks

const Zotero = require('Zotero');
const nunjucks = require('nunjucks');

// Ensure selected items are retrieved correctly

const targetItems = [item]

// never works, for some reason
//const targetItems = items || (item ? [item] : []);
//if (targetItems.length === 0) {
//    Zotero.alert(null, 'No items selected', 'Please select one or more items first.');
//    return;
//}

// Define paths
const vaultPath = 'C:\\Users\\scott\\OneDrive\\share\\ref\\obsidian\\Obsidian Share Vault';
const outputDir = `${vaultPath}\\Scratch Space`;
const templatePath = `${vaultPath}\\Obsidian\\templates\\literature_note.md`;

// Configure Nunjucks environment
const env = nunjucks.configure(vaultPath, {
    autoescape: true,
    watch: false,
    noCache: true,
});

// Helper functions
async function getAttachments(item) {
    const attachmentIDs = await item.getAttachments();
    const attachmentsInfo = [];
    for (const attachmentID of attachmentIDs) {
        const attachmentItem = await Zotero.Items.getAsync(attachmentID);
        if (attachmentItem.isAttachment() && attachmentItem.isFileAttachment()) {
            const filePath = await attachmentItem.getFilePathAsync();
            attachmentsInfo.push({ path: filePath, title: attachmentItem.getDisplayTitle() });
        }
    }
    return attachmentsInfo;
}

async function getNotes(item) {
    const noteIDs = await item.getNotes();
    const notesArray = [];
    for (const id of noteIDs) {
        const noteItem = await Zotero.Items.getAsync(id);
        notesArray.push({
            note: noteItem.getNote(),
            dateModified: noteItem.dateModified,
            key: noteItem.key,
            uri: `zotero://select/library/items/${noteItem.key}`,
        });
    }
    return notesArray;
}

// Process each selected item
for (const currentItem of targetItems) {
    try {
        // Extract metadata fields
        const citekeyMatch = currentItem.getField('extra').match(/Citation Key: (\S+)/);
        const citekey = citekeyMatch ? citekeyMatch[1] : '';
        const data = {
            citekey,
            title: currentItem.getField('title'),
            abstractNote: currentItem.getField('abstractNote') || '',
            date: currentItem.getField('date') || '',
            DOI: currentItem.getField('DOI') || '',
            url: currentItem.getField('url') || '',
            creators: currentItem.getCreators().map((creator) => ({
                firstName: creator.firstName || '',
                lastName: creator.lastName || '',
                name: creator.firstName ? `${creator.firstName} ${creator.lastName}` : creator.lastName,
                creatorType: creator.creatorType,
            })),
            tags: currentItem.getTags().map((tag) => tag.tag),
            collections: await currentItem.getCollections(),
            attachments: await getAttachments(currentItem),
            notes: await getNotes(currentItem),
            desktopURI: `zotero://select/library/items/${currentItem.key}`,
            exportDate: new Date().toISOString().split('T')[0],
            publicationTitle: currentItem.getField('publicationTitle') || '',
            volume: currentItem.getField('volume') || '',
            issue: currentItem.getField('issue') || '',
            pages: currentItem.getField('pages') || '',
            publisher: currentItem.getField('publisher') || '',
            place: currentItem.getField('place') || '',
            ISBN: currentItem.getField('ISBN') || '',
        };

        // Render template using Nunjucks
        const renderedContent = env.render(templatePath, data);

        // Save rendered content to a markdown file
        const outputFilePath = `${outputDir}\\${citekey}.md`;
        await Zotero.File.putContentsAsync(outputFilePath, renderedContent);
    } catch (error) {
        Zotero.logError(`Error processing item ${currentItem.key}: ${error.message}`);
    }
}
Zotero.alert(null, 'Success', 'Literature notes created for all selected items.');
