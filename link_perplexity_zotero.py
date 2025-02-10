# %% [markdown]
# ### Zoteroize and Obsidianize a Perplexity Dialogue from `Save my Chatbot`
# 
# Replace the citation numbers in a saved Save my Chatbot Perplexity dialogue with matching literature note or zotero item links

# %%
import pathlib as pl
from collections import defaultdict, Counter
import sys
import re
from typing import Optional, Dict, List, Tuple
import datetime as dt
import pandas as pd

refwrangle_dir = pl.Path('~/ref/refwrangle').expanduser() # can't reliably get dir of an .ipynb 
sys.path.append(str(refwrangle_dir))
# import refwrangle as rfw
import refwrangle as rfw
import re

# %%
TOP_HEADING_LEVEL_IN_AI = 2
MIN_SCORE_TITLE_MATCH = 95 # max==100: stringent, limit false matches
ANSWER_HEADER = "## AI answer"
USER_HEADER = '## User'
MAX_WORDS_USER_HEADER = 10

# %% [markdown]
# ##### get the URLs of all parent items in the zotero db, and find out which have obsidian literature notes
# %%
def get_zotero_data(verbose=False):
    """"""
    zotero_cache = rfw.ZoteroCache()
    parent_items = zotero_cache.get_data()

    # %%
    # Collect info about each zotero DB item that has a URL
    lit_note_file_stems = {fNm.stem for fNm in rfw.lit_notes_obsidian_dir.glob('*.md')}

    zot_db_items = []
    url_to_citekey = defaultdict(list)
    for parent in parent_items:
        pdat = parent['data']
        if not (title := pdat.get('title')):
            continue

        citekey_this = rfw.get_citation_key(pdat)
        zot_db_items.append(dict(citekey=citekey_this, zotkey=parent['key'], title=title, hasLitNote=citekey_this in lit_note_file_stems))

        if url := pdat.get('url'):
            if normalized_url :=rfw.normalize_url(url):
                url_to_citekey[normalized_url].append(citekey_this)

    if repeated_urls := {url:url_to_citekey[url] for url in url_to_citekey.keys() if len(url_to_citekey[url])>1}:
        print(f"Found {len(repeated_urls)} URLs with > 1 parent (citekey)")
        for url, citekeys in repeated_urls.items():
            print(f"{', '.join(citekeys)}\n\t{url}")
        raise Exception('Not written for repeated URLs')

    citekey_to_url = {citekeys[0]: url for url, citekeys in url_to_citekey.items()}

    zot_db_items = pd.DataFrame(zot_db_items).set_index('citekey')
    zot_db_items['url'] = pd.Series(citekey_to_url)
    zot_db_items = zot_db_items.reset_index()

    if sum(has_no_url := zot_db_items.url.isna()):
        print(f"Dropping {sum(has_no_url)} of {len(zot_db_items)} zotero entries with no URL:")
        zot_db_items = zot_db_items[~has_no_url]

        if verbose:
            zot_db_items_no_url = zot_db_items[has_no_url]
            display(zot_db_items_no_url.head())

    return zot_db_items # , citekey_to_url, url_to_citekey # not needed? 

# %%
def find_zotero_item_by_url(url: str, zot_db_items: pd.DataFrame) -> Optional[Dict]:
    """Find a Zotero item by its URL."""
    normalized_url = rfw.normalize_url(url)
    matches = zot_db_items[zot_db_items['url'] == normalized_url]
    if not matches.empty:
        return matches.iloc[0].to_dict()  # Return df row as dictionary
    return None

def find_zotero_item_by_title(target_title: str, zot_db_items: pd.DataFrame) -> Optional[Dict]:
    """Find the Zotero item with the best matching title."""
    zotero_items = zot_db_items.to_dict('records')
    best_match_item = None
    best_score = 0

    for item in zotero_items:
        score = rfw.match_titles(target_title, item['title'], main_title_only=False)
        if score > best_score:
            best_match_item = item.copy()
            best_score = score

    if best_score > MIN_SCORE_TITLE_MATCH:
        return best_match_item 
  
    return None

def build_source_url_to_title(sources_content: str) -> Dict[str, str]:
    """Build a dictionary mapping URLs to titles from the sources section."""
   
    source_url_to_title = {}
    matches = re.findall(r'- \[(.*?)\]\((https?://\S+)\)', sources_content)
    for title, url in matches:
        normalized_url = rfw.normalize_url(url)
        title = re.sub(r'^\s*\(\d+\)\s*', '', title) # remove ref num
        source_url_to_title[normalized_url] = title.strip()
    return source_url_to_title

def replace_links_with_zotero_items(
    body_content: str,
    sources_content: str,
    zot_db_items: pd.DataFrame,
) -> Tuple[str, str, Counter]:
    """
    Replace links in body content and sources content with Zotero links or leave them as-is.
    
    Returns: 
        - Relinked body content.
        - Relinked sources content.
        - A Counter of URLs in the body that were not found in the Sources part."""
    
    source_url_to_title = build_source_url_to_title(sources_content)

    unsourced_body_links = Counter()
    body_link_num_not_in_zotero = {}

    def link_to_obsidian_or_zotero(zotero_item):
        """Returns link to Obsidian lit note if it exists, else to zotero item"""
        if zotero_item.get('hasLitNote', False):
            obsidian_citekey = zotero_item["citekey"]
            return f'[[{obsidian_citekey}|{obsidian_citekey}]]'
        else:
            link_text = f'{zotero_item["citekey"]}\u2794{zotero_item["zotkey"]}'
            return rfw.zotero_item_link(zotero_item["zotkey"], link_text)

    def make_my_lit_link(url):
        """If a zotero item has a matching url, or title that matches a source's 
        section link title, then return a link to that item or its obsidian note."""

        if zotero_item := find_zotero_item_by_url(url, zot_db_items):
            return link_to_obsidian_or_zotero(zotero_item)

        if url in source_url_to_title:
            # try to replace matching source link title with zotero item title
            title = source_url_to_title[url]
            if zotero_item := find_zotero_item_by_title(title, zot_db_items):
                return link_to_obsidian_or_zotero(zotero_item)

        return None # no kind of zotero item match
            
    def swap_my_lit_link_body(doc_match):
        """Replace a body section link with one pointing to zotero/obsidian, if possible.
        Otherwise highlight it so it's clear there was no match
        
        Arg: doc_match: a regexp match object to a document body section link"""
         
        url_body_link = rfw.normalize_url(doc_match.group(2))
        body_link_num = doc_match.group(1)
        
        if url_body_link not in source_url_to_title:
            unsourced_body_links[url_body_link] += 1 # for later error reporting

        if my_link := make_my_lit_link(url_body_link):
            return my_link

        # a link in body that wasn't in zotero: highlight it in both the body and the sources
        body_link_num_not_in_zotero[body_link_num] = True
        return f'=={doc_match.group(0)}=='

    def append_my_lit_link_source(doc_match):
        """Append a sources section link with a highlighted link pointing to zotero/obsidian, if possible.
        
        Arg: doc_match: a regexp match object to a document sources section link"""

        url_source_link = rfw.normalize_url(doc_match.group(3))

        source_link_num = doc_match.group(1)
        output_link_num = f'({source_link_num})'
        descript_source_link = doc_match.group(2)
        if my_link := make_my_lit_link(url_source_link):
            return f'[{output_link_num} {descript_source_link}]({url_source_link}) **{my_link}**'

        if body_link_num_not_in_zotero.get(source_link_num):
            output_link_num = f'=={output_link_num}==' # highlight it, to match body appearance
        
        return f'[{output_link_num} {descript_source_link}]({url_source_link})'
    
    relinked_body_content = re.sub(r'\[(.*?)\]\((https?://\S+)\)', swap_my_lit_link_body, body_content)

    relinked_sources_content = re.sub(r'\[\((\d+)\)\s*(.*?)\]\((https?://\S+)\)', append_my_lit_link_source, sources_content)
    return relinked_body_content, relinked_sources_content, unsourced_body_links


def relink_perplexity_export_smc(input_file: str, output_file: str, zot_db_items: pd.DataFrame):
    """Process a markdown file to replace links with Zotero references."""
    
    with open(input_file, 'r',  encoding='utf-8') as infile:
        content = infile.read()

    sections = re.split(rf'(?<=\n){USER_HEADER}', content)

    # start the output with Obsidian frontmatter, and a link to original perplexity chat and date
    front_matter = f'---\ncategory: aichat\ncreated date: {dt.datetime.now()}\n---\n'
    chat_source = " ".join(sections[0].split("\n")[1:]) # remove redundant header
    processed_sections = [front_matter + f'{chat_source.lstrip(' ')}\n']
        
    log_missing_links = []

    def capitalize_first_word_if_needed(text):
        first_word = text.split()[0] if text.strip() else ""
        if any(char.isupper() for char in first_word):
            return text  # Return the original string if the first word has capitals
        else:
            return text[0].upper() + text[1:] if text else text
 
    def get_first_n_words(text, n, stop_phrase=None):
        if stop_phrase and stop_phrase in text:
            text = text.split(stop_phrase)[0]
        
        words = text.split()
        return ' '.join(words[:n])

    def summarize_prompt(prompt, num_words, stop_phrase=None):
        prompt = get_first_n_words(prompt, num_words, stop_phrase)
        return rfw.make_atx_header(f'User: "{capitalize_first_word_if_needed(prompt)}..."', 
                                   TOP_HEADING_LEVEL_IN_AI - 1)

    for section_idx, section in enumerate(sections[1:], start=1):  # Skip anything before the first "User" section
        section_parts = re.split(r'(\n---\s*\n\s*\*\*Sources:\*\*\s*\n)', section)
        if len(section_parts) < 3:
            print('Incomplete Body/Sources pair: assume no Sources for this section')
            section_parts += ['','']
        else:
            section_parts[1] = f"\n{rfw.make_atx_header('Sources', TOP_HEADING_LEVEL_IN_AI)}\n"

        body, sources_header, sources = section_parts
        user_header = summarize_prompt(body, MAX_WORDS_USER_HEADER, ANSWER_HEADER)

        body, sources, unsourced_body_links = replace_links_with_zotero_items(body, sources, zot_db_items)
        body = rfw.setext_headers_to_atx(body, TOP_HEADING_LEVEL_IN_AI+1) # AI subheaders are all setext
        
        if unsourced_body_links:
            # TODO: Need to fix this so that the reference numbers are correctly parsed from the source links
            # log_missing_links.append(
            #     f"Section {section_idx}: Body links not in source: " +
            #     ", ".join([f"{url} (count: {count})" for url, count in unsourced_body_links.items()]))
            pass

        processed_sections += [user_header, body, sources_header, sources]

    # Strip empty lines: lines are mostly separated in separate strings in the list but not totally
    # This compaction might be a little too much.  Try it for a while and see.
    processed_sections = "\n".join(line for line in processed_sections.split("\n") if line.strip())    
    processed_sections = ''.join(processed_sections)
    
    with open(output_file, 'w',  encoding='utf-8') as outfile:
        outfile.write(''.join(processed_sections))

    if log_missing_links:
        print("Log of missing links:")
        for log_entry in log_missing_links:
            print(log_entry)