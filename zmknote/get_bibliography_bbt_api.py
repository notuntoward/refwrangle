# This works.
# See: https://retorque.re/zotero-better-bibtex/exporting/json-rpc/index.html
# See: https://www.perplexity.ai/search/can-pyzotero-get-a-bibliograph-GOBZjDewTvOsa0uKBnB2Tw
# See: https://www.zotero.org/styles?q=idb%3Amodern-language-association

import json
import sys

import requests

def get_bibliography_bbt_api(item_citekey_bbt: str) -> str:
    """Fetches bibliography entry from Better BibTeX using the provided citation key."""
    # See: https://retorque.re/zotero-better-bibtex/exporting/json-rpc/index.html
    # See: https://www.perplexity.ai/search/can-pyzotero-get-a-bibliograph-GOBZjDewTvOsa0uKBnB2Tw
    # See: https://www.zotero.org/styles?q=idb%3Amodern-language-association"""
    
    url = "http://localhost:23119/better-bibtex/json-rpc"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    data = {
        "jsonrpc": "2.0",
        "method": "item.bibliography",
        "params": [
            [item_citekey_bbt],
            {
                "contentType": "text",
                "id": "modern-language-association",
                "locale": "en-US",
                "quickCopy": False
            }
        ]
    }

    response = requests.post(url, headers=headers, data=json.dumps(data), timeout=5)
    if response.status_code == 200:
        result = response.json()
        return result["result"]
    
    print(f"Error getting BBT biography: {response.status_code=}, {response.text=}", file=sys.stderr)
    return ""

item_key = 'Dale19CompleteGuideBulgSquat'    
bib = get_bibliography_bbt_api(item_key)
print(f'{item_key=}: {bib=}')
    
# url = "http://localhost:23119/better-bibtex/json-rpc"
# headers = {
#     "Content-Type": "application/json",
#     "Accept": "application/json"
# }
# data = {
#     "jsonrpc": "2.0",
#     "method": "item.bibliography",
#     "params": [
#         ["Dale19CompleteGuideBulgSquat"],
#         {
#             "contentType": "text",
#             "id": "modern-language-association",
#             "locale": "en-US",
#             "quickCopy": False
#         }
#     ]
# }

# response = requests.post(url, headers=headers, data=json.dumps(data), timeout=5)

# if response.status_code == 200:
#     result = response.json()
#     print(result["result"])
# else:
#     print(f"Error: {response.status_code}, {response.text}")    

