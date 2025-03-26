"""A listener that can maybe handle the output of the save my chatbot browser exension.
Advice from: https://www.perplexity.ai/search/what-is-a-webhook-url-0DbzcuJ4TRav2oD9crQoIg#3

To run it:  python webhook_listener.py"""

import datetime as dt
import pathlib as pl
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog

from flask import Flask, Response, request
from icecream import ic

refwrangle_dir = Path(__file__).resolve().parent.parent
# refwrangle_dir = pl.Path('~/ref/refwrangle').expanduser() # can't reliably get dir of an .ipynb 
sys.path.append(str(refwrangle_dir))
import refwrangle as rfw
import link_ai_lit as lal

WRITE_LOG_FILE = True

watcher_dir = rfw.refwrangle_tmp_dir / 'watchter'
raw_inputs_dir = watcher_dir / 'raw'
raw_inputs_dir.mkdir(parents=True, exist_ok=True)
default_relinked_output_dir = watcher_dir / 'relinked'
default_relinked_output_dir.mkdir(parents=True, exist_ok=True)

ic(raw_inputs_dir.exists(), default_relinked_output_dir.exists())

# Create a queue for communication between threads
gui_queue = queue.Queue()

def get_output_file_thread():
    """Gets the relinked output file name from the user."""
    root = tk.Tk()
    root.withdraw()  # Hide the root window

    while True:
        try:
            # Check for tasks in the queue
            task = gui_queue.get(block=False)
            if task == "exit":
                break
            # Process save file dialog task
            
            output_file_path = filedialog.asksaveasfilename(
                initialdir=task["initial_output_dir"],
                initialfile=task["default_output_filename"],
                defaultextension=".md",
                filetypes=[("Markdown files", "*.md"), ("All files", "*.*")]
            )
            task["callback"](output_file_path)
        except queue.Empty:
            root.update_idletasks()
            root.update()

# Start Tkinter in a separate thread
threading.Thread(target=get_output_file_thread, daemon=True).start()

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    """Stores perplexity file extracted by the Save my Chatbot browser plugin"""

    file_basename = f'perplexity_{dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'

    if 'multipart/form-data' in request.content_type:
        # get and save the expected payload

        form_data = request.form.to_dict()
        files = request.files
        input_smc_files = []
        for filename, file in files.items():
            print(f"File Received: {str(filename)}")
            file_counter = f'_{len(input_smc_files)}' if len(files) > 1 else ''
            file_raw_path = raw_inputs_dir / f'{file_basename}_data{file_counter}.md'
            print(f"Saving data: {str(file_raw_path)}")
            file.save(file_raw_path)
            input_smc_files.append(file_raw_path)

        logstr = ''         
        if (num_got_files := len(input_smc_files)) > 1:
            logstr = f'Expected to receive only one file, got {num_got_files}: Converting only the first.'
            print(logstr)

        if WRITE_LOG_FILE:
            file_raw_path = raw_inputs_dir / f'{file_basename}.log'
            print(f'Writing webhook log to {str(file_raw_path)}')
            with open(file_raw_path, "w", encoding='utf-8') as log_file:
                if logstr:
                    log_file.write(logstr)
                log_file.write(f"Form Data:\n{form_data}\n")
                log_file.write(f"Files:\n{list(files.keys())}\n")

        input_smc_file = input_smc_files[0]

        def relink_smc_file(output_relinked_file):
            # zot_db_items = lpz.get_zotero_data()

            if output_relinked_file:
                print(f'{input_smc_file}\n-->\n{output_relinked_file}')
                chat_files = rfw.ensure_iterable(pl.Path(output_relinked_file))
                ic(chat_files)

                lal.relink_chat_files(pl.Path(input_smc_file), pl.Path(output_relinked_file))
                print('Done.')
            else:
                print('Save operation cancelled')

        # Send task to Tkinter thread
        gui_queue.put({"initial_output_dir": default_relinked_output_dir,
                       "default_output_filename": f'{file_basename}.md',
                       "callback": relink_smc_file})
    else:
        # Fallback for an unexpected content type
        raw_data = request.data.decode('utf-8')
        print("Received unexpected webhook content.  Raw Data:", raw_data)

    # return "File dialog opened", 200 # R1 recomendation:  https://www.perplexity.ai/search/explain-what-this-code-does-an-p_8QpQwCQm2BZsM7iu_bbg#1
    return Response(status=200) # what working, I think from perplexity's own engine

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
