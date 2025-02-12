# %%
import re
from zoneinfo import ZoneInfoNotFoundError
import pandas as pd
import pathlib as pl
from collections import Counter, defaultdict
from typing import Optional, Dict, Tuple
import datetime as dt
import refwrangle as rfw

TOP_HEADING_LEVEL_IN_AI = 2
ANSWER_HEADING = "## AI answer"
USER_HEADING = '## User'
MAX_WORDS_USER_HEADING = 10

class ZoteroLinkConverter:
    """Converts web links to Zotero/Obsidian links in content sections"""
    
    def __init__(self, verbose: bool = False):
        """Initialize with Zotero data and literature note status"""
        zotero_cache = rfw.ZoteroCache()
        parent_items = zotero_cache.get_data()
        
        # Collect literature note metadata
        lit_note_stems = {f.stem for f in rfw.lit_notes_obsidian_dir.glob('*.md')}
        url_to_citekey = defaultdict(list)
        zotero_items = []

        # Build Zotero item records with note status
        for item in parent_items:
            item_data = item['data']
            if not (title := item_data.get('title')):
                continue # messes up title search, must be malformed anyway?
                
            citekey = rfw.get_citation_key(item_data)
            item_row = {
                'citekey': citekey,
                'zotkey': item['key'],
                'title': title,
                'hasLitNote': citekey in lit_note_stems
            }
            
            if url := item_data.get('url'):
                if norm_url := rfw.normalize_url(url):
                    url_to_citekey[norm_url].append(citekey)
                    item_row['url'] = norm_url
                    
            zotero_items.append(item_row) # items with at least a title

        # Create DataFrame and validate URLs
        self.zotero_items = pd.DataFrame(zotero_items)
        if url_conflicts := {u: c for u, c in url_to_citekey.items() if len(c) > 1}:
            print(f"Found {len(url_conflicts)} URLs with multiple citekeys:")
            for url, cites in url_conflicts.items():
                print(f"  {url}: {', '.join(cites)}")
            raise ValueError("URL collisions in Zotero database")

        # Initialize regex and caches
        self._note_url_zotero_cache: Dict[str, Optional[Dict]] = {}
        self._note_title_zotero_cache: Dict[str, Optional[Dict]] = {}
        self.body_link_re = re.compile(r'\[(.*?)\]\((https?://\S+)\)')
        self.source_link_re = re.compile(r'\[\((\d+)\)\s*(.*?)\]\((https?://\S+)\)')


    def _find_zotero_item_via_url(self, url: str) -> Optional[Dict]:
        """Find Zotero item using normalized URL from content"""
        norm_url = rfw.normalize_url(url)
        if norm_url not in self._note_url_zotero_cache:
            matches = self.zotero_items[self.zotero_items['url'] == norm_url]
            self._note_url_zotero_cache[norm_url] = matches.iloc[0].to_dict() if not matches.empty else None
        return self._note_url_zotero_cache[norm_url]

    def _find_zotero_item_via_title(self, target_title: str) -> Optional[Dict]:
        """Find best title match from content using similarity scoring"""
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

    def _create_obsidian_or_zotero_link(self, item: Dict) -> str:
        """Create Obsidian wikilink if literature note exists, otherwise Zotero URL link"""
        if item.get('hasLitNote'):
            return f'[[{item["citekey"]}|{item["citekey"]}]]'
        
        return rfw.zotero_item_link(
            item["zotkey"], 
            f'{item["citekey"]}\u2794{item["zotkey"]}'
        )

    def convert_content_links(self, body_text: str, sources_text: str) -> Tuple[str, str, Counter]:
        """Replace URLs with Zotero/Obsidian links in both content sections"""
        source_url_map = rfw.build_source_url_to_title_smc(sources_text)
        unsourced_links = Counter()
        unmatched_links = {}

        def _replace_body_link(match: re.Match) -> str:
            url = rfw.normalize_url(match.group(2))
            link_num = match.group(1)
            
            if url not in source_url_map:
                unsourced_links[url] += 1
                
            if item := self._find_zotero_item_via_url(url):
                return self._create_obsidian_or_zotero_link(item)
            if title := source_url_map.get(url):
                if item := self._find_zotero_item_via_title(title):
                    return self._create_obsidian_or_zotero_link(item)
            
            unmatched_links[link_num] = True
            return f'=={match.group(0)}=='

        def _replace_source_link(match: re.Match) -> str:
            link_num, desc, url = match.groups()
            norm_url = rfw.normalize_url(url)
            item = self._find_zotero_item_via_url(norm_url) or self._find_zotero_item_via_title(desc)
            
            if item:
                new_link = self._create_obsidian_or_zotero_link(item)
                return f'[({link_num}) {desc}]({url}) **{new_link}**'
            if link_num in unmatched_links:
                return f'==[({link_num}) {desc}]({url})=='
            return match.group(0)

        processed_body = self.body_link_re.sub(_replace_body_link, body_text)
        processed_sources = self.source_link_re.sub(_replace_source_link, sources_text)
        
        return processed_body, processed_sources, unsourced_links

def relink_perplexity_export_smc(input_file: str, output_file: str):
    """Replace links in "Save my Chatbot" Perplexity output with links to Zotero items or Obsidian lit notes."""
    converter = ZoteroLinkConverter()
    
    with open(input_file, 'r', encoding='utf-8') as infile:
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
        
        processed_body, processed_sources, unsourced_links = converter.convert_content_links(body, sources)
        processed_body = rfw.setext_headers_to_atx(processed_body,
                                                   TOP_HEADING_LEVEL_IN_AI + 1)

        if unsourced_links:
            log_missing_links.append(
                "Body links not in source: " +
                ", ".join([f"{url} (count: {count})" for url, count in unsourced_links.items()])
            )

        processed_sections += [user_header, processed_body, sources_header, processed_sources]

    with open(output_file, 'w', encoding='utf-8') as outfile:
        outfile.write('\n'.join(processed_sections))

    if log_missing_links:
        print("Missing links detected:")
        for log_entry in log_missing_links:
            print(log_entry)

# Example usage
if __name__ == "__main__":
    tmp_dir = rfw.refwrangle_test_dir / 'tmp'

    input_file = rfw.refwrangle_test_dir / "dat" / 'perplexity_multi_prompt_savemychatbot_example.md'
    #input_file = pl.Path(r"C:\Users\scott\share\ref\refwrangle\tmp\watchter\raw\perplexity_2025-02-10_20-04-06_data.md")
    output_file = tmp_dir / 'tmp_savemychatbot_multiprompt_perplexity_example.md'
    
    relink_perplexity_export_smc(input_file, output_file)