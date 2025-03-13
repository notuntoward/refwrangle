from bs4 import BeautifulSoup
import re
import json
from urllib.parse import unquote

def convert_zotero_html_to_obsidian_md(html_content):
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
    for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'blockquote', 'p'], recursive=False):
        if element.name.startswith('h'):
            level = int(element.name[1])
            md_lines.append(f"{'#' * level} {element.get_text().strip()}")
        elif element.name in ['ul', 'ol']:
            list_lines = process_list(element, 0)
            md_lines.extend(list_lines)
        elif element.name == 'blockquote':
            quote_lines = element.get_text().strip().split('\n')
            md_lines.append('\n'.join([f"> {line.strip()}" for line in quote_lines]))
        elif element.name == 'p' and element.get_text().strip():
            md_lines.append(element.get_text().strip())
    
    # Join lines with proper spacing
    markdown = '\n'.join(md_lines)
    
    return markdown.strip()

def process_list(list_element, level=0):
    """Process a list element with proper indentation for nested lists"""
    lines = []
    
    for li in list_element.find_all('li', recursive=False):
        # Get list item text (without nested lists)
        item_text = get_list_item_text(li)
        
        # Add the list item with proper indentation
        if level == 0:
            lines.append(f"- {item_text}")
        else:
            lines.append(f"\t- {item_text}")
        
        # Process nested lists with consistent indentation
        for nested_list in li.find_all(['ul', 'ol'], recursive=False):
            nested_lines = process_list(nested_list, 1)  # Always use level 1 for nested
            lines.extend(nested_lines)
    
    return lines

def get_list_item_text(li_element):
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

# Test with the provided data
if __name__ == "__main__":
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
<p></p>
</div>"""

    obsidian_md = convert_zotero_html_to_obsidian_md(TEST_HTML)
    print(obsidian_md)
    
    # Compare with expected output
    EXPECTED_MD = """## Points
- Recommended reading in SQL course: [Lawrence, 2022](zotero://select/library/items/B7TNABNU)
- clear graph of a set of foreign keys
## SQL
- big list of SQL variants
- scales "vertically": make a single server bigger
- ACID stingent security complant (always)
- SQL use cases
	- ACID required by regulations
	- transactional
	- enterprise resource planning e.g. supply chain, human resources,…
## NoSQL
- not always SQL (can do SQL too)
- scaled "horizontally": I think this means can expand by adding a new compute node
- use when data changes fast, must be scalable, and when it's non-structured
- usually doesn't meet stringent ACID standards
	- SQL often does
	- some NoSQL does e.g. Mongo's
- big list of NoSQL types
	- Document
	- Key-value
	- Column-family stores
	- Graph
- NoSQL use cases
	- transactional (can just do internal SQL-type tables), or when store unstructured
	- document and digital assets management
	- graph and network analysis
	- IoT"""
    
    # Check if the output matches the expected format
    if obsidian_md.strip() == EXPECTED_MD.strip():
        print("\n✓ Output matches expected format exactly")
    else:
        print("\n✗ Output doesn't match expected format")
