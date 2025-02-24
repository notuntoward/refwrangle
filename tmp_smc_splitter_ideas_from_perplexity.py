# Something cleaner from perplexity, although it loses strict order testing
#
# import re
# from dataclasses import dataclass

# PROMPT_HEADER_SMC = '## User'
# RESPONSE_HEADER_SMC = '## AI Answer'
# SOURCES_HEADER_SMC = r'\*\*Sources\*\*'

# @dataclass
# class PromptResponseSplit:
#     prompt: str
#     response: str
#     sources: str

# def split_prompt_response_text_smc(input_string: str) -> PromptResponseSplit:
#     """Splits a single prompt/response/source string from Save My Chatbot output markdown."""
    
#     # Define a pattern with capturing groups for headers
#     pattern = rf"(?m)^({PROMPT_HEADER_SMC}|{RESPONSE_HEADER_SMC}|{SOURCES_HEADER_SMC})"
    
#     # Use re.split to split and include the matched headers in the result
#     parts = re.split(pattern, input_string)
    
#     # Filter out empty strings from parts (if any)
#     parts = [part.strip() for part in parts if part.strip()]
    
#     # Process parts to extract prompt, response, and sources
#     prompt = ""
#     response = ""
#     sources = ""
    
#     # Iterate through parts to assign content based on headers
#     for i in range(len(parts)):
#         if parts[i] == PROMPT_HEADER_SMC and i + 1 < len(parts):
#             prompt = parts[i + 1]
#         elif parts[i] == RESPONSE_HEADER_SMC and i + 1 < len(parts):
#             response = parts[i + 1]
#         elif parts[i] == SOURCES_HEADER_SMC and i + 1 < len(parts):
#             sources = parts[i + 1]
    
#     return PromptResponseSplit(prompt=prompt, response=response, sources=sources)

# # Example usage
# input_string = """## User
# This is a user input.
# ## AI Answer
# This is an AI response.
# **Sources**
# These are the sources."""
# result = split_prompt_response_text_smc(input_string)
# print(result)
# 
#---------------------------------------------------------------------------------
#
# perplexity verssion that maintains order
#
# import re
# from dataclasses import dataclass

# PROMPT_HEADER_SMC = '## User'
# RESPONSE_HEADER_SMC = '## AI Answer'
# SOURCES_HEADER_SMC = r'\*\*Sources\*\*'

# @dataclass
# class PromptResponseSplit:
#     prompt: str
#     response: str
#     sources: str = ""  # Default to an empty string if sources are not provided

# def split_prompt_response_text_smc(input_string: str) -> PromptResponseSplit:
#     """Splits a single prompt/response/source string from Save My Chatbot output markdown, with optional sources."""
    
#     # Regex pattern to match required headers (in order) and optional sources
#     pattern = rf"""
#         ^{PROMPT_HEADER_SMC}\n(.*?)       # Match ## User and capture its content
#         \n{RESPONSE_HEADER_SMC}\n(.*?)   # Match ## AI Answer and capture its content
#         (?:\n{SOURCES_HEADER_SMC}\n(.*))?$  # Optionally match **Sources** and capture its content
#     """
    
#     match = re.match(pattern, input_string, re.DOTALL | re.VERBOSE)
    
#     if not match:
#         raise ValueError("Input string does not match the expected format.")
    
#     # Extract matched groups with default for sources if not present
#     prompt, response, sources = match.group(1).strip(), match.group(2).strip(), (match.group(3) or "").strip()
    
#     return PromptResponseSplit(prompt=prompt, response=response, sources=sources)

# # Example usage
# input_string_with_sources = """## User
# This is a user input.
# ## AI Answer
# This is an AI response.
# **Sources**
# These are the sources."""

# input_string_without_sources = """## User
# This is a user input.
# ## AI Answer
# This is an AI response."""

# # Test with sources present
# result_with_sources = split_prompt_response_text_smc(input_string_with_sources)
# print(result_with_sources)

# # Test without sources present
# result_without_sources = split_prompt_response_text_smc(input_string_without_sources)
# print(result_without_sources)
