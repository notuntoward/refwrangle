"""Python functions for converting a zotero item's metadata into an obsidian note. Intended 
to be called directly from zotero, instead of from Obsidian, as the Obsidian Zotero Integration 
plugin requires.  Formatting is a similar to notes created by Zotero Integraion,
in fact, the jinja2 template used here tries to match the output of my Zotero Integration
nunjucks template (currently Obsidian/templates/literature note.md).

This code  populates a dict with data obtained from pyzotero but the functions here
Can also use data from the Zotero actions and tags plugin, specifically the javascript
I 'wrote' for it.  That scripts feeds a webhook listener, which strips off a mystery <div>
prepended to zotero item notes export.

A PUZZLE.  when I put the zotero note to markdown function here and reference it
elsewhere stuff doesn't work.  The best is to put it all into the action and tags
webhook listener.  Everything works if I do that, for some reason.

THIS PYZOTERO INTERFACE ISEXTREMELY SLOW, 10-15 seconds to get an answer, and the local
API is even slower.  Althought I doubt I'll use this, I'll keep it around, jusct in case."""

import html
import pathlib as pl
import sys
from datetime import datetime

import dateutil.parser as dp
from jinja2 import Template
from pyzotero import zotero

import zotero_to_obsidian_note_listener as zol

# Define paths and credentials
refwrangle_dir = Path(__file__).resolve().parent.parent.parent # works??
#refwrangle_dir = pl.Path('~/ref/refwrangle').expanduser()
sys.path.append(str(refwrangle_dir))
import refwrangle.utils.refwrangle as rfw  # Import your custom refwrangle module


# %%
def parse_date(date_str: str, format_dts: str) -> str:
    """Parses a date string and returns it in a standard format."""
    try:
        date = dp.parse(date_str)
        return date.strftime(format_dts)
    except Exception as e:
        print(f"Error parsing date {date_str}: {e}")
        return ''


def write_literature_note(itemkey: str, output_file: pl.Path, item_data: dict, 
                          collection_key_to_name: dict, zot: zotero.Zotero) -> None:
    """Creates an Obsidian literature note from a Zotero item."""
    # Fetch collections for this item
    try:
        collections = [collection_key_to_name[key] for key in item_data['collections']]
        # TODO: someday, change the javascript and restore the below
        # This was compatible w/ nunjucks, but a bother to do in javascript
        # collections = [
        #     {'key': key, 'name': collection_key_to_name[key]}
        #     for key in item_data['collections']]
    except Exception as e:
        print(f"Error fetching collections: {e}")
        raise

    # Fetch related items
    related_items = []
    relations = item_data.get('relations', {})
    related_keys = relations.get('dc:relation', [])

    if isinstance(related_keys, str):
        related_keys = [related_keys]

    for uri in related_keys:
        related_itemkey = uri.split('/')[-1]
        try:
            related_item = zot.item(related_itemkey)
            related_items.append({
                'citekey': related_item['data'].get('citekey', ''),
                'key': related_itemkey,
                'title': related_item['data'].get('title', ''),
            })
        except Exception as e:
            print(f"Could not fetch related item {related_itemkey}: {e}")

    # Fetch notes attached to this item by getting the item's children and filtering for notes
    notes = []
    try:
        children = zot.children(itemkey)
        for child in children:
            if child['data']['itemType'] == 'note':
                # Convert HTML notes to Markdown
                html_note = child['data'].get('note', '')
                markdown_note = zol.zotero_note_html_to_md(html_note)
                notes.append(markdown_note)
                # outdir = pl.Path(r"C:\Users\scott\tmp")
                # (outdir / "zot_to_obs_note_pyzotero_html.html").write_text(html_note,encoding='utf-8')
                # (outdir / "zot_to_obs_note_pyzotero_markdown.md").write_text(markdown_note,encoding='utf-8')

    except Exception as e:
        print(f"Could not fetch notes: {e}")
        raise

    # Fetch attachments for this item
    attachments = []
    try:
        children = zot.children(itemkey)
        for child in children:
            if child['data']['itemType'] == 'attachment':
                # Get the path of the attachment
                if 'data' in child and 'path' in child['data']:
                    path = child['data']['path'].removeprefix("attachments:")
                else:
                    path = ""
                attachments.append({'title': child['data'].get('title', ''), 'path': path})
    except Exception as e:
        print(f"Could not fetch attachments: {e}")
        raise

    
    # Make the data dict for the jinja2 template
    all_tags = [tag['tag'] for tag in item_data.get('tags', [])]
    citekey = rfw.get_citation_key(item_data)

    data = {
        'title': item_data.get('title', ''),
        'citekey': citekey,
        'tags': all_tags,
        # TODO: below is compatible w/ nunjucks, but a bother to do in javascript.  Go back to it someday?
        # 'tags': item_data.get('tags', []),
        'collections': collections,
        'exportDate': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'desktopURI': f'zotero://select/library/items/{itemkey}',
        'DOI': item_data.get('DOI', ''),
        'url': item_data.get('url', ''),
        'abstractNote': item_data.get('abstractNote', ''),
        'creators': item_data.get('creators', []),
        'date': parse_date(item_data.get('date'), "%Y-%m-%d") if item_data.get('date') else '',
        'itemkey': itemkey,
        'itemType': item_data.get('itemType', ''),
        'publicationTitle': item_data.get('publicationTitle', ''),
        'volume': item_data.get('volume', ''),
        'issue': item_data.get('issue', ''),
        'publisher': item_data.get('publisher', ''),
        'place': item_data.get('place', ''),
        'pages': item_data.get('pages', ''),
        'ISBN': item_data.get('ISBN', ''),
        'allTags': all_tags,
        'relations': related_items,
        'bibliography': rfw.get_bibliography_bbt_api(citekey),
        'notes': notes,
        'attachments': attachments,
    }

    print(f"{data['notes']=}")
    # Render the template
    template = Template(zol.template_str, trim_blocks=True, lstrip_blocks=True)
    output_text = template.render(**data)

    print(f'Writing to {output_file}')
    output_file.write_text(output_text, encoding='utf-8')

def write_literature_notes(itemkeys: list[str], output_dir: pl.Path, local_api: bool = False) -> None:
    """Writes literature notes for given Zotero item keys to the specified output directory."""

    if isinstance(itemkeys, str):
        itemkeys = [itemkeys]

    timer = rfw.Timer()
    try:
        zot = zotero.Zotero(rfw.zotero_library_id, rfw.zotero_library_type, 
                            rfw.zotero_api_key, local=local_api)
    except Exception as e:
        print(f"Error initializing Zotero: {e}")
        raise

    # Fetch collections
    try:
        collection_key_to_name = {
            collection['key']: collection['data']['name']
            for collection in zot.all_collections()
        }
    except Exception as e:
        print(f"Error fetching collections: {e}")
        raise

    # Fetch items in batches of 50 (API max limit)
    item_data = {}
    for i in range(0, len(itemkeys), 50):
        batch_keys = itemkeys[i : i + 50]
        try:
            items = zot.get_subset(batch_keys)
            item_data.update({item['data']['key']: item['data'] for item in items})
        except Exception as e:
            print(f"Error fetching items: {e}")
            raise

    for itemkey in itemkeys:
        item_data_this = item_data[itemkey]
        output_file = output_dir / f'{rfw.get_citation_key(item_data_this)}.md'
        
        write_literature_note(itemkey, output_file, item_data_this , collection_key_to_name, zot)
    print("Done.")
    timer.mark()

if __name__ == '__main__':
    # Example usage with a single item key
    # itemkeys = ['I4G6IXQS'] # <div> wraps whole note
    #itemkeys = ['U7NTFFTP']  # Example with two keys
    itemkeys = ['YK4TVDBM'] # test all on this
    # Example usage with a list of item keys
    #itemkeys = ['I4G6IXQS', 'U7NTFFTP']  # Example with two keys
    
    output_dir = pl.Path(r'C:\Users\scott\OneDrive\share\ref\obsidian\Obsidian Share Vault\Scratch Space')

    write_literature_notes(itemkeys, output_dir)

# %%
