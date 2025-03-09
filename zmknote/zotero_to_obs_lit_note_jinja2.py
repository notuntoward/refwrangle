from jinja2 import Template
from datetime import datetime

from icecream import ic
import pathlib as pl
from pyzotero import zotero
import pandas as pd
from IPython.display import display, HTML

import pathlib as pl
from icecream import ic
import sys

refwrangle_dir = pl.Path('~/ref/refwrangle').expanduser() # can't reliably get dir of an .ipynb 
sys.path.append(str(refwrangle_dir))
import refwrangle as rfw
import re

output_file = pl.Path(fr'C:\Users\scott\OneDrive\share\ref\obsidian\Obsidian Share Vault\Scratch Space\tmp_zotero_to_obs_lit_note_jinja2.md')

# Corrected Jinja2 template
template_str = """
{%- macro truncateTitle(title, n) -%}
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
category: literaturenote

tags:

read: false
in-progress: false
linked: false

aliases:
- "{{ title }}"
- "{{ truncateTitle(title, 5) }}"

citekey: {{ citekey }}

ZoteroTags:
{%- for tag in tags %}
- {{ tag.tag | lower | replace(" ", "_") }}
{%- endfor %}

ZoteroCollections:
{%- for collection in collections %}
- {{ collection.name | lower | replace(" ", "_") }}
{%- endfor %}

created date: {{ exportDate.strftime("%Y-%m-%d") }}
modified date:
---

> [!info]- [**Zotero**]({{ desktopURI }}) {% if DOI %} | [**DOI**](https://doi.org/{{ DOI }}){% endif %}{% if url %} | [**URL**]({{ url }}){% endif %}{% for attachment in attachments if attachment.path.endswith(".pdf") %} | **[[{{ basename(attachment.path) }}|PDF]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".html") %} | **[[{{ basename(attachment.path) }}|HTM]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".docx") %} | **[[{{ basename(attachment.path) }}|DOC]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".pptx") %} | **[[{{ basename(attachment.path) }}|PPT]]**{% endfor %}{% for attachment in attachments if attachment.path.endswith(".txt") %} | **[[{{ basename(attachment.path) }}|TXT]]**{% endfor %}

> {% if abstractNote %}
> **Abstract**
> {{ abstractNote.replace("\\n"," ") }}
> {% endif %}

{% for type, creators in creators|groupby("creatorType") %}
  {% for creator in creators %}
> **{% if loop.first %}{{ type.capitalize() }}{% endif %}**::
    {% if creator.name %}
      {{ creator.name }}
    {% else %}
      {{ creator.lastName }}, {{ creator.firstName }}
    {% endif %}
  {% endfor %}
{% endfor %}

> **Title**:: "{{ title }}"
> **Date**:: {{ date.strftime("%Y-%m-%d") }}
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
> **Related**::{% for relation in relations if relation.citekey %} [[@{{ relation.citekey }}]]{% if not loop.last %}, {% endif %}{% endfor %}
>{% if bibliography %} {{ bibliography }}{% endif %}
  
{% block persist_Obsidian_Notes %}
___

==Delete this and write here. Don't delete the `persist` directives above and below.==

___
{% endblock persist_Obsidian_Notes %}

{% if notes|length > 0 %}
> [!note]- Zotero Note ({{ notes|length }})
>
{%- for note in notes %}
>{{ note.note.replace("# ", "### ").replace("\\n", "\\n> ") }}
>{{ note.tags | map(attribute='tag') | join(', ') }}
>
> 📝️ (modified: {{ note.dateModified.strftime("%Y-%m-%d") }}) [link](zotero://select/library/items/{{ note.key }}) - [web]({{ note.uri }})
>
---
{% endfor %}
{% endif %}
"""

# Example data structure populated with Zotero-like data
zotero_data = {
    "title": "Understanding Artificial Intelligence",
    "exportDate": datetime.now(),
    "citekey": "Smith2025AI",
    "DOI": "10.1234/example.doi",
    "url": "https://example.com/ai-paper",
    "desktopURI": "zotero://select/library/items/12345",
    "attachments": [
        {"path": "/papers/Smith2025AI.pdf"},
        {"path": "/papers/supplementary.html"}
    ],
    "tags": [{"tag": "Artificial Intelligence"}, {"tag": "Machine Learning"}],
    "collections": [{"name": "AI Papers"}, {"name": "ML Resources"}],
    "creators": [
        {"creatorType": "author", "firstName": "John", "lastName": "Smith"},
        {"creatorType": "editor", "name": "Jane Doe"}
    ],
    "date": datetime.now(),
    "itemKey": "12345ABC",
    "itemType": "journalArticle",
    "publicationTitle": "Journal of AI Research",
    "volume": "12",
    "issue": "3",
    "publisher": "",
    "place": "",
    "pages": "",
    "ISBN": "",
    "relations": [{"citekey": "Doe2024ML"}],
    "bibliography": None,
    "notes": [
        {
            "note": "# Summary\nThis paper explores AI applications.",
            "tags": [{"tag": "Summary"}],
            "dateModified": datetime.now(),
            "key": "67890XYZ",
            "uri": "/notes/67890XYZ"
        }
    ]
}

# Render the template with the data
template = Template(template_str)
rendered_output = template.render(**zotero_data)

#print(rendered_output)

print(f'writing to {output_file=}')
output_file.write_text(rendered_output, encoding='utf-8')
print("Done.")