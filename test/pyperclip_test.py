
"""Just a test of the pyperclip clipboard reader and modifier.

Reads the text in a windows clipboard, and uppercase all of it, so that you see all upper case text when you do a paste.

Usage:
  - Copy some text to your clipboard.
  - Run the script.
  - Paste the text wherever needed; it will then be in uppercase.
"""

import pyperclip

# Read text from the clipboard
clipboard_text = pyperclip.paste()

# Convert the text to uppercase
uppercase_text = clipboard_text.upper()

# Copy the uppercase text back to the clipboard
pyperclip.copy(uppercase_text)
