
"""A webhook interface between selected zotero items and a python webhook message receiver (this script), which write the corresponding obsidian notes. Dialog buttons that popup if the file the receiver wants to write already exists, in order to get user overwrite confirmation. The only way to do this in a decent way in python was to do the popup dialog in a browser, unfortunately. The exruciating details are here: https://www.perplexity.ai/search/the-javascript-below-is-intend-Tic7.jP4TQiZ6R9CAl9EBQ The companion javascript for this, zotero_to_obsidian_note_sender.js, goes into the zotero action and tags plugin."""

from flask import Flask, request, jsonify, render_template_string, Response
import logging
import json
from datetime import datetime
import time
import threading
from pathlib import Path
import uuid
import webbrowser
from typing import Union
from waitress import serve
import bs4
from jinja2 import Template
import open_obsidian_note_by_uri as onu

# Create storage directory path
VAULT_PATH = Path(r"C:\Users\scott\OneDrive\share\ref\obsidian\Obsidian Share Vault").expanduser()
NOTE_VAULT_PATH = 'lit/lit_notes'
NOTE_OS_PATH = VAULT_PATH / NOTE_VAULT_PATH
LISTEN_PORT = 5050

# the installer script should use the same file
# TODO: make a central file for this? or is that more complexity for little gain?
RECEIVER_LOG_FILE = "zotero_item_receiver.log"

# Jinja2 template for output obsidian literature note.
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

> [!info]- [**Zotero**]({{ desktopURI }}){% if DOI %} | [**DOI**](https://doi.org/{{ DOI }}){% endif %}{% if url %} | [**URL**]({{ url }}){% endif %}{% for attachment in attachments if attachment.path.endswith(".pdf") %} | **[[{{ basename(attachment.path) }}|PDF]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".html") %} | **[[{{ basename(attachment.path) }}|HTM]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".docx") %} | **[[{{ basename(attachment.path) }}|DOC]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".pptx") %} | **[[{{ basename(attachment.path) }}|PPT]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".txt") %} | **[[{{ basename(attachment.path) }}|TXT]]**{% endfor %}
> {%- if abstractNote %}
> **Abstract**
> {{ abstractNote.replace("\\n"," ") }}
> {% endif %}
{{ "" }}
{%- for type, creators in creators|groupby("creatorType") %}
> **{{ type.capitalize() }}**:: {%- for creator in creators %} {%- if creator.name %} {{ creator.name }}{% else %} {{ creator.lastName }}, {{ creator.firstName }}{% endif %}{% if not loop.last %}, {% endif %} {%- endfor %}
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
> [!note]- Zotero Note ({{ notes|length }})
> {%- for note in notes -%}
>{{ note.replace("# ", "### ").replace("\\n", "\\n> ")}}
>{{ note.tags | map(attribute='tag') | join(', ') }}
---
{%- endfor -%}
{% endif %}
"""

def zotero_note_html_to_md(zotero_note_html: str) -> str:
    """Convert from html into Obsidian markdown one note of the 'notes' key in a Zotero item JSON export."""
    # copy the zotero note contents with the

# Flask app initialization
app = Flask(__name__)

@app.route('/note', methods=['POST'])
def handle_note():
    """Handle incoming webhook requests to create or update notes."""
    data = request.json
    logging.info(f"Received note data: {data}")

    # Extract note details from the request data
    note_name = data.get('note_name')
    note_content = data.get('note_content')

    if not note_name or not note_content:
        logging.error("Missing note_name or note_content")
        return jsonify({"error": "Missing note_name or note_content"}), 400

    # Determine the full path to the note file
    note_path = NOTE_OS_PATH / f"{note_name}.md"

    if note_path.exists():
        # If the file already exists, show options to the user
        html_content = render_template_string("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Note Exists</title>
            </head>
            <body>
                <h1>Note Already Exists</h1>
                <p>The note "{{ note_name }}" already exists. What would you like to do?</p>
                <button onclick="window.location.href='/open?note={{ note_name }}';">Open</button>
                <button onclick="window.location.href='/overwrite?note={{ note_name }}';">Overwrite</button>
                <button onclick="window.location.href='/cancel';">Cancel</button>
            </body>
            </html>
        """, note_name=note_name)
        return Response(html_content, mimetype='text/html')

    # If the file does not exist, create it
    try:
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(note_content)
        logging.info(f"Note created successfully: {note_path}")
        return jsonify({"status": "Note created successfully"}), 201
    except Exception as e:
        logging.error(f"Error creating note: {e}")
        return jsonify({"error": "Failed to create note"}), 500

@app.route('/open', methods=['GET'])
def open_note():
    """Open an existing note in Obsidian."""
    note_name = request.args.get('note')
    if not note_name:
        logging.error("Missing note parameter")
        return jsonify({"error": "Missing note parameter"}), 400

    # Construct the internal Obsidian path for the note
    obsidian_note_path = f"{NOTE_VAULT_PATH}/{note_name}"

    # Call the function to open the note in Obsidian
    status = onu.open_obsidian_note(obsidian_note_path, vault_path=VAULT_PATH)

    if status["note_found"]:
        logging.info(f"Note opened successfully: {obsidian_note_path}")
        return jsonify({"status": "Note opened successfully"}), 200
    else:
        logging.error(f"Failed to open note: {obsidian_note_path}")
        return jsonify({"error": "Failed to open note"}), 404

@app.route('/overwrite', methods=['GET'])
def overwrite_note():
    """Overwrite an existing note."""
    note_name = request.args.get('note')
    if not note_name:
        logging.error("Missing note parameter")
        return jsonify({"error": "Missing note parameter"}), 400

    note_path = NOTE_OS_PATH / f"{note_name}.md"
    if not note_path.exists():
        logging.error(f"Note not found: {note_path}")
        return jsonify({"error": "Note not found"}), 404

    try:
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(request.args.get('content', ''))
        logging.info(f"Note overwritten successfully: {note_path}")
        return jsonify({"status": "Note overwritten successfully"}), 200
    except Exception as e:
        logging.error(f"Error overwriting note: {e}")
        return jsonify({"error": "Failed to overwrite note"}), 500

@app.route('/cancel', methods=['GET'])
def cancel_action():
    """Cancel any actions."""
    logging.info("Action canceled")
    return jsonify({"status": "Action canceled"}), 200

if __name__ == '__main__':
    logging.basicConfig(filename=RECEIVER_LOG_FILE, level=logging.INFO)
    serve(app, host='0.0.0.0', port=LISTEN_PORT)
