"""A simple test of the zotero action and tags plugin.  Can it send a zotero item's citekey and and can this listener receive it and print it?

The answer is 'yes.'"""

from flask import Flask, request

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    citekey = data.get('citekey')
    itemkey = data.get('zotero_key')

    print(f"Received Citation Key: {citekey}")
    print(f"Received Zotero Item Key: {itemkey}")

    # Add your logic here...

    return "Webhook received", 200

if __name__ == '__main__':
    app.run(port=5050)
















