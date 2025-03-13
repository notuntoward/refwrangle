"""Python functions for converting a zotero item's metadata into an obsidian note. Intended 
to be called directly from zotero, instead of from Obsidian, as the Obsidian Zotero Integration 
plugin requires.  Formattig is a similar to notes created by Zotero Integraion,
in fact, the jinja2 template used here tries to match the output of my Zotero Integration
nunjucks template (currently Obsidian/templates/literature note.md)."""

import html
import pathlib as pl
import re
import sys
from datetime import datetime

import dateutil.parser as dp
from icecream import ic
from jinja2 import Template
from markdownify import markdownify
from pyzotero import zotero
from bs4 import BeautifulSoup
import json
from urllib.parse import unquote

# Define paths and credentials
refwrangle_dir = pl.Path('~/ref/refwrangle').expanduser()
sys.path.append(str(refwrangle_dir))
import refwrangle as rfw  # Import your custom refwrangle module

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
- {{ tag | lower | replace(" ", "_") }}
{% endfor %}
ZoteroCollections: 
{% for collection in collections %}
- {{ collection | lower | replace(" ", "_") }}
{% endfor %}
created date: {{ exportDate }}
modified date:
---

> [!info]- &nbsp;[**Zotero**]({{ desktopURI }}) {% if DOI %} | [**DOI**](https://doi.org/{{ DOI }}){% endif %}{% if url %} | [**URL**]({{ url }}){% endif %}{% for attachment in attachments if attachment.path.endswith(".pdf") %} | **[[{{ basename(attachment.path) }}|PDF]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".html") %} | **[[{{ basename(attachment.path) }}|HTM]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".docx") %} | **[[{{ basename(attachment.path) }}|DOC]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".pptx") %} | **[[{{ basename(attachment.path) }}|PPT]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".txt") %} | **[[{{ basename(attachment.path) }}|TXT]]**{% endfor %}

> {%- if abstractNote %}
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
> **Date**:: {{ date }}
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
> **ZoteroCollections**:: {{ collections }}
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
> [!note]- &nbsp;Zotero Note ({{ notes|length }})
>
{%- for note in notes -%}
>{{ note.replace("# ", "### ").replace("\\n", "\\n> ")}}
>{{ note.tags | map(attribute='tag') | join(', ') }}
---
{%- endfor -%}
{% endif %}
"""
# %%
def parse_date(date_str: str, format_dts: str) -> str:
    """Parses a date string and returns it in a standard format."""
    try:
        date = dp.parse(date_str)
        return date.strftime(format_dts)
    except Exception as e:
        print(f"Error parsing date {date_str}: {e}")
        return ''


# raw perplexity, not the original that worked in the test file
# def zotero_note_html_to_md(html_content: str):
#     """Convert Zotero note HTML content to Obsidian-compatible markdown"""
#     if not html_content:
#         return ""
        
#     soup = BeautifulSoup(html_content, 'html.parser')
    
#     # Process citations with correct Zotero URI format
#     for citation in soup.find_all('span', class_='citation'):
#         citation_item = citation.find('span', class_='citation-item')
#         if citation_item and citation.get('data-citation'):
#             try:
#                 citation_data = unquote(citation['data-citation'])
#                 citation_json = json.loads(citation_data, strict=False)
                
#                 if citation_json.get('citationItems') and citation_json['citationItems'][0].get('uris'):
#                     raw_uri = citation_json['citationItems'][0]['uris'][0]
#                     item_id = raw_uri.split('/')[-1]
#                     zotero_uri = f"zotero://select/library/items/{item_id}"
#                     citation.replace_with(f"[{citation_item.text}]({zotero_uri})")
#             except Exception as e:
#                 print(f"Citation parsing error: {e}")
#                 citation.replace_with(citation_item.text)
    
#     # Process formatting tags
#     for tag in soup.find_all(['b', 'strong']):
#         tag.replace_with(f"**{tag.get_text()}**")
    
#     for tag in soup.find_all(['i', 'em']):
#         tag.replace_with(f"*{tag.get_text()}*")
    
#     for span in soup.find_all('span'):
#         if span.get('style') and 'background-color' in span.get('style'):
#             span.replace_with(f"=={span.get_text()}==")
    
#     # Build markdown document
#     md_lines = []
    
#     # Get content area - body or whole document
#     content_area = soup.body if soup.body else soup
    
#     # Process all headings throughout the document
#     for heading in content_area.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
#         level = int(heading.name[1])
#         md_lines.append(f"{'#' * level} {heading.get_text().strip()}")
    
#     # Process all paragraphs
#     for para in content_area.find_all('p'):
#         if para.get_text().strip():
#             md_lines.append(para.get_text().strip())
    
#     # Process lists - only top-level ones to avoid duplication
#     for list_elem in [lst for lst in content_area.find_all(['ul', 'ol']) 
#                       if not lst.find_parent(['ul', 'ol'])]:
#         list_lines = process_list(list_elem, is_root=True)
#         md_lines.extend(list_lines)
    
#     # Process blockquotes
#     for quote in content_area.find_all('blockquote'):
#         quote_lines = quote.get_text().strip().split('\n')
#         md_lines.append('\n'.join([f"> {line.strip()}" for line in quote_lines]))
    
#     # Fallback: If no structured content found, try divs
#     if not md_lines:
#         for div in content_area.find_all('div'):
#             if div.get_text().strip():
#                 md_lines.append(div.get_text().strip())
    
#     # Last resort: get all text if nothing else worked
#     if not md_lines and content_area.get_text().strip():
#         md_lines.append(content_area.get_text().strip())
    
#     # Join lines with proper spacing
#     markdown = '\n\n'.join(md_lines)
    
#     return markdown.strip()

# def process_list(list_element: BeautifulSoup, is_root: bool = False, prefix: str = '') -> list[str]:
#     """Process a list element with proper indentation for nested lists"""
#     lines = []
    
#     for li in list_element.find_all('li', recursive=False):
#         # Get list item text (without nested lists)
#         item_text = get_list_item_text(li)
        
#         # Format the list item with proper indentation
#         lines.append(f"{prefix}- {item_text}")
        
#         # Process nested lists with tab indentation
#         for nested_list in li.find_all(['ul', 'ol'], recursive=False):
#             # Use a tab character for nested lists
#             nested_prefix = '\t' if is_root else prefix + '\t'
#             nested_lines = process_list(nested_list, is_root=False, prefix=nested_prefix)
#             lines.extend(nested_lines)
    
#     return lines

# def get_list_item_text(li_element: BeautifulSoup) -> str:
#     """Extract text content from a list item, excluding nested lists"""
#     # Check for paragraphs first
#     paragraphs = li_element.find_all('p', recursive=False)
#     if paragraphs:
#         return paragraphs[0].get_text().strip()
    
#     # Otherwise collect direct text content
#     content = []
#     for child in li_element.children:
#         if isinstance(child, str):
#             if child.strip():
#                 content.append(child.strip())
#         elif hasattr(child, 'name') and child.name not in ['ul', 'ol']:
#             text = child.get_text().strip()
#             if text:
#                 content.append(text)
    
#     return ' '.join(content).strip()
    
# def zotero_note_html_to_md(html_content: str):
#     """Convert Zotero note HTML content to Obsidian-compatible markdown"""
    
#     soup = BeautifulSoup(html_content.splitlines(), 'html.parser')
    
#     # Process citations with correct Zotero URI format
#     for citation in soup.find_all('span', class_='citation'):
#         citation_item = citation.find('span', class_='citation-item')
#         if citation_item and citation.get('data-citation'):
#             try:
#                 citation_data = unquote(citation['data-citation'])
#                 citation_json = json.loads(citation_data, strict=False)
                
#                 if citation_json.get('citationItems') and citation_json['citationItems'][0].get('uris'):
#                     raw_uri = citation_json['citationItems'][0]['uris'][0]
#                     item_id = raw_uri.split('/')[-1]
#                     zotero_uri = f"zotero://select/library/items/{item_id}"
#                     citation.replace_with(f"[{citation_item.text}]({zotero_uri})")
#             except Exception as e:
#                 print(f"Citation parsing error: {e}")
#                 citation.replace_with(citation_item.text)
    
#     # Process formatting tags
#     for tag in soup.find_all(['b', 'strong']):
#         tag.replace_with(f"**{tag.get_text()}**")
    
#     for tag in soup.find_all(['i', 'em']):
#         tag.replace_with(f"*{tag.get_text()}*")
    
#     for span in soup.find_all('span'):
#         if span.get('style') and 'background-color' in span.get('style'):
#             span.replace_with(f"=={span.get_text()}==")
    
#     # Build markdown document
#     md_lines = []
    
#     # Process each type of element in order of appearance
#     for element in soup.body.children if soup.body else soup.children:
#         ic(element.name)
#         if element.name:
#             if element.name.startswith('h'):
#                 level = int(element.name[1])
#                 md_lines.append(f"{'#' * level} {element.get_text().strip()}")
#             elif element.name in ['ul', 'ol']:
#                 list_lines = process_list(element, is_root=True)
#                 md_lines.extend(list_lines)
#             elif element.name == 'blockquote':
#                 quote_lines = element.get_text().strip().split('\n')
#                 md_lines.append('\n'.join([f"> {line.strip()}" for line in quote_lines]))
#             elif element.name == 'p' and element.get_text().strip():
#                 md_lines.append(element.get_text().strip())
    
#     ic(md_lines)
#     # Join lines with proper spacing - using single newlines to match expected output
#     markdown = '\n'.join(md_lines)
    
#     return markdown.strip()

# def process_list(list_element: BeautifulSoup, is_root: bool = False, prefix: str = '') -> list[str]:
#     """Process a list element with proper indentation for nested lists"""
#     lines = []
    
#     for li in list_element.find_all('li', recursive=False):
#         # Get list item text (without nested lists)
#         item_text = get_list_item_text(li)
        
#         # Format the list item with proper indentation
#         lines.append(f"{prefix}- {item_text}")
        
#         # Process nested lists with tab indentation
#         for nested_list in li.find_all(['ul', 'ol'], recursive=False):
#             # Use a tab character for nested lists
#             nested_prefix = '\t' if is_root else prefix + '\t'
#             nested_lines = process_list(nested_list, is_root=False, prefix=nested_prefix)
#             lines.extend(nested_lines)
    
#     return lines

# def get_list_item_text(li_element: BeautifulSoup) -> str:
#     """Extract text content from a list item, excluding nested lists"""
#     # Check for paragraphs first
#     paragraphs = li_element.find_all('p', recursive=False)
#     if paragraphs:
#         return paragraphs[0].get_text().strip()
    
#     # Otherwise collect direct text content
#     content = []
#     for child in li_element.children:
#         if isinstance(child, str):
#             if child.strip():
#                 content.append(child.strip())
#         elif hasattr(child, 'name') and child.name not in ['ul', 'ol']:
#             text = child.get_text().strip()
#             if text:
#                 content.append(text)
    
#     return ' '.join(content).strip()

def zotero_note_html_to_md(html_content: str):
    """Convert Zotero note HTML content to Obsidian-compatible markdown"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Process citations with correct Zotero URI format
    for citation in soup.find_all('span', class_='citation'):
        citation_item = citation.find('span', class_='citation-item')
        if citation_item and citation.get('data-citation'):
            try:
                citation_data = unquote(citation['data-citation'])
                citation_json = json.loads(citation_data, strict=False)
                
                if citation_json.get('citationItems') and citation_json['citationItems'][0].get('uris'):
                    raw_uri = citation_json['citationItems'][0]['uris'][0]
                    item_id = raw_uri.split('/')[-1]
                    zotero_uri = f"zotero://select/library/items/{item_id}"
                    citation.replace_with(f"[{citation_item.text}]({zotero_uri})")
            except Exception as e:
                print(f"Citation parsing error: {e}")
                citation.replace_with(citation_item.text)
    
    # Process formatting tags
    for tag in soup.find_all(['b', 'strong']):
        tag.replace_with(f"**{tag.get_text()}**")
    
    for tag in soup.find_all(['i', 'em']):
        tag.replace_with(f"*{tag.get_text()}*")
    
    for span in soup.find_all('span'):
        if span.get('style') and 'background-color' in span.get('style'):
            span.replace_with(f"=={span.get_text()}==")
    
    # Build markdown document
    md_lines = []
    
    # Process each type of element in order of appearance
    for element in soup.body.children if soup.body else soup.children:
        if element.name:
            if element.name.startswith('h'):
                level = int(element.name[1])
                md_lines.append(f"{'#' * level} {element.get_text().strip()}")
            elif element.name in ['ul', 'ol']:
                list_lines = process_list(element, is_root=True)
                md_lines.extend(list_lines)
            elif element.name == 'blockquote':
                quote_lines = element.get_text().strip().split('\n')
                md_lines.append('\n'.join([f"> {line.strip()}" for line in quote_lines]))
            elif element.name == 'p' and element.get_text().strip():
                md_lines.append(element.get_text().strip())
    
    # Join lines with proper spacing - using single newlines to match expected output
    markdown = '\n'.join(md_lines)
    
    return markdown.strip()

def process_list(list_element: BeautifulSoup, is_root: bool = False, prefix: str = '') -> list[str]:
    """Process a list element with proper indentation for nested lists"""
    lines = []
    
    for li in list_element.find_all('li', recursive=False):
        # Get list item text (without nested lists)
        item_text = get_list_item_text(li)
        
        # Format the list item with proper indentation
        lines.append(f"{prefix}- {item_text}")
        
        # Process nested lists with tab indentation
        for nested_list in li.find_all(['ul', 'ol'], recursive=False):
            # Use a tab character for nested lists
            nested_prefix = '\t' if is_root else prefix + '\t'
            nested_lines = process_list(nested_list, is_root=False, prefix=nested_prefix)
            lines.extend(nested_lines)
    
    return lines

def get_list_item_text(li_element: BeautifulSoup) -> str:
    """Extract text content from a list item, excluding nested lists"""
    # Check for paragraphs first
    paragraphs = li_element.find_all('p', recursive=False)
    if paragraphs:
        return paragraphs[0].get_text().strip()
    
    # Otherwise collect direct text content
    content = []
    for child in li_element.children:
        if isinstance(child, str):
            if child.strip():
                content.append(child.strip())
        elif hasattr(child, 'name') and child.name not in ['ul', 'ol']:
            text = child.get_text().strip()
            if text:
                content.append(text)
    
    return ' '.join(content).strip()

def write_literature_note(item_key: str, output_file: pl.Path, item_data: dict, 
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
                ic(html_note)
                pl.Path(r"C:\Users\scott\tmp\html_content.html").write_text(html_note)
                markdown_note = zotero_note_html_to_md(html_note) if html_note else ''
                ic(markdown_note)
                notes.append(markdown_note)

                # markdown_note = markdownify(html_note) if html_note else ''
                # # Custom formatting adjustments
                # markdown_note = re.sub(r'\*\*%', r'**', markdown_note)  # Fix bolded percentages
                # markdown_note = markdown_note.replace('+', '-')  # Escape '+' characters

                # # Improved list formatting
                # markdown_note = re.sub(
                #     r'^\s*([+\-*])\s*(.*)$', r'\1 \2', markdown_note, flags=re.MULTILINE
                # )  # Fix up lists
                # notes.append({
                #     'note': markdown_note,
                #     # TODO: verify that this is really the date the note (not entry) was modified, or just get rid of it
                #     'dateModified': parse_date(child['data'].get('dateModified'), '%Y-%m-%d %H:%M:%S'),
                #     'key': child['data'].get('key'),
                #     'uri': child['data'].get('uri'),
                #     'tags': child['data'].get('tags', []),
                # })
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
        'desktopURI': f'zotero://select/library/items/{item_key}',
        'DOI': item_data.get('DOI', ''),
        'url': item_data.get('url', ''),
        'abstractNote': item_data.get('abstractNote', ''),
        'creators': item_data.get('creators', []),
        'date': parse_date(item_data.get('date'), "%Y-%m-%d") if item_data.get('date') else '',
        'itemKey': item_key,
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

    #ic(data)
    # Render the template
    template = Template(template_str, trim_blocks=True, lstrip_blocks=True)
    output_text = template.render(**data)

    print(f'Writing to {output_file}')
    output_file.write_text(output_text, encoding='utf-8')

def write_literature_notes(item_keys: list[str], output_dir: pl.Path, local_api: bool = False) -> None:
    """Writes literature notes for given Zotero item keys to the specified output directory."""

    if isinstance(item_keys, str):
        item_keys = [item_keys]

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
    for i in range(0, len(item_keys), 50):
        batch_keys = item_keys[i : i + 50]
        try:
            items = zot.get_subset(batch_keys)
            item_data.update({item['data']['key']: item['data'] for item in items})
        except Exception as e:
            print(f"Error fetching items: {e}")
            raise

    for item_key in item_keys:
        item_data_this = item_data[item_key]
        output_file = output_dir / f'{rfw.get_citation_key(item_data_this)}.md'
        
        write_literature_note(item_key, output_file, item_data_this , collection_key_to_name, zot)
        
    print("Done.")
    timer.mark()

if __name__ == '__main__':
    # Example usage with a single item key
    # item_keys = ['I4G6IXQS']
    # Example usage with a list of item keys
    item_keys = ['I4G6IXQS', 'U7NTFFTP']  # Example with two keys
    
    output_dir = pl.Path(r'C:\Users\scott\OneDrive\share\ref\obsidian\Obsidian Share Vault\Scratch Space')

    write_literature_notes(item_keys, output_dir)
