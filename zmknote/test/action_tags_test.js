// Makes an obsidian note by hand, given a selected zotero item
// Similar to: https://www.reddit.com/r/ObsidianMD/comments/1f48x0g/obsidian_plugin_autocreating_notes_from_zotero/

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

function createNoteMarkdown(dir, citekey, title) {
    const noteFile = Zotero.File.pathToFile(dir.path + "\\" + citekey + ".md");
    if (noteFile.exists()) {
        return false;
    }
    noteFile.create(Components.interfaces.nsIFile.NORMAL_FILE_TYPE, 0o664);
    Zotero.File.putContents(noteFile, "[[" + citekey + ".pdf]] \n# " + title + "\n\n");
    return true;
}

// function createNotePDF(dir, pdf, citekey) {
//     if (pdf == null) {
//         return false;
//     }
//     pdf.copyTo(dir, citekey + ".pdf");
//     return true;
// }

function createNote(item) {
    const title = item.getField("title");
    const citekey = item.getField("citekey");
    const pdf = getPDFFile(item);
    //const dir = Zotero.File.pathToFile(fpath + "\\" + citekey);
    // if (!dir.exists()) {
    //     dir.create(Components.interfaces.nsIFile.DIRECTORY_TYPE, 0o755);
    // }
    const createMd = createNoteMarkdown(fpath, citekey, title);
    // const createPdf = createNotePDF(dir, pdf, citekey);
    // if (createPdf) {
    //     if (createMd) {
    //         return "Note " + citekey + " created successfully";
    //     } else {
    //         return "Adding PDF to note " + citekey;
    //     }
    // } else {
    //     if (createMd) {
    //         return "Note " + citekey + " created without PDF";
    //     } else {
    //         return "Note " + citekey + " already existing";
    //     }
    // }
}

return createNote(item);
