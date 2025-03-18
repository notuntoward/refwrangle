"""This is the python companion to zotero_to_obsidian_note_action_tags.js.  Between then, they make an obsidian note(s) for selected zotero item(s).  This script converts the zotero metada coming from zotero_to_obsidian_note_action_tags.js via a webhook POST, and converts it to an obsidian literature note, fairly close to how the obsidian zotero integration plugin works (in fact the jinja2 template is a close mimic of the nunjucks template I use for the obsidian plugin.

But this method is much more convenient.

In a shell with the conda refwrangle environment activated, you sstart it like so: python zotero_to_obsidian_note_listener.py"""

import json
import pathlib as pl
import urllib
from encodings import utf_8
from typing import Union

import bs4
from flask import Flask, jsonify, request
from icecream import ic
from jinja2 import Template

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
> **ZoteroItemKey**:: {{ itemkey }}
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

def zotero_note_html
_to_md(complex_html: str) -> str:
    """Convert from html into Obsidian markdown one note of the 
    'notes' key in a Zotero item JSON export.
    
    Args:
        complex_html (str): The complex HTML string
        
    Returns:
        str: Obsidian Markdown"""
        
    # Parse the HTML
    soup = bs4.BeautifulSoup(complex_html, 'html.parser')
    
    # Initialize markdown output
    markdown_blocks = []
    
    # Find main content container
    main_div = soup.find('div')
    if not main_div:
        main_div = soup.body if soup.body else soup
    
    # Process text content at the div level
    if main_div.string and main_div.string.strip():
        markdown_blocks.append(main_div.string.strip())
    
    # Process block-level elements
    for child in main_div.children:
        if isinstance(child, str) and child.strip():
            markdown_blocks.append(child.strip())
            continue
            
        if not hasattr(child, 'name'):
            continue
            
        if child.name == 'blockquote':
            block_md = process_blockquote(child)
            if block_md:
                markdown_blocks.append(block_md)
        elif child.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = int(child.name[1])
            header_text = process_inline_formatting(child)
            markdown_blocks.append(f"{'#' * level} {header_text}")
        elif child.name == 'p':
            p_text = process_inline_formatting(child)
            if p_text.strip():
                markdown_blocks.append(p_text.strip())
        elif child.name == 'ul':
            list_items = []
            for li in child.find_all('li', recursive=False):
                li_text = process_inline_formatting(li)
                if li_text.strip():
                    list_items.append(f"- {li_text.strip()}")
            if list_items:
                markdown_blocks.append("\n".join(list_items))
        elif child.name == 'small':
            small_text = process_inline_formatting(child)
            if small_text.strip():
                markdown_blocks.append(small_text.strip())
    
    # Build final markdown with proper spacing
    markdown = ""
    prev_is_list_item = False
    prev_is_blockquote = False
    
    for block in markdown_blocks:
        is_list_item = block.startswith("- ")
        is_blockquote = block.startswith("> ")
        
        # Determine if we need a blank line
        if markdown:  # Not the first block
            if is_list_item and prev_is_list_item:
                # No blank line between list items
                markdown += "\n" + block
            elif is_blockquote and prev_is_blockquote:
                # No blank line between blockquote blocks (already handled within process_blockquote)
                markdown += "\n" + block
            else:
                # Add blank line between different block types
                markdown += "\n\n" + block
        else:
            # First block
            markdown += block
        
        prev_is_list_item = is_list_item
        prev_is_blockquote = is_blockquote
    
    return markdown + "\n" # separate from next note, if any

def process_blockquote(blockquote: bs4.element.Tag) -> str:
    """Process a blockquote element into markdown format with proper paragraph spacing."""
    # Initialize result list
    result = []
    
    # Process each paragraph or element within the blockquote
    for element in blockquote.children:
        if isinstance(element, str):
            if element.strip():
                # Add non-empty text nodes as lines
                for line in element.strip().split('\n'):
                    if line.strip():
                        result.append(f"> {line.strip()}")
        elif element.name == 'p':
            # Process each paragraph
            p_text = process_inline_formatting(element)
            if p_text.strip():
                # Split paragraph text into lines if it contains newlines
                for line in p_text.strip().split('\n'):
                    if line.strip():
                        result.append(f"> {line.strip()}")
                
                # Add empty blockquote line after paragraph
                result.append(">")
        else:
            # Process other elements (headings, lists, etc.) in the blockquote
            formatted_text = process_inline_formatting(element)
            if formatted_text.strip():
                # Split into lines
                for line in formatted_text.strip().split('\n'):
                    if line.strip():
                        result.append(f"> {line.strip()}")
                
                # Add empty blockquote line
                result.append(">")
    
    # Remove trailing empty blockquote if present
    if result and result[-1] == ">":
        result.pop()
    
    return "\n".join(result)

def process_inline_formatting(element: Union[str, bs4.element.Tag]) -> str:
    """
    Process inline HTML formatting to markdown.
    Handles citations, links, bold, italic, and highlights.
    """
    if isinstance(element, str):
        return element
    
    result = ""
    
    # Process each child node
    for child in element.contents:
        if isinstance(child, str):
            result += child
        elif child.name == 'span':
            # Citation handling
            if 'citation' in child.get('class', []):
                citation_item = child.find(class_='citation-item')
                if citation_item:
                    citation_text = citation_item.get_text(strip=True)
                    
                    # Extract Zotero ID from citation data
                    citation_data = child.get('data-citation', '')
                    if citation_data:
                        try:
                            citation_json = json.loads(urllib.parse.unquote(citation_data))
                            if 'citationItems' in citation_json and citation_json['citationItems']:
                                uri = citation_json['citationItems'][0]['uris'][0]
                                zotero_id = uri.split('/')[-1]
                                result += f"([{citation_text}](zotero://select/library/items/{zotero_id}))"
                                continue
                        except:
                            pass
                
                # Fallback for citation
                result += f"({child.get_text(strip=True)})"
                
            # Highlight handling
            elif child.get('style') and ('background-color' in child.get('style') or 'highlight' in child.get('style')):
                highlighted_text = process_inline_formatting(child)
                result += f"=={highlighted_text}=="
                
            # Bold/Italic handling via style
            elif child.get('style'):
                style = child.get('style')
                text = process_inline_formatting(child)
                
                is_bold = 'bold' in style or 'font-weight' in style
                is_italic = 'italic' in style or 'font-style' in style
                
                if is_bold and is_italic:
                    result += f"***{text}***"
                elif is_bold:
                    result += f"**{text}**"
                elif is_italic:
                    result += f"*{text}*"
                else:
                    result += text
            else:
                # Regular span
                result += process_inline_formatting(child)
                
        # Bold elements
        elif child.name in ['strong', 'b']:
            text = process_inline_formatting(child)
            result += f"**{text}**"
            
        # Italic elements
        elif child.name in ['em', 'i']:
            text = process_inline_formatting(child)
            result += f"*{text}*"
            
        # Links
        elif child.name == 'a':
            text = process_inline_formatting(child)
            href = child.get('href', '')
            result += f"[{text}]({href})"
            
        # Other elements
        else:
            result += process_inline_formatting(child)
    
    return result

# %%

# Where the obsidian lit notes. generated by this webhook listener are written
output_dir = pl.Path(r"C:\Users\scott\OneDrive\share\ref\obsidian\Obsidian Share Vault\Scratch Space")

app = Flask(__name__)

@app.route('/', methods=['POST'])
def webhook_listener():
    try:
        # Parse incoming JSON data
        data = request.get_json()
        print(f'Got data')
        #print(f'got data: {data}')
        
        if isinstance(data, list):
            # DON'T NEED THIS: get_json() does it automatically
            #item_jsons = [dict(item) for item in data]  # Convert each top-level element into a dict
            print("Received and parsed data")
            # print("Received and processed data:", processed_data)
            
            # for each zotero item...
            # convert note html to markdown (couldn't get the markdown conversion to work in javascript)
            for item_json in data:
                output_file = output_dir / f'{item_json["citekey"]}.md'
                notes_md = []
                for note_html in item_json['notes']:
                    md_note = zotero_note_html_to_md(note_html)
                    notes_md.append(md_note)
                    # outdir = pl.Path(r"C:\Users\scott\tmp")
                    # (outdir / "listener_JSON_html.html").write_text(note_html,encoding='utf-8')
                    # (outdir / "listener_converted_markdown.md").write_text(md_note,encoding='utf-8')

                item_json['notes'] = notes_md
                print(f"{item_json['notes']=}")

                ic(item_json['citekey'])
                try:
                    with output_file.open('w', encoding='utf-8') as f:
                        template = Template(template_str, trim_blocks=True, lstrip_blocks=True)
                        output_text = template.render(**item_json)
                        print(f'Writing to {output_file}')
                        f.write(output_text)
                except ValueError as e:
                    print(f'Error writing to {output_file}: {e}')
            return jsonify({"status": "success", "message": "Data received and processed"}), 200
        else:
            return jsonify({"status": "error", "message": "Invalid data format.  Expected a list."}), 400
    
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5050)
