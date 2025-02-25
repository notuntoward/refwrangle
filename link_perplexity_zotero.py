# %%
import re
from collections import Counter, defaultdict
from typing import Optional, Dict, Tuple, List, Callable
import datetime as dt
import pathlib as pl
from outcome import Value
import pandas as pd
import refwrangle as rfw
from dataclasses import dataclass, field
from icecream import ic


TOP_HEADING_LEVEL_IN_AI = 2
ANSWER_HEADING = "## AI answer"
USER_HEADING = '## User'
MAX_WORDS_PROMPT_HEADING = 10

# like in smc body
#citenum_url_link_re = re.compile(r'\[(?P<orig>\d+)\]\((?P<url>https?://[^\)]+)\)')
citenum_url_link_re = re.compile(r'\[\^?(?P<num>\d+)\]\((?P<url>https?://[^\)]+)\)') # handles both ^ and plain number syntax
# like in smc source list
source_link_re = re.compile(r'\[\((\d+)\)\s*(.*?)\]\((https?://\S+)\)')
source_citenum_title_re = re.compile(r'^\((?P<citenum>\d+)\)\s*(?P<title>.+)')
#citenum_plain_re = re.compile(r'\[(?P<num>\d+)\]')
citenum_plain_re = re.compile(r'\[\^?(?P<num>\d+)\]') # handles both ^ and plain number syntax

@dataclass
class PromptResponseSplit:
    """The components of a single Perplexity Prompt-Response"""
    preamble: str
    prompt: str
    response: str
    citenum_url_pairs: List[Tuple]
    url_to_source_title: pd.Series
    # url_to_source_title: Dict[str, str]    
    #url_to_source_title: Dict[str, str] = field(default_factory=dict)

@dataclass
class PromptResponseSplitDeDup:
    """The components of a single Perplexity Prompt-Response, after the citenums have been deduplicated"""
    preamble: str
    prompt: str
    response_dedup: str
    citenum_to_url_df: pd.DataFrame
    url_to_source_title: pd.Series
    # url_to_source_title: Dict[str, str]    
    # url_to_source_title: Dict[str, str] = field(default_factory=dict)    

class ZoteroLinkConverter:
    """Converts web links to Zotero/Obsidian links in content sections"""
    
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
                    print(f'{item['key']}: skipping parent with no title')
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
                print(f"Found {len(url_conflicts)} URLs with multiple citekeys:")
                for url, cites in url_conflicts.items():
                    print(f"  {url}: {', '.join(cites)}")
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

        source_link = f'({numbered_link})'
        if not (zotero_item or source_title):
            source_link += f" {doc_url}"
        elif not zotero_item and source_title:
            source_link += f" {source_title}"
        elif zotero_item and not source_title:
            source_link += f" **{resp_link}**"
        else:
            source_link += f" {source_title} **{resp_link}**"

        if cite_num in all_resp_cite_nums and not zotero_item:
            source_link = f'=={source_link} ==' # "in ressponse, not in zotero"
        
        # ic(body_link, source_link)
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
            #print(f'{url=}, {nums}')
            if (num_dups := len(nums)) > 1 and verbose:
                display_citenums_map = True
                print(f'URL has {num_dups} dups: {nums=}, {url=}')
                
            for num in nums:
                #print(f'{num}')
                lut.append({'orig_num': num, 'dedup_num': str(dedup_cite_num), 'url': url})
            
            dedup_cite_num += 1
        
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
        In the response, the prs_split_func is assumed to have replaced any [citenum](url) links with plain [citenum] link.
        Duplicate citenums are removed, and the mapping from original 
        to deduplicated numbers is in citenumes_to_url_source"""
        
        prs_split = prs_split_func(markdown_text)
        citenum_to_url_df = self.dedup_citenums_to_urls(prs_split.citenum_url_pairs)
        
        response_dedup = self.replace_response_citenums(prs_split.response, citenum_to_url_df.dedup_num.to_dict())
        
        # no blank lines btween list elements
        response_dedup = rfw.shrink_lists(response_dedup)
        
        # omni3 overuses them, and also sometimes get converted to headers below
        response_dedup = rfw.remove_markdown_dividers(response_dedup)

        # replace underline-style headings.  May need to go lower level than this, depending
        response_dedup = rfw.setext_headers_to_atx(response_dedup, 2) 

        return PromptResponseSplitDeDup(prs_split.preamble, prs_split.prompt, response_dedup,
                                        citenum_to_url_df, url_to_source_title=prs_split.url_to_source_title)

# a relinker use here and by any importer of this file.  Only make one of these and share it.
relinker = ZoteroLinkConverter()

PROMPT_HEADER_SMC = '## User'
RESPONSE_HEADER_SMC = '## AI answer'
SOURCES_HEADER_SMC = r'\*\*Sources:\*\*'

def split_single_prs_text_smc(single_prs_markdown: str) -> PromptResponseSplit:
    """Splits a single prompt-response-source chunk from a Save my Chatbot perplexity export
    into prompt, response and source sections, returning the source information in citenum_url_pairs 
    and url_to_source_title.  The response parts of SMC exports also have [citenum][url] markdown links; 
    the citenum_url pairs extracted from them are often inconsistent with those
    in the sources list.  This function merges source list and response citenum_url pairs
    and attempts to unify them.  In the response, [citenum][url] markdown links are
    replaced with plain [citenum] links, simplifying downstream merging of multiple 
    prompt-response-sources."""
    
    pattern = rf"(?m)^({PROMPT_HEADER_SMC}|{RESPONSE_HEADER_SMC}|{SOURCES_HEADER_SMC})"    
    parts = re.split(pattern, single_prs_markdown)

    if (num_parts := len(parts)) < 1:
        raise ValueError("Empty document or failed to find any headers in expected places")
    
    if num_parts < 3 or not re.match(rf'^{PROMPT_HEADER_SMC}.*',parts[1]):
        raise ValueError(f"Failed to find prompt header ({PROMPT_HEADER_SMC}) in expected place")

    if num_parts < 4 or not re.match(rf'^{RESPONSE_HEADER_SMC}.*',parts[3]):
        raise ValueError(f"Failed to find response header ({RESPONSE_HEADER_SMC}) in expected place")

    if num_parts < 5:
        raise ValueError("Incomplete prompt/response pair")
        
    preamble, prompt, response = parts[0], parts[2], parts[4]
    
    if num_parts > 6 and re.match(rf'^{SOURCES_HEADER_SMC}.*',parts[5]):
        sources = parts[6]
    else:
        print(f"Sources header({SOURCES_HEADER_SMC}) not in expected place or no source list: Assume no sources.")
        sources = ''

    citenum_url_pairs_response = rfw.get_link_tu_pairs(response, citenum_url_link_re)
    # separate link needed?
    #num_url_link_re = re.compile(r'\[(.*?)\]\((https?://\S+)\)')
    #citenum_url_pairs_response = rfw.get_link_tu_pairs(response, num_url_link_re)

    # Include plain response citenums (SMC is supposed to be [num](url) but it's inconsistent)
    ok_response_citenums = set([cupair[0] for cupair in citenum_url_pairs_response])
    for citenum_plain in set([m for m in re.findall(citenum_plain_re, response)]):
        if citenum_plain not in ok_response_citenums:
            warning_url = f"https://BARE_CITE_NUMBER_{citenum_plain}_IN_RESPONSE_WITH_NO_URL"
            print(f'Malformed Plain citenum [{citenum_plain}] appears without URL in response')
            citenum_url_pairs_response.append((citenum_plain, warning_url))
    
    citenum_url_pairs, url_to_source_title = [], {}
    if len(sources)>0:
        #print(f'getting citenum_url_pairs from sources.')
        for link_text, url in rfw.get_link_tu_pairs(sources, r'- \[(.*?)\]\((https?://\S+)\)'):
            if match := re.match(source_citenum_title_re, link_text):
                citenum, title = match['citenum'], match['title']
                citenum_url_pairs.append((citenum, url))
                url_to_source_title[url] = title.strip()
            else:
                raise ValueError(f'Failed to parse source link text: {link_text=}')
        
        # Append response num/url pairs not in sources list (sometimes happens in SMC)
        for num_url_pair in citenum_url_pairs_response:
            if num_url_pair not in citenum_url_pairs:
                print(f'{num_url_pair[0]=}, {num_url_pair[1]=} in response but not source list')
                citenum_url_pairs.append(num_url_pair)
                url_to_source_title[num_url_pair[1]] = 'Cite in response but no entry in sources list'
    else:
        #print(f'getting citenum_url_pairs from response')
        for (num, url) in citenum_url_pairs_response:
            url_to_source_title[num] = 'Response with following no sources list'
        citenum_url_pairs = citenum_url_pairs_response
        
    # substitue plain citenum links into the response, for easier downstream merging
    response = re.sub(citenum_url_link_re, lambda m: f'[{m.group("num")}]', response)
    
    url_to_source_title = pd.Series(url_to_source_title, dtype='str')
    return PromptResponseSplit(preamble, prompt, response, citenum_url_pairs, url_to_source_title)

def read_markdown_file(file_path: pl.Path) -> str:
    """Reads a markdown file and returns its content as a string.
    Always read with utf-8, and converts to python standard \n newlines, 
    as some AI files have windows-styple \r\n e.g. ChatGPT-4o exported from Perplexity."""
    
    try:
        if isinstance(file_path, str):
            file_path = pl.Path(file_path)
    except Exception as e:
        raise ValueError(f"Invalid file path: {file_path}") from e
        
    if file_path.suffix != '.md':
        raise ValueError(f"File does not have a .md extension: {file_path}")

    try:
        with file_path.open('r', encoding='utf-8', newline=None) as file:
            markdown_content = file.read()
    except Exception as e:
        raise Exception(e)
    
    return markdown_content

def make_obsidian_front_matter():
    """Makes obsidian note front mater"""
    return f'---\ncategory: aichat\ncreated date: {dt.datetime.now()}\n---\n'

def is_smc_content(markdown_content: str) -> bool:
    """Returns True if the given markdown content came from the SaveMyChatbot browser plugin."""
    try:
        lines = markdown_content.splitlines()
        
        if len(lines) < 2:
            return False
        
        heading = lines[0].strip()
        metadata = lines[1].strip()
        
        if not heading.startswith("# "):
            return False
        
        exported_pattern = r"Exported on (\d{2}/\d{2}/\d{4}) at (\d{2}:\d{2}:\d{2})"
        match = re.search(exported_pattern, metadata)
        if not match:
            return False
        
        try:
            dt.datetime.strptime(f"{match.group(1)} {match.group(2)}", "%d/%m/%Y %H:%M:%S")
        except ValueError:
            return False
        
        if not ("Perplexity.ai" in metadata and "SaveMyChatbot" in metadata):
            return False
        
        return True

    except Exception as e:
        raise Exception(f"Error processing markdown content: {e}")

def count_prompts_smc_content(file_contents: str) -> int:
    """ Counts user/response prompts in the contents of an smc perplexity output file.
    A prompt is defined as a pair of ## User and ## AI Answer headers."""
    
    lines = file_contents.splitlines()

    prompt_count, user_found = 0, False
    for line in lines:
        line = line.strip()
        if line == "## User":
            if user_found:
                raise ValueError("Unmatched ## User header found without a corresponding ## AI Answer.")
            user_found = True  # Mark that a user header is found
        elif line == "## AI Answer":
            if not user_found:
                raise ValueError("Unmatched ## AI Answer header found without a preceding ## User.")
            # if here, prompt pair is complete.  Restart pair search
            prompt_count += 1  
            user_found = False 

    if user_found:
        raise ValueError("Unmatched ## User header found without a corresponding ## AI Answer.")

    if prompt_count == 0:
        raise ValueError("No valid prompt pairs (## User, ## AI Answer) found in the file.")

    return prompt_count


    
# Example usage
if __name__ == "__main__":
    #input_file = pl.Path(r"C:\Users\scott\OneDrive\share\ref\refwrangle\test\dat\merge_chats_smc\GPT-4o-BGtrail.md")
    #input_file = rfw.refwrangle_test_dir / "dat" / 'perplexity_multi_prompt_savemychatbot_example.md'
    input_file = rfw.refwrangle_test_dir / "dat" / 'perplexity_single_prompt_savemychatbot_example.md'
    output_dir = pl.Path(r"C:\Users\scott\OneDrive\share\ref\obsidian\Obsidian Share Vault\Scratch Space")
    output_file = output_dir / 'tmp_savemychatbot_output.md'
    
    print(f'{input_file=}\n-->\n{output_file=}')
    relink_single_file_smc(input_file, output_file)
    print('Done.')
# %%
