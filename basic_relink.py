# %% [markdown]
#
#  ### Zoteroize and Obsidianize a Perplexity Dialogue
# 
# After a very simple split of a perplexity exported markdown file, turn the markdown footnotes into links.
# If the corresponding footnote number is associated with a url in zotero, the link is to matching Obsidian
# literature notes (if it exists) or to the matching Zotero item.  The foot notes are also turned into
# the appropriate markdown links.

import datetime as dt
from pathlib import Path
import re
import sys
from typing import List, Tuple, Union
import numpy as np
import pandas as pd
from icecream import ic
import link_perplexity_zotero as lpz
import refwrangle as rfw
import link_ai_lit as lat

relinker = lpz.ZoteroLinkConverter()

def split_markdown_footnotes(text: str) -> tuple[str, str]:
    """Split markdown text into body and footnotes sections using regex only."""
    
    # remove pointless leading markdwown divider and 1st empty heading, if either exist
    text = rfw.remove_markdown_dividers(text)
    
    if lines := text.splitlines():
        empty_heading_index = None
        for i, line in enumerate(lines):
            if line.strip() == '#':
                empty_heading_index = i
                break
        
        if empty_heading_index is not None:
            lines = lines[:empty_heading_index] + lines[empty_heading_index+1:]
        
        # Join the remaining lines back into a string
        text = '\n'.join(lines)
    
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

def relink_text(md_text):

    body, footnotes = split_markdown_footnotes(md_text)
    citenum_to_url = dict(rfw.get_link_tu_pairs(footnotes, lat.SOURCE_LIST_PATTERN_PERPLEX_RE))
    
    footnote_links, body_relinked = relinker.basic_relink(body, citenum_to_url)
    footnote_links = "\n".join(footnote_links)
   
    return f'{body_relinked.strip()}\n# Sources\n{footnote_links}'

def relink_file(in_filepath: Union[str, Path], out_filepath: Union[str, Path]):
    
    md_text = rfw.read_markdown_file(in_filepath)
    md_text = '\n'.join(line for line in md_text.splitlines() if line.strip()) # remove blank lines

    relinked_text = relink_text(md_text)
    relinked_text = f'{lat.make_obsidian_front_matter()}\n{relinked_text}'
    
    out_filepath = out_filepath if isinstance(out_file, Path) else Path(out_filepath)
    out_filepath.write_text(relinked_text, encoding='utf-8')
        
    
    
# %%

if __name__ == "__main__":
   in_file = Path('~/ref/refwrangle/dat/orig/dialog_perplex_250323.md').expanduser()
   out_dir = Path(r"C:\Users\scott\OneDrive\share\ref\obsidian\Obsidian Share Vault\Scratch Space")
   out_file = out_dir / 'tmp_basic_relink.md'
   ic(in_file, out_file)
   
   ic(in_file, out_file)
   relink_file(in_file, out_file)
