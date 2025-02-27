# %%
import re
from collections import defaultdict
from typing import Optional, Dict, Tuple, List, Callable
import pandas as pd
import refwrangle as rfw
from dataclasses import dataclass
from icecream import ic

# like in smc source list
source_link_re = re.compile(r'\[\((\d+)\)\s*(.*?)\]\((https?://\S+)\)')
citenum_plain_re = re.compile(r'\[\^?(?P<num>\d+)\]') # handles both ^ and plain number syntax

@dataclass
class PromptResponseSplit:
    """The components of a single Perplexity Prompt-Response"""
    preamble: str
    prompt: str
    response: str
    citenum_url_pairs: List[Tuple]
    url_to_source_title: pd.Series

@dataclass
class PromptResponseSplitDeDup:
    """The components of a single Perplexity Prompt-Response, after the citenums have been deduplicated"""
    preamble: str
    prompt: str
    response_dedup: str
    citenum_to_url_df: pd.DataFrame
    url_to_source_title: pd.Series

class ZoteroLinkConverter:
    """Scans web links in a markdown file and looks for links to the same source in a Zotero database or Obsidian vault.  
    If it finds matches, it replaces the them with links to obsidian literature notes (preferably) or to a
    to the zotero database if an obsidian literature note hasn't been created yet.
    
    This was written to parse markdown files exported from AI chats, so it it assumes that there are prompts, 
    responses and sources derived from web links."""
    
    def __init__(self, verbose: bool = False):
        """Initialize with Zotero data and literature note status"""

        self._note_url_zotero_cache: Dict[str, Optional[Dict]] = {}
        self._note_title_zotero_cache: Dict[str, Optional[Dict]] = {}
        self.zotero_items = self._get_zotero_item_details(verbose)

    def _get_zotero_item_details(self, verbose: bool = False) -> pd.DataFrame:
        """Initialize with Zotero data and literature note status"""
        zotero_cache = rfw.ZoteroCache()
        parent_items = zotero_cache.get_data()
        
        lit_note_file_name_stems = {f.stem for f in rfw.lit_notes_obsidian_dir.glob('*.md')}

        url_to_citekey = defaultdict(list)
        zotero_items = []
        for item in parent_items:
            item_data = item['data']
            if not (title := item_data.get('title')):
                if verbose:
                    rfw.error_message(f'{item['key']}: skipping parent with no title')
                continue # messes up title search, must be malformed anyway?
                
            citekey = rfw.get_citation_key(item_data)
            item_row = {'citekey': citekey,
                        'zotkey': item['key'],
                        'title': title,
                        'hasLitNote': citekey in lit_note_file_name_stems }
            
            if url := item_data.get('url'):
                if norm_url := rfw.normalize_url(url):
                    url_to_citekey[norm_url].append(citekey)
                    item_row['url'] = norm_url
                    
            zotero_items.append(item_row) # items with at least a title

            if url_conflicts := {u: c for u, c in url_to_citekey.items() if len(c) > 1}:
                rfw.error_message("Found {len(url_conflicts)} URLs with multiple citekeys:")
                for url, cites in url_conflicts.items():
                    rfw.error_message("  {url}: {', '.join(cites)}")
                raise ValueError("URL collisions in Zotero database")

        return pd.DataFrame(zotero_items)
    
    def find_zotero_item_via_url(self, url: str) -> Optional[Dict]:
        """Find Zotero item using normalized URL from content"""
        norm_url = rfw.normalize_url(url)
        if norm_url not in self._note_url_zotero_cache:
            matches = self.zotero_items[self.zotero_items['url'] == norm_url]
            self._note_url_zotero_cache[norm_url] = matches.iloc[0].to_dict() if not matches.empty else None
            
        return self._note_url_zotero_cache[norm_url]

    def find_zotero_item_via_title(self, target_title: str) -> Optional[Dict[str, Optional[Dict]]]:
        """Find best title match from content using similarity scoring"""
        if not target_title or len(target_title) < 1:
            return None
        
        if target_title not in self._note_title_zotero_cache:
            best_match = None
            best_score = 0
            for item in self.zotero_items.to_dict('records'):
                score = rfw.match_titles(target_title, item['title'], main_title_only=False)
                if score > best_score and score > rfw.MIN_SCORE_TITLE_MATCH:
                    best_match = item
                    best_score = score
            self._note_title_zotero_cache[target_title] = best_match
        return self._note_title_zotero_cache[target_title]

    def create_obsidian_or_zotero_link(self, item: Dict) -> str:
        """Create Obsidian wikilink if literature note exists, otherwise Zotero URL link"""
       
        if item.get('hasLitNote'):
            return f'[[{item["citekey"]}|{item["citekey"]}]]'

        return rfw.zotero_item_link(item["zotkey"], f'{item["citekey"]}\u2794{item["zotkey"]}')
    
    def make_relinks(self, cite_num: str, doc_url: str, all_resp_cite_nums: set, source_title: Optional[str] = None) -> Tuple[str, str]:
        """Returns what a relinked citation would look like if present in the body,
        given a source citation number and url (found in sources, possibly in body).  
        Also, returns a relinked source list line. Note that the source_title is present in
        Save my Chatbot output, but not in stock perplexity"""
        
        if not (zotero_item := self.find_zotero_item_via_url(doc_url)):
            zotero_item = self.find_zotero_item_via_title(source_title)

        numbered_link = f"[{cite_num}]({doc_url})"
        if zotero_item:
            resp_link = self.create_obsidian_or_zotero_link(zotero_item)
        else:
            resp_link = f"=={numbered_link}==" # "in body, not in zotero"

        # TODO: here, depending upon a flag substitute a URL if there is no title ??
        
        source_link = f'({numbered_link})'
        if not (zotero_item or source_title):
            source_link += f" {doc_url}"\
        elif not zotero_item and source_title:
            source_link += f" {source_title}"
        elif zotero_item and not source_title:
            source_link += f" **{resp_link}**"
        else:
            source_link += f" {source_title} **{resp_link}**"

        if cite_num in all_resp_cite_nums and not zotero_item:
            source_link = f'=={source_link} ==' # "in ressponse, not in zotero"
        
        return resp_link, source_link
    
    def dedup_citenums_to_urls(self, num_url_pairs: list[Tuple[str, str]], verbose: bool = False) -> pd.DataFrame:
        """Return a dataframe mapping from citenums to url.
        Citenums are remapped when >1 citenums map to the same URL."""
        
        url_to_citenums = defaultdict(list)
        for num, url in num_url_pairs:
            url_to_citenums[url].append(num)
        
        # Create new citation numbers if there are duplicates
        dedup_cite_num = 1
        lut = []
        display_citenums_map = False
        for url, nums in url_to_citenums.items():
            if (num_dups := len(nums)) > 1 and verbose:
                display_citenums_map = True
                rfw.error_message('URL has {num_dups} dups: {nums=}, {url=}')
                
            for num in nums:
                lut.append({'orig_num': num, 'dedup_num': str(dedup_cite_num), 'url': url})
            
            dedup_cite_num += 1

        if len(lut) == 0:
            return pd.DataFrame(columns=['orig_num','dedup_num', 'url'])

        citenums_to_url = pd.DataFrame(lut).drop_duplicates().set_index(['orig_num'])
        if display_citenums_map:
            ic(citenums_to_url)
    
        return citenums_to_url
        
    def replace_response_citenums(self, response: str, oldnum_to_new: Dict[str, str]) -> str:
        """Replace citation numbers in the body with new ones.  
        Works for both plain cites, as in perplexity outputs, and web links, as in SMC outputs.
        Assumes that source numbers and urls matched those in source list, and that if there were
        number/url duplicates, the duplication was the same in both the source list and the body. 
        On stock perplexity outputs, this appeared to be the case."""
        
        return re.sub(citenum_plain_re, lambda m: f'[{oldnum_to_new[m.group(1)]}]', response) # assumed 1st group scitenum

    def relink_response_and_sources(self, prsplit: PromptResponseSplitDeDup, citenum_col: str = 'dedup_num') -> Tuple[str, list[str]]:
        """For both body and source, replaces links with Zotero or Obsidian links.""" 

        citenum_to_url = rfw.unique_rows(prsplit.citenum_to_url_df,[citenum_col, 'url'])
        citenum_to_url = dict(zip(citenum_to_url[citenum_col], citenum_to_url.url))
        
        all_response_nums = set(re.findall(citenum_plain_re, prsplit.response_dedup))
        
        # TODO: depending upon a flag, install missing titles w/ URLs instead of meaningless messages.
        # TODO: do it here b/c it can be after self.make_relinks() does its title search (don't do title searches on fake URL titles)
        # so maybe the flat goes to self.make_relinks()
        source_num_to_link, relinked_source_lines = {}, []
        for num, url in citenum_to_url.items():
            title = prsplit.url_to_source_title[url] if prsplit.url_to_source_title else None
            response_link, relinked_source = self.make_relinks(num, url, all_response_nums, title)
            source_num_to_link[num] = response_link
            relinked_source_lines.append(relinked_source)
        
        response_relinked = re.sub(citenum_plain_re,  # only matching and replace the num
                    lambda m: f' {source_num_to_link.get(m.group(1))}', prsplit.response_dedup)

        return response_relinked, relinked_source_lines
    
    def split_single_prs_dedup(self, markdown_text: str, prs_split_func: Callable[[str], PromptResponseSplit]) -> PromptResponseSplitDeDup:
        """Splits a single perplexity output markdown text into prompt, response and source sections.
        In the response, the prs_split_func is assumed to have replaced any [citenum](url) links with 
        plain [citenum] links. Duplicate citenums are removed, and the mapping from original 
        to deduplicated numbers is in citenumes_to_url_source"""
        
        prs_split = prs_split_func(markdown_text) # split apart and parse prompt-response-sources
        citenum_to_url_df = self.dedup_citenums_to_urls(prs_split.citenum_url_pairs)
        
        response_dedup = self.replace_response_citenums(prs_split.response, citenum_to_url_df.dedup_num.to_dict())
        
        # no blank lines between list elements
        response_dedup = rfw.condense_markdown_lists(response_dedup)
        
        # omni3 overuses them, and also sometimes get converted to headers below
        response_dedup = rfw.remove_markdown_dividers(response_dedup)

        # replace underline-style headings.  May need to go lower level than this, depending
        response_dedup = rfw.setext_headers_to_atx(response_dedup, 2) 

        return PromptResponseSplitDeDup(prs_split.preamble, prs_split.prompt, response_dedup,
                                        citenum_to_url_df, url_to_source_title=prs_split.url_to_source_title)
