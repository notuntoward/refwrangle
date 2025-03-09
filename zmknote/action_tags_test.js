// Path to References directory in the shared Obsidian vault
const fpath = String.raw`C:\Users\scott\OneDrive\share\ref\obsidian\Obsidian Share Vault\Scratch Space`

function getPDFFile(item) {
    const attachments = item.getAttachments();
    for (let attachmentID of attachments) {
        let attachment = Zotero.Items.get(attachmentID);
        if (attachment.attachmentContentType === "application/pdf") {
            return Zotero.File.pathToFile(attachment.getFilePath());
        }
    }
    return null;
}

function createNoteMarkdown(dir, citationKey, title) {
    const noteFile = Zotero.File.pathToFile(dir.path + "\\" + citationKey + ".md");
    if (noteFile.exists()) {
        return false;
    }
    noteFile.create(Components.interfaces.nsIFile.NORMAL_FILE_TYPE, 0o664);
    Zotero.File.putContents(noteFile, "[[" + citationKey + ".pdf]] \n# " + title + "\n\n");
    return true;
}

// function createNotePDF(dir, pdf, citationKey) {
//     if (pdf == null) {
//         return false;
//     }
//     pdf.copyTo(dir, citationKey + ".pdf");
//     return true;
// }

function createNote(item) {
    const title = item.getField("title");
    const citationKey = item.getField("citationKey");
    const pdf = getPDFFile(item);
    //const dir = Zotero.File.pathToFile(fpath + "\\" + citationKey);
    // if (!dir.exists()) {
    //     dir.create(Components.interfaces.nsIFile.DIRECTORY_TYPE, 0o755);
    // }
    const createMd = createNoteMarkdown(fpath, citationKey, title);
    // const createPdf = createNotePDF(dir, pdf, citationKey);
    // if (createPdf) {
    //     if (createMd) {
    //         return "Note " + citationKey + " created successfully";
    //     } else {
    //         return "Adding PDF to note " + citationKey;
    //     }
    // } else {
    //     if (createMd) {
    //         return "Note " + citationKey + " created without PDF";
    //     } else {
    //         return "Note " + citationKey + " already existing";
    //     }
    // }
}

return createNote(item);
