import requests

def get_bibliography_string(item_key):
    """
    Retrieves a formatted bibliography string for a given Zotero item key
    using the Better BibTeX web API.

    Args:
        item_key (str): The Zotero item key.

    Returns:
        str: The formatted bibliography string, or an error message if the
             request fails.
    """
    try:
        # Construct the API call URL
        api_url = f'http://127.0.0.1:23119/better-bibtex/export/item/{item_key}?format=biblatex'

        # Make the API call
        response = requests.get(api_url)

        # Check if the request was successful
        if response.status_code == 200:
            return response.text
        else:
            return f"Error: Unable to retrieve bibliography string. Status code: {response.status_code}"

    except requests.exceptions.ConnectionError as e:
        return f"Error: Connection error.  Is Zotero running with Better BibTeX enabled? {e}"


# Example usage
item_key = "I4G6IXQS"
bibliography_string = get_bibliography_string(item_key)
print(bibliography_string)
