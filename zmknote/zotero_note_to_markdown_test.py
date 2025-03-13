from bs4 import BeautifulSoup
import re
import json
from urllib.parse import unquote
import zotero_to_obsidian_note as z2o
import pathlib as pl

# def zotero_note_html_to_md(html_content: str):
#     """Convert Zotero note HTML content to Obsidian-compatible markdown"""
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

# Test with the provided data
if __name__ == "__main__":
    # Your test HTML data here
    TEST_HTML = """<h2>Points</h2>
<ul>
<li>
Recommended reading in SQL course: <span class="citation" data-citation="%7B%22citationItems%22%3A%5B%7B%22uris%22%3A%5B%22http%3A%2F%2Fzotero.org%2Fusers%2F60638%2Fitems%2FB7TNABNU%22%5D%7D%5D%2C%22properties%22%3A%7B%7D%7D">(<span class="citation-item">Lawrence, 2022</span>)</span>
</li>
<li>
clear graph of a set of foreign keys
</li>
</ul>
<h2>SQL</h2>
<ul>
<li>
big list of SQL variants
</li>
<li>
scales "vertically": make a single server bigger
</li>
<li>
ACID stingent security complant (always)
</li>
<li>
<p>SQL use cases</p>
<ul>
<li>
ACID required by regulations
</li>
<li>
transactional
</li>
<li>
enterprise resource planning e.g. supply chain, human resources,…
</li>
</ul>
</li>
</ul>
<h2>NoSQL</h2>
<ul>
<li>
not always SQL (can do SQL too)
</li>
<li>
scaled "horizontally": I think this means can expand by adding a new compute node
</li>
<li>
use when data changes fast, must be scalable, and when it's non-structured
</li>
<li>
<p>usually doesn't meet stringent ACID standards</p>
<ul>
<li>
SQL often does
</li>
<li>
some NoSQL does e.g. Mongo's
</li>
</ul>
</li>
<li>
<p>big list of NoSQL types</p>
<ul>
<li>
Document
</li>
<li>
Key-value
</li>
<li>
Column-family stores
</li>
<li>
Graph
</li>
</ul>
</li>
<li>
<p>NoSQL use cases</p>
<ul>
<li>
transactional (can just do internal SQL-type tables), or when store unstructured
</li>
<li>
document and digital assets management
</li>
<li>
graph and network analysis
</li>
<li>
IoT
</li>
</ul>
</li>
</ul>
<p></p>
<p></p>"""
# %%
use_json_input = True
if use_json_input:
    test_dat_dir = pl.Path(r"C:\Users\scott\OneDrive\share\ref\refwrangle\zmknote\dat")
    
    pl.Path(r"C:\Users\scott\OneDrive\share\ref\refwrangle\zmknote\dat\zotero_item_date_YK4TVDBM.json")
    # Test with a sample JSON fed to a webhook listener. Assume it's for a zotero entry.
    #test_json_input_file = test_dat_dir / "zotero_item_date_YK4TVDBM.json"
    test_json_input_file = test_dat_dir / "zotero_item_date_LWXDDZCG.json"
    data = json.loads(test_json_input_file.read_text(encoding="utf-8"))

    if isinstance(data, list):
        item_jsons = [dict(item) for item in data]  # Convert each top-level element into a dict
        # assume it's a single zotero item, so only one json in the list
        TEST_HTML_JSON = item_jsons[0]['notes'][0]
        TEST_HTML = "\n".join(TEST_HTML_JSON.splitlines()[1:]) # remove mystery <div> @ top
    else:
        raise ValueError('expected a list')

# %%   
     
#obsidian_md = zotero_note_html_to_md(TEST_HTML)
obsidian_md = z2o.zotero_note_html_to_md(TEST_HTML)

# Save the result to a file to avoid tab/space confusion
outfile = pl.Path(r"C:\Users\scott\OneDrive\share\ref\obsidian\Obsidian Share Vault\Scratch Space\zotero_to_obsidian_output.md")
with open(outfile, "w", encoding="utf-8") as f:
    f.write(obsidian_md)

print("Conversion complete! Output saved to zotero_to_obsidian_output.md")

# Also print to console for reference
print("\n--- CONVERTED OUTPUT ---\n")
print(obsidian_md)
