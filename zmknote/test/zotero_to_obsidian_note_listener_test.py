"""A test of a flask webhook interface with zotero, with dialog buttons that popup if the file the 
listener wants to generate already exists.  The only way to do this in a decent way in python was to
popup the dialog in a browser, unfortunately.  The exruciating details are here:

https://www.perplexity.ai/search/the-javascript-below-is-intend-Tic7.jP4TQiZ6R9CAl9EBQ

The companion javascript for this goes in zotero action and tags plugin. and is multikey_sender_test.js"""

from flask import Flask, request, jsonify, render_template_string, redirect
import logging
import json
from datetime import datetime
import time
import threading
from pathlib import Path
import sys
import os
import uuid
import webbrowser

import json
import pathlib as pl
import urllib
from encodings import utf_8
from typing import Union

import bs4
from flask import Flask, jsonify, request
from icecream import ic
from jinja2 import Template

# Create storage directory path
STORAGE_DIR = Path("~/tmp/zotero_items").expanduser()
LISTEN_PORT = 5050

# Jinja2 template for output obsidian literature note.  
# DON'T TOUCH ANY SPACES
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

def zotero_note_html_to_md(zotero_note_html: str) -> str:
    """Convert from html into Obsidian markdown one note of the 
    'notes' key in a Zotero item JSON export."""
        
    soup = bs4.BeautifulSoup(zotero_note_html, 'html.parser')
    
    markdown_blocks = [] # obsidian note markdown
    
    # copy the zotero note string inside the s/b only <div>, but checks body just in case
    main_div = soup.find('div')
    if not main_div:
        main_div = soup.body if soup.body else soup
    
    # if no html structure, just get the pure text (won't have children)
    if main_div.string and main_div.string.strip():
        markdown_blocks.append(main_div.string.strip())
    
    # get structured blocks (won't do anything if main_div.string contained anything
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
            header_text = convert_inline_formatting(child)
            markdown_blocks.append(f"{'#' * level} {header_text}")
        elif child.name == 'p':
            p_text = convert_inline_formatting(child)
            if p_text.strip():
                markdown_blocks.append(p_text.strip())
        elif child.name == 'ul':
            list_items = []
            for li in child.find_all('li', recursive=False):
                li_text = convert_inline_formatting(li)
                if li_text.strip():
                    list_items.append(f"- {li_text.strip()}")
            if list_items:
                markdown_blocks.append("\n".join(list_items))
        elif child.name == 'small':
            small_text = convert_inline_formatting(child)
            if small_text.strip():
                markdown_blocks.append(small_text.strip())
    
    # Space the html block contents so that they look similar in obsidian markdown
    output_markdown = ""
    prev_is_list_item = False
    prev_is_blockquote = False
    
    for block in markdown_blocks:
        is_list_item = block.startswith("- ")
        is_blockquote = block.startswith("> ")
        
        # Determine if we need a blank line
        if output_markdown:  # Not the first block
            if is_list_item and prev_is_list_item:
                # No blank line between list items
                output_markdown += "\n" + block
            elif is_blockquote and prev_is_blockquote:
                # No blank line between blockquote blocks (already handled within process_blockquote)
                output_markdown += "\n" + block
            else:
                # Add blank line between different block types
                output_markdown += "\n\n" + block
        else:
            # First block
            output_markdown += block
        
        prev_is_list_item = is_list_item
        prev_is_blockquote = is_blockquote
    
    return output_markdown + "\n" # separate from next note, if any

def process_blockquote(blockquote: bs4.element.Tag) -> str:
    """Process a blockquote element into markdown format with proper paragraph spacing."""
    # Initialize result list
    markdown_chunks = []
    
    # Process each paragraph or element within the blockquote
    for element in blockquote.children:
        if isinstance(element, str):
            if element.strip():
                # Add non-empty text nodes as lines
                for line in element.strip().split('\n'):
                    if line.strip():
                        markdown_chunks.append(f"> {line.strip()}")
        elif element.name == 'p':
            # Process each paragraph
            p_text = convert_inline_formatting(element)
            if p_text.strip():
                # Split paragraph text into lines if it contains newlines
                for line in p_text.strip().split('\n'):
                    if line.strip():
                        markdown_chunks.append(f"> {line.strip()}")
                
                # Add empty blockquote line after paragraph
                markdown_chunks.append(">")
        else:
            # Process other elements (headings, lists, etc.) in the blockquote
            formatted_text = convert_inline_formatting(element)
            if formatted_text.strip():
                # Split into lines
                for line in formatted_text.strip().split('\n'):
                    if line.strip():
                        markdown_chunks.append(f"> {line.strip()}")
                
                # Add empty blockquote line
                markdown_chunks.append(">")
    
    # Remove trailing empty blockquote if present
    if markdown_chunks and markdown_chunks[-1] == ">":
        markdown_chunks.pop()
    
    return "\n".join(markdown_chunks)

def convert_inline_formatting(element: Union[str, bs4.element.Tag]) -> str:
    """ Convert inline HTML formatting to markdown.
    Handles citations, links, bold, italic, and highlights."""
    
    if isinstance(element, str):
        return element # you're already done
    
    # Convert each child to markdown
    output_markdown = ""
    for child in element.contents:
        if isinstance(child, str):
            output_markdown += child
        elif child.name == 'span':
            # Internal link to a zotero item: make it work from inside of obsidian w/ a URI substitute
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
                                output_markdown += f"([{citation_text}](zotero://select/library/items/{zotero_id}))"
                                continue
                        except:
                            pass
                
                # Fallback for citation
                output_markdown += f"({child.get_text(strip=True)})"
                
            # Highlights
            elif child.get('style') and ('background-color' in child.get('style') or 'highlight' in child.get('style')):
                highlighted_text = convert_inline_formatting(child)
                output_markdown += f"=={highlighted_text}=="
                
            # Bold/Italic handling via style
            elif child.get('style'):
                style = child.get('style')
                text = convert_inline_formatting(child)
                
                is_bold = 'bold' in style or 'font-weight' in style
                is_italic = 'italic' in style or 'font-style' in style
                
                if is_bold and is_italic:
                    output_markdown += f"***{text}***"
                elif is_bold:
                    output_markdown += f"**{text}**"
                elif is_italic:
                    output_markdown += f"*{text}*"
                else:
                    output_markdown += text
            else:
                # Regular span
                output_markdown += convert_inline_formatting(child)
                
        # Bold
        elif child.name in ['strong', 'b']:
            text = convert_inline_formatting(child)
            output_markdown += f"**{text}**"
            
        # Italic
        elif child.name in ['em', 'i']:
            text = convert_inline_formatting(child)
            output_markdown += f"*{text}*"
            
        # Web Links
        elif child.name == 'a':
            text = convert_inline_formatting(child)
            href = child.get('href', '')
            output_markdown += f"[{text}]({href})"
            
        # Other elements
        else:
            output_markdown += convert_inline_formatting(child)
    
    return output_markdown

# %%

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("zotero_watcher.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# For icecream debugging if available
try:
    from icecream import ic
except ImportError:
    def ic(*args, **kwargs):
        pass

# Create Flask app
app = Flask(__name__)

# Create lock for synchronization
dir_lock = threading.Lock()

# Dictionary to store overwrite/skip/skipall dialog results
dialog_results = {}
dialog_events = {}

# HTML template for the dialog
DIALOG_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            padding: 20px;
            max-width: 500px;
            margin: 0 auto;
        }
        .message {
            margin-bottom: 20px;
        }
        .buttons {
            display: flex;
            gap: 10px;
        }
        button {
            padding: 10px 15px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        .overwrite {
            background-color: #4CAF50;
            color: white;
        }
        .skip {
            background-color: #f44336;
            color: white;
        }
        .skip-all {
            background-color: #ff9800;
            color: white;
        }
    </style>
    <script>
        function submitAndClose(action) {
            // Submit the form via fetch API
            fetch('/dialog-response/{{ dialog_id }}', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: 'action=' + action
            })
            .then(response => {
                // Try multiple ways to close the window
                window.close();
                
                // If window is still open, try with a delay
                setTimeout(function() {
                    window.close();
                }, 100);
            })
            .catch(error => {
                console.error('Error:', error);
                // Still try to close the window even if there was an error
                window.close();
            });
            
            // Return false to prevent default form submission
            return false;
        }
    </script>
</head>
<body>
    <div class="message">{{ message }}</div>
    <div class="buttons">
        <button onclick="submitAndClose('overwrite');" class="overwrite">Overwrite</button>
        <button onclick="submitAndClose('cancel');" class="skip">Skip</button>
        {% if show_skip_all %}
        <button onclick="submitAndClose('cancel_all');" class="skip-all">Skip All</button>
        {% endif %}
    </div>
</body>
</html>
"""

def ensure_storage_dir(request_id):
    """
    Ensure the storage directory exists with proper synchronization.
    Returns True if successful, False otherwise.
    """
    with dir_lock:
        if not STORAGE_DIR.exists():
            logger.info(f"[{request_id}] Creating storage directory: {STORAGE_DIR}")
            try:
                STORAGE_DIR.mkdir(parents=True, exist_ok=True)
                # Small delay to ensure directory is fully created and visible to all threads
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"[{request_id}] Error creating directory: {e}")
                return False
        
        # Double-check directory exists
        if not STORAGE_DIR.exists():
            logger.error(f"[{request_id}] Directory does not exist after creation attempt: {STORAGE_DIR}")
            return False
            
        return True

@app.route('/dialog/<dialog_id>')
def show_dialog(dialog_id):
    """Show a dialog in the browser"""
    if dialog_id not in dialog_events:
        return "Dialog not found", 404
        
    dialog_data = dialog_events[dialog_id]
    return render_template_string(
        DIALOG_TEMPLATE,
        title="File Exists",
        message=dialog_data['message'],
        dialog_id=dialog_id,
        show_skip_all=dialog_data.get('show_skip_all', False)
    )

@app.route('/dialog-response/<dialog_id>', methods=['POST'])
def dialog_response(dialog_id):
    """Handle dialog response"""
    if dialog_id not in dialog_events:
        return "Dialog not found", 404
        
    action = request.form.get('action', 'cancel')
    logger.info(f"Dialog {dialog_id} response: {action}")
    
    # Store the result
    dialog_results[dialog_id] = action
    
    # Signal the event to notify the waiting thread
    dialog_events[dialog_id]['event'].set()
    
    # Return success - the browser window should be closed by JavaScript
    return "OK"

def show_web_dialog(title, message, options, request_id):
    """Show a dialog in the browser and wait for response"""
    dialog_id = f"dialog_{uuid.uuid4().hex[:8]}"
    
    # Create an event to wait for the response
    event = threading.Event()
    
    # Store dialog information
    dialog_events[dialog_id] = {
        'title': title,
        'message': message,
        'event': event,
        'show_skip_all': options == 'yesnocancel'
    }
    
    # URL for the dialog
    url = f"http://localhost:{LISTEN_PORT}/dialog/{dialog_id}"
    
    # Open the URL in a browser
    logger.info(f"[{request_id}] Opening dialog in browser: {url}")
    webbrowser.open(url)
    
    # Wait for response with timeout
    if not event.wait(timeout=60):
        logger.warning(f"[{request_id}] Dialog timeout after 60 seconds")
        # Clean up
        if dialog_id in dialog_events:
            del dialog_events[dialog_id]
        return "cancel"  # Default to cancel on timeout
    
    # Get the result
    result = dialog_results.get(dialog_id, "cancel")
    
    # Clean up
    if dialog_id in dialog_results:
        del dialog_results[dialog_id]
    if dialog_id in dialog_events:
        del dialog_events[dialog_id]
    
    return result
def show_overwrite_popup(citekey, is_last_item, total_items, request_id):
    """Display a popup asking whether to overwrite the file"""
    logger.info(f"[{request_id}] Showing overwrite popup for '{citekey}'")
    
    # Simple message for all cases
    message = f"File for citekey '{citekey}' already exists."
    
    # Use our web-based dialog
    result = show_web_dialog(
        "File Exists",
        message,
        "yesno" if (total_items == 1 or is_last_item) else "yesnocancel",
        request_id
    )
    
    logger.info(f"[{request_id}] User selected: {result} for '{citekey}'")
    return result

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Endpoint that receives webhook data from Zotero Tags and Actions plugin.
    Expects a JSON array of objects with zotero item information, including itemkey and citekey.
    """
    # Generate a unique ID for this request for traceability
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] Received webhook request")
    
    try:
        # Get the JSON data from the request
        webhook_item_list = request.get_json()
        
        if not webhook_item_list:
            logger.error(f"[{request_id}] No data received")
            return jsonify({"status": "error", "message": "No data received"}), 400
            
        if not isinstance(webhook_item_list, list):
            logger.error(f"[{request_id}] Expected JSON array, got {type(webhook_item_list)}: {webhook_item_list}")
            return jsonify({"status": "error", "message": "Expected JSON array"}), 400
        
        logger.info(f"[{request_id}] Processing {len(webhook_item_list)} items")
        ic(webhook_item_list)  # Debug the data
        
        # Ensure storage directory exists before processing
        if not ensure_storage_dir(request_id):
            return jsonify({
                "status": "error", 
                "message": "Failed to create storage directory",
                "request_id": request_id
            }), 500
        
        # Process the received items
        results = process_items(webhook_item_list, request_id)
        
        logger.info(f"[{request_id}] Completed processing with {len(results)} results")
        return jsonify({
            "status": "success", 
            "processed": len(results),
            "items": results,
            "request_id": request_id
        })
        
    except Exception as e:
        logger.exception(f"[{request_id}] Error processing webhook data: {str(e)}")
        return jsonify({"status": "error", "message": str(e), "request_id": request_id}), 500

def process_items(items, request_id):
    """
    Process Zotero items received from the webhook using EAFP approach.
    
    Args:
        items (list): List of dictionaries with itemkey and citekey
        request_id (str): Unique ID for this request
        
    Returns:
        list: Results of processing each item
    """
    cancel_all = False
    results = []
    
    logger.info(f"[{request_id}] Starting to process {len(items)} Zotero items")
    total_items = len(items)
    
    # Ensure storage directory exists first
    if not ensure_storage_dir(request_id):
        logger.error(f"[{request_id}] Could not ensure storage directory exists")
        return []
    
    for index, item in enumerate(items):
        if cancel_all:
            logger.info(f"[{request_id}] Skipping remaining items due to 'cancel all' selection")
            break
            
        # Extract keys from the item
        itemkey = item.get('itemkey')
        citekey = item.get('citekey')
        
        if not itemkey or not citekey:
            logger.warning(f"[{request_id}] Missing required keys in item: {item}")
            continue
        
        logger.info(f"[{request_id}] Processing item {index+1}/{total_items}: {citekey}")
        
        # make obsidian lit note markdown

        # zotero item note(s) to obsidian markdown
        notes_md = []
        for note_html in item['notes']:
            md_note = zotero_note_html_to_md(note_html)
            notes_md.append(md_note)
        item['notes'] = notes_md

        template = Template(template_str, trim_blocks=True, lstrip_blocks=True)
        obs_note_markdown = template.render(**item)
        
        # Write obsidian lit note without overwiting existing note unless user confirms
        
        filename = f"{citekey}.md"
        filepath = STORAGE_DIR / filename
        is_last_item = (index == total_items - 1)
        
        logger.debug(f"[{request_id}] Checking existence of: {filepath.resolve()}")

        def create_result_entry(itemkey: str, citekey: str, filepath: Path) -> dict:
            """Create a result entry dictionary with timestamp."""
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return {
                "itemkey": itemkey,
                "citekey": citekey,
                "timestamp": timestamp,
                "filepath": str(filepath)
            }
        
        try:
            # EAFP atomic file create approach:  Try to open the file in 'x' mode which fails if file exists
            logger.debug(f"[{request_id}] Attempting to create file exclusively: {filepath}")
            with open(filepath, 'x', encoding='utf-8') as f:
                # File created successfully, write the contents
                f.write(obs_note_markdown)
                logger.info(f"[{request_id}] Successfully created new file: {filepath}")
                
                results.append(create_result_entry(itemkey, citekey, filepath))
                
                logger.info(f"[{request_id}] Processed item: {citekey} (Zotero key: {itemkey})")
            
        except FileExistsError:
            # File already exists, ask if user wants to overwrite
            logger.info(f"[{request_id}] File already exists (caught exception): {filepath}")
            
            action = show_overwrite_popup(citekey, is_last_item, total_items, request_id)
            
            if action == "cancel":
                logger.info(f"[{request_id}] Skipping file: {filepath}")
                continue
            elif action == "cancel_all":
                logger.info(f"[{request_id}] Cancelling all remaining operations")
                cancel_all = True
                continue
            
            # User chose to overwrite, write to the file
            try:
                logger.debug(f"[{request_id}] Overwriting file: {filepath}")
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(obs_note_markdown)

                logger.info(f"[{request_id}] Successfully overwrote file: {filepath}")
                
                results.append(create_result_entry(itemkey, citekey, filepath))
                
                logger.info(f"[{request_id}] Processed item: {citekey} (Zotero key: {itemkey})")
            except Exception as e:
                logger.error(f"[{request_id}] Error overwriting file: {e}", exc_info=True)
                continue
                
        except Exception as e:
            # Other errors during file writing
            logger.error(f"[{request_id}] Error writing file: {e}", exc_info=True)
            continue
    
    return results

@app.route('/status', methods=['GET'])
def status():
    """Simple endpoint to verify the server is running"""
    # First ensure storage directory exists
    if not STORAGE_DIR.exists():
        return jsonify({
            "status": "running",
            "time": datetime.now().isoformat(),
            "storage_dir": str(STORAGE_DIR),
            "storage_exists": False,
            "files_in_dir": []
        })
    
    # Get files if directory exists
    try:
        files_list = [f.name for f in STORAGE_DIR.iterdir() if f.is_file()]
    except Exception as e:
        files_list = [f"Error listing files: {str(e)}"]
        
    return jsonify({
        "status": "running",
        "time": datetime.now().isoformat(),
        "storage_dir": str(STORAGE_DIR),
        "storage_exists": True,
        "files_in_dir": files_list,
        "active_dialogs": list(dialog_events.keys())
    })

if __name__ == '__main__':
    log_file = Path("zotero_watcher.log")
    logger.info(f"Starting Zotero Lit Note Watcher")
    logger.info(f"Storage directory path: {STORAGE_DIR}")
    logger.info(f"Log file: {log_file.resolve()}")
    
    # Create storage directory at startup
    try:
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Storage directory exists or was created successfully")
    except Exception as e:
        logger.warning(f"Note: Could not create storage directory at startup: {e}")
    
    # Start Flask server
    logger.info(f"Starting server on port {LISTEN_PORT}")
    app.run(host='localhost', port=LISTEN_PORT, debug=False, threaded=True)
