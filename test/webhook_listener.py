"""A listener that can maybe handle the output of the save my chatbot browser exension.
Advice from: https://www.perplexity.ai/search/what-is-a-webhook-url-0DbzcuJ4TRav2oD9crQoIg#3

To run it:  python webhook_listener.py"""

import pathlib as pl
import datetime as dt
from flask import Flask, request, Response

write_log_file = True

outdir = pl.Path(r'C:\Users\scott\tmp')

app = Flask(__name__)
@app.route('/webhook', methods=['POST'])

def webhook():
    """Stores perplexity file extracted by the Save my Chatbot browser plugin"""

    file_name_head = outdir / f'perplexity_{dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'

    if 'multipart/form-data' in request.content_type:
        # get and save the expected payload

        form_data = request.form.to_dict()
        #print("Form Data:", form_data)

        files = request.files
        fileix=0
        for filename, file in files.items():
            print(f"File Received: {filename}")
            file_counter = f'_{fileix}' if len(files) > 1 else ''
            file_path = f'{file_name_head}_data{file_counter}.md'
            print(f"Saving data: {file_path}")
            file.save(file_path)
            fileix += 1

        if write_log_file:
            file_path = f'{file_name_head}.log'
            print(f'Writing webhook log to {file_path}')
            with open(file_path, "w", encoding='utf-8') as log_file:
                log_file.write(f"Form Data:\n{form_data}\n")
                log_file.write(f"Files:\n{list(files.keys())}\n")
    else:
        # fallback for an uexpected content type
        raw_data = request.data.decode('utf-8')
        print("Unexpected Content.  Raw Data:", raw_data)
        if write_log_file:
            file_path = f'{file_name_head}.log'
            print(f'writing webhook log to {file_path}')
            with open(file_path, "w", encoding='utf-8') as log_file:
                log_file.write(f"Raw Data:\n{raw_data}\n")

    return Response(status=200)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
