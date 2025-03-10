from flask import Flask, request

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    citation_key = data.get('citekey')
    zotero_item_key = data.get('zotero_key')

    print(f"Received Citation Key: {citation_key}")
    print(f"Received Zotero Item Key: {zotero_item_key}")

    # Add your logic here...

    return "Webhook received", 200

if __name__ == '__main__':
    app.run(port=5050)
















