"""A listener that can maybe handle the output of the save my chatbot browser exension.
Advice from: https://www.perplexity.ai/search/what-is-a-webhook-url-0DbzcuJ4TRav2oD9crQoIg#3

To run it:  python webhook_listener.py"""

# this one only understands json
# from flask import Flask, request, Response

# app = Flask(__name__)

# @app.route('/webhook', methods=['POST'])
# def webhook():
#     # Get JSON payload from the webhook
#     data = request.json
#     print("Received webhook data:", data)

#     # Save the data to a file (optional)
#     with open("webhook_output.json", "w") as file:
#         file.write(str(data))

#     # Respond with HTTP 200 status
#     return Response(status=200)

# if __name__ == '__main__':
#     # Run the app on localhost at port 5000
#     # Using this, I should type http://localhost:5000/webhook into the save my chatbot box
#     app.run(host='0.0.0.0', port=5000)

# I got a zero-lenght file from this one
#
# from flask import Flask, request, Response

# app = Flask(__name__)

# @app.route('/webhook', methods=['POST'])
# def webhook():
#     # Check if Content-Type is JSON
#     if request.content_type == 'application/json':
#         data = request.json  # Parse JSON payload
#     else:
#         # Handle non-JSON payloads
#         data = request.data.decode('utf-8')  # Decode raw payload as string

#     print("Received webhook data:", data)

#     # Save the data to a file (optional)
#     with open("webhook_output.txt", "w") as file:
#         file.write(str(data))

#     return Response(status=200)

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000)


# this should tell me about the payload

# from flask import Flask, request, Response

# app = Flask(__name__)

# @app.route('/webhook', methods=['POST'])
# def webhook():
#     # Log raw data and headers for debugging
#     raw_data = request.data.decode('utf-8')  # Raw payload
#     headers = request.headers  # HTTP headers

#     print("Headers:", headers)
#     print("Raw Data:", raw_data)

#     # Save raw data to a file for inspection
#     with open("webhook_output.txt", "w") as file:
#         file.write(f"Headers:\n{headers}\n\nRaw Data:\n{raw_data}")

#     return Response(status=200)

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000)

# Perplexity's suggestion for handline the kind of payload it's sending.  It finally wrote an (almost empty) file.

# from flask import Flask, request, Response

# app = Flask(__name__)

# @app.route('/webhook', methods=['POST'])
# def webhook():
#     # Check if the request contains files (multipart/form-data)
#     if 'multipart/form-data' in request.content_type:
#         # Log all form fields
#         form_data = request.form.to_dict()
#         print("Form Data:", form_data)

#         # Log any uploaded files
#         files = request.files
#         for filename, file in files.items():
#             print(f"File Received: {filename}")
#             # Save the file locally (optional)
#             file.save(filename)

#         # Save raw form data to a file for inspection
#         with open("webhook_output.txt", "w") as file:
#             file.write(f"Form Data:\n{form_data}\n")
#             file.write(f"Files:\n{list(files.keys())}\n")
#     else:
#         # Handle other content types (fallback)
#         raw_data = request.data.decode('utf-8')
#         print("Raw Data:", raw_data)
#         with open("webhook_output.txt", "w") as file:
#             file.write(f"Raw Data:\n{raw_data}\n")

#     return Response(status=200)

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000)

# said to be useful for diagnosing the problem

from flask import Flask, request, Response

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    # Check if the request contains files (multipart/form-data)
    if 'multipart/form-data' in request.content_type:
        # Log all form fields
        form_data = request.form.to_dict()
        print("Form Data:", form_data)

        # Handle uploaded files
        files = request.files
        for filename, file in files.items():
            print(f"File Received: {filename}")

            # Save the file locally for inspection
            saved_file_path = f"received_{filename}"
            file.save(saved_file_path)
            print(f"File saved as: {saved_file_path}")

        # Save form data and file names to a log file
        with open("webhook_output.txt", "w") as log_file:
            log_file.write(f"Form Data:\n{form_data}\n")
            log_file.write(f"Files:\n{list(files.keys())}\n")
    else:
        # Handle other content types (fallback)
        raw_data = request.data.decode('utf-8')
        print("Raw Data:", raw_data)
        with open("webhook_output.txt", "w") as log_file:
            log_file.write(f"Raw Data:\n{raw_data}\n")

    return Response(status=200)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
