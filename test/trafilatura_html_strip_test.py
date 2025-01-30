# trafilatura lib strips everything but bare text from a web page.  It seems quite robust, although sometimes, there is a lot of junk
# Can either download and strip from a URL, or can strip an already downloaded html file

import pathlib as pl
url = 'https://investor.vanguard.com/investor-resources-education/iras/roth-ira-income-limits#:~:text=Income%20limits%20for%20a%20Roth,to%20make%20a%20full%20contribution.'

hpath = pl.Path(r'C:/Users/scott/OneDrive/share/ref/obsidian/Obsidian Share Vault/lit/lit_sources/')

#html_file_path = hpath / 'Tumulty24FrischLearnedDemsShould.html'  # fails on this commplex WA Post page (prints None)
html_file_path = hpath / 'Walther24barstoolConservatism.html'     # works
# html_file_path = hpath / 'Yan24berkeleyFuncCallLeaderBrd.html'     # works, pure text is a mess

file_path = html_file_path

# -------- detect encoding for open() if necessary
# use cchardet instead of chardet b/c perplexity sez it's more efficient

import cchardet as chardet  # alias faster cchardet to standard chardet 
#from trafilatura import extract_from_file # doesn't exist

def detect_encoding(file_path, max_bytes=1048576):  # 1 MB limit
    with open(file_path, 'rb') as file:
        raw_data = file.read(max_bytes)
    result = chardet.detect(raw_data)
    return result['encoding']

#detected_encoding = detect_encoding(file_path)
#print(f'{detected_encoding=}')


# ---------- download html from web and parse

# import trafilatura

# # URL of the article you want to download and process
# url = "https://example.com/article-url"


# # Download and extract the main content
# downloaded_content = trafilatura.fetch_url(url)
# text_content = trafilatura.extract(downloaded_content)

# # Print the extracted text
# print(text_content)

# # Optionally, save the extracted text to a file
# with open("extracted_article.txt", "w", encoding="utf-8") as file:
#     file.write(text_content)

# ---------- parse already downloaded html -----------

# THIS DOES WORK.  Extracts pure text, so a bit garbled.

from trafilatura import extract
# from trafilatura.core import extract_metadata did this ever work?

html_file_path = str(html_file_path)

# internal functions: these are hallucinations: filepath arg doesn't exist
#extracted_text = extract(filepath=html_file_path)
#metadata = extract_metadata(filepath=html_file_path)

# if you know the encoding
with open(html_file_path, 'r', encoding='utf-8') as file:
    html_content = file.read()

extracted_text = extract(html_content)
print(extracted_text)    


# import trafilatura

# def clean_html(html_file_path):
#     with open(html_file_path, 'r', encoding='utf-8') as file:
#         html_content = file.read()
#     extracted_text = trafilatura.extract(html_content)
#     return f"<html><body>{extracted_text}</body></html>"