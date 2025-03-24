import re

def split_markdown_footnotes(text):
    """Split markdown text into body and footnotes sections using regex only."""
    
    # Regex pattern to identify footnote definitions with integers and URLs
    footnote_def_pattern = re.compile(r'^\s*\[\^?(\d+)\]:\s*(https?://\S+)')
    
    body_lines = []
    footnote_lines = []
    
    # Check each line against the footnote pattern
    for line in text.split('\n'):
        if footnote_def_pattern.match(line):
            footnote_lines.append(line)
        else:
            body_lines.append(line)
    
    return '\n'.join(body_lines), '\n'.join(footnote_lines)

# Test cases
test_text = """
This is a body line with a footnote reference[1].
[1]: https://example.com
Another body line.
[^abc]: https://invalid.com - This should NOT be detected as a footnote
[^2]: https://example.org
[3]: not-a-valid-url - This should NOT be detected as a footnote
  [4]:   https://example.net - This should be detected (with whitespace)
Yet another body line.
[5] : https://spacing-test.com - This should NOT be detected (space before colon)
[^6]: https://caret-test.com
"""

# Run the function on the test text
body, footnotes = split_markdown_footnotes(test_text)

# Print the results
print("Body:")
print(body)
print("\nFootnotes:")
print(footnotes)
