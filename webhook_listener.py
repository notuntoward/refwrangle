"""A listener that can maybe handle the output of the save my chatbot browser exension.
Advice from: https://www.perplexity.ai/search/what-is-a-webhook-url-0DbzcuJ4TRav2oD9crQoIg#3

To run it:  python webhook_listener.py"""

import pathlib as pl
import datetime as dt
from flask import Flask, request, Response
import sys
from icecream import ic
import datetime as dt
import tkinter as tk
from tkinter import filedialog

refwrangle_dir = pl.Path('~/ref/refwrangle').expanduser() # can't reliably get dir of an .ipynb 
sys.path.append(str(refwrangle_dir))
# import refwrangle as rfw
import refwrangle as rfw

import link_perplexity_zotero as lpz

write_log_file = True

watcher_dir = rfw.refwrangle_tmp_dir / 'watchter'
raw_inputs_dir = watcher_dir / 'raw'
raw_inputs_dir.mkdir(parents=True, exist_ok=True)
relinked_output_dir = watcher_dir / 'relinked'
relinked_output_dir.mkdir(parents=True, exist_ok=True)

ic(raw_inputs_dir.exists(), relinked_output_dir.exists())

def save_file_dialog(initial_dir, default_filename):
    """
    Opens a save file dialog with specified initial directory and default filename.
    
    Args:
        initial_dir (str): The directory to start the dialog in.
        default_filename (str): The initial filename to suggest in the dialog.

    Returns:
        str: The full path to the selected file, or None if the user cancels.
    """
    # Hide the root window
    root = tk.Tk()
    root.withdraw()

    # Open the save file dialog
    file_path = filedialog.asksaveasfilename(
        initialdir=initial_dir,
        initialfile=default_filename,
        defaultextension=".md",
        filetypes=[("Markdown files", "*.md"), ("All files", "*.*")]
    )

    # Return the selected file path or None if canceled
    return file_path


app = Flask(__name__)
@app.route('/webhook', methods=['POST'])

def webhook():
    """Stores perplexity file extracted by the Save my Chatbot browser plugin"""

    base_name = f'perplexity_{dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'

    input_file_name_head = raw_inputs_dir / base_name
    output_file = relinked_output_dir / f'{base_name}.md'

    if 'multipart/form-data' in request.content_type:
        # get and save the expected payload

        form_data = request.form.to_dict()
        #print("Form Data:", form_data)

        files = request.files
        input_files = []
        for filename, file in files.items():
            print(f"File Received: {filename}")
            file_counter = f'_{len(input_files)}' if len(files) > 1 else ''
            file_path = f'{input_file_name_head}_data{file_counter}.md'
            print(f"Saving data: {file_path}")
            file.save(file_path)
            input_files.append(file_path)

        logstr = ''         
        if (nGotFiles := len(input_files)) > 1:
            logstr = f'Expected to receive only one file, got {nGotFiles}: Converting only the first.'
            print(logstr)

        if write_log_file:
            file_path = f'{input_file_name_head}.log'
            print(f'Writing webhook log to {file_path}')
            with open(file_path, "w", encoding='utf-8') as log_file:
                if logstr:
                    log_file.write(logstr)
                log_file.write(f"Form Data:\n{form_data}\n")
                log_file.write(f"Files:\n{list(files.keys())}\n")

        zot_db_items = lpz.get_zotero_data()

        output_file = save_file_dialog(relinked_output_dir, f'{base_name}.md')

        if output_file:
            input_file = input_files[0]
            print(f'{input_file}\n-->\n{output_file}')
            lpz.relink_perplexity_export_SmC(input_file, output_file, zot_db_items)
            print('Done.')
        else:
            print('Save operation cancelled')

    else:
        # fallback for an uexpected content type
        raw_data = request.data.decode('utf-8')
        print("Received unexpected webhook content.  Raw Data:", raw_data)
        if write_log_file:
            file_path = f'{input_file_name_head}.log'
            print(f'writing webhook log to {file_path}')
            with open(file_path, "w", encoding='utf-8') as log_file:
                log_file.write(f"Raw Data:\n{raw_data}\n")

    return Response(status=200)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
