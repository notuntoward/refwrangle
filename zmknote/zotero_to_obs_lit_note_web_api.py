from pyzotero import zotero
from jinja2 import Template
from datetime import datetime
from dateutil.parser import parse as parse_date
import pathlib as pl
import re
import sys
from markdownify import markdownify
from icecream import ic

# Define paths and credentials
refwrangle_dir = pl.Path('~/ref/refwrangle').expanduser()
sys.path.append(str(refwrangle_dir))
import refwrangle as rfw  # Import your custom refwrangle module

output_dir = pl.Path(
    r'C:\Users\scott\OneDrive\share\ref\obsidian\Obsidian Share Vault\Scratch Space'
)

# Replace these with your actual Zotero credentials and item key:
LIBRARY_ID = rfw.library_id
LIBRARY_TYPE = 'user'  # or 'group'
API_KEY = rfw.api_key

# Jinja2 template for output literature note
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


# Initialize Zotero client
try:
    zot = zotero.Zotero(LIBRARY_ID, LIBRARY_TYPE, API_KEY)
except Exception as e:
    print(f"Error initializing Zotero: {e}")
    raise


def create_literature_note(item_key, output_dir, item_data, collection_key_to_name):
    """
    Creates an Obsidian literature note from a Zotero item.

    Args:
        item_key (str): The Zotero item key.
        output_dir (Path): The directory to save the note to.
        item_data (dict): The item data dictionary
        collection_key_to_name (dict): A dictionary mapping collection keys to names
    """
    # Fetch collections for this item
    try:
        collections = [
            {'key': key, 'name': collection_key_to_name[key]}
            for key in item_data['collections']
        ]
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
            related_item = zot.item(related_item_key)
            related_items.append({
                'citekey': related_item['data'].get('citekey', ''),
                'key': related_item_key,
                'title': related_item['data'].get('title', ''),
            })
        except Exception as e:
            print(f"Could not fetch related item {related_item_key}: {e}")

    # Fetch notes attached to this item by getting the item's children and filtering for notes
    notes = []
    try:
        children = zot.children(item_key)
        for child in children:
            if child['data']['itemType'] == 'note':
                # Convert HTML notes to Markdown
                html_note = child['data'].get('note', '')
                markdown_note = markdownify(html_note) if html_note else ''

                # Custom formatting adjustments
                markdown_note = re.sub(r'\*\*%', r'**', markdown_note)  # Fix bolded percentages
                markdown_note = markdown_note.replace('+', '-')  # Escape '+' characters

                # Improved list formatting
                markdown_note = re.sub(
                    r'^\s*([+\-*])\s*(.*)$', r'\1 \2', markdown_note, flags=re.MULTILINE
                )  # Fix up lists
                notes.append({
                    'note': markdown_note,
                    'dateModified': parse_date(child['data'].get('dateModified')),
                    'key': child['data'].get('key'),
                    'uri': child['data'].get('uri'),
                    'tags': child['data'].get('tags', []),
                })
    except Exception as e:
        print(f"Could not fetch notes: {e}")
        raise

    # Fetch attachments for this item
    attachments = []
    try:
        children = zot.children(item_key)
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
    citekey = rfw.get_citation_key(item_data)
    data = {
        'title': item_data.get('title', ''),
        'citekey': citekey,
        'tags': item_data.get('tags', []),
        'collections': collections,
        'exportDate': datetime.now(),
        'desktopURI': item_data.get('desktopURI'),
        'DOI': item_data.get('DOI', ''),
        'url': item_data.get('url', ''),
        'abstractNote': item_data.get('abstractNote', ''),
        'creators': item_data.get('creators', []),
        'date': parse_date(item_data.get('date')) if item_data.get('date') else datetime.now(),
        'itemKey': item_key,
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
        'bibliography': rfw.get_bibliography_bbt_api(citekey),
        'notes': notes,
        'attachments': attachments,
    }

    # Jinja2 template for output literature note
#     template_str = """{%- macro truncateTitle(title, n) -%}
# {%- set words = title.split(' ') -%}
# {%- set truncatedTitle = ' '.join(words[:n]) -%}
# {{ truncatedTitle }}
# {%- endmacro %}
# {%- macro basename(filePath) -%}
# {%- set normalizedPath = filePath.replace("\\\\", "/") -%}
# {%- set fileParts = normalizedPath.split("/") -%}
# {%- set endpath = fileParts[-1] -%}
# {{- endpath -}}
# {%- endmacro %}
# ---
# category:
# - literaturenote
# tags:
# read: false
# in-progress: false
# linked: false
# aliases:
# - "{{ title }}"
# - "{{ truncateTitle(title, 5) }}"
# citekey: {{ citekey }}
# ZoteroTags:
# {% for tag in tags %}
# - {{ tag.tag | lower | replace(" ", "_") }}
# {% endfor %}
# ZoteroCollections:
# {% for collection in collections %}
# - {{ collection.name | lower | replace(" ", "_") }}
# {% endfor %}
# created date: {{ exportDate.strftime("%Y-%m-%d") }}
# modified date:
# ---
# > [!info]- [**Zotero**]({{ desktopURI }}) {% if DOI %} | [**DOI**](https://doi.org/{{ DOI }}){% endif %}{% if url %} | [**URL**]({{ url }}){% endif %}{% for attachment in attachments if attachment.path.endswith(".pdf") %} | **[[{{ basename(attachment.path) }}|PDF]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".html") %} | **[[{{ basename(attachment.path) }}|HTM]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".docx") %} | **[[{{ basename(attachment.path) }}|DOC]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".pptx") %} | **[[{{ basename(attachment.path) }}|PPT]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".txt") %} | **[[{{ basename(attachment.path) }}|TXT]]**{% endfor %}

# > {% if abstractNote %}
# > **Abstract**
# > {{ abstractNote.replace("\\n"," ") }}
# > {% endif %}
# {{ "" }}
# {%- for type, creators in creators|groupby("creatorType") %}
# > **{{ type.capitalize() }}**::
# {%- for creator in creators %}
# {%- if creator.name %} {{ creator.name }}{% else %} {{ creator.lastName }}, {{ creator.firstName }}{% endif %}{% if not loop.last %}, {% endif %}
# {%- endfor %}
# {% endfor %}
# > **Title**:: "{{ title }}"
# > **Date**:: {{ date.strftime("%Y-%m-%d") }}
# > **Citekey**:: {{ citekey }}
# > **ZoteroItemKey**:: {{ itemKey }}
# > **itemType**:: {{ itemType }}
# > **DOI**:: {{ DOI }}
# > **URL**:: {{ url }}
# > **Journal**:: {{ publicationTitle }}
# > **Volume**:: {{ volume }}
# > **Issue**:: {{ issue }}
# > **Book**:: {{ publicationTitle }}
# > **Publisher**:: {{ publisher }}
# > **Location**:: {{ place }}
# > **Pages**:: {{ pages }}
# > **ISBN**:: {{ ISBN }}
# > **ZoteroTags**:: {{ allTags }}
# > **Related**::{% for relation in relations if relation.citekey %} [[@{{ relation.citekey }}]]{% if not loop.last %}, {% endif %}{% endfor %}
# > {% if bibliography %} {{ bibliography }}{% endif %}
# {% block persist_Obsidian_Notes %}
# %% begin Obsidian Notes %%
# ___
# ==Delete this and write here. Don't delete the `persist` directives above and below.==
# ___
# {% endblock persist_Obsidian_Notes %}
# %% end Obsidian Notes %%
# {% if notes|length > 0 %}
# > [!note]- Zotero Note ({{ notes|length }})

# {%- for note in notes %}
# >{{ note.note.replace("# ", "### ").replace("\\n", "\\n> ") }}
# >{{ note.tags | map(attribute='tag') | join(', ') }}

# > 📝️ (modified: {{ note.dateModified.strftime("%Y-%m-%d") }}) [link](zotero://select/library/items/{{ note.key }}) - [web]({{ note.uri }})

# ---
# {% endfor %}
# {% endif %}
# """

    # Render the template
    template = Template(template_str, trim_blocks=True, lstrip_blocks=True)
    output_text = template.render(**data)

    output_file = output_dir / f'{citekey}.md'
    print(f'Writing to {output_file}')
    output_file.write_text(output_text, encoding='utf-8')
    print("Done.")


if __name__ == '__main__':
    # Example usage with a single item key
    # item_keys = ['I4G6IXQS']
    # Example usage with a list of item keys
    item_keys = ['I4G6IXQS', 'SAUNMD5H']  # Example with two keys

    if isinstance(item_keys, str):
        item_keys = [item_keys]

    # Fetch collections
    try:
        collection_key_to_name = {
            collection['key']: collection['data']['name']
            for collection in zot.all_collections()
        }
    except Exception as e:
        print(f"Error fetching collections: {e}")
        raise

    # Fetch items in batches of 50
    item_data = {}
    for i in range(0, len(item_keys), 50):
        batch_keys = item_keys[i : i + 50]
        try:
            items = zot.get_subset(batch_keys)
            item_data.update({item['data']['key']: item['data'] for item in items})
        except Exception as e:
            print(f"Error fetching items: {e}")
            raise

    for item_key in item_keys:
        create_literature_note(item_key, output_dir, item_data[item_key], collection_key_to_name)
