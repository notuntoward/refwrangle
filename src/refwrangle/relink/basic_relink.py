"""Zoteroize and Obsidianize an Exported Perplexity Dialogue

After a very simple split of a perplexity exported markdown file, turn the markdown footnotes into links.
If the corresponding footnote number is associated with a url in zotero, the link is to matching Obsidian
literature notes (if they exist) or to matching Zotero items.  The footnotes are also turned into
the appropriate markdown links."""

# %% [markdown]

from pathlib import Path
import re
from typing import Union
from icecream import ic
import src.refwrangle.relink.link_perplexity_zotero as lpz
import refwrangle as rfw
import src.refwrangle.relink.link_ai_lit as lat

relinker = lpz.ZoteroLinkConverter()

def split_markdown_footnotes(text: str) -> tuple[str, str]:
    """Split markdown text into body and footnotes sections.  Very basic."""

    # Split by "is line just a footnote with url or not?"
    body_lines = []
    footnote_lines = []
    footnote_def_pattern = re.compile(r'^\s*\[\^?(\d+)\]:\s*(https?://\S+)')
    for line in text.split('\n'):
        if footnote_def_pattern.match(line):
            footnote_lines.append(line)
        else:
            body_lines.append(line)
    
    return '\n'.join(body_lines), '\n'.join(footnote_lines)

def perplex_to_obs_note_text(md_text:str) -> str:
    """Convert perplexity export markdown text to a better-formatted Obsidian note
    with the footnotes replaced with links to obsidian notes or zotero items 
    (when they exist), and to markdown URL links otherwise."""
    
    # Remove pointless leading markdwown divider, 1st empty heading, blank lines
    md_text = rfw.remove_markdown_dividers(md_text)
    if lines := md_text.splitlines():
        empty_heading_index = None
        for i, line in enumerate(lines):
            if line.strip() == '#':
                empty_heading_index = i
                break
        
        if empty_heading_index is not None:
            lines = lines[:empty_heading_index] + lines[empty_heading_index+1:]
        
        # Join the remaining lines back into a string
        md_text = '\n'.join([line.strip() for line in lines])
    
    body, footnotes = split_markdown_footnotes(md_text)
    
    # Replace footnotes with links to URL, obsidian or zotero
    citenum_to_url = dict(rfw.get_link_tu_pairs(footnotes, 
                                                lat.SOURCE_LIST_PATTERN_PERPLEX_RE))
    sources_relinked, body_relinked = relinker.basic_relink(body, citenum_to_url)
    sources_relinked_str = "\n".join(sources_relinked)
    
    return f'{body_relinked.strip()}\n# Sources\n{sources_relinked_str}'

def perplex_to_obs_note_file(in_filepath: Union[str, Path], out_filepath: Union[str, Path]) -> None:
    """Convert perplexity export markdown file to better-formatted obsidian note
    file, with the footnotes replaced with links to obsidian notes or zotero items 
    (when the exist), and to markdown URL links otherwise."""

    md_text = rfw.read_markdown_file(Path(in_filepath))

    relinked_text = perplex_to_obs_note_text(md_text)
    relinked_text = f'{lat.make_obsidian_front_matter()}\n{relinked_text}'
    
    Path(out_filepath).write_text(relinked_text, encoding='utf-8')
    
# %%
if __name__ == "__main__":
   in_file = Path('~/ref/refwrangle/dat/orig/dialog_2_perplex_250323.md').expanduser()
   out_dir = Path(r"C:\Users\scott\OneDrive\share\ref\obsidian\Obsidian Share Vault\Scratch Space")
   out_file = out_dir / 'tmp_basic_relink.md'
   ic(in_file, out_file)

   perplex_to_obs_note_file(in_file, out_file)
