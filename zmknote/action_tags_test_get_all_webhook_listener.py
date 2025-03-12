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
            processed_data = [dict(item) for item in data]  # Convert each top-level element into a dict
            
            # Log or process the data as needed
            print("Received and parsed data")
            # print("Received and processed data:", processed_data)
            
            for item in processed_data:
                output_file = output_dir / f'{item["citekey"]}.md'
                ic(item['citekey'])
                try: 
                    with output_file.open('w', encoding='utf-8') as f:
                        template = Template(z2o.template_str, trim_blocks=True, lstrip_blocks=True)
                        output_text = template.render(**item)
                        print(f'Writing to {output_file}')
                        f.write(output_text)
                except Exception as e:
                    print(f'Error writing to {output_file}: {e}')

            return jsonify({"status": "success", "message": "Data received and processed"}), 200
        else:
            return jsonify({"status": "error", "message": "Invalid data format.  Expected a list."}), 400
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5050)
