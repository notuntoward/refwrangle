import re
import markdown
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor

class MarkdownFootnoteExtension(Extension):
    """Extension that keeps footnotes in markdown format."""
    
    def __init__(self, **kwargs):
        self.config = {
            'LINK_TEXT': ['{}', "The text string that links from the reference to the footnote."],
            'SEPARATOR': [':', 'Footnote separator.']
        }
        super().__init__(**kwargs)
        
    def extendMarkdown(self, md):
        footnote_preprocessor = MarkdownFootnotePreprocessor(self)
        md.preprocessors.register(footnote_preprocessor, 'md_footnotes', 175)
        
class MarkdownFootnotePreprocessor(Preprocessor):
    """Preprocessor to find and process footnote references and definitions."""
    
    def __init__(self, extension):
        self.extension = extension
        self.footnotes = {}
        self.footnote_refs = []
        super().__init__()
        
    def run(self, lines):
        # First pass: collect footnote definitions
        body_lines = []
        footnote_lines = []
        footnote_def_pattern = re.compile(r'^\s*\[\^([^\]]+)\]:\s*(.*)')
        
        for line in lines:
            match = footnote_def_pattern.match(line)
            if match:
                id, text = match.groups()
                self.footnotes[id] = text.strip()
                footnote_lines.append(line)
            else:
                body_lines.append(line)
        
        # Second pass: process footnote references
        result_lines = []
        footnote_ref_pattern = re.compile(r'\[\^([^\]]+)\]')
        
        for line in body_lines:
            # Find all footnote references in the line
            line_copy = line
            matches = footnote_ref_pattern.findall(line)
            
            # Process each reference
            for ref_id in matches:
                if ref_id in self.footnotes:
                    url = self.footnotes[ref_id]
                    # Replace the footnote reference with a markdown link
                    link_text = self.extension.getConfig('LINK_TEXT').format(ref_id)
                    line_copy = line_copy.replace(f'[^{ref_id}]', f'[{link_text}]({url})')
                    
            result_lines.append(line_copy)
        
        return result_lines, body_lines, footnote_lines

def makeExtension(**kwargs):
    return MarkdownFootnoteExtension(**kwargs)

def process_markdown_footnotes(text, link_text='{}'):
    """
    Process markdown text with footnotes and convert them to markdown links.
    
    Args:
        text (str): Markdown text with footnotes
        link_text (str): Format for the link text. Use {} as placeholder for footnote ID.
        
    Returns:
        tuple: (processed_text, body_text, footnote_text)
    """
    # Create an instance of the extension
    footnote_ext = MarkdownFootnoteExtension(LINK_TEXT=link_text)
    
    # Create a markdown instance with our extension
    md = markdown.Markdown(extensions=[footnote_ext])
    
    # Split the input text into lines
    lines = text.split('\n')
    
    # Access our preprocessor directly from the registry
    for name, preprocessor in md.preprocessors._data.items():
        if isinstance(preprocessor, MarkdownFootnotePreprocessor):
            # Process the markdown text with our preprocessor
            processed_lines, body_lines, footnote_lines = preprocessor.run(lines)
            return '\n'.join(processed_lines), '\n'.join(body_lines), '\n'.join(footnote_lines)
    
    # If our preprocessor wasn't found, return the original text and empty strings for body and footnotes
    return text, '', ''

# Example usage
if __name__ == "__main__":
    # Sample markdown text with footnotes
    text = """
# Sample Document with Footnotes

This is a test document with a footnote reference[^1] and another[^2].

[^1]: https://example.com
[^2]: https://another-example.com
"""
    
    processed_text, body_text, footnote_text = process_markdown_footnotes(text)
    print("Processed Text:")
    print(processed_text)
    print("\nBody Text:")
    print(body_text)
    print("\nFootnote Text:")
    print(footnote_text)
