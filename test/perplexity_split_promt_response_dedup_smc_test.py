# %% [markdown]
# ### test function to split up SMC preplexity responses into chunks

# %%
from icecream import ic
import pathlib as pl

refwrangle_dir = pl.Path('~/ref/refwrangle').expanduser() # can't reliably get dir of an .ipynb 
import sys
sys.path.append(str(refwrangle_dir))
import refwrangle as rfw
import link_perplexity_zotero as lpz

# %load_ext autoreload
# %autoreload 2

# tmpdir = rfw.refwrangle_test_dir / 'tmp'
# tmpdir.mkdir(parents=True, exist_ok=True)

# datdir = rfw.refwrangle_test_dir / 'dat' / 'merge_chats_perplex'
# datdir.mkdir(parents=True, exist_ok=True)

# %%
input_file=pl.Path(r'C:/Users/scott/OneDrive/share/ref/refwrangle/test/dat/smc_single_pompt_test_dat.md')
#input_file = rfw.refwrangle_test_dir / "dat" / 'perplexity_multi_prompt_savemychatbot_example.md'
#input_file = pl.Path(r"C:\Users\scott\share\ref\refwrangle\tmp\watchter\raw\perplexity_2025-02-10_20-04-06_data.md")
# output_dir = pl.Path(r"C:\Users\scott\OneDrive\share\ref\obsidian\Obsidian Share Vault\Scratch Space")
# output_file = output_dir / 'tmp_savemychatbot_multiprompt_perplexity_example.md'
input_file

# %%
input_string = lpz.read_markdown_file(input_file)

#lpz.split_prompt_response_text_smc(text)

#lpz.split_prompt_response_dedup_smc(section)

PROMPT_HEADER_SMC = '## User'
RESPONSE_HEADER_SMC = '## AI Answer'
SOURCES_HEADER_SMC = r'\*\*Sources\*\*'
  
# Define a pattern with capturing groups for headers
pattern = rf"(?m)^({PROMPT_HEADER_SMC}|{RESPONSE_HEADER_SMC}|{SOURCES_HEADER_SMC})"

# Use re.split to split and include the matched headers in the result
parts = re.split(pattern, input_string)

# Filter out empty strings from parts (if any)
parts = [part.strip() for part in parts if part.strip()]

# Process parts to extract prompt, response, and sources
prompt = ""
response = ""
sources = ""

# Iterate through parts to assign content based on headers
for i in range(len(parts)):
    if parts[i] == PROMPT_HEADER_SMC and i + 1 < len(parts):
        prompt = parts[i + 1]
    elif parts[i] == RESPONSE_HEADER_SMC and i + 1 < len(parts):
        response = parts[i + 1]
    elif parts[i] == SOURCES_HEADER_SMC and i + 1 < len(parts):
        sources = parts[i + 1]

citenum_url_pairs, url_to_source_title = [], {}
if sources:
    # citenum/url/title from sources list
    for link_text, url in rfw.get_link_tu_pairs(sources, r'- \[(.*?)\]\((https?://\S+)\)'):
        if match := re.match(source_citenum_title_re, link_text):
            citenum, title = match['citenum'], match['title']
            citenum_url_pairs.append((citenum, url))
            url_to_source_title[url] = title.strip()
        else:
            raise ValueError(f'Failed to parse source link text: {link_text=}')
else:
    # citenum/url from body
    citenum_url_pairs = rfw.get_link_tu_pairs(response, r'\[(.*?)\]\((https?://\S+)\)')

return PromptResponseSplit(preamble, prompt, response, citenum_url_pairs, url_to_source_title)

# %%



