# Header
- bullet 1
- bullet 2

**And this is a drawing**

```mermaid
graph TD;
    Perplexity-->Body;
    Perplexity-->Cites;
    Zotero-->zotItems;
    Obsidian-->litNotes;
    zotItems--URLs-->zotURLtoItem
    zotItems<--citekey-->litNotes
    Body--URLs-->ReplaceLinkNumZotOrObs
    Cites-->URLs-->ReplaceLinkNumZotOrObs
    ReplaceLinkNumZotOrObs --> outputCites
    ReplaceLinkNumZotOrObs --> outputBody
    outputBody --> outputDoc
    outputCites --> outputDoc
    Cites -- Title --> zotTitleMatch
    Cites -- Url --> zotURLmatch
    zotURLmatch -- item --> hasURL{urlMatch}
    hasURL -- no --> zotTitleMatch{titlematch}
    hasURL -- yes(item)) --> makeZotOrObsLink{hasObsLink?}
    zotTitleMatch -- no --> highlightOldLink
    zotTitleMatch -- yes(item) --> makeZotOrObsLink{hasObsLink?}
    makeZotOrObsLink-- yes(citekey) --> makeObsLink
    makeZotOrObsLink-- no(item) --> makeZotLink
    


    

```
