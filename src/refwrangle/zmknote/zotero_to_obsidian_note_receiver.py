"""A webhook interface between selected zotero items and a python webhook message receiver (this script), which write
the corresponding obsidian notes.  Dialog buttons that popup if the file the receiver wants to write already exists, in order to get user overwrite confirmation.  The only way to do this in a decent way in python was to do the popup dialog in a browser, unfortunately.  The exruciating details are here:

https://www.perplexity.ai/search/the-javascript-below-is-intend-Tic7.jP4TQiZ6R9CAl9EBQ

The companion javascript for this, zotero_to_obsidian_note_sender.js, goes into the zotero action and tags plugin."""

import json
import logging
import threading
import time
import uuid
import urllib.parse
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from pathlib import Path
from typing import Union

import bs4
from flask import Flask, jsonify, request
from jinja2 import Template
from waitress import serve  # type: ignore
import open_obsidian_note_by_uri as onu

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

SENDER_ID_ZOTERO_TO_OBSIDIAN_NOTE = "zotero_to_obsidian_note"
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

> [!info]- &nbsp;[**Zotero**]({{ desktopURI }}) {% if DOI %} | [**DOI**](https://doi.org/{{ DOI }}){% endif %}{% if url %} | [**URL**]({{ url }}){% endif %}{% for attachment in attachments if attachment.path.endswith(".pdf") %} | **[[{{ basename(attachment.path) }}|PDF]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".html") %} | **[[{{ basename(attachment.path) }}|HTM]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".docx") %} | **[[{{ basename(attachment.path) }}|DOC]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".pptx") %} | **[[{{ basename(attachment.path) }}|PPT]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".epub") %} | **[[{{ basename(attachment.path) }}|EPUB]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".txt") %} | **[[{{ basename(attachment.path) }}|TXT]]**{% endfor %}

> {%- if abstractNote %}
> **Abstract**
> {{ abstractNote.replace("\\n"," ") }}
> {% endif %}
{{ "" }}
{%- for type, creators in creators|groupby("creatorType") %}
> **{{ type.capitalize() }}**::
{%- for creator in creators %}
    {%- if creator.name %} {{ creator.name }}{% else %} {{ creator.lastName }}, {{ creator.firstName }}{% endif %}{% if not loop.last %}, {% endif %}
{%- endfor -%}
{%- endfor -%}

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


>{%- if bibliography %} {{ bibliography }}{% endif %}



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
    root = tk.Tk()
    root.withdraw()
    result = messagebox.askyesno(
        "File Exists", f"File '{citekey}.md' already exists. Overwrite?"
    )
    root.destroy()
    answer = "overwrite" if result else "skip"
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

        if sender_id == SENDER_ID_ZOTERO_TO_OBSIDIAN_NOTE:
            results = write_obsidian_md_note(webhook_item_list, request_id)
        elif sender_id == SENDER_ID_OPEN_OBSIDIAN_NOTE:
            # TODO: add dialog asking if want to write the note, since item should already be in zotero if here
            results = open_note_in_new_tab(
                webhook_item_list, request_id, items_data=webhook_item_list
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
    root.withdraw()

    messagebox.showwarning(
        "Note Does Not Exist", f"Note '{citekey}.md' does not exist."
    )

    root.destroy()

    logger.info(
        f"[{request_id}] User acknowledged non-existent note warning for {citekey}"
    )


def open_note_in_new_tab(
    citekey_or_keys: Union[str, list],
    request_id: str,
    items_data: Union[dict, list, None] = None,
) -> list:
    """Opens existing note(s) in new obsidian tab(s).
    If a note doesn't exist, shows a popup asking user to cancel or create the note.

    Args:
        citekey_or_keys: Single citekey string or list of citekeys
        request_id: Unique ID for this request
        items_data: Optional dict or list of dicts containing item data for note creation
                    (needed if user chooses to create a non-existent note)

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
            status = onu.open_obsidian_note(notepath_vault, OS_PATH_TO_VAULT_ROOT)

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
            logger.info(
                f"[{request_id}] Problem opening Obsidian note for item {citekey}: ", e
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

        logger.info(
            f"[{request_id}] Working on item {index + 1}/{total_items}: {citekey}"
        )

        # zotero item note(s) to obsidian markdown
        notes_md = []
        for note_html in item["notes"]:
            md_note = zotero_note_html_to_md(note_html)
            notes_md.append(md_note)
        item["notes"] = notes_md

        # all item data to markdown
        template = Template(template_str, trim_blocks=True, lstrip_blocks=True)
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
                        logger.info(
                            f"[{request_id}] Successfully overwrote file: {filepath_os}"
                        )
                else:
                    # EAFP atomic file create approach:  Try to open the file in 'x' mode which fails if file exists
                    with open(filepath_os, "x", encoding="utf-8") as f:
                        f.write(obs_note_markdown)
                        logger.info(
                            f"[{request_id}] Successfully created file: {filepath_os}"
                        )
            except FileExistsError:
                return "exists"

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

            open_note_in_new_tab(citekey, request_id)

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
            if answer == "open":
                logger.info(f"[{request_id}] Opening file: {note_path_in_vault}")
                open_note_in_new_tab(citekey, request_id)
                continue
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

    # Start waitress server, intead of flask, as it's more "production ready"
    logger.info(f"Starting server on port {LISTEN_PORT}")
    serve(app, host="0.0.0.0", port=LISTEN_PORT)
