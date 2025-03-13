from bs4 import BeautifulSoup
import re
import json
from urllib.parse import unquote

def convert_zotero_html_to_obsidian_md(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Process citations with CORRECTED ZOTERO URI FORMAT
    for citation in soup.find_all('span', class_='citation'):
        citation_item = citation.find('span', class_='citation-item')
        if citation_item and citation.get('data-citation'):
            try:
                citation_data = unquote(citation['data-citation'])
                citation_json = json.loads(citation_data, strict=False)
                
                if citation_json.get('citationItems') and citation_json['citationItems'][0].get('uris'):
                    raw_uri = citation_json['citationItems'][0]['uris'][0]
                    # Extract just the item ID and create proper zotero URI
                    item_id = raw_uri.split('/')[-1]
                    zotero_uri = f"zotero://select/library/items/{item_id}"
                    citation.replace_with(f"[{citation_item.text}]({zotero_uri})")
            except Exception as e:
                print(f"Citation parsing error: {e}")
                citation.replace_with(f"{citation_item.text}")
    
    # Process highlighted text
    for span in soup.find_all('span'):
        style = span.get('style', '')
        if 'background-color' in style:
            span.replace_with(f"=={span.get_text()}==")
    
    # Manual conversion to ensure control over exact output format
    html = str(soup)
    md = html
    
    # Handle blockquotes
    md = re.sub(r'<blockquote>\s*<p>(.*?)</p>\s*<p>(.*?)</p>\s*</blockquote>', 
               r'> \1\n> \2\n\n', md, flags=re.DOTALL)
    md = re.sub(r'<blockquote>\s*<p>(.*?)</p>\s*</blockquote>', 
               r'> \1\n\n', md, flags=re.DOTALL)
    
    # Handle headings (h1-h6)
    for i in range(1, 7):
        md = re.sub(f'<h{i}>(.*?)</h{i}>', f'{"#" * i} \\1', md)
    
    # Handle paragraphs - but not if already in blockquotes
    md = re.sub(r'<p>((?!>).*?)</p>', r'\1\n\n', md)
    
    # Handle bold - both <strong> and <b> tags (Zotero typically uses <b>)
    md = re.sub(r'<(strong|b)>(.*?)</\1>', r'**\2**', md)
    
    # Handle em (italic) - both <em> and <i> tags
    md = re.sub(r'<(em|i)>(.*?)</\1>', r'*\2*', md)
    
    # Handle links
    md = re.sub(r'<a href="(.*?)".*?>(.*?)</a>', r'[\2](\1)', md)
    
    # Handle lists
    # Unordered lists
    md = re.sub(r'<ul>(.*?)</ul>', lambda m: process_list(m.group(1), '-'), md, flags=re.DOTALL)
    # Ordered lists
    md = re.sub(r'<ol>(.*?)</ol>', lambda m: process_list(m.group(1), '1.'), md, flags=re.DOTALL)
    
    # Remove div tags
    md = re.sub(r'</?div.*?>', '', md)
    
    # Clean up &nbsp; entities
    md = md.replace('&nbsp;', ' ')
    
    # Remove any remaining HTML tags
    md = re.sub(r'<.*?>', '', md)
    
    # Fix any escaped periods in headers
    md = re.sub(r'(#+\s+.*?)\\\.', r'\1.', md)
    
    # Remove multiple consecutive newlines
    md = re.sub(r'\n{3,}', '\n\n', md)
    
    # Final cleanup for blockquotes
    md = re.sub(r'^>[ \t]*$', '>', md, flags=re.MULTILINE)
    
    return md.strip()

def process_list(list_content, marker):
    """Process HTML list items into Markdown list items"""
    # Extract list items
    items = re.findall(r'<li>(.*?)</li>', list_content, re.DOTALL)
    result = ""
    for item in items:
        # Check if the item has a nested list
        if '<ul>' in item or '<ol>' in item:
            # Split the content and the nested list
            parts = re.split(r'(<[ou]l>.*?</[ou]l>)', item, 1, re.DOTALL)
            if len(parts) >= 3:
                text = parts[0].strip()
                nested_list = parts[1]
                # Determine the nested list type
                nested_marker = '-' if '<ul>' in nested_list else '1.'
                # Process the nested list with indentation
                processed_nested = process_list(nested_list, nested_marker)
                processed_nested = '\n'.join('  ' + line for line in processed_nested.split('\n'))
                result += f"{marker} {text}\n{processed_nested}\n"
        else:
            result += f"{marker} {item.strip()}\n"
    return result

# Test HTML data
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
scales “vertically”: make a single server bigger
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
scaled “horizontally”: I think this means can expand by adding a new compute node
</li>
<li>
use when data changes fast, must be scalable, and when it’s non-structured
</li>
<li>
<p>usually doesn’t meet stringent ACID standards</p>
<ul>
<li>
SQL often does
</li>
<li>
some NoSQL does e.g. Mongo’s
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

# Main execution
if __name__ == "__main__":
    try:
        obsidian_md = convert_zotero_html_to_obsidian_md(TEST_HTML)
        print("======= SUCCESSFUL CONVERSION =======")
        print(obsidian_md)
        
        # Verify formatting
        if "**Here is some bold text.**" in obsidian_md:
            print("\n✓ Bold formatting is correct")
        
        if "> A block quote that\n> is multiline" in obsidian_md:
            print("✓ Blockquote formatting is correct")
            
        if "[Grose, 2024](zotero://select/library/items/" in obsidian_md:
            print("✓ Citation link formatting is correct with proper URI format")
    except Exception as e:
        print(f"ERROR: {e}")
