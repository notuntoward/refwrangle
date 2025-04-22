"""Tests to see if the pyzotero can use zotero's local API. It can."""

# %%
import pathlib as pl
import sys
from icecream import ic

# Define paths and credentials
refwrangle_dir = Path(__file__).resolve().parent.parent # works??
#refwrangle_dir = pl.Path('~/ref/refwrangle').expanduser()
sys.path.append(str(refwrangle_dir))
import refwrangle.utils.refwrangle as rfw  # Import your custom refwrangle module

# %%
# Works when I add local=True. From here:  https://github.com/urschrei/pyzotero

from pyzotero import zotero

zot = zotero.Zotero(rfw.zotero_library_id, rfw.zotero_library_type, rfw.zotero_api_key, local=True) # local=True for read access to local Zotero
items = zot.top(limit=5)
# we've retrieved the latest five top-level items in our library
# we can print each item's item type and ID
for item in items:
    print('Item: %s | Key: %s' % (item['data']['itemType'], item['data']['key']))

# %%    
#  Works.  From here: https://github.com/urschrei/pyzotero/blob/main/example/local_get_item_detail.py

from pyzotero import zotero
from pprint import pprint

def get_item_detail(item_id):
    """
    Get detailed information about a specific Zotero item
    Args:
        item_id (str): Zotero item ID
    """
    # Initialize Zotero client with local=True
    zot = zotero.Zotero(library_id=rfw.zotero_library_id, library_type='user', local=True)

# rfw.zotero_library_id, rfw.zotero_library_type, rfw.zotero_api_key,
    try:
        # Get the item
        item = zot.item(item_id)

        # Print basic information
        print("\nItem Details:")
        print("-" * 50)
        print(f"Item ID: {item['key']}")
        print(f"Item Type: {item['data'].get('itemType', 'Not specified')}")
        print(f"Title: {item['data'].get('title', 'No title')}")

        # If it's an attachment, show parent item
        if item['data'].get('parentItem'):
            try:
                parent = zot.item(item['data']['parentItem'])
                print("\nParent Item:")
                print(f"Parent ID: {parent['key']}")
                print(f"Parent Title: {parent['data'].get('title', 'No title')}")
            except Exception as e:
                print(f"Error getting parent item: {e!s}")

        # If it has child items (attachments), show them
        children = zot.children(item_id)
        if children:
            print("\nChild Items:")
            for child in children:
                print(f"- {child['data'].get('title', 'No title')} "
                      f"(ID: {child['key']}, "
                      f"Type: {child['data'].get('itemType', 'Unknown')})")

        # Show collections this item belongs to
        collections = item['data'].get('collections', [])
        if collections:
            print("\nCollections:")
            try:
                for coll_id in collections:
                    coll = zot.collection(coll_id)
                    print(f"- {coll['data'].get('name', 'Unnamed')} (ID: {coll_id})")
            except Exception as e:
                print(f"Error retrieving collections: {e!s}")

        # Show all metadata
        print("\nFull Metadata:")
        print("-" * 50)
        pprint(item['data'])

    except Exception as e:
        print(f"Error getting item details: {e!s}")
        return None
    else:
        return item

if __name__ == "__main__":
    # Example usage with a specific item ID
    item_id = 'QD383V7V'  # Replace with your item ID
    item_detail = get_item_detail(item_id) 
