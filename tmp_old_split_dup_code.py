          
    
# def split_dedup_prompt_response_smc(markdown_text: str) -> Tuple[str, str, pd.DataFrame]:
#     """Splits a single file's worth of Save My Chatbot output markdown text into 
#     prompt, response and source sections. In the response, duplicate citenums
#     are removed, and the mapping from original to deduplicated numbers is in
#     citenumes_to_url_source"""
    
#     front_matter = f'---\ncategory: aichat\ncreated date: {dt.datetime.now()}\n---\n'
#     sections_prompt_response = re.split(rf'(?<=\n){USER_HEADING}', markdown_text)
    
#     chat_source = " ".join(sections_prompt_response[0].split("\n")[1:])  # Remove redundant header
#     file_header = front_matter + f'{chat_source.lstrip()}\n'
#     # processed_sections = [front_matter + f'{chat_source.lstrip()}\n']
        
#     for section in sections_prompt_response[1:]:  # Process each user section
#         try:        
#             _, prompt, response, sources  = split_prompt_response_text_smc(section)
#         except:
#             print(e)
#             continue # don't die if only one is section is bad
        
#         citenum_url_pairs = rfw.get_link_tu_pairs(sources, source_list_pattern_smc)
   
#         citenums_to_url_source = relinker.citenums_to_urls_dedup(citenum_url_pairs)
    
#         response_dedup = relinker.replace_body_citenums(response, citenums_to_url_source.new_num.to_dict())
#         response_dedup = rfw.remove_markdown_dividers(response_dedup) # too many in o3-mini (2/2025)
        

#     return preamble, prompt, response_dedup, citenums_to_url_source
                
# def split_prompt_response_dedup_smc(markdown_text: str) -> PromptResponseSplitDeDup:
#     """Splits perplexity Save My Chatbot output markdown text into prompt, response and source sections.
#     In the response, duplicate citenums are removed, and the mapping from original 
#     to deduplicated numbers is in citenumes_to_url_source"""
    
#     return relinker.split_prompt_response_dedup(markdown_text, split_prompt_response_text_perplex)
