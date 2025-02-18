# %%
import re
from collections import Counter, defaultdict
from typing import Optional, Dict, Tuple
import datetime as dt
import pathlib as pl
import pandas as pd
import refwrangle as rfw
from icecream import ic


TOP_HEADING_LEVEL_IN_AI = 2
ANSWER_HEADING = "## AI answer"
USER_HEADING = '## User'
MAX_WORDS_USER_HEADING = 10

# like in smc body
#citenum_url_link_re = re.compile(r'\[(?P<orig>\d+)\]\((?P<url>https?://[^\)]+)\)')
citenum_url_link_re = re.compile(r'\[\^?(?P<orig>\d+)\]\((?P<url>https?://[^\)]+)\)') # handles both ^ and plain number syntax
# like in smc source list
source_link_re = re.compile(r'\[\((\d+)\)\s*(.*?)\]\((https?://\S+)\)')
source_citenum_title_re = re.compile(r'^\((?P<citenum>\d+)\)\s*(?P<title>.+)')
#citenum_plain_re = re.compile(r'\[(?P<num>\d+)\]')
citenum_plain_re = re.compile(r'\[\^?(?P<num>\d+)\]') # handles both ^ and plain number syntax



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
    
    def make_relinks(self, cite_num: str, doc_url: str, all_body_cite_nums: set, source_title: Optional[str] = None) -> Tuple[str, str]:
        """Returns what a relinked citation would look like if present in the body,
        given a source citation number and url (found in sources, possibly in body).  
        Also, returns a relinked source line. The source_title is present in
        Save my Chatbot output, but not in stock perplexity"""
        
        if not (zotero_item := self.find_zotero_item_via_url(doc_url)):
            zotero_item = self.find_zotero_item_via_title(source_title)

        numbered_link = f"[{cite_num}]({doc_url})"
        if zotero_item:
            body_link = self.create_obsidian_or_zotero_link(zotero_item)
        else:
            body_link = f"=={numbered_link}==" # "in body, not in zotero"

        source_link = f'({numbered_link})'
        if not (zotero_item or source_title):
            source_link += f" {doc_url}"
        elif not zotero_item and source_title:
            source_link += f" {source_title}"
        elif zotero_item and not source_title:
            source_link += f" **{body_link}**"
        else:
            source_link += f" {source_title} **{body_link}**"

        if cite_num in all_body_cite_nums and not zotero_item:
            source_link = f'=={source_link} ==' # "in body, not in zotero"
        
        # ic(body_link, source_link)
        return body_link, source_link
    
    def citenums_to_urls_dedup(self, num_url_pairs: list[Tuple[str, str]], verbose: bool = False) -> pd.DataFrame:
        """Return a dataframe mapping from citenums to url.
        Citenums are remapped when >1 citenums map to the same URL."""
        
        url_to_citenums = defaultdict(list)
        for num, url in num_url_pairs:
            url_to_citenums[url].append(num)
        
        # Create new citation numbers if there are duplicates
        new_cite_num = 1
        lut = []
        display_citenums_map = False
        for url, nums in url_to_citenums.items():
            if (nDups := len(nums)) > 1 and verbose:
                display_citenums_map = True
                print(f'URL has {nDups} dups: {nums=}, {url=}')
                
            for num in nums:
                lut.append({'orig_num': num, 'new_num': str(new_cite_num), 'url': url})
            
            new_cite_num += 1
        
        citenums_to_url = pd.DataFrame(lut).set_index(['orig_num'])
        if display_citenums_map:
            ic(citenums_to_url)
        
        return citenums_to_url
    
    def replace_body_citenums(self, body: str, oldnum_to_new: Dict[str, str]) -> str:
        """Replace citation numbers in the body with new ones.  
        Works for both plain cites, as in perplexity outputs, and web links, as in SMC outputs.
        This is assuming that the urls in the original SMC body cites were intially correct, 
        even if the citenums were duplicates.  On stock perplexity outptus, this appeared to be the case."""
        
        return re.sub(citenum_plain_re, lambda m: f'[{oldnum_to_new[m.group("num")]}]', body)
    
    def relink_body_and_make_source_links(self, body_dedup: str, citenums_to_url: pd.DataFrame, source_url_to_title: Optional[Dict[str, str]] = None) -> Tuple[str, list[str]]:
        """For both body and source, replaces links with Zotero or Obsidian links. Assumes that duplicate citenums
        have already been removed from the body text (body_dedup)"""

        new_num_to_url = citenums_to_url.set_index('new_num').url.to_dict() # dedup citenums to url
        body_citenums = set(re.findall(citenum_plain_re, body_dedup))
        
        source_num_to_link, relinked_source_lines = {}, []
        for num, url in new_num_to_url.items():
            title = source_url_to_title[url] if source_url_to_title else None
            body_link, relinked_source = self.make_relinks(num, url, body_citenums, title)
            source_num_to_link[num] = body_link
            relinked_source_lines.append(relinked_source)
        
        if source_url_to_title:
            # TODO: instead, make relinker.replace_body_citenums() force substitue plain links w/ no URL?
            body_relinked = re.sub(citenum_url_link_re,  # match and replace the entire link
                                lambda m: f' {source_num_to_link.get(m.group("orig"))}', body_dedup)
        else:
            body_relinked = re.sub(citenum_plain_re,  # only matching and replace the num
                                lambda m: f' {source_num_to_link.get(m.group("num"))}', body_dedup)
            
        return body_relinked, relinked_source_lines

def relink_perplexity_export_smc(perplexity_smc_file: pl.Path, relinked_file: pl.Path):
    """Replace links in "Save my Chatbot" Perplexity output with links 
    to Zotero items or Obsidian lit notes."""

    relinker = ZoteroLinkConverter()
    
    def relink_body_source(body_text: str, sources_text: str) -> Tuple[str, str, Optional[Counter[str]], pd.DataFrame]:
        """Replace URLs with Zotero/Obsidian links in both content sections"""
        def parse_source_lines(sources_content: str) -> Tuple[Dict[str, str], list[Tuple[str, str]]]:
            """Map Build a dictionary mapping URLs to titles from the sources section of a "Save my Chatbot" output."""
           
            url_to_title: Dict[str, str] = {}
            citenum_url_pairs: list[Tuple[str, str]] = []
            matches = re.findall(r'- \[(.*?)\]\((https?://\S+)\)', sources_content)
            for link_text, link_url in matches:
                normalized_url = rfw.normalize_url(link_url)
                match = re.match(source_citenum_title_re, link_text)
                if match:
                    citenum, title = match['citenum'], match['title']
                    citenum_url_pairs.append((citenum, normalized_url))
                    url_to_title[normalized_url] = title.strip()
                else:
                    print(f'failed to parse source link text: {link_text=}')

            return url_to_title, citenum_url_pairs

        source_url_to_title, source_citenum_url_pairs = parse_source_lines(sources_text)
        
        citenums_to_url = relinker.citenums_to_urls_dedup(source_citenum_url_pairs)
        body_depup = relinker.replace_body_citenums(body_text, citenums_to_url.new_num.to_dict())
        relinked_body, relinked_sources = relinker.relink_body_and_make_source_links(body_depup, citenums_to_url, source_url_to_title)
        relinked_sources = "\n".join(sorted(relinked_sources, key=lambda line: int(re.search(citenum_plain_re, line).group(1))))
        return relinked_body, relinked_sources, None, citenums_to_url
        
    with open(perplexity_smc_file, 'r', encoding='utf-8') as infile:
        content = infile.read()

    sections = re.split(rf'(?<=\n){USER_HEADING}', content)
    front_matter = f'---\ncategory: aichat\ncreated date: {dt.datetime.now()}\n---\n'
    chat_source = " ".join(sections[0].split("\n")[1:])  # Remove redundant header
    processed_sections = [front_matter + f'{chat_source.lstrip()}\n']
    log_missing_links = []

    for section in sections[1:]:  # Process each user section
        section_parts = re.split(r'(\n---\s*\n\s*\*\*Sources:\*\*\s*\n)', section)
        if len(section_parts) < 3:
            print('Incomplete Body/Sources pair: assuming no Sources')
            section_parts += ['', '']

        body, sources_header, sources = section_parts
        user_header = rfw.summarize_prompt(body, MAX_WORDS_USER_HEADING,
                                           ANSWER_HEADING, TOP_HEADING_LEVEL_IN_AI)
        
        processed_body, processed_sources, unsourced_links, citenums_to_url = relink_body_source(body, sources)
        processed_body = rfw.setext_headers_to_atx(processed_body,
                                                   TOP_HEADING_LEVEL_IN_AI + 1)

        if unsourced_links:
            log_missing_links.append(
                "Body links not in source: " +
                ", ".join([f"{url} (count: {count})" for url, count in unsourced_links.items()])
            )

        processed_sections += [user_header, processed_body, sources_header, processed_sources]

    with open(relinked_file, 'w', encoding='utf-8') as outfile:
        outfile.write('\n'.join(processed_sections))

    if log_missing_links:
        print("Missing links detected:")
        for log_entry in log_missing_links:
            print(log_entry)

def read_markdown_file(file_path: str) -> bool:
    """Reads a markdown file."""
    try:
        file_path = pl.Path(file_path)
        
        if file_path.suffix != '.md':
            raise ValueError(f"File does not have a .md extension: {file_path}")
        
        with file_path.open('r', encoding='utf-8') as file:
            markdown_content = file.read()
    except Exception as e:
        raise Exception(f"Error processing file: {e}")
    
    return markdown_content

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
    input_file = rfw.refwrangle_test_dir / "dat" / 'merge_chats_smc' / 'chatgpt4o_MissLinkBG.md'
    #input_file = rfw.refwrangle_test_dir / "dat" / 'perplexity_multi_prompt_savemychatbot_example.md'
    #input_file = pl.Path(r"C:\Users\scott\share\ref\refwrangle\tmp\watchter\raw\perplexity_2025-02-10_20-04-06_data.md")
    output_file = rfw.refwrangle_test_dir / 'tmp' / 'tmp_savemychatbot_multiprompt_perplexity_example.md'
    
    print(f'{input_file=}\n-->\n{output_file=}')
    relink_perplexity_export_smc(input_file, output_file)
    print('Done.')
# %%
