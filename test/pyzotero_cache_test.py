"""A cacher of a pyzotero database connection to zotero 7"""

import json
import os
from pyzotero import zotero

class ZoteroCache:
    def __init__(self, library_id, library_type, api_key, cache_file="zotero_cache.json"):
        """
        Initialize the ZoteroCache object.
        - Loads the cache from a file if available.
        - Fetches the latest updates from Zotero to ensure cache coherence.
        """
        self.zot = zotero.Zotero(library_id, library_type, api_key)
        self.cache_file = cache_file
        self.cache = {"items": [], "last_version": 0}
        
        # Load cache from file if it exists
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'r') as file:
                self.cache = json.load(file)
        
        # Synchronize cache with Zotero database
        self._sync_cache_with_zotero()

    def _sync_cache_with_zotero(self):
        """
        Fetch incremental updates from Zotero and update the local cache.
        """
        changes = self.zot.everything(self.zot.items(since=self.cache["last_version"]))
        item_dict = {item['key']: item for item in self.cache["items"]}

        for change in changes:
            if change["data"].get("deleted", False):
                # Remove deleted items from the cache
                item_dict.pop(change["key"], None)
            else:
                # Add or update items in the cache
                item_dict[change["key"]] = change

        # Update the cache list and version
        self.cache["items"] = list(item_dict.values())
        if changes:
            self.cache["last_version"] = max(item["version"] for item in changes)

        # Save updated cache to disk
        self._save_cache()

    def _save_cache(self):
        """Save the current state of the cache to a file."""
        with open(self.cache_file, 'w') as file:
            json.dump(self.cache, file)

    def get_item(self, item_key):
        """
        Retrieve an item by its key from the local cache.
        If not found in the cache, fetch it from Zotero and update the cache.
        """
        for item in self.cache["items"]:
            if item["key"] == item_key:
                return item

        # If not in cache, fetch from Zotero and update the cache
        item = self.zot.item(item_key)
        self._update_cache_item(item)
        return item

    def update_item(self, item):
        """
        Update an item in Zotero and synchronize it with the local cache.
        """
        updated_item = self.zot.update_item(item)
        
        # Update the local cache with the modified item
        self._update_cache_item(updated_item)

    def delete_item(self, item_key):
        """
        Delete an item in Zotero and remove it from the local cache.
        """
        self.zot.delete_item(item_key)
        
        # Remove the deleted item from the local cache
        self.cache["items"] = [item for item in self.cache["items"] if item["key"] != item_key]
        
        # Save updated cache to disk
        self._save_cache()

    def add_item(self, data):
        """
        Add a new item to Zotero and update the local cache.
        """
        new_item = self.zot.create_items([data])[0]
        
        # Add the new item to the local cache
        self._update_cache_item(new_item)

    def _update_cache_item(self, item):
        """Update or add a single item in the local cache."""
        for i, cached_item in enumerate(self.cache["items"]):
            if cached_item["key"] == item["key"]:
                self.cache["items"][i] = item  # Update existing entry
                break
        else:
            self.cache["items"].append(item)  # Add new entry
        
        # Save updated cache to disk
        self._save_cache()

    def get_all_top_level_items(self):
        """
        Retrieve all top-level items (equivalent to zot.everything(zot.top())).
        - Fetches incremental updates from Zotero.
        - Returns all top-level items from the local cache.
        - Updates the local cache with any changes.
        """
        # Ensure the cache is synced with the latest Zotero data
        self._sync_cache_with_zotero()
        
        # Return items with no parentItem (i.e., top-level items)
        return [
            item for item in self.cache["items"]
            if not item["data"].get("parentItem")
        ]

    def search_items(self, query):
        """
        Search for items locally using a query dictionary. Avoids API calls.
        Example query: {'title': 'example'}
        """
        results = []
        for item in self.cache["items"]:
            match = True
            for key, value in query.items():
                # Case-insensitive partial match for string fields
                if isinstance(value, str):
                    item_value = item["data"].get(key, "").lower()
                    if value.lower() not in item_value:
                        match = False
                        break
                else:
                    # Exact match for non-string fields
                    if item["data"].get(key) != value:
                        match = False
                        break
            if match:
                results.append(item)
        return results


if __name__ == "__main__":

    import pathlib as pl
    from collections import defaultdict
    import pandas as pd
    import sys
    from icecream import ic
    import requests
    from bs4 import BeautifulSoup
    from requests.exceptions import Timeout, RequestException
    import time

    refwrangle_dir = pl.Path('~/ref/refwrangle').expanduser() # can't reliably get dir of an .ipynb 
    sys.path.append(str(refwrangle_dir))
    import refwrangle as rfw

    zot_cache = ZoteroCache(rfw.library_id, library_type="user", api_key=rfw.api_key, cache_file="tmp_zotero_cache.json")
        
    
    # Get all top-level items (leveraging caching)
    parent_items = zot_cache.get_all_top_level_items()

    # Print titles of retrieved items
    for item in parent_items:
        print(f"Title: {item['data'].get('title', 'No Title')}")


