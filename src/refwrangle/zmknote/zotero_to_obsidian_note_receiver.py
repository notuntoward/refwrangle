"""A webhook interface between selected zotero items and a python webhook message receiver (this script), which write
the corresponding obsidian notes.  Dialog buttons that popup if the file the receiver wants to write already exists, in order to get user overwrite confirmation.  The only way to do this in a decent way in python was to do the popup dialog in a browser, unfortunately.  The exruciating details are here:

https://www.perplexity.ai/search/the-javascript-below-is-intend-Tic7.jP4TQiZ6R9CAl9EBQ

The companion javascript for this, new_obsidian_note_sender.js, goes into the zotero action and tags plugin."""

import json
import logging
import os
import re
import threading
import time
import uuid
import urllib.parse
import requests
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from pathlib import Path
from typing import Union

import bs4
from flask import Flask, jsonify, request
from jinja2 import Environment, Template


def yaml_escape(value: str) -> str:
    """Escape a string for safe inclusion in YAML double-quoted strings.
    
    Handles backslashes, double quotes, and other special characters
    that would break YAML quoting.
    """
    if not isinstance(value, str):
        return value
    escaped = value.replace("\\", "\\\\")
    escaped = escaped.replace('"', '\\"')
    return escaped
from waitress import serve  # type: ignore
import open_obsidian_note as onu

# Cached result of CLI availability check performed at startup.
# Populated in __main__; used by open_note_in_new_tab() to avoid re-running
# per-note subprocess checks on every request.
_startup_cli_check: dict | None = None


def validate_filepath(filepath: str) -> dict:
    """Validate a filepath for cross-platform compatibility (Windows, macOS, Linux).
    
    Args:
        filepath: The full filepath to validate (e.g., "lit/lit_notes/Smith2024.md")
        
    Returns:
        dict with 'valid' boolean and 'reason' string if invalid
    """
    if not filepath or not isinstance(filepath, str):
        return {"valid": False, "reason": "Filepath is empty or not a string"}
    
    # Get the filename (last component)
    filename = Path(filepath).name
    
    if not filename:
        return {"valid": False, "reason": "Filepath has no filename component"}
    
    # Check for empty filename
    if filename.strip() == '':
        return {"valid": False, "reason": "Filename is empty"}
    
    # Characters invalid on Windows (most restrictive)
    # Windows forbids: < > : " / \ | ? * and control chars (0-31)
    # Note: / and \ are path separators, but we're checking the filename part
    windows_invalid_chars = r'[<>:"|?*\x00-\x1F]'
    if re.search(windows_invalid_chars, filename):
        invalid_chars = re.findall(windows_invalid_chars, filename)
        unique_chars = []
        for c in invalid_chars:
            if c == '\x00':
                unique_chars.append('NULL')
            elif c == '\t':
                unique_chars.append('TAB')
            elif c == '\n':
                unique_chars.append('NEWLINE')
            elif c == '\r':
                unique_chars.append('CR')
            elif c not in unique_chars:
                unique_chars.append(f"'{c}'")
        return {
            "valid": False,
            "reason": f"Filename contains invalid character(s): {', '.join(unique_chars)}. These characters cannot be used in filenames on Windows."
        }
    
    # Check for backslash in filename (shouldn't happen but check anyway)
    if '\\' in filename:
        return {"valid": False, "reason": "Filename contains backslash '\\\\' which is invalid in filenames"}
    
    # Check for forward slash in filename (path separator, shouldn't be in filename)
    if '/' in filename:
        return {"valid": False, "reason": "Filename contains forward slash '/' which is invalid in filenames"}
    
    # Windows reserved names (CON, PRN, AUX, NUL, COM1-COM9, LPT1-LPT9)
    # Strip extension for this check
    name_without_ext = Path(filename).stem
    reserved_pattern = re.compile(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$', re.IGNORECASE)
    if reserved_pattern.match(name_without_ext):
        return {"valid": False, "reason": f"'{name_without_ext}' is a reserved Windows device name and cannot be used as a filename"}
    
    # Check for leading/trailing spaces or periods (Windows issue)
    if filename != filename.strip():
        return {"valid": False, "reason": "Filename has leading or trailing spaces"}
    if filename.endswith('.'):
        return {"valid": False, "reason": "Filename ends with a period, which is not allowed in Windows filenames"}
    
    # Check maximum filepath length (Windows limit is 260 for full path, 255 for filename)
    if len(filename) > 255:
        return {"valid": False, "reason": f"Filename is too long ({len(filename)} chars). Maximum is 255 characters."}
    
    # Check full path length
    if len(filepath) > 260:
        return {"valid": False, "reason": f"Full filepath is too long ({len(filepath)} chars). Maximum is 260 characters on Windows."}
    
    return {"valid": True, "reason": None}


def invalid_filepath_popup(filepath: str, reason: str, citekey: str) -> None:
    """Show a popup when the filepath is invalid.
    
    Args:
        filepath: The invalid filepath
        reason: The reason why it's invalid
        citekey: The citekey that caused the issue
    """
    root = tk.Tk()
    root.wm_attributes("-topmost", 1)
    root.withdraw()
    
    messagebox.showerror(
        "Invalid File Path",
        f"Cannot create note for citation key '{citekey}'.\n\n"
        f"File path: {filepath}\n\n"
        f"Reason: {reason}\n\n"
        f"Please edit the citation key in Zotero to fix this issue.",
        parent=root
    )
    
    root.destroy()

# Better BibTeX local JSON-RPC endpoint
BBT_JSON_RPC_URL = "http://localhost:23119/better-bibtex/json-rpc"
BBT_TIMEOUT_SECS = 10


def cleanup_bibliography_text(bibliography: str) -> str:
    """Clean returned bibliography text to match the existing JS-side behavior."""
    if not bibliography:
        return ""

    # Remove URLs (http://, https://)
    bibliography = re.sub(r'https?://\S+', '', bibliography)

    # Remove other URLs (www.something.com style)
    bibliography = re.sub(r'www\.\S+', '', bibliography)

    # Remove DOIs (doi.org pattern)
    bibliography = re.sub(r'doi\.org/\S+', '', bibliography)

    # Remove trailing commas and spaces before a period
    bibliography = re.sub(r',\s*\.', '.', bibliography)

    # Remove trailing comma at end of string and replace with period
    bibliography = re.sub(r',\s*$', '.', bibliography)

    # Remove orphaned commas
    bibliography = re.sub(r',\s+,', ',', bibliography)
    bibliography = re.sub(r',\s*\.', '.', bibliography)

    # Clean up multiple spaces
    bibliography = re.sub(r'\s+', ' ', bibliography).strip()

    return bibliography


def fetch_bbt_bibliography(citekey: str) -> str:
    """Ask Better BibTeX to format a bibliography string for one citekey."""
    payload = {
        "jsonrpc": "2.0",
        "method": "item.bibliography",
        "params": [
            [citekey],
            {
                "contentType": "text",
                "id": "modern-language-association",
                "locale": "en-US",
                "quickCopy": False
            }
        ]
    }

    response = requests.post(
        BBT_JSON_RPC_URL,
        json=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        timeout=BBT_TIMEOUT_SECS
    )
    response.raise_for_status()

    result = response.json()

    if result.get("error"):
        error_msg = result["error"].get("message", "Unknown Better BibTeX JSON-RPC error")
        raise RuntimeError(error_msg)

    bibliography = result.get("result", "") or ""
    return cleanup_bibliography_text(bibliography)


def bibliography_warning_popup(message: str) -> None:
    """Show a user-understandable warning when bibliography generation fails."""
    root = tk.Tk()
    root.wm_attributes("-topmost", 1)
    root.withdraw()
    messagebox.showwarning("Bibliography Warning", message, parent=root)
    root.destroy()
    

# Operating system path Obsidian Vault the top directory (includes the vault name)
OS_PATH_TO_VAULT_ROOT = Path(
    r"C:\Users\scott\OneDrive\share\ref\obsidian\Obsidian Share Vault"
).expanduser()

# Path to notes directory within obsidian vault (NOTE_VAULT_PATH for root would be "")
# NOTE_VAULT_PATH = 'Scratch Space'
VAULT_PATH_NOTES = "lit/lit_notes"
NOTES_OS_PATH = OS_PATH_TO_VAULT_ROOT / VAULT_PATH_NOTES

# Max button wait for each note in payload
# (should be << RECEIVER_RESPONSE_WAIT_TIMEOUT_SECS)
RECEIVER_BUTTON_WAIT_SECS = 20

# port used by webhook
LISTEN_PORT = 5050
# the installer script should use the same file
# TODO: just move this to onu.* so it's in one central file?
RECEIVER_LOG_FILE = "zotero_item_receiver.log"

SENDER_ID_NEW_OBSIDIAN_NOTE = "new_obsidian_note_from_zotero"
SENDER_ID_OPEN_OBSIDIAN_NOTE = "open_obsidian_note"

# Jinja2 template for output obsidian literature note.
# Should fairly well match Zotero Integration Plugin template, "literature note.md"
# DON'T TOUCH ANY SPACES WITHIN
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
- "{{ title | yaml_escape }}"
- "{{ truncateTitle(title, 5) | yaml_escape }}"
citekey: {{ citekey | yaml_escape }}
ZoteroTags: 
{% for tag in tags %}
- {{ (tag | lower | replace(" ", "_")) | yaml_escape }}
{% endfor %}
ZoteroCollections: 
{% for collection in collections %}
- {{ (collection | lower | replace(" ", "_")) | yaml_escape }}
{% endfor %}
created date: {{ exportDate | yaml_escape }}
modified date:
---

> [!info]- &nbsp;[**Zotero**]({{ desktopURI }}) {% if DOI %} | [**DOI**](https://doi.org/{{ DOI }}){% endif %}{% if url %} | [**URL**]({{ url }}){% endif %}{% for attachment in attachments if attachment.path.endswith(".pdf") %} | **[[{{ basename(attachment.path) }}|PDF]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".html") %} | **[[{{ basename(attachment.path) }}|HTM]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".docx") %} | **[[{{ basename(attachment.path) }}|DOC]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".pptx") %} | **[[{{ basename(attachment.path) }}|PPT]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".epub") %} | **[[{{ basename(attachment.path) }}|EPUB]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".txt") %} | **[[{{ basename(attachment.path) }}|TXT]]**{% endfor %}
{{ "" }}
{% if abstractNote %}
> **Abstract**
> {{ abstractNote.replace("\\n"," ") }}{% endif %}

{% for type, creators in creators|groupby("creatorType") %}
> **{{ type.capitalize() }}**::{% for creator in creators %}{% if creator.name %} {{ creator.name }}{% else %} {{ creator.lastName }}, {{ creator.firstName }}{% endif %}{% if not loop.last %}, {% endif %}{% endfor %}
{% endfor %}
{{ "" }}
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


{% if bibliography %}
> {{ bibliography }}
{% endif %}



___
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

    # copy the zotero note contents with the <div> or <body>
    soup = bs4.BeautifulSoup(zotero_note_html, "html.parser")
    main_div = soup.find("div")
    if not main_div:
        main_div = soup.body if soup.body else soup

    # if no html structure captured, just get the pure text (won't have children)
    markdown_blocks = []  # obsidian note markdown
    if hasattr(main_div, "string") and main_div.string and main_div.string.strip():
        markdown_blocks.append(main_div.string.strip())

    # Get structured blocks (if no html children structure, then this doesn't do anything)
    # Some bs4 PageElement subclasses may not expose `.children`, so fall back to `.contents`
    if hasattr(main_div, "children"):
        child_iterable = main_div.children
    elif hasattr(main_div, "contents"):
        child_iterable = main_div.contents
    else:
        # Last resort: treat the main_div itself as a single node
        child_iterable = [main_div]

    for child in child_iterable:
        if isinstance(child, str) and child.strip():
            markdown_blocks.append(child.strip())
            continue  # next child

        if not hasattr(child, "name"):
            continue  # skips blank space and non-tag elements

        if child.name is None:
            continue  # skips blank space, I think

        if child.name == "blockquote":
            block_md = process_blockquote(child)
            if block_md:
                markdown_blocks.append(block_md)
        elif child.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            level = int(child.name[1])
            header_text = convert_inline_formatting(child)
            markdown_blocks.append(f"{'#' * level} {header_text}")
        elif child.name == "p":
            p_text = convert_inline_formatting(child)
            if p_text.strip():
                markdown_blocks.append(p_text.strip())
        elif child.name == "ul":
            list_items = []
            for li in child.find_all("li", recursive=False):
                li_text = convert_inline_formatting(li)
                if li_text.strip():
                    list_items.append(f"- {li_text.strip()}")
            if list_items:
                markdown_blocks.append("\n".join(list_items))
        elif child.name == "small":
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

    return output_markdown + "\n"  # separate from next note, if any


def process_blockquote(blockquote: bs4.element.Tag) -> str:
    """Process a blockquote element into markdown format with proper paragraph spacing."""
    # Initialize result list
    markdown_chunks = []

    # Process each paragraph or element within the blockquote
    for element in blockquote.children:
        if isinstance(element, str):
            if element.strip():
                # Add non-empty text nodes as lines
                for line in element.strip().split("\n"):
                    if line.strip():
                        markdown_chunks.append(f"> {line.strip()}")
        elif getattr(element, "name", None) == "p":
            # Process each paragraph
            if isinstance(element, bs4.element.Tag):
                p_text = convert_inline_formatting(element)
            else:
                p_text = str(element)
            if p_text.strip():
                # Split paragraph text into lines if it contains newlines
                for line in p_text.strip().split("\n"):
                    if line.strip():
                        markdown_chunks.append(f"> {line.strip()}")

                # Add empty blockquote line after paragraph
                markdown_chunks.append(">")
        else:
            # Process other elements (headings, lists, etc.) in the blockquote
            if isinstance(element, bs4.element.Tag):
                formatted_text = convert_inline_formatting(element)
            else:
                formatted_text = str(element)
            if formatted_text.strip():
                # Split into lines
                for line in formatted_text.strip().split("\n"):
                    if line.strip():
                        markdown_chunks.append(f"> {line.strip()}")

                # Add empty blockquote line
                markdown_chunks.append(">")

    # Remove trailing empty blockquote if present
    if markdown_chunks and markdown_chunks[-1] == ">":
        markdown_chunks.pop()

    return "\n".join(markdown_chunks)


def convert_inline_formatting(element: Union[str, bs4.element.Tag]) -> str:
    """Convert inline HTML formatting to markdown.
    Handles citations, links, bold, italic, and highlights."""

    if isinstance(element, str):
        return element  # you're already done

    # Convert each child to markdown
    output_markdown = ""
    for child in element.contents:
        if isinstance(child, str):
            output_markdown += child
        elif hasattr(child, "name") and child.name == "span":
            # Internal link to a zotero item: make it work from inside of obsidian w/ a URI substitute
            if (
                hasattr(child, "get")
                and hasattr(child, "find")
                and "citation" in child.get("class", [])
            ):
                citation_item = child.find(class_="citation-item")
                if citation_item:
                    citation_text = citation_item.get_text(strip=True)

                    # Extract Zotero ID from citation data
                    citation_data = (
                        child.get("data-citation", "") if hasattr(child, "get") else ""
                    )
                    if citation_data:
                        try:
                            citation_json = json.loads(
                                urllib.parse.unquote(citation_data)
                            )
                            if (
                                "citationItems" in citation_json
                                and citation_json["citationItems"]
                            ):
                                uri = citation_json["citationItems"][0]["uris"][0]
                                zotero_id = uri.split("/")[-1]
                                output_markdown += f"([{citation_text}](zotero://select/library/items/{zotero_id}))"
                                continue
                        except Exception:
                            pass

                # Fallback for citation
                output_markdown += f"({child.get_text(strip=True) if hasattr(child, 'get_text') else str(child)})"

            # Highlights
            elif (
                hasattr(child, "get")
                and child.get("style")
                and (
                    "background-color" in child.get("style")
                    or "highlight" in child.get("style")
                )
            ):
                highlighted_text = (
                    convert_inline_formatting(child)
                    if isinstance(child, bs4.element.Tag)
                    else str(child)
                )
                output_markdown += f"=={highlighted_text}=="

            # Bold/Italic handling via style
            elif hasattr(child, "get") and child.get("style"):
                style = child.get("style")
                text = (
                    convert_inline_formatting(child)
                    if isinstance(child, bs4.element.Tag)
                    else str(child)
                )

                is_bold = "bold" in style or "font-weight" in style
                is_italic = "italic" in style or "font-style" in style

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
                output_markdown += (
                    convert_inline_formatting(child)
                    if isinstance(child, bs4.element.Tag)
                    else str(child)
                )

        # Bold
        elif hasattr(child, "name") and child.name in ["strong", "b"]:
            text = (
                convert_inline_formatting(child)
                if isinstance(child, bs4.element.Tag)
                else str(child)
            )
            output_markdown += f"**{text}**"

        # Italic
        elif hasattr(child, "name") and child.name in ["em", "i"]:
            text = (
                convert_inline_formatting(child)
                if isinstance(child, bs4.element.Tag)
                else str(child)
            )
            output_markdown += f"*{text}*"

        # Web Links
        elif hasattr(child, "name") and child.name == "a":
            text = (
                convert_inline_formatting(child)
                if isinstance(child, bs4.element.Tag)
                else str(child)
            )
            href = child.get("href", "") if hasattr(child, "get") else ""
            output_markdown += f"[{text}]({href})"

        # Other elements
        else:
            if isinstance(child, bs4.element.Tag):
                output_markdown += convert_inline_formatting(child)
            else:
                output_markdown += str(child)

    return output_markdown


# %%

# Set up functions for webhook receiver overwrite/skip/skip all popup dialogs

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(RECEIVER_LOG_FILE), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

dir_lock = threading.Lock()  # lock needed for reliable existence detect

# Dictionary to store overwrite/skip/skipall dialog results
dialog_events: dict[str, dict] = {}
dialog_answers: dict[str, str] = {}


# HTML template for the dialog
def ensure_storage_dir(request_id: str) -> bool:
    """Ensure the storage directory exists with proper synchronization.
    Returns True if successful, False otherwise."""
    with dir_lock:
        if not NOTES_OS_PATH.exists():
            logger.info(f"[{request_id}] Creating storage directory: {NOTES_OS_PATH}")
            try:
                NOTES_OS_PATH.mkdir(parents=True, exist_ok=True)
                # Small delay to ensure directory is fully created and visible to all threads
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"[{request_id}] Error creating directory: {e}")
                return False

        # Double-check directory exists
        if not NOTES_OS_PATH.exists():
            logger.error(
                f"[{request_id}] Directory does not exist after creation attempt: {NOTES_OS_PATH}"
            )
            return False

        return True


app = Flask(__name__)


def dialog_response(dialog_id: str) -> tuple:
    """Handle dialog response"""
    if dialog_id not in dialog_events:
        return "Dialog not found", 404

    action = request.form.get("action", "skip")
    logger.info(f"Dialog {dialog_id} response: {action}")

    # Store the result
    dialog_answers[dialog_id] = action

    # Signal the event to notify the waiting thread
    dialog_events[dialog_id]["event"].set()

    # Return success - the browser window should be closed by JavaScript
    return "OK", 200


def ask_overwrite_popup(
    citekey: str, is_last_item: bool, total_items: int, request_id: str
) -> str:
    """Show overwrite/skip dialog for an existing note.
    
    For single items or the last item in a batch, shows Yes/No (Overwrite/Skip).
    For multi-item batches (not the last), shows Yes/No/Cancel (Overwrite/Skip/Skip All).
    
    Returns: 'overwrite', 'skip', or 'skip_all'
    """
    root = tk.Tk()
    root.wm_attributes("-topmost", 1)
    root.withdraw()
    
    if total_items > 1 and not is_last_item:
        # Multi-item: offer Overwrite / Skip / Skip All
        # Use a custom dialog with three buttons
        dialog = tk.Toplevel(root)
        dialog.wm_attributes("-topmost", 1)
        dialog.title("File Exists")
        dialog.resizable(False, False)
        
        answer_holder = {"answer": "skip"}
        
        msg = tk.Label(
            dialog,
            text=f"File '{citekey}.md' already exists.\n\nWhat would you like to do?",
            padx=20, pady=10, justify="left"
        )
        msg.pack()
        
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        def on_overwrite():
            answer_holder["answer"] = "overwrite"
            dialog.destroy()
        
        def on_skip():
            answer_holder["answer"] = "skip"
            dialog.destroy()
        
        def on_skip_all():
            answer_holder["answer"] = "skip_all"
            dialog.destroy()
        
        tk.Button(btn_frame, text="Overwrite", command=on_overwrite, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Skip", command=on_skip, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Skip All", command=on_skip_all, width=10).pack(side=tk.LEFT, padx=5)
        
        # Center dialog on screen
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - dialog.winfo_reqwidth()) // 2
        y = (dialog.winfo_screenheight() - dialog.winfo_reqheight()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        dialog.grab_set()
        root.wait_window(dialog)
        answer = answer_holder["answer"]
    else:
        # Single item or last item: just Yes/No
        result = messagebox.askyesno(
            "File Exists",
            f"File '{citekey}.md' already exists. Overwrite?",
            parent=root
        )
        answer = "overwrite" if result else "skip"
    
    root.destroy()
    logger.info(f"User selected '{answer}' for {citekey}")
    return answer


@app.route("/webhook", methods=["POST"])
def webhook() -> tuple:
    """
    Endpoint that receives webhook data from Zotero Tags and Actions plugin.
    Expects a JSON array of objects with zotero item information, including itemkey and citekey.
    """
    # Generate a unique ID for this request for traceability
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] Received webhook request")

    try:
        # Get the JSON data from the request
        payload = request.get_json()
        sender_id = payload.get("sender_id")
        webhook_item_list = payload.get("data")

        if not webhook_item_list:
            logger.error(f"[{request_id}] No data received")
            return jsonify({"status": "error", "message": "No data received"}), 400

        if not isinstance(webhook_item_list, list):
            logger.error(
                f"[{request_id}] Expected JSON array, got {type(webhook_item_list)}: {webhook_item_list}"
            )
            return jsonify({"status": "error", "message": "Expected JSON array"}), 400

        logger.info(f"[{request_id}] Processing {len(webhook_item_list)} items")

        # Ensure storage directory exists before processing
        if not ensure_storage_dir(request_id):
            return jsonify(
                {
                    "status": "error",
                    "message": "Failed to create storage directory",
                    "request_id": request_id,
                }
            ), 500

        if not sender_id:
            logger.error(f"[{request_id}] Payload missing sender_id")
            return jsonify({"status": "error", "message": "Missing sender_id"}), 400

        if sender_id == SENDER_ID_NEW_OBSIDIAN_NOTE:
            results = write_obsidian_md_note(webhook_item_list, request_id)
        elif sender_id == SENDER_ID_OPEN_OBSIDIAN_NOTE:
            # Use new_tab=False so Obsidian focuses an already-open tab for the note
            # rather than duplicating it. If the note is not open, obsidian://open
            # will open it in the current active pane (acceptable fallback).
            # TODO: add dialog asking if want to write the note, since item should already be in zotero if here
            results = open_note_in_new_tab(
                webhook_item_list, request_id, items_data=webhook_item_list,
                new_tab=False, prefer_uri=True,
            )
        else:
            logger.error(f"[{request_id}] Unknown sender_id, got {sender_id}")
            return jsonify({"status": "error", "message": f"Unknown {sender_id=}"}), 400

        logger.info(
            f"[{request_id}] Ended webhook message processing with {len(results)} items acted upon"
        )

        return jsonify(
            {
                "status": "success",
                "processed": len(results),
                "items": results,
                "request_id": request_id,
            }
        ), 200

    except Exception as e:
        logger.exception(f"[{request_id}] Error processing webhook data: {str(e)}")
        return jsonify(
            {"status": "error", "message": str(e), "request_id": request_id}
        ), 500


def nonexistent_note_popup(citekey: str, request_id: str) -> None:
    """Show a warning popup that a note doesn't exist.

    Args:
        citekey: The citekey of the note that doesn't exist
        request_id: Unique ID for this request

    Returns:
        None
    """
    root = tk.Tk()
    root.wm_attributes("-topmost", 1)
    root.withdraw()

    messagebox.showwarning(
        "Note Does Not Exist", f"Note '{citekey}.md' does not exist.", parent=root
    )

    root.destroy()

    logger.info(
        f"[{request_id}] User acknowledged non-existent note warning for {citekey}"
    )


def show_cli_unavailable_popup(failure_reason: str) -> None:
    """Show a specific error popup based on why the Obsidian CLI is unavailable."""
    messages = {
        "not_on_path": (
            "Obsidian CLI Not Found",
            "The Obsidian CLI executable was not found on PATH.\n\n"
            "To fix this:\n"
            "  1. Download and run a fresh Obsidian installer (v1.12.4+).\n"
            "     In-app update is NOT sufficient.\n"
            "  2. In Obsidian: Settings → General → enable 'Command line\n"
            "     interface' → click 'Register CLI'.\n"
            "  3. Restart this receiver script."
        ),
        "binary_broken": (
            "Obsidian CLI Not Responding",
            "The Obsidian CLI was found but is not responding.\n\n"
            "To fix this:\n"
            "  In Obsidian: Settings → General → click 'Register CLI' again.\n"
            "  Then restart this receiver script."
        ),
        "obsidian_not_running": (
            "Obsidian Is Not Running",
            "The Obsidian CLI is installed, but Obsidian is not running\n"
            "or the vault is not open.\n\n"
            "Please open Obsidian and load your vault, then try again."
        ),
        "cli_disabled": (
            "Obsidian CLI Disabled",
            "Obsidian is running but the CLI is disabled in Settings.\n\n"
            "To fix this:\n"
            "  In Obsidian: Settings → General → enable\n"
            "  'Command line interface'."
        ),
    }
    title, message = messages.get(
        failure_reason,
        ("Obsidian CLI Unavailable", "The Obsidian CLI is not available. Check Obsidian settings.")
    )
    root = tk.Tk()
    root.wm_attributes("-topmost", 1)
    root.withdraw()
    messagebox.showerror(title, message, parent=root)
    root.destroy()


def open_note_in_new_tab(
    citekey_or_keys: Union[str, list],
    request_id: str,
    items_data: Union[dict, list, None] = None,
    cli_check: dict | None = None,
    new_tab: bool = True,
    prefer_uri: bool = False,
) -> list:
    """Opens existing note(s) in Obsidian.
    If a note doesn't exist, shows a popup warning.

    Args:
        citekey_or_keys: Single citekey string or list of citekeys
        request_id: Unique ID for this request
        items_data: Optional dict or list of dicts containing item data for note creation
                    (needed if user chooses to create a non-existent note)
        cli_check: Optional pre-computed CLI availability dict to avoid re-checking per call
        new_tab: If True (default), open in a new Obsidian tab.
                 If False, reuse the existing tab if the note is already open.
        prefer_uri: If True, skip the CLI and use the URI method directly.
                    Useful when overwriting an existing note, since the standard
                    obsidian://open URI reliably focuses the already-open tab
                    rather than duplicating it.

    Return value is list of attempted citekeys, for now.
    """

    citekeys = (
        citekey_or_keys if isinstance(citekey_or_keys, list) else [citekey_or_keys]
    )

    # If items_data is provided, convert to dict keyed by citekey for easy lookup
    items_dict = {}
    if items_data:
        if isinstance(items_data, dict):
            items_dict[items_data.get("citekey")] = items_data
        elif isinstance(items_data, list):
            for item in items_data:
                if "citekey" in item:
                    items_dict[item["citekey"]] = item

    results = []
    for citekey in citekeys:
        try:
            notepath_vault = f"{VAULT_PATH_NOTES}/{citekey}.md"
            filepath_os = OS_PATH_TO_VAULT_ROOT / notepath_vault

            # Check if note exists before trying to open it

            if not filepath_os.exists():
                logger.info(f"[{request_id}] Note does not exist: {notepath_vault}")
                nonexistent_note_popup(citekey, request_id)
                logger.info(f"[{request_id}] Skipping non-existent note {citekey}")
                results.append(f"Skipped - note does not exist: {notepath_vault}")
                continue

            # Note exists, proceed to open it
            # Try CLI first (more reliable), fall back to URI method.
            # Reuse startup check if available to avoid per-note subprocess overhead.
            effective_cli_check = cli_check if cli_check is not None else (
                _startup_cli_check if _startup_cli_check is not None
                else onu.check_obsidian_cli_available(OS_PATH_TO_VAULT_ROOT)
            )

            if effective_cli_check["cli_enabled"] and not prefer_uri:
                cli_result = onu.open_note_via_cli(notepath_vault, OS_PATH_TO_VAULT_ROOT, new_tab=new_tab)
                if cli_result["success"]:
                    logger.info(f"[{request_id}] CLI opened note (new_tab={new_tab}): {notepath_vault}")
                else:
                    logger.warning(f"[{request_id}] CLI open failed: {cli_result['error']} — "
                                   f"falling back to URI method.")
                    # Fallback: original URI method
                    status = onu.open_obsidian_note(notepath_vault, OS_PATH_TO_VAULT_ROOT, new_tab=new_tab)
                    message_tail = f"({citekey}): {status=})"
                    if not (
                        status["note_found"]
                        and status["vault_found"]
                        and status["uri_used"] != ""
                    ):
                        logger.info(
                            f"[{request_id}] Couldn't open note in Obsidian due to path or URI problem {message_tail}"
                        )
                    elif status["new_tab_requested"] and status["new_tab_possible"] is not True:
                        logger.info(
                            f"[{request_id}] Couldn't open note in NEW Obsidian tab due to Obsidian config problem {message_tail}"
                        )
            else:
                # CLI not available or URI preferred — use URI method
                reason = "prefer_uri=True" if prefer_uri else f"CLI not available ({effective_cli_check['failure_reason']})"
                logger.info(f"[{request_id}] Using URI method ({reason}).")
                status = onu.open_obsidian_note(notepath_vault, OS_PATH_TO_VAULT_ROOT, new_tab=new_tab)
                message_tail = f"({citekey}): {status=})"
                if not (
                    status["note_found"]
                    and status["vault_found"]
                    and status["uri_used"] != ""
                ):
                    logger.info(
                        f"[{request_id}] Couldn't open note in Obsidian due to path or URI problem {message_tail}"
                    )
                elif status["new_tab_requested"] and status["new_tab_possible"] is not True:
                    logger.info(
                        f"[{request_id}] Couldn't open note in NEW Obsidian tab due to Obsidian config problem {message_tail}"
                    )
        except Exception as e:
            logger.warning(
                f"[{request_id}] Problem opening Obsidian note for item {citekey}: {e}",
                exc_info=True,
            )

        results.append(f"Tried to open note at {notepath_vault}")

    return results


def write_obsidian_md_note(items: list, request_id: str) -> list:
    """Write an Obsidian note from the items data, avoiding overwrite unless user accepts it,
    and returning status of items written."""

    if not ensure_storage_dir(request_id):
        logger.error(f"[{request_id}] Could not ensure storage directory exists")
        return []

    total_items = len(items)
    obs_note_write_record = []
    skip_all = False
    for index, item in enumerate(items):
        if skip_all:
            logger.info(
                f"[{request_id}] Skipping remaining items due to timeout or 'skip all' selection"
            )
            break

        itemkey = item.get("itemkey")
        citekey = item.get("citekey")
        if not itemkey or not citekey:
            logger.warning(f"[{request_id}] Missing required keys in item: {item}")
            continue

        # Validate the full filepath before attempting to write
        note_basename = f"{citekey}.md"
        note_path_in_vault = f"{VAULT_PATH_NOTES}/{note_basename}"
        validation = validate_filepath(note_path_in_vault)
        if not validation["valid"]:
            logger.warning(f"[{request_id}] Invalid filepath for citekey '{citekey}': {validation['reason']}")
            invalid_filepath_popup(note_path_in_vault, validation["reason"], citekey)
            continue

        logger.info(
            f"[{request_id}] Working on item {index + 1}/{total_items}: {citekey}"
        )

        # If Zotero-side bib fetch failed, try calling Better BibTeX from Python.
        if not item.get("bibliography", "").strip() and citekey:
            try:
                item["bibliography"] = fetch_bbt_bibliography(citekey)
                logging.info(f"Fetched bibliography from Better BibTeX in Python for {citekey}")
            except requests.exceptions.ConnectionError:
                logging.warning(f"Could not reach Better BibTeX for {citekey}")
                bibliography_warning_popup(
                    "Could not reach Better BibTeX in Zotero to generate the bibliography.\n\n"
                    "Please make sure Zotero is running and the Better BibTeX add-on is installed.\n\n"
                    "The note will still be created, but without bibliography text."
                )
            except requests.exceptions.Timeout:
                logging.warning(f"Timed out talking to Better BibTeX for {citekey}")
                bibliography_warning_popup(
                    "Timed out while asking Better BibTeX for bibliography text.\n\n"
                    "The note will still be created, but without bibliography text."
                )
            except Exception as e:
                logging.warning(f"Failed to fetch bibliography from Better BibTeX for {citekey}: {e}")
                bibliography_warning_popup(
                    "Better BibTeX returned an error while generating bibliography text.\n\n"
                    f"Details: {e}\n\n"
                    "The note will still be created, but without bibliography text."
                )
        
        # zotero item note(s) to obsidian markdown
        notes_md = []
        for note_html in item["notes"]:
            md_note = zotero_note_html_to_md(note_html)
            notes_md.append(md_note)
        item["notes"] = notes_md

        # all item data to markdown
        env = Environment(trim_blocks=True, lstrip_blocks=True)
        env.filters['yaml_escape'] = yaml_escape
        template = env.from_string(template_str)
        obs_note_markdown = template.render(**item)

        def write_note(
            notepath_in_vault: Union[str, Path], obs_note_markdown: str, overwrite: bool
        ) -> str:
            """Write an obsidian note and open it in a new Obsidian tab.  If overwrite=False,
            then a write Exception will mean that the file already exists."""

            filepath_os = OS_PATH_TO_VAULT_ROOT / notepath_in_vault
            try:
                if overwrite:
                    with open(filepath_os, "w", encoding="utf-8") as f:
                        f.write(obs_note_markdown)
                        f.flush()  # Ensure data is written to disk
                        os.fsync(f.fileno())  # Force write to storage
                    logger.info(
                        f"[{request_id}] Successfully overwrote file: {filepath_os}"
                    )
                else:
                    # EAFP atomic file create approach:  Try to open the file in 'x' mode which fails if file exists
                    with open(filepath_os, "x", encoding="utf-8") as f:
                        f.write(obs_note_markdown)
                        f.flush()  # Ensure data is written to disk
                        os.fsync(f.fileno())  # Force write to storage
                    logger.info(
                        f"[{request_id}] Successfully created file: {filepath_os}"
                    )
            except FileExistsError:
                return "exists"
            
            # Small delay to allow file system and OneDrive sync to catch up
            time.sleep(0.3)

            logger.debug(
                f"[{request_id}] Checking existence of: {filepath_os.resolve()}"
            )

            obs_note_write_record.append(
                dict(
                    itemkey=itemkey,
                    citekey=citekey,
                    timestamp=datetime.now().strftime("%Y%m%d_%H%M%S"),
                    filepath=str(filepath_os),
                )
            )

            if not overwrite:
                # New note: open in a fresh tab via CLI (reliable, no file-watcher lag).
                open_note_in_new_tab(citekey, request_id, new_tab=True)
            else:
                # Overwrite: Obsidian auto-reloads the existing tab from the file
                # change on disk. We still need to focus that tab for the user.
                # Use the standard obsidian://open URI (prefer_uri=True, new_tab=False):
                # this navigates Obsidian to the file, focusing the already-open tab
                # without duplicating it, and without going through the file-watcher.
                open_note_in_new_tab(citekey, request_id, new_tab=False, prefer_uri=True)

            logger.info(f"[{request_id}] Completed item: {citekey=}, {itemkey=}")

            return "done"

        # Write obsidian lit note without overwiting existing note, unless user confirms
        note_basename = f"{citekey}.md"
        note_path_in_vault = f"{VAULT_PATH_NOTES}/{note_basename}"
        is_last_item = index == total_items - 1

        if (
            write_resp := write_note(
                note_path_in_vault, obs_note_markdown, overwrite=False
            )
        ) == "exists":
            logger.info(f"[{request_id}] File already exists: {note_path_in_vault}")

            answer = ask_overwrite_popup(citekey, is_last_item, total_items, request_id)
            if answer == "skip":
                logger.info(f"[{request_id}] Skipping file: {note_path_in_vault}")
                continue
            elif answer == "skip_all":
                logger.info(f"[{request_id}] Skipping all remaining operations")
                skip_all = True
                continue

            # Do overwrite, as requested
            if (
                write_note(note_path_in_vault, obs_note_markdown, overwrite=True)
                != "done"
            ):
                logger.error(f"[{request_id}] Error overwriting file", exc_info=True)
                continue
        elif write_resp != "done":
            logger.error(
                f"[{request_id}] Error writing file: {write_resp=}", exc_info=True
            )
            continue

    return obs_note_write_record


@app.route("/status", methods=["GET"])
def status():
    """Simple endpoint to verify to sender that receiver is running"""
    # First ensure storage directory exists
    if not NOTES_OS_PATH.exists():
        return jsonify(
            {
                "status": "running",
                "time": datetime.now().isoformat(),
                "storage_dir": str(NOTES_OS_PATH),
                "storage_exists": False,
                "files_in_dir": [],
            }
        )

    try:
        files_list = [f.name for f in NOTES_OS_PATH.iterdir() if f.is_file()]
    except Exception as e:
        files_list = [f"Error listing files: {str(e)}"]

    return jsonify(
        {
            "status": "running",
            "time": datetime.now().isoformat(),
            "storage_dir": str(NOTES_OS_PATH),
            "storage_exists": True,
            "files_in_dir": files_list,
            "active_dialogs": list(dialog_events.keys()),
        }
    )


if __name__ == "__main__":
    log_file = Path(RECEIVER_LOG_FILE)
    logger.info("Starting Zotero Item Receiver")
    logger.info(f"Storage directory path: {NOTES_OS_PATH}")
    logger.info(f"Log file: {log_file.resolve()}")

    # Create storage directory at startup
    try:
        NOTES_OS_PATH.mkdir(parents=True, exist_ok=True)
        logger.info("Storage directory exists or was created successfully")
    except Exception as e:
        logger.warning(f"Note: Could not create storage directory at startup: {e}")

    # Check CLI availability in the background so the server starts immediately
    # and can accept requests while the check (up to 15 s) is still in progress.
    logger.info("Starting background Obsidian CLI availability check …")
    def _background_cli_check() -> None:
        global _startup_cli_check
        result = onu.check_obsidian_cli_available(OS_PATH_TO_VAULT_ROOT)
        _startup_cli_check = result
        if result["cli_enabled"]:
            logger.info("Obsidian CLI is available and enabled.")
        else:
            logger.warning(
                f"Obsidian CLI not available: {result['failure_reason']} — "
                f"will fall back to URI method for opening notes."
            )
            show_cli_unavailable_popup(result["failure_reason"])

    threading.Thread(target=_background_cli_check, daemon=True, name="cli-check").start()

    # Start waitress server, instead of flask, as it's more "production ready"
    logger.info(f"Starting server on port {LISTEN_PORT}")
    serve(app, host="0.0.0.0", port=LISTEN_PORT)
