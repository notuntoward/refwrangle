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
        ic(numbered_link)
        if zotero_item := relinker.find_zotero_item_via_url(doc_url):
            body_link = relinker.create_obsidian_or_zotero_link(zotero_item)
            relinked_sources.append(f'({numbered_link}) **{body_link}**')
        else:
            body_link = f"=={numbered_link}==" # mark it as "not in zotero"
            source_line = f'({numbered_link}) {doc_url}'
            source_line = f'=={source_line} ==' if cite_num in body_cite_nums else source_line
            relinked_sources.append(source_line)

        ic(body_link)            
        return body_link

    relinker = lpz.ZoteroLinkConverter()
    relinked_sources = []
    
    body_cite_nums = set(re.findall(r'\[(\d+)\]', body))
    #source_num_to_link = {num: make_relinks_from_source(num, url) for url, num in url_to_source_num.items()}
    
    source_num_to_link = {m.group('num'): make_relinks_from_source(m.group('num'), m.group('url'))
                          for m in source_matches }
    
    ic(source_num_to_link)
    
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
from collections import defaultdict
import pandas as pd

# get the sources from all docs to be merged
all_bodies, all_url_to_source_nums = [], []
for doc in [perplexity_dialog_file]:
    body, url_to_source_num = split_body_source(doc)
    all_bodies.append(body)
    all_url_to_source_nums.append(url_to_source_num)

# find all the doc citations for each unique URL
allurls = defaultdict(list)
print(allurls)
for docIx, url_to_source_num in enumerate(all_url_to_source_nums):
    for url, num in url_to_source_num.items():
        allurls[url].append(dict(orig_num=num, docIx=docIx))

# create new citenums for a combined document with a combined sources section
new_cite_num = 1
lut = []
for url, infos in allurls.items():
    for info in infos:
        lut.append({'url': url, 'new_cite_num': str(new_cite_num)} | info)
    new_cite_num += 1

lut = pd.DataFrame(lut).set_index(['docIx', 'orig_num'])
all_new_cite_nums = lut.new_cite_num.unique()


# make single body with cite numbers replaced by combined cite numbers
concat_bodies = ""
for docIx, body in enumerate(all_bodies):
    old_to_new_num = lut.loc[0].new_cite_num
    body_newnums = re.sub(r'\[(\d+)\]', 
                          lambda m: old_to_new_num[m.group(1)], body)
    concat_bodies += f"\n**{docIx=}**\n" + body_newnums


# %%
url_to_source_num = lut.set_index('url')['new_cite_num'].to_dict()

relink_chunks(concat_bodies, url_to_source_num, output_file)


# %%
print(body)

#body_relinked = re.sub(r'\[(\d+)\]', 
#                           lambda m: f' {source_num_to_link.get(m.group(1))}', body)


# %%
#output_file

re.findall(r'\[(\d+)\]', lambda m: f' {source_num_to_link.get(m.group(1))}', body)

# %%


# %%
display(lut)
#lut.loc[0, '3'].new_cite_num
all_new_cite_nums

# %%
import re

# Input string and regex pattern
text = "apple banana apple orange banana"
pattern = r'\b(\w+)\b'  # Matches words

# Step 1: Extract all matches
matches = re.findall(pattern, text)

# Step 2: Compute unique substitutes
unique_substitutes = {match: f"word_{i}" for i, match in enumerate(set(matches), start=1)}

# Step 3: Define replacement function
def replacement_function(match):
    return unique_substitutes[match.group(0)]

# Step 4: Perform substitutions
result = re.sub(pattern, replacement_function, text)

print("Original:", text)
print("Modified:", result)


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


