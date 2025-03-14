from bs4 import BeautifulSoup
import re
import json
from urllib.parse import unquote
import zotero_to_obsidian_note as z2o
import pathlib as pl
from icecream import ic


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

# def zotero_note_html_to_md(html_content: str, remove_first_div: bool = False):
#     """
#     Convert Zotero note HTML content to Obsidian-compatible markdown
    
#     Args:
#         html_content: The HTML content to convert
#         remove_first_div: If True, removes the first div section if it exists
#     """
#     soup = BeautifulSoup(html_content, 'html.parser')

    
#     # Remove the first div if requested and if it exists
#     if remove_first_div:
#         first_div = soup.find('div')
#         if first_div:
#             print("\nWHAT WAS IN THE HTML\n")
#             print(html_content)

#             print("\nWHAT'S IN THE FIRST DIV (OR NOT)\n")
#             first_div = soup.find('div')
#             print(first_div.text)
            
#             first_div.extract()  # Removes the element from the tree

#             print("\nWHAT'S LEFT (OR NOT) AFTER EXTRACT\n")
#             print(soup)
#             print("\nEND of what's left after the extract (or not)\n")
#         else:
#             print("\nNO FIRST DIV\n")
            
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
    
#     # Add proper spacing
#     result_lines = [""]  # Start with a blank line at the top
    
#     # Helper function to check if a line is a paragraph (not a list item, header, or blockquote)
#     def is_paragraph(line):
#         return line.strip() and not line.strip().startswith(('- ', '#', '>'))
    
#     # Process each line
#     for i, line in enumerate(md_lines):
#         # Add the current line
#         result_lines.append(line)
        
#         # If current line and next line are both paragraphs, add a blank line between them
#         if i < len(md_lines) - 1 and is_paragraph(line) and is_paragraph(md_lines[i+1]):
#             result_lines.append("")
    
#     # Join the result lines
#     markdown = '\n'.join(result_lines)
    
#     return markdown

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



# Test with a sample JSON fed to a webhook listener. Assume it's for a zotero entry.
test_dat_dir = pl.Path(r"C:\Users\scott\OneDrive\share\ref\refwrangle\zmknote\dat")
#test_json_input_file = test_dat_dir / "zotero_item_date_YK4TVDBM.json"
#test_json_input_file = test_dat_dir / "zotero_item_date_LWXDDZCG.json"
test_json_input_file = pl.Path(r"C:\Users\scott\tmp\zotero_item_dat.json")
data = json.loads(test_json_input_file.read_text(encoding="utf-8"))

if isinstance(data, list):
    item_jsons = [dict(item) for item in data]  # Convert each top-level element into a dict
    # assume it's a single zotero item, so only one json in the list
    TEST_HTML = item_jsons[0]['notes'][0]
    #print("REMOVED DIV REMOVAL")
    TEST_HTML = "\n".join(TEST_HTML.splitlines()[1:]) # remove mystery <div> @ top
else:
    raise ValueError('expected a list')

# %%   

from bs4 import BeautifulSoup
import json
from urllib.parse import unquote

def zotero_note_html_to_md(html_content: str, remove_first_div: bool = False):
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
            span.replace_with(span.get_text())  # Remove highlighting

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

    # Add proper spacing
    result_lines = [""]  # Start with a blank line at the top

    # Process each line
    for i, line in enumerate(md_lines):
        # Add the current line
        result_lines.append(line)
        # If current line and next line are both paragraphs, add a blank line between them
        if i < len(md_lines) - 1 and is_paragraph(line) and is_paragraph(md_lines[i+1]):
            result_lines.append("")

    # Join the result lines
    markdown = '\n'.join(result_lines)
    return markdown

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

def is_paragraph(line):
    return line.strip() and not line.strip().startswith(('- ', '#', '>'))

# # Test the function
# TEST_HTML = item_jsons[0]['notes'][0]
# markdown_content = zotero_note_html_to_md(TEST_HTML)
# print("Markdown content:")
# print(markdown_content)

# %%
     
obsidian_md = zotero_note_html_to_md(TEST_HTML)
#obsidian_md = z2o.zotero_note_html_to_md(TEST_HTML)

# Save the result to a file to avoid tab/space confusion
outfile = pl.Path(r"C:\Users\scott\OneDrive\share\ref\obsidian\Obsidian Share Vault\Scratch Space\zotero_to_obsidian_note_output.md")
with open(outfile, "w", encoding="utf-8") as f:
    f.write(obsidian_md)

print(f"Conversion complete! Output saved to {outfile}")

# Also print to console for reference
print("\n--- CONVERTED OUTPUT ---\n")
print(obsidian_md)
