from pyzotero import zotero
from jinja2 import Template
from datetime import datetime
from dateutil.parser import parse as parse_date

from jinja2 import Template
from datetime import datetime
from dateutil import parser as date_parser
import pathlib as pl
import requests
import re
import sys
from markdownify import markdownify
from icecream import ic

# Define paths and credentials
refwrangle_dir = pl.Path('~/ref/refwrangle').expanduser()
sys.path.append(str(refwrangle_dir))
import refwrangle as rfw  # Import your custom refwrangle module

output_file = pl.Path(
    r'C:\Users\scott\OneDrive\share\ref\obsidian\Obsidian Share Vault\Scratch Space\tmp_zotero_to_obs_lit_note_jinja2.md'
)

ATTACHMENT_FOLDER = pl.Path(
    r'C:\Users\scott\OneDrive\share\ref\obsidian\Obsidian Share Vault\lit\lit_sources'
)


# Replace these with your actual Zotero credentials and item key:
LIBRARY_ID = rfw.library_id
LIBRARY_TYPE = 'user'  # or 'group'
API_KEY = rfw.api_key
#ITEM_KEY = 'QCVVWIGL'
#ITEM_KEY = 'I4G6IXQS'
ITEM_KEY = 'SAUNMD5H'
# Initialize Zotero client
try:
    zot = zotero.Zotero(LIBRARY_ID, LIBRARY_TYPE, API_KEY)
except Exception as e:
    print(f"Error initializing Zotero: {e}")
    raise

# Fetch the item
# Verified: zot.item() exists and takes itemID as a parameter [1][4]
try:
    item = zot.item(ITEM_KEY)
    item_data = item['data']
except Exception as e:
    print(f"Error fetching item: {e}")
    raise

# Fetch collections for this item
# Verified: There is no zot.collections_for_item() method [1][4]
# Using zot.collections() and filtering manually.  This is less efficient but correct.
try:
    collection_key_to_name = {collection['key']:collection['data']['name'] for collection in zot.all_collections()} 
    collections = [{'key':key, 'name': collection_key_to_name[key]} for key in item['data']['collections']]
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
    related_item_key = uri.split('/')[-1]
    try:
        # Verified: zot.item() exists and takes itemID as a parameter [1][4]
        related_item = zot.item(related_item_key)
        related_items.append({
            'citekey': related_item['data'].get('citekey', ''),
            'key': related_item_key,
            'title': related_item['data'].get('title', '')
        })
    except Exception as e:
        print(f"Could not fetch related item {related_item_key}: {e}")

# Fetch notes attached to this item by getting the item's children and filtering for notes
notes = []
# Verified: zot.children() exists and takes itemID as a parameter [1][4]
try:
    children = zot.children(ITEM_KEY)
    for child in children:
        if child['data']['itemType'] == 'note':
            # Convert HTML notes to Markdown
            html_note = child['data'].get('note', '')
            markdown_note = markdownify(html_note) if html_note else ''

            # Custom formatting adjustments
            markdown_note = re.sub(r'\*\*%', r'**', markdown_note)  # Fix bolded percentages
            markdown_note = markdown_note.replace('+', '-')  # Escape '+' characters
            # markdown_note = markdown_note.replace('+', '\\+')  # Escape '+' characters

            # Improved list formatting
            markdown_note = re.sub(r'^\s*([+\-*])\s*(.*)$', r'\1 \2', markdown_note, flags=re.MULTILINE) #Fix up lists

            notes.append({
                'note': markdown_note,
                'dateModified': parse_date(child['data'].get('dateModified')),
                'key': child['data'].get('key'),
                'uri': child['data'].get('uri'),
                'tags': child['data'].get('tags', [])
            })            
            # # Convert HTML notes to Markdown
            # html_note = child['data'].get('note', '')
            # markdown_note = markdownify(html_note) if html_note else ''
            # notes.append({
            #     'note': markdown_note,
            #     'dateModified': parse_date(child['data'].get('dateModified')),
            #     'key': child['data'].get('key'),
            #     'uri': child['data'].get('uri'),
            #     'tags': child['data'].get('tags', [])
            # })
except Exception as e:
    print(f"Could not fetch notes: {e}")
    raise

# Fetch attachments for this item
attachments = []
# Verified: zot.children() exists and takes itemID as a parameter [1][4]
try:
    children = zot.children(ITEM_KEY)
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

# Prepare data dictionary for the template
data = {
    'title': item_data.get('title', ''),
    'citekey': item_data.get('citekey', ''),
    'tags': item_data.get('tags', []),
    'collections': collections,
    'exportDate': datetime.now(),
    'desktopURI': item['links'].get('alternate', {}).get('href', ''),
    'DOI': item_data.get('DOI', ''),
    'url': item_data.get('url', ''),
    'abstractNote': item_data.get('abstractNote', ''),
    'creators': item_data.get('creators', []),
    'date': parse_date(item_data.get('date')) if item_data.get('date') else datetime.now(),
    'itemKey': ITEM_KEY,
    'itemType': item_data.get('itemType', ''),
    'publicationTitle': item_data.get('publicationTitle', ''),
    'volume': item_data.get('volume', ''),
    'issue': item_data.get('issue', ''),
    'publisher': item_data.get('publisher', ''),
    'place': item_data.get('place', ''),
    'pages': item_data.get('pages', ''),
    'ISBN': item_data.get('ISBN', ''),
    'allTags': [tag['tag'] for tag in item_data.get('tags', [])],
    'relations': related_items,
    'bibliography': '',  # Requires separate bibliography generation if needed
    'notes': notes,
    'attachments': attachments,
}

ic(data['attachments'], data['collections'], data['tags'])

# Jinja2 template
template_str = """{%- macro truncateTitle(title, n) -%}
  {%- set words = title.split(' ') -%}
  {%- set truncatedTitle = ' '.join(words[:n]) -%}
  {{ truncatedTitle }}
{%- endmacro %}
{%- macro basename(filePath) -%}
  {%- set normalizedPath = filePath.replace("\\\\", "/") -%}
  {%- set fileParts = normalizedPath.split("/") -%}
  {%- set endpath = fileParts[-1] -%}
  {{- endpath -}}
{%- endmacro %}
---
category: 
- literaturenote
tags:
read: false
in-progress: false
linked: false
aliases:
- "{{ title }}"
- "{{ truncateTitle(title, 5) }}"
citekey: {{ citekey }}
ZoteroTags:
{% for tag in tags %}
- {{ tag.tag | lower | replace(" ", "_") }}
{% endfor %}
ZoteroCollections:
{% for collection in collections %}
- {{ collection.name | lower | replace(" ", "_") }}
{% endfor %}
created date: {{ exportDate.strftime("%Y-%m-%d") }}
modified date:
---

> [!info]- [**Zotero**]({{ desktopURI }}) {% if DOI %} | [**DOI**](https://doi.org/{{ DOI }}){% endif %}{% if url %} | [**URL**]({{ url }}){% endif %}{% for attachment in attachments if attachment.path.endswith(".pdf") %} | **[[{{ basename(attachment.path) }}|PDF]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".html") %} | **[[{{ basename(attachment.path) }}|HTM]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".docx") %} | **[[{{ basename(attachment.path) }}|DOC]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".pptx") %} | **[[{{ basename(attachment.path) }}|PPT]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".txt") %} | **[[{{ basename(attachment.path) }}|TXT]]**{% endfor %}
>
> {% if abstractNote %}
> **Abstract**
> {{ abstractNote.replace("\\n"," ") }}
> {% endif %}
{{ "" }}
{%- for type, creators in creators|groupby("creatorType") %}
> **{{ type.capitalize() }}**::
{%- for creator in creators %}
    {%- if creator.name %} {{ creator.name }}{% else %} {{ creator.lastName }}, {{ creator.firstName }}{% endif %}{% if not loop.last %}, {% endif %}
{%- endfor %}
{% endfor %}

> **Title**:: "{{ title }}"
> **Date**:: {{ date.strftime("%Y-%m-%d") }}
> **Citekey**:: {{ citekey }}
> **ZoteroItemKey**:: {{ itemKey }}
> **itemType**:: {{ itemType }}
> **DOI**:: {{ DOI }}
> **URL**:: {{ url }}
> **Journal**:: {{ publicationTitle }}
> **Volume**:: {{ volume }}
> **Issue**:: {{ issue }}
> **Book**:: {{ publicationTitle }}
> **Publisher**:: {{ publisher }}
> **Location**:: {{ place }}
> **Pages**:: {{ pages }}
> **ISBN**:: {{ ISBN }}
> **ZoteroTags**:: {{ allTags }}
> **Related**::{% for relation in relations if relation.citekey %} [[@{{ relation.citekey }}]]{% if not loop.last %}, {% endif %}{% endfor %}
> {% if bibliography %} {{ bibliography }}{% endif %}

{% block persist_Obsidian_Notes %}

%% begin Obsidian Notes %%
___
==Delete this and write here. Don't delete the `persist` directives above and below.==
___
{% endblock persist_Obsidian_Notes %}
%% end Obsidian Notes %%
{% if notes|length > 0 %}
> [!note]- Zotero Note ({{ notes|length }})
>
{%- for note in notes %}
>{{ note.note.replace("# ", "### ").replace("\\n", "\\n> ") }}
>{{ note.tags | map(attribute='tag') | join(', ') }}
>
> 📝️ (modified: {{ note.dateModified.strftime("%Y-%m-%d") }}) [link](zotero://select/library/items/{{ note.key }}) - [web]({{ note.uri }})
>
---
{% endfor %}
{% endif %}
"""


# Render the template
template = Template(template_str, trim_blocks=True, lstrip_blocks=True)
output_text = template.render(**data)

# Output result (e.g., print or save to file)
#print(output)

print(f'Writing to {output_file}')

output_file.write_text(output_text, encoding='utf-8')

print("Done.")

