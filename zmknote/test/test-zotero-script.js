// zotero-obsidian-complete.js
const fs = require('fs');
const path = require('path');

// 1. Zotero Mock Implementation
class MockZotero {
    constructor() {
        this.items = new Map();
        this.collections = new Map();
    }

    static File = {
        pathToFile: (p) => ({
            exists: () => false,
            create: () => true,
            copyTo: () => true,
            path: p
        }),
        putContents: (file, content) => fs.writeFileSync(file.path, content)
    };
}

class MockItem {
    constructor(data) {
        this.key = data.key;
        this.data = data;
        this.attachments = [];
        this.notes = [];
        this.relations = { DC: { relation: [] } };
    }

    getField(field) {
        const fields = {
            citationKey: this.data.citationKey,
            title: this.data.title,
            dateAdded: '2024-03-15',
            abstractNote: this.data.abstract,
            itemType: this.data.itemType,
            DOI: this.data.doi,
            url: this.data.url,
            publicationTitle: this.data.publication,
            volume: '1',
            issue: '1',
            publisher: 'Test Publisher',
            place: 'Test City',
            pages: '100-150',
            ISBN: '123-4567890123',
            date: '2024-01-01'
        };
        return fields[field] || '';
    }

    getCreators() {
        return this.data.creators.map(c => ({
            creatorType: c.type,
            firstName: c.firstName,
            lastName: c.lastName,
            name: c.name
        }));
    }

    getTags() {
        return this.data.tags.map(t => ({ tag: t }));
    }

    getAttachments() {
        return this.attachments;
    }
}

// 2. Markdown Processor
function formatDate(dateStr) {
    return dateStr ? new Date(dateStr).toISOString().split('T')[0] : '';
}

function truncateTitle(title, words = 5) {
    return title.split(' ').slice(0, words).join(' ');
}

function processCreators(creators) {
    return creators.reduce((acc, creator) => {
        const type = creator.creatorType || 'author';
        const name = creator.name || `${creator.lastName}, ${creator.firstName}`;
        acc[type] = acc[type] || [];
        acc[type].push(name);
        return acc;
    }, {});
}

function generateMarkdown(item) {
    const citekey = item.getField('citationKey');
    const title = item.getField('title');
    const abstract = item.getField('abstractNote');
    const creators = processCreators(item.getCreators());
    const tags = item.getTags().map(t => t.tag.toLowerCase().replace(/ /g, '_'));
    const attachments = item.getAttachments().map(att => ({
        name: att.getField('filename'),
        type: att.getField('filename').split('.').pop().toLowerCase()
    }));

    const md = `---
category: literaturenote
tags:
read: false
in-progress: false
linked: false
aliases: ["${title}", "${truncateTitle(title)}"]
citekey: ${citekey}
ZoteroTags:
${tags.map(t => `- ${t}`).join('\n')}
created date: ${formatDate(item.getField('dateAdded'))}
modified date: 

---

> [!info]- &nbsp;[**Zotero**](zotero://select/items/${item.key})${
    item.getField('DOI') ? ` | [**DOI**](https://doi.org/${item.getField('DOI')})` : ''
}${item.getField('url') ? ` | [**URL**](${item.getField('url')})` : ''}${
    attachments.map(att => ` | **[[${att.name}|${att.type.toUpperCase()}]]**`).join('')
}

${abstract ? `> **Abstract**  \n> ${abstract.replace(/\n/g, ' ')}\n` : ''}

${Object.entries(creators).map(([type, names]) => 
    `> **${type.charAt(0).toUpperCase() + type.slice(1)}**::\n${names.map(n => `> ${n}`).join('\n')}`
).join('\n\n')}

> **Title**:: ${title}
> **Date**:: ${formatDate(item.getField('date'))}
> **Citekey**:: ${citekey}
> **ItemType**:: ${item.getField('itemType')}
> **DOI**:: ${item.getField('DOI')}
> **URL**:: ${item.getField('url')}
> **PublicationTitle**:: ${item.getField('publicationTitle')}
> **Volume**:: ${item.getField('volume')}
> **Issue**:: ${item.getField('issue')}
> **Publisher**:: ${item.getField('publisher')}
> **Place**:: ${item.getField('place')}
> **Pages**:: ${item.getField('pages')}
> **ISBN**:: ${item.getField('ISBN')}

___
==Delete this and write here. Don't delete the \`persist\` directives above and below.==
___`;

    return md;
}

// 3. Test Execution
const outputDir = 'C:\\Users\\scott\\OneDrive\\share\\ref\\obsidian\\Obsidian Share Vault\\Scratch Space';

// Create test item with PDF and HTML attachments
const testItem = new MockItem({
    key: 'TEST123',
    citationKey: 'Doe2024',
    title: 'Understanding Zotero-Obsidian Integration',
    abstract: 'A comprehensive guide to connecting Zotero with Obsidian\nwith multiple lines',
    itemType: 'journalArticle',
    doi: '10.1234/example',
    url: 'https://example.com/zotero-obsidian',
    creators: [
        { type: 'author', firstName: 'John', lastName: 'Doe' },
        { type: 'editor', name: 'Jane Smith' }
    ],
    tags: ['reference_management', 'knowledge_graph']
});

testItem.attachments.push(
    { getField: (f) => f === 'filename' ? 'paper.pdf' : '' },
    { getField: (f) => f === 'filename' ? 'supplement.html' : '' }
);

// Generate and save
const markdown = generateMarkdown(testItem);
const dirPath = path.join(outputDir, testItem.getField('citationKey'));
if (!fs.existsSync(dirPath)) fs.mkdirSync(dirPath, { recursive: true });
const filePath = path.join(dirPath, `${testItem.getField('citationKey')}.md`);
fs.writeFileSync(filePath, markdown);

// Expected output validation
const expectedOutput = `---
category: literaturenote
tags:
read: false
in-progress: false
linked: false
aliases: ["Understanding Zotero-Obsidian Integration", "Understanding Zotero-Obsidian Integration"]
citekey: Doe2024
ZoteroTags:
- reference_management
- knowledge_graph
created date: 2024-03-15
modified date: 

---

> [!info]- &nbsp;[**Zotero**](zotero://select/items/TEST123) | [**DOI**](https://doi.org/10.1234/example) | [**URL**](https://example.com/zotero-obsidian) | **[[paper.pdf|PDF]]** | **[[supplement.html|HTML]]**

> **Abstract**  
> A comprehensive guide to connecting Zotero with Obsidian with multiple lines

> **Author**::  
> John Doe

> **Editor**::  
> Jane Smith

> **Title**:: Understanding Zotero-Obsidian Integration
> **Date**:: 2024-01-01
> **Citekey**:: Doe2024
> **ItemType**:: journalArticle
> **DOI**:: 10.1234/example
> **URL**:: https://example.com/zotero-obsidian
> **PublicationTitle**:: 
> **Volume**:: 1
> **Issue**:: 1
> **Publisher**:: Test Publisher
> **Place**:: Test City
> **Pages**:: 100-150
> **ISBN**:: 123-4567890123

___
==Delete this and write here. Don't delete the \`persist\` directives above and below.==
___`;

console.assert(markdown === expectedOutput, "Generated Markdown doesn't match expected format");
console.log('Success! Generated file at:', filePath);
