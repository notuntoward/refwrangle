import pathlib as pl
from icecream import ic
import urllib.parse
import os
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import pickle
from pypdf import PdfWriter, PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from datetime import datetime
import io

refdir = obsidian_vault_dir = pl.Path(r"C:\Users\scott\OneDrive\share\ref")

# path to obsidian vault  (MACHINE SPECIFIC)
obsidian_vault_dir = refdir / "obsidian/Obsidian Share Vault"

# entry info extracted from Zotero DB
refwrangle_dir = refdir / 'refwrangle'
extractedZoteroEntriesFNm = refwrangle_dir / 'dat/zotero_entries.pkl'

# My Zotero API credentials
library_id = '60638'
library_type = 'user'  # or 'group' if using a group library
api_key = 'VFJnuXqeaJPcVjCQHQAELCuu'


# where both zotero and obsidian look for literature notes and attachments
lit_dir_shared = obsidian_vault_dir / 'lit'

# where zotero-linked pdfs, etc are stored (zotero setting: "linked attachment base directory"). It's shared by obsidan.
lit_attachment_dir_shared = lit_dir_shared / 'lit_sources'

# markdown literature notes writting by obsidian, accessible from zotero using MarkDB-Connect plugin
lit_notes_dir_shared = lit_dir_shared / 'lit_sources'

from bs4 import BeautifulSoup

from bs4 import BeautifulSoup
import re

# improveents from sonnet huge.  Says it removes structure, which sounds abd
from bs4 import BeautifulSoup
import re

def clean_html(html_file_path):
    """
    Cleans and extracts the main content from a downloaded HTML file, removing promotional links
    and other non-essential elements.

    Args:
        html_file_path (str or pathlib.Path): Path to the HTML file.

    Returns:
        str: Cleaned HTML content.
    """
    # Step 1: Load the HTML file
    with open(html_file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()

    # Step 2: Parse with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    # Step 3: Try to locate the main content
    article = soup.find('article') or \
              soup.find('div', class_=re.compile(r'(content|article|post|entry)')) or \
              soup.find('main')

    # Fallback: Broad search for large <div> with significant text content
    if not article:
        potential_divs = soup.find_all('div')
        article = max(potential_divs, key=lambda div: len(div.get_text(strip=True)), default=None)

    if not article:
        print("Main article content not found!")
        return ""

    # Step 4: Remove unwanted elements
    unwanted_elements = [
        'script', 'style', 'iframe', 'form', 'button', 'aside', 'nav',
        'header', 'footer', 'figcaption', 'figure', 'noscript'
    ]
    for element in article.find_all(unwanted_elements):
        element.decompose()

    # Step 5: Remove promotional links and related content
    for element in article.find_all(['div', 'section', 'ul']):
        try:
            if any(re.search(r'(related|recommended|popular|more articles|read next)', 
                   str(attr), re.I) for attr in element.attrs.values()):
                element.decompose()
        except Exception as e:
            print(f"Error processing element: {e}")
            continue

    # Step 6: Remove inline styles and classes
    for tag in article.find_all(True):
        tag.attrs = {}

    # Step 7: Replace links with their text content
    for link in article.find_all('a'):
        link.replace_with(link.get_text())

    # Step 8: Remove empty tags
    for tag in article.find_all():
        if len(tag.get_text(strip=True)) == 0:
            tag.decompose()

    # Step 9: Remove excessive whitespace
    cleaned_text = re.sub(r'\s+', ' ', article.get_text()).strip()

    return cleaned_text


# works, and preserves some file structure but leaves too many links in Tumulty
# Seems the best compromise for now of structure preservation and cleaning.
# An LLM cleaner like in the pymupdf4llm pdf cleaner might well work better, 
# but you'd have to run it before this cleaner because it turns links into plain text, which
# probably won't be recognizable as irrelevant content to a RAG.
def clean_html(html_file_path):
    """
    Cleans and extracts the main content from a downloaded HTML file by targeting
    broader structures if specific tags or classes are not found.  From GPt-4o.
    OK on my 3 test cases.a  WA post still has tons of textified links.

    Args:
        html_file_path (str or pathlib.Path): Path to the HTML file.

    Returns:
        str: Cleaned HTML content.
    """
    # Step 1: Load the HTML file
    with open(html_file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()

    # Step 2: Parse with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    # Step 3: Try to locate the main content
    # Primary attempt: Look for <article> tag
    article = soup.find('article')
    
    # Secondary attempt: Look for a div with a specific class (adjust as needed)
    if not article:
        article = soup.find('div', {'class': 'blog-content'})  # Example class name
    
    # Fallback: Broad search for large <div> with significant text content
    if not article:
        potential_divs = soup.find_all('div')
        for div in potential_divs:
            if len(div.get_text(strip=True)) > 500:  # Adjust threshold as needed
                article = div
                break

    if not article:
        print("Main article content not found!")
        return ""

    # Step 4: Remove unwanted tags from the article content
    for tag in article(['script', 'style', 'img', 'button']):
        tag.decompose()

    # Step 5: Simplify links by replacing <a> tags with their text content
    for link in article.find_all('a'):
        link.replace_with(link.text)

    # Step 6: Remove empty tags
    for tag in article.find_all():
        if not tag.text.strip():
            tag.decompose()

    # Step 7: Return cleaned HTML as a string
    return str(article)

def html_to_pdf_playwright(input_html, output_pdf_path):
    """
    Converts an HTML string to a PDF file.
    Args:
        input_html (str): HTML content as a string.
        output_pdf_path (str): Path to save the generated PDF.

    Notes:
        - Requires Playwright's `sync_playwright`.
        - Does not work in Jupyter Notebook or VSCode Interactive Window.

    Example: html_to_pdf("<h1>Hello</h1>", "output.pdf")
    """
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(input_html)
        page.pdf(path=output_pdf_path, format='A4') # write file
        browser.close()


def load_pickle_data(fNm):
    """Returns the data stored in a pickle file"""
    print(f'Reading from {fNm}...')
    with open(fNm, 'rb') as file:
        data = pickle.load(file)
    return data

def save_pickle_data(fNm, data):
    """Saves data to a pickle file"""
    print(f'Writing to {fNm}...')
    with open(fNm, 'wb') as file:
        pickle.dump(data, file)

def create_title_page(writer, pdf_files):
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=letter)
    
    # Add timestamp and PDF count header
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.setFont("Helvetica-Bold", 14)
    header = f"{len(pdf_files)} PDFs merged on {timestamp}"
    c.drawString(72, 750, header)
    
    # Add separator line
    c.line(72, 735, 540, 735)
    
    # List of articles
    c.setFont("Helvetica", 12)
    y_position = 700
    
    for i, pdf_path in enumerate(pdf_files, 1):
        pdf_basename = os.path.basename(pdf_path).split('.')[0]
        title = f"Article {i}: {pdf_basename}"
        c.drawString(72, y_position, title)
        y_position -= 20
        
        if y_position < 50:
            c.showPage()
            c.setFont("Helvetica", 12)
            y_position = 750
    
    c.showPage()
    c.save()
    packet.seek(0)
    title_pdf = PdfReader(packet)
    writer.add_page(title_pdf.pages[0])

def add_separator_page(writer, pdf_basename, full_path, metadata):
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=letter)
    
    c.setFont("Helvetica-Bold", 16)
    c.setFillColorRGB(0, 0, 1)  # Blue
    
    text = pdf_basename
    x, y = 100, 600
    c.linkURL(full_path, (x, y-5, x+200, y+20), relative=1)
    c.drawString(x, y, text)
    
    c.setFont("Helvetica", 12)
    c.setFillColorRGB(0, 0, 0)  # Black
    y_position = 500
    for key, value in metadata.items():
        c.drawString(100, y_position, f"{key}: {value}")
        y_position -= 30
    
    c.showPage()
    c.save()
    packet.seek(0)
    separator_pdf = PdfReader(packet)
    writer.add_page(separator_pdf.pages[0])

def add_margin_text(page, basename):
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=letter)
    
    # Add vertical margin text
    c.saveState()
    c.setFont("Helvetica", 12)  # legible when small
    # c.setFont("Helvetica-Bold", 12)    
    c.setFillColor(colors.darkgreen)
    # st arg is right shift.  Max for letter page is 612 pts (8.5")
    c.translate(600, 400)
    # c.translate(580, 400) # previous
    c.rotate(90)
    c.drawString(0, 0, basename)
    c.restoreState()
    
    c.showPage()
    c.save()
    packet.seek(0)
    
    margin_pdf = PdfReader(packet)
    margin_page = margin_pdf.pages[0]
    margin_page.merge_page(page)
    return margin_page

def merge_pdfs_with_structure(pdfs_info, output_path):
    """Merge pdfs into a single pdf, intended to have RAG-friendly page and bookmark structure
    Perplexity:
      https://www.perplexity.ai/search/fix-the-bug-in-the-code-below-plw_2PR4TUWH6xqSZ7M_nQ#27"""

    writer = PdfWriter()
    
    # Add title page first
    pdf_files = [pdf_info['file'] for pdf_info in pdfs_info]
    
    create_title_page(writer, pdf_files)
        
    current_page = 1
    for i, pdf_path in enumerate(pdf_files, 1):
        pdf_basename = os.path.basename(pdf_path).split('.')[0]
        full_path = os.path.abspath(pdf_path)
        
        add_separator_page(writer, pdf_basename, full_path, pdfs_info[i-1]['metainfo'])
#        add_separator_page(writer, pdf_basename, full_path, sample_metadata[i-1])
        article_title = f"Article {i}: {pdf_basename}"
        separator_bookmark = writer.add_outline_item(article_title, current_page)
        current_page += 1
        
        pdf = PdfReader(pdf_path)
        page_offset = current_page
        
        # Add pages with margin text
        for page in pdf.pages:
            modified_page = add_margin_text(page, pdf_basename)
            writer.add_page(modified_page)
            
        if pdf.outline:
            seen_bookmarks = set()
            for item in pdf.outline:
                if isinstance(item, dict) and '/Page' in item:
                    title = item['/Title']
                    if title not in seen_bookmarks:
                        seen_bookmarks.add(title)
                        page_num = pdf.get_destination_page_number(item)
                        writer.add_outline_item(
                            title,
                            page_offset + page_num,
                            parent=separator_bookmark
                        )
        
        current_page += len(pdf.pages)
    
    with open(output_path, 'wb') as output:
        writer.write(output)

# # fontconfig file required by weasyprint and others
# os.environ['FONTCONFIG_FILE'] = str(pl.Path(r'./fonts.conf').resolve()) # avoid error messages
# #os.environ['FONTCONFIG_FILE'] = str(pl.Path(r'../fonts.conf').resolve()) # avoid error messages
# fontconfig_file = os.environ.get('FONTCONFIG_FILE', None)
# if not pl.Path(fontconfig_file).exists():
#     raise Exception(f"fontconfig file doesn't exist at {fontconfig_file}")

# # Fontconfig success also requires GTK+: winget install --id=tschoonj.GTKForWindows -e
# if not any('gtk' in path.lower() for path in os.environ['PATH'].split(os.pathsep)):
#     raise Exception('GTK+ is not in path')

# # These imports after fontconfig configuration
# from weasyprint import HTML, CSS # after fontconfig setup to avoid error messages
# from bs4 import BeautifulSoup

# def clean_html(html_content):
#     """
#     Cleans and extracts the main content from a downloaded HTML file by targeting
#     broader structures if specific tags or classes are not found.  From GPt-4o.
#     OK on my 3 test cases.  WA post still has tons of textified links.

#     Args:
#         html_content (str): content to clea

#     Returns:
#         str: Cleaned HTML content.
#     """

#     # Step 1: Parse with BeautifulSoup
#     soup = BeautifulSoup(html_content, 'html.parser')

#     # Step 2: Try to locate the main content
#     # Primary attempt: Look for <article> tag
#     article = soup.find('article')
    
#     # Secondary attempt: Look for a div with a specific class (adjust as needed)
#     if not article:
#         article = soup.find('div', {'class': 'blog-content'})  # Example class name
    
#     # Fallback: Broad search for large <div> with significant text content
#     if not article:
#         potential_divs = soup.find_all('div')
#         for div in potential_divs:
#             if len(div.get_text(strip=True)) > 500:  # Adjust threshold as needed
#                 article = div
#                 break

#     if not article:
#         print("Main article content not found!")
#         return ""

#     # Step 3: Remove unwanted tags from the article content
#     for tag in article(['script', 'style', 'img', 'button']):
#         tag.decompose()

#     # Step 4: Simplify links by replacing <a> tags with their text content
#     for link in article.find_all('a'):
#         link.replace_with(link.text)

#     # Step 5: Remove empty tags
#     for tag in article.find_all():
#         if not tag.text.strip():
#             tag.decompose()

#     # Step 6: Return cleaned HTML as a string
#     return str(article)

# def html_to_pdf(source_html, output_pdf_path, header_link_text, header_link_dest, verbose=True):
#     """
#     Convert HTML to PDF with a clickable header link.

#     Args:
#         cleaned_html (str): Main HTML content.
#         output_pdf_path (str): Output PDF file path.
#         header_link_text (str): Filename for header display.
#         header_link_dest (Path): Original file path for header link.
#         verbose: if true, print output filename

#     Returns:
#         The return value of weasyprint.HTML().write_pdf().
#     """
#     # URI format for clickable link
#     file_uri = urllib.parse.urljoin('file:', urllib.parse.quote(str(header_link_dest.absolute())))
    
#     # Create the HTML content with running header containing the link
#     html_content = f"""
#     <!DOCTYPE html>
#     <html>
#     <head>
#         <style>
#             @page {{
#                 size: A4;
#                 margin: 1in;
#             }}
#             #header {{
#                 position: running(header);
#                 text-align: right;
#                 font-size: 10pt;
#             }}
#             #header a {{
#                 color: blue;
#                 text-decoration: underline;
#             }}
#             @page {{
#                 @top-right {{
#                     content: element(header);
#                 }}
#             }}
#         </style>
#     </head>
#     <body>
#         <div id="header">
#             <a href="{file_uri}">{header_link_text}</a>
#         </div>
#         {source_html}
#     </body>
#     </html>
#     """
    
#     if verbose:
#         print(f'writing to {output_pdf_path}')
#     HTML(string=html_content).write_pdf(output_pdf_path)

# def html_file_to_clean_pdf(input_html_path, output_pdf_path, do_clean=True):
#     """
#     Process HTML file to PDF with cleaning and conversion.

#     Args:
#         input_html_path (Path): Path to input HTML file.
#         output_pdf_path (Path): Path for output PDF file.
#     """

#     with open(input_html_path, 'r', encoding='utf-8') as file:
#         html_content = file.read()

#     if do_clean:
#         cleaned_html = clean_html(html_content)
#     else:
#         raise Exeception('Not implemented.  This html_to_pdf() adds html wrapper, would fail with raw html_content')

#     basename = input_html_path.stem
#     html_to_pdf(cleaned_html, output_pdf_path, basename, input_html_path)
