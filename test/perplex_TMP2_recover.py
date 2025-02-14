# %% [markdown]
# ### Zoteroize and Obsidianize a Perplexity Dialogue
# 
# In a Perplexity dialogue copied to the clipboard by the perplexity copy button and then saved to a file, replace 
# the citation numbers with matching Obsidian literature note or Zotero item links

# %%
import re
import pathlib as pl
import sys
from icecream import ic

refwrangle_dir = pl.Path('~/ref/refwrangle').expanduser() # can't reliably get dir of an .ipynb 
sys.path.append(str(refwrangle_dir))
import refwrangle as rfw
import link_perplexity_zotero as lpz

%load_ext autoreload
%autoreload 2

# %%
def split_body_source(perplexity_file: pl.Path):
    """Replace links in standard Perplexity (saved clipboard) output with links 
    to Zotero items or Obsidian lit notes."""    
    
    content = perplexity_file.read_text(encoding='utf-8')
    section_parts = content.split("\nCitations:\n", 1)
    if len(section_parts) < 2:
        print("Missing citations")
        body, citations = section_parts, ""
    else:
        body, citations = section_parts
    
    source_matches = re.finditer(r'^\[(?P<num>\d+)\]\s+(?P<url>https?://\S+)', citations, flags=re.M)

    url_to_source_num = {m.group('url'): m.group('num') for m in source_matches}
    
    return body, url_to_source_num

def relink_chunks(body, url_to_source_num, relinked_file: pl.Path) -> None:

    def make_relinks_from_source(cite_num: str, doc_url: str) -> str:
        """Returns what a relinked citation would look like if present in the body,
        given a source part citation number and url.  Also appends to the global list, 
        relinked_sources, a relinked source part link.  Expects the global set, body_cite_nums."""
        
        numbered_link = f"[{cite_num}]({doc_url})"
        if zotero_item := relinker.find_zotero_item_via_url(doc_url):
            body_link = relinker.create_obsidian_or_zotero_link(zotero_item)
            relinked_sources.append(f'({numbered_link}) **{body_link}**')
        else:
            body_link = f"=={numbered_link}==" # mark it as "not in zotero"
            source_line = f'({numbered_link}) {doc_url}'
            source_line = f'=={source_line} ==' if cite_num in body_cite_nums else source_line
            relinked_sources.append(source_line)
            
        return body_link

    relinker = lpz.ZoteroLinkConverter()
    relinked_sources = []
    
    body_cite_nums = set(re.findall(r'\[(\d+)\]', body))
    source_num_to_link = {url: make_relinks_from_source(num, url) for url, num in url_to_source_num.items()}

    # source_num_to_link = {m.group('num'): make_relinks_from_source(m.group('num'), m.group('url'))
    #                       for m in source_matches }
    
    body_relinked = re.sub(r'\[(\d+)\]', 
                           lambda m: f' {source_num_to_link.get(m.group(1))}', body)
    sources_relinked = "\n".join(relinked_sources)
    
    relinked_text = f"{body_relinked}\nCitations:\n{sources_relinked}"
    relinked_file.write_text(f"{body_relinked}\nCitations:\n{sources_relinked}", 
                             encoding='utf-8')

def relink_perplexity_export(perplexity_file: pl.Path, relinked_file: pl.Path) -> None:
    body, url_to_source_num = split_body_source(perplexity_file)
    relink_chunks(body, url_to_source_num, relinked_file)    

# %%
perplexity_dialog_file = rfw.refwrangle_test_dir / "dat" / 'perplexity_example.md'
output_file = rfw.refwrangle_test_dir / 'tmp' / "tmp_new_cites_perplexity_example.md"
print(f'{perplexity_dialog_file=}\n-->\n{output_file=}')

relink_perplexity_export(perplexity_dialog_file, output_file)
print('Done.')

# %%
# def relink_perplexity_export(perplexity_file: pl.Path, relinked_file: pl.Path) -> None:
#     """Replace links in standard Perplexity (saved clipboard) output with links 
#     to Zotero items or Obsidian lit notes."""    
    
#     relinker = lpz.ZoteroLinkConverter()

#     def make_relinks_from_source(cite_num: str, doc_url: str) -> str:
#         """Returns what a relinked citation would look like if present in the body,
#         given a source part citation number and url.  Also appends to the global list, 
#         relinked_sources, a relinked source part link.  Expects the global set, body_cite_nums."""
        
#         numbered_link = f"[{cite_num}]({doc_url})"
#         if zotero_item := relinker.find_zotero_item_via_url(doc_url):
#             body_link = relinker.create_obsidian_or_zotero_link(zotero_item)
#             relinked_sources.append(f'({numbered_link}) **{body_link}**')
#         else:
#             body_link = f"=={numbered_link}==" # mark it as "not in zotero"
#             source_line = f'({numbered_link}) {doc_url}'
#             source_line = f'=={source_line} ==' if cite_num in body_cite_nums else source_line
#             relinked_sources.append(source_line)
            
#         return body_link
    
#     content = perplexity_file.read_text(encoding='utf-8')
#     section_parts = content.split("\nCitations:\n", 1)
#     if len(section_parts) < 2:
#         print("Missing citations")
#         body, citations = section_parts, ""
#     else:
#         body, citations = section_parts
    
#     source_matches = re.finditer(r'^\[(?P<num>\d+)\]\s+(?P<url>https?://\S+)', citations, flags=re.M)

#     relinked_sources = []
#     body_cite_nums = set(re.findall(r'\[(\d+)\]', body))
#     url_to_source_num = {m.group('url'): m.group('num') for m in source_matches}
#     #ic(len(url_to_source_num))
#     source_num_to_link = {url: make_relinks_from_source(num, url) for url, num in url_to_source_num.items()}
#     #ic(len(source_num_to_link), len(url_to_source_num))
#     # source_num_to_link = {m.group('num'): make_relinks_from_source(m.group('num'), m.group('url'))
#     #                       for m in source_matches }
    
#     body_relinked = re.sub(r'\[(\d+)\]', 
#                            lambda m: f' {source_num_to_link.get(m.group(1))}', body)
#     sources_relinked = "\n".join(relinked_sources)
    
#     relinked_text = f"{body_relinked}\nCitations:\n{sources_relinked}"
#     relinked_file.write_text(f"{body_relinked}\nCitations:\n{sources_relinked}", 
#                              encoding='utf-8')
    
#     return relinked_text, source_num_to_link


