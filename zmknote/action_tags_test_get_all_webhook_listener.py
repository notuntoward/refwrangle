from flask import Flask, request, jsonify
from jinja2 import Template 
import pathlib as pl
from icecream import ic
import zotero_to_obsidian_note as z2o

output_dir = pl.Path(r"C:\Users\scott\OneDrive\share\ref\obsidian\Obsidian Share Vault\Scratch Space")

app = Flask(__name__)

@app.route('/', methods=['POST'])
def webhook_listener():
    try:
        # Parse incoming JSON data
        data = request.get_json()
        print(f'got data: {data}')
        
        if isinstance(data, list):
            item_jsons = [dict(item) for item in data]  # Convert each top-level element into a dict
            print("Received and parsed data")
            # print("Received and processed data:", processed_data)
            
            # for each zotero item...
            # convert note html to markdown (couldn't get the markdown conversion to work in javascript)
            for item_json in item_jsons:
                output_file = output_dir / f'{item_json["citekey"]}.md'
                notes_md = []
                for note_html in item_json['notes']:
                    # remove mystery <div> @ top
                    note_html = "\n".join(note_html.splitlines()[1:])
                    notes_md.append(z2o.zotero_note_html_to_md(note_html))

                item_json['notes'] = notes_md

                ic(item_json['citekey'])
                try:
                    with output_file.open('w', encoding='utf-8') as f:
                        template = Template(z2o.template_str, trim_blocks=True, lstrip_blocks=True)
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
