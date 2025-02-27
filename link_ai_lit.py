# %% [markdown]
#
#  ### Zoteroize and Obsidianize a Perplexity Dialogue
# 
#  In a Perplexity dialogue copied to the clipboard by the perplexity copy button and then saved to a file, replace
#  the citation numbers with matching Obsidian literature note or Zotero item links

import datetime as dt
import pathlib as pl
# %%
import re
import sys
from typing import List, Tuple

import numpy as np
import pandas as pd
from icecream import ic

refwrangle_dir = pl.Path('~/ref/refwrangle').expanduser() # can't reliably get dir of an .ipynb 
sys.path.append(str(refwrangle_dir))
import link_perplexity_zotero as lpz
import refwrangle as rfw

# %load_ext autoreload
# %autoreload 2

# %%
relinker = lpz.ZoteroLinkConverter()

# Save my chatbot output section separator headings
PROMPT_HEADER_SMC = '## User'
RESPONSE_HEADER_SMC = '## AI answer'
SOURCES_HEADER_SMC = r'\*\*Sources:\*\*'

# Matches both ^ and plain number syntax
CITENUM_URL_LINK_RE = r'\[\^?(?P<num>\d+)\]\((?P<url>https?://[^\)]+)\)'
SOURCE_CITENUM_TITLE_RE = re.compile(r'^\((?P<citenum>\d+)\)\s*(?P<title>.+)')

def split_single_prs_text_smc(single_prs_markdown: str) -> lpz.PromptResponseSplit:
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
        rfw.error_message(f"Sources header({SOURCES_HEADER_SMC}) not in expected place or no source list: Assume no sources.")
        sources = ''

    citenum_url_pairs_response = rfw.get_link_tu_pairs(response, CITENUM_URL_LINK_RE)

    # Include plain response citenums (SMC is supposed to be [num](url) but it's inconsistent)
    ok_response_citenums = set([cupair[0] for cupair in citenum_url_pairs_response])
    for citenum_plain in set([m for m in re.findall(lpz.citenum_plain_re, response)]):
        if citenum_plain not in ok_response_citenums:
            warning_url = f"https://BARE_CITE_NUMBER_{citenum_plain}_IN_RESPONSE_WITH_NO_URL"
            rfw.error_message(f'Malformed Plain citenum [{citenum_plain}] appears without URL in response')
            citenum_url_pairs_response.append((citenum_plain, warning_url))
    
    citenum_url_pairs, url_to_source_title = [], pd.Series(dtype=str)
    if len(sources)>0:
        for link_text, url in rfw.get_link_tu_pairs(sources, r'- \[(.*?)\]\((https?://\S+)\)'):
            if match := re.match(SOURCE_CITENUM_TITLE_RE, link_text):
                citenum, title = match['citenum'], match['title']
                citenum_url_pairs.append((citenum, url))
                url_to_source_title[url] = title.strip()
            else:
                raise ValueError(f'Failed to parse source link text: {link_text=}')
        
        # Append response num/url pairs not in sources list (sometimes happens in SMC)
        for num_url_pair in citenum_url_pairs_response:
            if num_url_pair not in citenum_url_pairs:
                rfw.error_message(f'{num_url_pair[0]=}, {num_url_pair[1]=} in response but not source list')
                citenum_url_pairs.append(num_url_pair)
                url_to_source_title[num_url_pair[1]] = 'Cite in response but no entry in sources list'
    else:
        for (num, url) in citenum_url_pairs_response:
            url_to_source_title[num] = 'Response with following no sources list'
        citenum_url_pairs = citenum_url_pairs_response
        
    # substitue plain citenum links into the response, for easier downstream merging
    response = re.sub(CITENUM_URL_LINK_RE, lambda m: f'[{m.group("num")}]', response)
    
    return lpz.PromptResponseSplit(preamble, prompt, response, citenum_url_pairs, url_to_source_title)

def make_obsidian_front_matter():
    """Returns obsidian note front matter."""
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
        raise ValueError(f"Error processing markdown content: {e}") from e

# %%
def split_single_prs_text_perplex(pr_text: str) -> lpz.PromptResponseSplit:
    """Splits stock perplexity export markdown text into prompt, response and source sections,
    returning the source information in citenum_url_pairs.  This is the only way
    to associate citenums to urls, as stock perplexity response citenums are markdown footnotes,
    with plain citenums, like this: [citenum] or [^citenum].  Here, these are left as is."""

    match = re.search(r'(?m)^# (?P<heading_text>.+)', pr_text)
    if match is None or ((heading_start_index := match.start('heading_text')) == -1):
        raise ValueError('Could not find prompt heading')
    
    preamble = pr_text[:heading_start_index].strip()
    
    prompt_end_index, response_start_index = rfw.find_markdown_divider_boundaries(pr_text)
        
    if heading_start_index >= prompt_end_index:
        raise ValueError(f'{heading_start_index=} >= {prompt_end_index=}. '
                         'Probably missed the starting level 1 header part of the prompt.')
    
    prompt = pr_text[heading_start_index:prompt_end_index+1].strip()

    response_sources_divider = '<div style="text-align: center">⁂</div>'
    response_sources_divider_index = pr_text.rfind(response_sources_divider)

    if response_sources_divider_index == -1:
        raise ValueError('Could not find divider between AI response and sources list')

    if response_sources_divider_index <= response_start_index:
        raise ValueError('body_sources_divider_index <= response_sources_divider_index')
    
    response = f"{pr_text[response_start_index:response_sources_divider_index]}".strip()
    
    sources = pr_text[response_sources_divider_index:]
    source_list_pattern_perplex = r'\[\^?(?P<num>\d+)\]:\s*(?P<url>http[s]?://\S+)'
    citenum_url_pairs = rfw.get_link_tu_pairs(sources, source_list_pattern_perplex)
    
    return lpz.PromptResponseSplit(preamble, prompt, response, citenum_url_pairs, pd.Series()) # no source titles

# %% [markdown]
# ##### Fix any duplicate cite numbers inside of each body and collect them

# %%

def load_and_dedup_chat_files(files: list, verbose: bool = True) -> Tuple[list, list, pd.DataFrame]:
    """Read chat files and fix any duplicate cite numbers in the responses and organize them."""
    
    files = files if isinstance(files, list) else [files]
    all_prompts, all_responses, citenums_to_url_list = [], [], []
    
    for file_index, chat_file in enumerate(files):
        if verbose:
            print(f'Parsing {chat_file.name}')
            
        file_text = rfw.read_markdown_file(chat_file)

        # split the file into prompt, response and source section (if SMC)
        if is_smc_content(file_text):
            # SMC files can have multiple prompts and responses
            prs_splits = []    
            sections = re.split(rf'(?<=\n){PROMPT_HEADER_SMC}', file_text)
            for section in sections[1:]:  # Process each user section
                section = f'{PROMPT_HEADER_SMC}\n{section}' # stick header back on for more certtain matching
                dedup_prs = relinker.split_single_prs_dedup(section, split_single_prs_text_smc)
                prs_splits.append(dedup_prs)
        else:
            # stock perplexity files have only a single prompt-response pair
            prs_splits = [relinker.split_single_prs_dedup(file_text, split_single_prs_text_perplex)]

        for prompt_index, prsplit in enumerate(prs_splits):
            all_prompts.append(prsplit.prompt)
            all_responses.append(prsplit.response_dedup)

            citenum_to_url_df = prsplit.citenum_to_url_df.copy().reset_index()
            citenum_to_url_df[['file_index','chat_file', 'prompt_index']] = file_index, chat_file, prompt_index
            if prsplit.url_to_source_title is not None:
                citenum_to_url_df = citenum_to_url_df.set_index('url', drop=True)
                citenum_to_url_df['title'] = prsplit.url_to_source_title            
                citenum_to_url_df = citenum_to_url_df.reset_index()

            citenums_to_url_list.append(citenum_to_url_df)
        
    all_citenums_to_url = pd.concat(citenums_to_url_list)

    if 'title' in all_citenums_to_url.columns:
        # Fill in missing titles with same-url titles from other prompt-response pair source lists
        fixed_title_dfs = []
        for url, df in all_citenums_to_url.groupby('url'):
            has_no_title = df.title.isna()

            if any(has_no_title):
                if len(titles := df.title[~has_no_title].unique()) > 1:
                    ic(url, titles)
                    raise ValueError('Different titles for same URL')

                if len(titles) > 0:
                    df = df.fillna({'title': titles[0]})

            fixed_title_dfs.append(df.copy())
        
        if len(fixed_title_dfs) > 0:
            all_citenums_to_url = pd.concat(fixed_title_dfs)

        all_citenums_to_url['title'] = all_citenums_to_url.title.fillna('NO TITLE: likely bare citenum in response w/ no URL')
    
    return all_prompts, all_responses, all_citenums_to_url

# %% [markdown]
# #### Make a unified cite number set for the merged document

# %%
def unify_citenums(all_citenums_to_url: pd.DataFrame) -> pd.DataFrame:
    """ Make a unified cite number set for the merged chat.
    Reorder the merged citenums, giving each url a new, unique citenum. 
    Urls get lower new citenums when they're mostly in early prompts of early files and with
    mostly low original citenums."""
    df = all_citenums_to_url.copy()
    df['dedup_num_int'] = df['dedup_num'].astype(int)  # so can sort

    url_ranks = df.groupby('url').agg(
        mean_file_index=('file_index', 'mean'),
        mean_dedup_num_int=('dedup_num_int', 'mean'),
        mean_prompt_index=('prompt_index', 'mean')
    ).reset_index()

    url_ranks = url_ranks.sort_values(by=['mean_file_index', 'mean_prompt_index', 'mean_dedup_num_int'], 
                                      ascending=True).reset_index(drop=True)

    url_ranks['unif_num'] = np.arange(1, len(url_ranks) + 1).astype(str)  # citenum == rank as string

    # Merge back the new citenums
    df = df.merge(url_ranks[['url', 'unif_num']], on='url')
    all_citenums_to_url = (df.sort_values(by='unif_num', key=lambda col: col.astype(int))
                           .rename(dict(new_num='doc_dedup_num', citenum_merged='new_num'), axis=1)
                           .drop('dedup_num_int', axis=1)
                           .set_index('file_index'))
    
    return all_citenums_to_url

# %% [markdown]
# #### Assign new, unified cite numbers to each body and concatenate them into a single string

# %%

def concat_prompts_responses(all_prompts: list, all_responses: list, source_chat_files: list, all_citenums_to_url: pd.DataFrame) -> str:
    """Concatenate prompts, responses and appropriate headings into a single markdown string."""
    
    source_chat_files = source_chat_files if isinstance(source_chat_files, list) else [source_chat_files]
    num_chat_files = len(source_chat_files)
    
    all_prompts_same = all(all_prompts[i].strip().lower() == all_prompts[i + 1].strip().lower()
                          for i in range(len(all_prompts) - 1)) if all_prompts else True

    output_markdown = [] # put here for helper funcs below.
    
    def heading_add(name, level):
        output_markdown.append(f'{rfw.make_atx_header(name, level)}\n')

    def text_add(text, top_level):
        text = rfw.hierarch_shift_markdown_headers(text, top_level).strip()
        output_markdown.append(f'{text}\n')

    def prompt_add(global_index, top_level):
        text_add(all_prompts[global_index], top_level)

    def heading_short_prompt_add(global_index, level):
        name = rfw.get_first_n_words(all_prompts[global_index], n=10)
        heading_add(name, level)

    def heading_short_filename_add(file_index, level):
        heading_add(source_chat_files[file_index].name, level)

    def response_add(response, top_level):
        text_add(response, top_level)

    def file_link_add(file_index):
        this_file = source_chat_files[file_index]
        output_markdown.append(f'{rfw.file_link_md("source", this_file)}\n')

    # setup for loop indexing
    is_multi_prompt_file = all_citenums_to_url.groupby('file_index')['prompt_index'].nunique() > 1
    all_citenums_to_url = all_citenums_to_url.reset_index() 
    full_prompt_indices = rfw.unique_rows(all_citenums_to_url, ['file_index', 'prompt_index'])
    all_citenums_to_url = all_citenums_to_url.set_index(['file_index', 'prompt_index'])
    
    for global_index, (file_index, prompt_index) in full_prompt_indices.iterrows():

        # remap the response's deduped citenums to unified citenums
        citenum_dedup_to_unified = (all_citenums_to_url.loc[file_index, prompt_index]
                                    .set_index('dedup_num').unif_num.to_dict())
        response_unified = relinker.replace_response_citenums(all_responses[global_index],
                                                              citenum_dedup_to_unified)

        # appropriately insert prompts and responses between headings
        is_first_prompt_in_file = prompt_index == 0
        if num_chat_files == 1:
            if is_first_prompt_in_file:
                file_link_add(file_index)
                if is_multi_prompt_file[file_index]:
                    heading_short_prompt_add(global_index, 1)
                else:
                    heading_add("Prompt", 1)
                prompt_add(global_index, 3)
            else:
                heading_short_prompt_add(global_index, 1)
                prompt_add(global_index, 3)
            
            heading_add("Response", 2)
            response_add(response_unified, 3)
        elif all_prompts_same and not is_multi_prompt_file[file_index]:
            # Print prompt once at top, then responses
            if file_index == 0 and is_first_prompt_in_file:
                heading_add("Prompt", 1)
                prompt_add(global_index, 2)
                heading_add("Responses", 1)

            heading_short_filename_add(file_index, 2)
            file_link_add(file_index)
            response_add(response_unified, 3)
        else:
            # print all prompt/response w/ separate prompt/resp headers
            if is_first_prompt_in_file:
                heading_short_filename_add(file_index, 1)
                file_link_add(file_index)

            heading_add("Prompt", 2)
            prompt_add(global_index, 3)
            heading_add("Response", 2)
            response_add(response_unified, 3)

    return ''.join(output_markdown)

# %% [markdown]
# ##### Insert links to Obsidian or Zotero

# %%
def relink_to_obsidian_and_zotero_merge(all_citenums_to_url, all_promptresp):
    """Insert links to Obsidian or Zotero and writes the merged file"""
    url_to_source_title = {}
    if 'title' in all_citenums_to_url.columns:
        for _, df in all_citenums_to_url.reset_index().groupby('unif_num'):
            url_to_source_title[df.iloc[0].url] = df.iloc[0].title

    prsplit_all = lpz.PromptResponseSplitDeDup('', '', all_promptresp, all_citenums_to_url, url_to_source_title)

    all_promptresp_unified_relinked, relinked_sources = relinker.relink_response_and_sources(prsplit_all, 'unif_num')
    relinked_sources = "\n".join(sorted(relinked_sources, key=lambda line: int(re.search(lpz.citenum_plain_re, line).group('num'))))


    return f'{make_obsidian_front_matter()}\n{all_promptresp_unified_relinked}\n# Citations\n{relinked_sources}'

# %%
def relink_chat_files(input_files: List[pl.Path], output_file: pl.Path,
                      verbose: bool = True) -> None:
    """Replaces web links in perplexity export markdown files with links to Obsidian lit notes
    or Zotero items.  It then merges them into a single file, with a single source list 
    and unified citation numbers."""

    all_prompts, all_responses, all_citenums_to_url = load_and_dedup_chat_files(input_files, verbose)

    all_citenums_to_url = unify_citenums(all_citenums_to_url)

    all_promptresp = concat_prompts_responses(all_prompts, all_responses, input_files,
                                              all_citenums_to_url)

    merged_chat = relink_to_obsidian_and_zotero_merge(all_citenums_to_url, all_promptresp)

    print(f'writing to {output_file=}')
    output_file.write_text(merged_chat, encoding='utf-8')
    print("Done.")

# %%

if __name__ == "__main__":
    tmpdir = rfw.refwrangle_test_dir / 'tmp'
    tmpdir.mkdir(parents=True, exist_ok=True)

    datdir = rfw.refwrangle_test_dir / 'dat' / 'merge_chats_perplex'
    datdir.mkdir(parents=True, exist_ok=True)

    # multi-file perplex, same prompt
    #chat_files = list(datdir.glob('*.md'))
    # multi-file, different prompt
    #chat_files = [chat_files[3], pl.Path(r"C:\Users\scott\OneDrive\share\ref\refwrangle\test\dat\perplexity_example.md")]
    # single file
    #chat_files = [chat_files[3]]

    # single smc file but multiprompt
    #chat_files = [pl.Path(r"C:\Users\scott\OneDrive\share\ref\refwrangle\test\dat\perplexity_multi_prompt_savemychatbot_example.md")]
    
    chat_files = [pl.Path(r"C:\Users\scott\OneDrive\share\ref\refwrangle\test\dat\bannon_smc_test.md")]

    output_dir = pl.Path(r"C:\Users\scott\OneDrive\share\ref\obsidian\Obsidian Share Vault\Scratch Space")
    merged_output_file = output_dir / 'tmp_perplexy_merged.md'

    relink_chat_files(chat_files, merged_output_file, verbose=True)


