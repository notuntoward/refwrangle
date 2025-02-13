"""Utility functions for reference wrangling."""

import io
import pathlib as pl
import pickle
import re
import struct
import subprocess
import sys
import traceback
import unicodedata
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, urlunparse
from xml.sax.saxutils import escape
import chardet
import markdown
import pandas as pd
import plotly.graph_objects as go
import pymupdf4llm
from bs4 import BeautifulSoup
from icecream import ic
from markdownify import markdownify
from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter
from pyzotero import zotero
from rapidfuzz import fuzz  # faster, more accurate than fuzzywuzzy
from readability import Document
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate
from youtube_transcript_api import YouTubeTranscriptApi

pdfmetrics.registerFont(TTFont('Verdana', 'Verdana.ttf'))
pdfmetrics.registerFont(TTFont('VerdanaItalic', 'Verdanai.ttf'))
pdfmetrics.registerFont(TTFont('VerdanaBold', 'Verdanab.ttf'))
pdfmetrics.registerFont(TTFont('VerdanaBoldItalic', 'Verdanaz.ttf'))

pdfmetrics.registerFontFamily('Verdana',
    normal='Verdana',
    bold='VerdanaBold',
    italic='VerdanaItalic',
    boldItalic='VerdanaBoldItalic'
)

refdir = obsidian_vault_dir = pl.Path(r"C:\Users\scott\OneDrive\share\ref")

# path to obsidian vault  (MACHINE SPECIFIC)
obsidian_vault_dir = refdir / "obsidian/Obsidian Share Vault"

# entry info extracted from Zotero DB
refwrangle_dir = refdir / 'refwrangle'
extractedZoteroEntriesFNm = refwrangle_dir / 'dat/zotero_entries.pkl'

refwrangle_test_dir = refwrangle_dir / 'test'
refwrangle_dat_dir = refwrangle_dir / 'dat'
refwrangle_tmp_dir = refwrangle_dir / 'tmp'

# After high quality html to markdown conversion, the md but be at least this big
# Otherwise, more cautious quality conversion will be done
MIN_BYTES_FOR_HIGH_QUALITY_HTML2MD = 4000
MIN_SCORE_TITLE_MATCH = 95 # max==100: stringent, limit false matches

# My Zotero API credentials
library_id = '60638'
library_type = 'user'  # or 'group' if using a group library
api_key = 'VFJnuXqeaJPcVjCQHQAELCuu'

procDir = refwrangle_dir / 'dat' / 'proc'
# html2pdf_cachedir = procDir / 'h2p_cache'
# html2pdf_cachedir.mkdir(parents=True, exist_ok=True)

# processed_source_cachedir = procDir / 'processed_source_cache'
# processed_source_cachedir.mkdir(parents=True, exist_ok=True)

attachments_as_md_cachedir = procDir / 'attachments_as_md_cache'
attachments_as_md_cachedir.mkdir(parents=True, exist_ok=True)

# where both zotero and obsidian look for literature notes and attachments
lit_dir_shared = obsidian_vault_dir / 'lit'

# where zotero-linked pdfs, etc are stored (zotero setting: "linked attachment base directory"). It's shared by obsidan.
lit_attachment_dir_shared = lit_dir_shared / 'lit_sources'

# markdown literature notes writting by obsidian, accessible from zotero using MarkDB-Connect plugin
lit_notes_obsidian_dir = lit_dir_shared / 'lit_notes'

orig_proc_dir = refwrangle_dat_dir / 'orig' / 'proc'
merged_RAG_source_dir = orig_proc_dir / 'Merged RAG Political Sources'

zoterodb_cache_file = orig_proc_dir / 'ZoteroDBcache.bin'

perplexity_api_key = "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"

# the desired attachment file extension for each child contentType
desiredFileExtention = {'application/pdf':'pdf', 'text/html':'html', 
                        'application/vnd.openxmlformats-officedocument.presentationml.presentation':'pptx'}

def zotero_item_link(zotero_item_key: str, link_text: str) -> str:
    """Makes a link to a zoter item, given key and text."""
    return f'[{link_text}](zotero://select/library/items/{zotero_item_key})'

class ZoteroCache:
    """Caches the result of the pyzotero command:  parent_items = self.zot.everything(self.zot.top())"""

    HEADER_FORMAT = "I"  # Format for an unsigned integer (serial number)
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(self, filename=zoterodb_cache_file, library_id=library_id, 
                 library_type=library_type, api_key=api_key):
        """Initialize the ZoteroCache with the given filename and Zotero API credentials."""
        self.filename = filename
        self.zot = zotero.Zotero(library_id, library_type, api_key)

    def download_and_save_cache(self):
        """ Fetch data from Zotero and write it to the cache file along with the current version."""
        # Fetch data from Zotero
        parent_items = self.zot.everything(self.zot.top())
        current_version = self.zot.last_modified_version()

        with open(self.filename, 'wb') as f:
            # Write the current version as a fixed-size header
            f.write(struct.pack(self.HEADER_FORMAT, current_version))
            # Serialize and write the parent items
            pickle.dump(parent_items, f)

    def read_version(self):
        """Read only the version number from the cache file."""
        try:
            with open(self.filename, 'rb') as f:
                # Read and unpack the fixed-size header
                header_data = f.read(self.HEADER_SIZE)
                return struct.unpack(self.HEADER_FORMAT, header_data)[0]
        except FileNotFoundError:
            return None  # Cache file does not exist

    def read_cache(self):
        """Read the cached data from the file."""
        try:
            with open(self.filename, 'rb') as f:
                # Skip the fixed-size header
                f.seek(self.HEADER_SIZE)
                # Load and deserialize the parent items
                return pickle.load(f)
        except FileNotFoundError:
            return None  # Cache file does not exist

    def is_cache_valid(self):
        """Check if the cached version matches the current version from Zotero."""
        cached_version = self.read_version()
        current_version = self.zot.last_modified_version()
        return cached_version == current_version

    def get_data(self):
        """Retrieve data from cache if valid; otherwise update cache and fetch fresh data."""
        if self.is_cache_valid():
            print("Reading from cache.")
            return self.read_cache()
        else:
            print("Updating cache.")
            self.download_and_save_cache()
            return self.read_cache()
        
def is_ignorable_child(child: Dict[str, Any]) -> bool:
    """Returns True if a child is not something that attachment processing 
    would need to deal with."""
    
    cdat = child['data']
    if cdat['itemType'] != 'attachment':
        return True # e.g. a zotero note of type type 'note'

    if cdat['title'] in ['PubMed entry', 'Semantic Scholar Link']:
        return True
    
    if 'path' not in cdat:
        return True # must not be a note then but I'm not sure what it is
    
    return False
        
def get_my_zotero_collections(top_collection_name: Optional[str] = None, zot: Optional[zotero.Zotero] = None) -> List[str]:
    """Returns the list of collections in my zotero DB. 
     top_collection_name: return only collections hierarchically below this collection. 
     zot is an opened pyzotero object
     
     TODO: make this accept a zotero cache, once this is storing that data
     TODO: use zot.collections_sub() and zot.collections_top()"""
    
    if zot is None:
        zot = zotero.Zotero(library_id, library_type, api_key)

    if top_collection_name is None:
        return [c['data']['name'] for c in zot.collections()]

    top_collection_data = next((c for c in zot.collections() if c['data']['name'] == top_collection_name), None)

    if top_collection_data:
        top_collection_key = top_collection_data['key']
        
        # Get all subcollections under 'Politics'
        return [c['data']['name'] for c in zot.all_collections(top_collection_key)]
    else:
        raise ValueError(f"'{top_collection_name}' collection not found")

def plot_my_zotero_collections(top_collection_name: Optional[str] = None) -> None:
    """Hierarchically plots the collections in my zotero DB. 
     top_collection_name: plot only collections hierarchically below this collection. """
    
    zot = zotero.Zotero(library_id, library_type, api_key)

    all_collections = zot.all_collections()

    # Build hierarchy
    hierarchy = {}
    for collection in all_collections:
        key = collection['key']
        name = collection['data']['name']
        parent = collection['data'].get('parentCollection', '')
        hierarchy[key] = {'name': name, 'parent': parent, 'children': []}

    # Populate children
    for key, data in hierarchy.items():
        if data['parent']:
            hierarchy[data['parent']]['children'].append(key)

    # Find the key of the top collection if specified
    top_collection_key = None
    if top_collection_name:
        for key, data in hierarchy.items():
            if data['name'] == top_collection_name:
                top_collection_key = key
                break
        if not top_collection_key:
            print(f"Collection '{top_collection_name}' not found.")
            return

    # Create a recursive function to build the tree
    def build_tree(key: str):
        node = hierarchy[key]
        children = [build_tree(child) for child in node['children']]
        return {'name': node['name'], 'children': children}

    # Build the tree structure
    if top_collection_key:
        tree_data = [build_tree(top_collection_key)]
    else:
        root_collections = [key for key, data in hierarchy.items() if not data['parent']]
        tree_data = [build_tree(root) for root in root_collections]

    # Create lists to hold the labels and parents
    labels = []
    parents = []

    # Function to flatten the tree structure
    def flatten_tree(node, parent=""):
        labels.append(node['name'])
        parents.append(parent)
        for child in node.get('children', []):
            flatten_tree(child, node['name'])

    # Flatten the tree structure
    for root in tree_data:
        flatten_tree(root)

    # Create the treemap
    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=parents,
        root_color="lightgrey"
    ))

    # Update the layout
    title = f"Zotero Collection Hierarchy: {top_collection_name}" if top_collection_name else "Zotero Collection Hierarchy"
    fig.update_layout(
        title=title,
        width=1000,
        height=800
    )

    # Show the plot
    fig.show()

def extra2dict(extra: str) -> Dict[str, str]:
    """Converts zotero extra field string into dict of keys and values"""
    dictionary = {}
    for line in extra.splitlines():
        if ': ' in line:
            key, value = line.split(': ', 1)
            dictionary[key] = value
    return dictionary

def get_citation_key(parent_dat: Dict[str, Any]) -> Optional[str]:
    """Gets the BBT citekey from the data dict of a zotero parent entry"""
    try:
        return extra2dict(parent_dat['extra'])['Citation Key']
    except:
        return None


def get_creator(item: Dict[str, Any]) -> str:
    """ Get a zotero parent item's "creator"

    This function extracts and formats the creator information from a Zotero item,
    which is typically retrieved using the pyzotero library.

    Args:
        item (dict): A Zotero item dictionary containing metadata.

    Returns:
        str: A formatted string representing the creator's name or "Unknown Author" if no creator is found.

    The function handles different creator types and formatting scenarios:
    1. If no creators are found, it returns "Unknown Author".
    2. For creator types like author, artist, editor, or director:
       - If a 'name' field is present, it returns that.
       - Otherwise, it formats as "LastName, FirstName".
    3. For institution or organization creator types, it returns the name or "Unknown Organization".
    4. For other creator types, it follows the same logic as point 2.
    
    TODO: robustify this by using zot.item_creator_types() and zot.item_types()"""
    
    creators = item['data'].get('creators', [])
    if not creators:
        return "Unknown Author"

    first_creator = creators[0]
    creator_type = first_creator.get('creatorType', '').lower()

    if creator_type in ['author', 'artist', 'editor', 'director']:
        if 'name' in first_creator:
            return first_creator['name']
        else:
            return f"{first_creator.get('lastName', '')}, {first_creator.get('firstName', '')}"
    elif creator_type in ['institution', 'organization']:
        return first_creator.get('name', 'Unknown Organization')
    else:
        if 'name' in first_creator:
            return first_creator['name']
        else:
            return f"{first_creator.get('lastName', '')}, {first_creator.get('firstName', '')}"
        
def get_title(item: Dict[str, Any]) -> str:
    """Get the title from a Zotero item.

    This function attempts to find the most appropriate title for a given Zotero item,
    considering various item types and their specific fields.

    Parameters:
    item (dict): A Zotero item retrieved using the pyzotero library.

    Returns:
    str: The extracted title or "Untitled Item" if no suitable title is found.

    The function checks for titles in the following order:
    1. 'title' field
    2. 'shortTitle' field
    3. Item type-specific fields:
       - Case: 'caseName'
       - Statute: 'nameOfAct'
       - Email: 'subject'
       - Interview/Podcast: 'title' or 'abstractNote'
       - Presentation: 'presentationTitle'
       - Letter: Constructs a title using 'recipient'
       - Map: 'mapTitle'

    If none of the above fields contain a title, "Untitled Item" is returned.
    """    
    data = item.get('data', {})
    
    # Check for 'title' directly
    if 'title' in data:
        return data['title']
    
    # Check for 'shortTitle'
    if 'shortTitle' in data:
        return data['shortTitle']
    
    # Check for specific item types
    item_type = data.get('itemType', '').lower()
    
    if item_type == 'case':
        return data.get('caseName', '')
    elif item_type == 'statute':
        return data.get('nameOfAct', '')
    elif item_type == 'email':
        return data.get('subject', '')
    elif item_type in ['interview', 'podcast']:
        return data.get('title', data.get('abstractNote', ''))
    elif item_type == 'presentation':
        return data.get('presentationTitle', '')
    elif item_type == 'letter':
        return f"Letter to {data.get('recipient', 'Unknown')}"
    elif item_type == 'map':
        return data.get('mapTitle', '')
    
    # If no title found, return a placeholder
    return "Untitled Item"

def normalize_url(url: str) -> str:
    """Converts to lowercase and strips trailing slashes from path."""
    parsed = urlparse(url.lower())
    return urlunparse(parsed._replace(path=parsed.path.rstrip('/')))

def normalize_string(string: str) -> str:
    """Lowercases, removes common words e.g. articles, and non-alphanumeric characters. """
    common_words = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
    string = string.lower()
    string = ''.join(c for c in string if c.isalnum() or c.isspace())
    words = string.split()
    words = [word for word in words if word not in common_words]
    return ' '.join(words)


def extract_main_title(full_title: str) -> str:
    """
    Extracts the main title from a full title string, attempting to remove trailing subtitles, authors, 
    publishers etc. by removing any substring beyond the first occurrence of typical delimiters.

    Args:
    full_title (str): The full title string to process.

    Returns:
    str: The extracted main title, stripped of leading and trailing whitespace.

    The following delimiters are tested in order: '|', ':', '--', and '. ' (period followed by a capital letter).
    It splits the title at the first occurrence of any of these delimiters.
    """
    full_title = full_title.strip()
    delimiters = r'\||:|--|\.(?=\s[A-Z])'
    parts = re.split(delimiters, full_title, 1)
    return parts[0].strip()


def match_titles(title1: str, title2: str, main_title_only: bool = True, 
                 normalize: bool =True, order_dependent: bool = True):
    """Returns a score of similarity between two title strings

    Args:
    title1 (str): The first title to compare.
    title2 (str): The second title to compare.
    main_title_only (bool): try remove subtitles, authors, ... before comparison
    normalize (bool): do standard string normalization before compare e.g. lower casing, etc.
    order_dependent (bool): word order dependent similarity 

    Return:
    float: The calculated similarity score (0,100), bigger is better

    By default, first extracts the main title from both inputs, then preprocesses them by removing common words
    and punctuation. It then uses RapidFuzz's partial_ratio or token_set_ratio to calculate the similarity between the processed titles. """

    if main_title_only:
        title1 = extract_main_title(title1)
        title2 = extract_main_title(title2)

    if normalize:
        title1 = normalize_string(title1)
        title2 = normalize_string(title2)

    if order_dependent:
        score = fuzz.partial_ratio(title1, title2)  # somewhat order dependant
        # ic(title1, title2, score)
        return score
    
    return fuzz.token_set_ratio(title1, title2) # order indepenent

def best_zotero_title_match(target_title: str, 
                            zotero_items:  List[Dict[str, Any]]) -> Tuple[Optional[dict], int]:
    """Find the title in a list of zotero items that best matches a target title, 
    return (item, score)."""

    best_score = 0
    best_match = None

    for item in zotero_items.items():
        item_title = item['data'].get('title', '')
        score = match_titles(target_title, item_title)

        if score > best_score:
            best_score = score
            best_match = item

    return best_match, best_score

def is_youtube_video(item: Dict) -> bool:
    """Returns True i a zotero DB item is a youtube video"""
    if item['data']['itemType'] == 'videoRecording':
        url = item['data'].get('url', '')
        return 'youtube.com' in url or 'youtu.be' in url
    return False

def get_youtube_video_id(url: str):
    """Extract video ID from YouTube URL"""
    video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    if video_id_match:
        return video_id_match.group(1)
    return None

def youtube2md(video_url: str, output_file: pl.Path):
    """Gets a youtube transcript and saves it in a timestamped markdown file"""
    video_id = get_youtube_video_id(video_url)
    if not video_id:
        print("Invalid YouTube URL")
        return

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)

        with open(output_file, 'w', encoding='utf-8') as file:
            for entry in transcript:
                timestamp = int(entry['start'])
                text = entry['text']
                minutes, seconds = divmod(timestamp, 60)
                timestamp_formatted = f"{minutes:02d}:{seconds:02d}"
                link = f"https://www.youtube.com/watch?v={video_id}&t={timestamp}s"
                # A blank line between chunks makes a more readable pdfXchange Editor conversion to pdf.
                # I'm not sure what happens after merge, though.
                file.write(f"[{timestamp_formatted}]({link}) {text}\n\n")
    except Exception as e:
        raise Exception(f"An error occurred: {e}")


def read_html_file(html_file: pl.Path) -> str:
    """Returns the html in an html file, with (hopefully) correct decoding."""
    with open(html_file, 'rb') as f:
        raw_data = f.read()
        try:
            detected = chardet.detect(raw_data)
            html = raw_data.decode(detected['encoding'] or 'utf-8')
        except UnicodeDecodeError:
            html = raw_data.decode('iso-8859-1')

    return html

# supposed to work on both cascade PBS and AP sites but it doesn't work well
def clean_html(html_file_path: str) -> str:
    """
    Enhanced HTML cleaner handling both AP News and Cascade PBS articles.
    But it's not great.
    """
    with open(html_file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()

    soup = BeautifulSoup(html_content, 'html.parser')

    # Try multiple content containers in order of specificity
    article = (
        # AP News specific containers
        soup.find('div', {'class': 'Article'}) or
        soup.find('div', {'data-key': 'article'}) or
        soup.find('div', {'class': 'article-body'}) or
        
        # Cascade PBS specific containers
        soup.find('div', {'class': 'pbs_email_body'}) or
        soup.find('div', {'id': 'email_body'}) or
        soup.find('div', {'class': 'content-area'}) or
        
        # Generic article containers
        soup.find('article') or
        soup.find('main')
    )
    
    # Additional fallback for Cascade PBS structure
    if not article:
        # Look for nested content structures common in PBS sites
        article = soup.find('div', {'class': ['body-content', 'main-content', 'content']})
    
    # Broader fallback with text length check
    if not article:
        potential_divs = soup.find_all('div')
        for div in potential_divs:
            text_content = div.get_text(strip=True)
            if len(text_content) > 500 and not div.find_parent('header'):
                article = div
                break

    if not article:
        print("Main article content not found!")
        return ""

    # Preserve specific PBS content structures before cleaning
    preserved_content = []
    if article:
        # Find and preserve all paragraph-like content
        preserved_content.extend(article.find_all(['p', 'div'], class_='paragraph'))
        preserved_content.extend(article.find_all('p'))
        
    # Clean unwanted elements
    unwanted_classes = [
        'RelatedStories', 'Advertisement', 'ShareBar', 'Header',
        'footer', 'nav', 'sidebar', 'menu'
    ]
    
    for class_name in unwanted_classes:
        for element in article.find_all(class_=lambda x: x and class_name.lower() in x.lower()):
            element.decompose()

    # Remove non-content elements
    for tag in article(['script', 'style', 'img', 'button', 'svg', 'iframe']):
        tag.decompose()

    # Special handling for links
    for link in article.find_all('a'):
        if link.string and len(link.string.strip()) > 0:
            link.replace_with(link.string)
        else:
            # Keep the most meaningful text content
            text_content = link.get_text(strip=True)
            if text_content:
                link.replace_with(text_content)
            else:
                link.unwrap()

    # If we preserved content earlier, reconstruct the article
    if preserved_content:
        new_article = soup.new_tag('div')
        for content in preserved_content:
            if content.get_text(strip=True):  # Only add non-empty content
                new_article.append(content)
        if new_article.get_text(strip=True):
            article = new_article

    # Final cleanup of empty elements
    for tag in article.find_all():
        if not tag.get_text(strip=True):
            tag.decompose()

    return str(article)

def html_to_pdf_wkhtmltopdf(input_file: pl.Path, output_file: pl.Path):
    """Converts and html_file into and html_file"""
    wkhtmltopdf_exe = pl.Path(r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")
    subprocess.run([str(wkhtmltopdf_exe), str(input_file), str(output_file)], check=False)

def html_to_pdf_playwright(input_html: str, output_pdf_path: pl.Path):
    """
    Converts an HTML string to a PDF file.
    Args:
        input_html (str): HTML content as a string.
        output_pdf_path (str): Path to save the generated PDF.

    Notes:
        - Requires Playwright's `sync_playwright`.
        - Does not work in Jupyter Notebook or VSCode Interactive Window.

    Example: html_to_pdf_playwright("<h1>Hello</h1>", "output.pdf")
    """

    ic(pl.Path(output_pdf_path).exists() and not os.access(output_pdf_path, os.W_OK))
    if pl.Path(output_pdf_path).exists() and not os.access(output_pdf_path, os.W_OK):
        print(f"Error: File '{output_pdf_path}' is not writable", file=sys.stderr)
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(input_html)
        page.emulate_media(media="screen")
        page.pdf(path=output_pdf_path, format="A4",
                landscape=True, margin={"top": "2cm"})
        browser.close()

def convert_html_to_pdf_subproc(html_file: pl.Path, pdf_file: pl.Path, cleaning=True):
    """Converts an html file to a pdf file, calling the converter in a subprocess. 
       Conversion uses the playwright lib, which doesn't work in an jupyter notebook or 
       vscode interactive cell.  So this function runs playwright by calling a 
       a standalone command line python script which uses playwright."""


    cleaning_arg = 'clean' if cleaning == True else 'noclean'

    result = subprocess.run(['python', str(refwrangle_dir / 'pdf_to_html_playwright_cleaned.py'), 
                             html_file, pdf_file, cleaning_arg],
                            capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(f"Subprocess Error: {result.stderr}")

def load_pickle_data(fNm: pl.Path):
    """Returns the data stored in a pickle file"""
    print(f'Reading from {fNm}...')
    with open(fNm, 'rb') as file:
        data = pickle.load(file)
    return data

def save_pickle_data(fNm: pl.Path, data):
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

def check_pdf_integrity(pdf_path):
    """Catches errors and returns them.  
       Does not capture errors like 'Ignoring wrong pointing object 255 0 (offset 0)'
       They're not exceptions."""
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            pass
        return True, None
    except Exception as e:
        return False, str(e)
    

def total_size(obj, seen=None):
    """Returns the total recursive size of an object"""
    if seen is None:
        seen = set()

    obj_id = id(obj)
    if obj_id in seen:
        return 0

    seen.add(obj_id)

    size = sys.getsizeof(obj)

    if isinstance(obj, dict):
        size += sum(total_size(k, seen) + total_size(v, seen) for k, v in obj.items())
    elif isinstance(obj, (list, tuple, set, frozenset)):
        size += sum(total_size(i, seen) for i in obj)

    return size

def is_file_big(file_path: pl.Path, min_bytes_for_big: int) -> bool:
    """Returns True if the size of the file pointed to by file_path is >= min_bytes_for_big bytes.
    Returns False if the file is smaller or doesn't exist."""

    if not isinstance(file_path, pl.Path):
        raise ValueError(f'file_path is not of type {str(pl.Path)}: {file_path}')
    
    nbytes_dest = file_path.stat().st_size if file_path.exists() else 0
    
    return nbytes_dest >= min_bytes_for_big


def make_atx_header(text: str, header_level: int) -> str:
    """
    Converts the given text into an ATX-style markdown header of the specified level.

    Args:
        text (str): The input text to be converted into a header.
        header_level (int): The desired header level (1 to 6).

    Returns:
        str: The text formatted as an ATX-style header.
    """
    if 1 <= header_level <= 6:  # Ensure valid heading level
        return f"{'#' * header_level} {text}"
    else:
        raise ValueError("header_level must be between 1 and 6.")

def setext_headers_to_atx(markdown_text: str, top_header_level: int):
    """
    Converts Setext-style headers in the given Markdown text to ATX-style headers.

    Args:
        markdown_text (str): The input Markdown text.

    Returns:
        str: The Markdown text with Setext-style headers converted to ATX-style headers.
    """
    # Convert first-level Setext headers (underlined with '-')
    markdown_text = re.sub(
        r'^(.*)\n-{2,}$',
        lambda match: make_atx_header(match.group(1), top_header_level),
        markdown_text,
        flags=re.MULTILINE
    )

    # Convert second-level Setext headers (underlined with '=')
    markdown_text = re.sub(
        r'^(.*)\n={2,}$',
        lambda match: make_atx_header(match.group(1), top_header_level+1),
        markdown_text,
        flags=re.MULTILINE
    )

    return markdown_text

def heirarch_shift_markdown_headers(markdown_text: int, top_level=None):
    """Hierarchically shifts headers so that the highest level is top_level.
    (no shift if top_level==None)
    Any levels > 6 are set to ordinary text."""
    if top_level is not None:
        if not (0 < top_level < 7):
            raise ValueError("top_level must be greater than 0 and less than 7")

    headers = re.findall(r'^(#+)\s', markdown_text, re.MULTILINE)

    if not headers or top_level is None:
        return markdown_text

    current_highest = min(len(h) for h in headers)
    shift = current_highest - top_level

    def replace_header(match):
        if (old_level := len(match.group(1))) > 6:
            return "" # fix bogus original level > 7
                             
        if (new_level := old_level - shift) > 6:
            return ""

        return '#' * new_level + ' '

    return re.sub(r'^(#+)\s', replace_header, markdown_text, flags=re.MULTILINE)

def html2md_cautious(html_input_file: pl.Path, md_output_file: pl.Path, verbose: bool = False):
    """Converts an html file to a cleaned markdown file, trying for maximum quality first,
     but if the markdown result is too short, it tries again with a more lenient cleaner."""
    
    # High qualty first
    html2md_readability(html_input_file, md_output_file, verbose)
    if is_file_big(md_output_file, MIN_BYTES_FOR_HIGH_QUALITY_HTML2MD):
        return
    
    if verbose:
        print(f'Reverting to cautious html2md for file: {str(html_input_file)}')

    html2md_BS_html_to_markdown(html_input_file, md_output_file)
    
def html2md_readability(html_input_file: pl.Path, md_output_file: pl.Path, verbose=False):
    """Converts an html file to a markdown file with readability, 
    post processed with markdownify.  This produces the cleanest and best markdown results 
    I've seen on most html files.  But occasionally, it deletes lot of the
    meaningful text, sometimes removing it entirely."""

    with open(html_input_file, 'r', encoding='utf-8') as file:
        html_content = file.read()
    if verbose:
        print(f'html_content after read: {total_size(html_content)}')

    # Reasonable settings compromise?:  Good on Klein25bidenWhatWentWrong, still bad on Anonymous24RealMedianEarnings (blank)
    doc = Document(html_content, min_text_length=100, retry_length=150)
    main_html_content = doc.summary()
    if verbose:
        print(f'main_html_content after readability doc.summary(): {total_size(main_html_content)}')

    # Remove images
    main_html_content = re.sub(r'<img[^>]*>', '', main_html_content)
    if verbose:
        print(f'main_html_content after img tag removal: {total_size(main_html_content)}')

    # Convert to markdown
    markdown_content = markdownify(main_html_content)
    if verbose:
        print(f'markdown_content after markdownify {total_size(markdown_content)}')

    markdown_content = fix_markdown_errors(markdown_content)
    if verbose:
        print(f'markdown_content after fix_markdown_errors {total_size(markdown_content)}')

    with open(md_output_file, 'w', encoding='utf-8') as file:
        file.write(markdown_content)

def normalize_odd_chars(text: str) -> str:
    """Normalize chars like in utf8 to NFKD form (compatibility decomposition).  
    Good for functions that don't handle utf8 chars, like the Johannes Kaufmann html2markdown CLI"""

    text = unicodedata.normalize('NFKD', text)
    
    # Replace common problematic characters
    replacements = {
        ''': "'",
        ''': "'",
        '"': '"',
        '"': '"',
        '…': '...',
        '—': '-',
        '–': '-',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Remove remaining non-ASCII characters
    text = re.sub(r'[^\x00-\x7F]+', '', text)
    
    return text

def preproc_BS4_lenient(html: str) -> str:
    """Preprocesses HTML content, removing images and extracting text while preserving structure.
    I haven't seen this delete meaninful text, but it sometimes leaves sequences 
    of leading and trailing link sequences and junk in the middle of some WA post articles."""

    soup = BeautifulSoup(html, features="html.parser")

    # Remove unwanted elements, including images
    for element in soup(['style', 'script', 'head', 'title', 'meta', '[document]', 'img']):
        element.decompose()

    def extract_text(element):
        """Extracts text, while preserving important structural elements"""
        if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a']:
            return str(element)
        elif element.name == 'p':
            return element.get_text() + '\n\n'
        else:
            return element.get_text()

    # Extract text while preserving heading and paragraph structure
    extracted_text = ''
    for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'a']):
        extracted_text += extract_text(element)

    # Clean up extra whitespace (does this remove too much whitespace?)
    # extracted_text = ' '.join(extracted_text.split())

    return extracted_text

def html2md_BS_html_to_markdown(input_html_file: pl.Path, output_md_file: pl.Path):
    """Converts an html file into a markdown file, using lenient BeautifulSoup html
    preprocessing, then converting to markdown with Johannes Kaufmann's html2markdown CLI.
    The result is usually fairly clean markdown text, occasionally with some leftover junk.
    I haven't seen it delete any meaninful text.
    
    Requires commandline install:
    - [repo](https://github.com/JohannesKaufmann/html-to-markdown)
    - install: `winget install html-to-markdown`
    """

    with open(input_html_file, 'r', encoding='utf-8') as infile:
        input_data = infile.read()

    input_data = preproc_BS4_lenient(input_data)

    # html2markdown doesn't like some utf8 chars
    processed_input = normalize_odd_chars(input_data)

    process = subprocess.Popen(['html2markdown'],
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

    # If htmlmarkdown doesn't handle utf8 (what I've seen), I don't know why
    # utf8'ing it on input and output is necessary.  But it's recommended by some.
    stdout, stderr = process.communicate(processed_input.encode('utf-8'))

    if stderr:
        raise Exception("html2markdown encountered an error", stderr.decode('utf-8'))

    output = stdout.decode('utf-8')

    # Write the output to the file
    with open(output_md_file, 'w', encoding='utf-8') as outfile:
        outfile.write(output)

def remove_weird_len_md_headers(markdown_text: str) -> str:
    """Remove out-of-range length headers in markdown text."""

    lines = markdown_text.split('\n')
    corrected_lines = []
    for line in lines:
        line_len = len(line.split())
        if re.match(r'^#+\s', line) and not 3 <= line_len <= 13:
            corrected_lines.append(line.lstrip('#').strip())
        else:
            corrected_lines.append(line)
    return '\n'.join(corrected_lines)

def fix_markdown_errors(content: str) -> str:
    """
    Fix the following markdown errors:
    1. Unclosed '*'
    2. Unclosed '**'
    3. weird length markdown headers
    4. Skipped header levels
    5. Unclosed inline code blocks
    """
    # Fix unclosed '*' and '**'
    def fix_emphasis(content):
        lines = content.split("\n")
        fixed_lines = []
        open_single = False
        open_double = False

        for line in lines:
            # Handle '**' first to avoid interfering with single '*'
            if line.count("**") % 2 != 0:
                if open_double:
                    line += "**"  # Close double asterisks
                    open_double = False
                else:
                    line = line + "**"  # Open double asterisks
                    open_double = True

            # Handle single '*', but exclude cases where '**' is present
            if line.count("*") % 2 != 0 and "**" not in line:
                if open_single:
                    line += "*"  # Close single asterisk
                    open_single = False
                else:
                    line = line + "*"  # Open single asterisk
                    open_single = True

            fixed_lines.append(line)

        return "\n".join(fixed_lines)

    # Fix skipped header levels
    def fix_header_levels(content):
        lines = content.split("\n")
        fixed_lines = []
        last_header_level = 0

        for line in lines:
            if line.startswith("#"):
                current_level = line.count("#")
                if last_header_level and current_level > last_header_level + 1:
                    line = "#" * (last_header_level + 1) + " " + line.lstrip("#").strip()
                last_header_level = current_level

            fixed_lines.append(line)

        return "\n".join(fixed_lines)

    # Fix unclosed inline code blocks
    def fix_inline_code(content):
        lines = content.split("\n")
        fixed_lines = []
        open_backtick = False

        for line in lines:
            if line.count("`") % 2 != 0:
                if open_backtick:
                    line += "`"  # Close backtick
                    open_backtick = False
                else:
                    line += "`"  # Open backtick (added at the end for simplicity)
                    open_backtick = True

            fixed_lines.append(line)

        return "\n".join(fixed_lines)

    # Apply all fixes in sequence
    content = fix_emphasis(content)
    content = remove_weird_len_md_headers(content)
    content = fix_header_levels(content)
    content = fix_inline_code(content)

    return content

def pdf2md_pymupdf4llm(input_pdf: pl.Path, output_md: pl.Path):
    "Reads a pdf file and writes it as utf-8 markdown"    

    md_text = pymupdf4llm.to_markdown(input_pdf, write_images=False,
                                      show_progress=False)
    
    md_text = fix_markdown_errors(md_text)
    
    pl.Path(output_md).write_bytes(md_text.encode()) # encode w/ no args uses utf-8

def bin_items_FFD(item_weights: list, max_bin_weight: float) -> pd.DataFrame:
    """
    Allocates items to bins, with the goal of the most equal bin packing with no bin exceeding max_bin_weight
    Uses the First-Fit Decreasing (FFD) bin packing algorithm.

    Parameters:
    - item_weights: List of item weights to be packed.
    - max_bin_weight: Maximum weight capacity of each bin.

    Returns:
    - bins: A dataframe, with a row for each allocated bin

    Raises:
    - ValueError: If any item's weight exceeds the max_bin_weight.
    """

    if any(item_weight > max_bin_weight for item_weight in item_weights):
        raise ValueError("A item's weight exceeds the maximum allowed weight limit.")

    # Sort in descending order by weight, returned tuples are (orig_index, weight)
    sorted_weights = sorted(enumerate(item_weights), key=lambda x: x[1], reverse=True)

    # Place each item into the first available bin that can accommodate it
    item_index_bins = []  # each bin contains original item indices
    total_weight_bin = [] # total weight of items in bin

    for item_index_orig, item_weight in sorted_weights:  # Heaviest item first
        # Put item in the 1st bin that fits
        placed = False
        for binIx, bin_weight in enumerate(total_weight_bin):  
            if bin_weight + item_weight <= max_bin_weight:
                item_index_bins[binIx].append(item_index_orig) # Fits: add it to this bin
                total_weight_bin[binIx] += item_weight
                placed = True
                break

        if not placed:
            # Doesn't fit: put it in a newly made bin
            item_index_bins.append([item_index_orig])
            total_weight_bin.append(item_weight)

    return pd.DataFrame(dict(item_indices=item_index_bins, weights=total_weight_bin))    

def count_words_in_markdown(content: str) -> int:
    """Count the words in the content (string) of a markdown file"""
    # Remove markdown syntax to focus on the text content
    import re
    text_only = re.sub(r'[\*\#\[\]\(\)\!\`\>\-]', '', content)
    # Split the text into words and count them
    words = text_only.split()
    return len(words)


### Version 3: extra debugging
def sanitize_markdown_before_reportlab(md_text: str) -> str:
    """
    Fixes Markdown content to ensure compatibility with ReportLab's paragraph parser.
    This includes rewriting problematic Markdown syntax, escaping special characters,
    and sanitizing unsupported HTML tags or attributes.
    """

    # 1. Convert setext headings (underlined with === or ---) into ATX (#) headings
    lines = md_text.split("\n")
    out_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if i < len(lines) - 1:
            next_line = lines[i + 1]
            if re.match(r"^=+\s*$", next_line):  # Level-1 heading
                out_lines.append("# " + line.strip())
                i += 2
                continue
            elif re.match(r"^-+\s*$", next_line):  # Level-2 heading
                out_lines.append("## " + line.strip())
                i += 2
                continue
        out_lines.append(line)
        i += 1

    fixed_md = "\n".join(out_lines)

    # 2. Escape special characters (<, >, &) to prevent parsing issues
    fixed_md = fixed_md.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # 3. Use BeautifulSoup to sanitize HTML content
    soup = BeautifulSoup(fixed_md, "html.parser")

    # Remove unsupported tags (e.g., <img>, <script>)
    for tag in soup.find_all(["img", "script"]):
        tag.decompose()

    # Remove or rewrite invalid attributes (e.g., rel="nofollow", onerror)
    for tag in soup.find_all(True):  # True matches all tags
        attrs_to_remove = []
        for attr in tag.attrs:
            if attr not in ["href", "src", "alt", "title", "style"]:  # Whitelisted attributes
                attrs_to_remove.append(attr)
        for attr in attrs_to_remove:
            del tag[attr]

    # Ensure proper nesting of tags (BeautifulSoup handles this automatically)

    # Convert back to a string and return the sanitized Markdown
    sanitized_html = str(soup)
    
    return sanitized_html

def remove_unsupported_html_tags(html_content: str) -> str:
    """Clean HTML to only include supported tags and attributes"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Define allowed tags and their allowed attributes
    ALLOWED_TAGS = {
        'p': [],
        'h1': [], 'h2': [], 'h3': [], 'h4': [], 'h5': [], 'h6': [],
        'b': [], 'strong': [],
        'i': [], 'em': [],
        'u': [],
        'br': []
    }
    
    def clean_tag(tag):
        if tag.name not in ALLOWED_TAGS:
            # Convert unsupported tags to paragraph
            tag.name = 'p'
        else:
            # Remove unsupported attributes
            allowed_attrs = ALLOWED_TAGS[tag.name]
            attrs = dict(tag.attrs)
            for attr in attrs:
                if attr not in allowed_attrs:
                    del tag.attrs[attr]
        
        # Clean children
        for child in tag.children:
            if hasattr(child, 'name') and child.name:
                clean_tag(child)
    
    # Clean all tags
    for tag in soup.find_all(True):
        clean_tag(tag)
    
    return str(soup)


def md2pdf_markdown_reportlab(markdown_data: str, output_file: pl.Path, verbose: bool = False) -> None:
    """Convert markdown to PDF with debug information.""" 
    try:
        # Register Verdana font family
        pdfmetrics.registerFont(TTFont('Verdana', 'Verdana.ttf'))
        pdfmetrics.registerFont(TTFont('VerdanaItalic', 'Verdanai.ttf'))
        pdfmetrics.registerFont(TTFont('VerdanaBold', 'Verdanab.ttf'))
        pdfmetrics.registerFont(TTFont('VerdanaBoldItalic', 'Verdanaz.ttf'))
        
        pdfmetrics.registerFontFamily('Verdana',
            normal='Verdana',
            bold='VerdanaBold',
            italic='VerdanaItalic',
            boldItalic='VerdanaBoldItalic'
        )
        
        if verbose:
            print("Converting markdown to HTML...")
        sanitized_markdown_data = sanitize_markdown_before_reportlab(markdown_data)
        html = markdown.markdown(sanitized_markdown_data)
        
        if verbose:
            print("Cleaning HTML of unsupported tags...")
        cleaned_html = remove_unsupported_html_tags(html)
        
        if verbose:
            print("Parsing cleaned HTML...")
        soup = BeautifulSoup(cleaned_html, 'html.parser')
        
        if verbose:
            print("Creating PDF document...")
        doc = SimpleDocTemplate(str(output_file), pagesize=letter)
        styles = getSampleStyleSheet()
        
        # Configure styles
        styles['Normal'].fontName = 'Verdana'
        for i in range(1, 7):
            style_name = f'CustomHeading{i}'
            styles.add(
                ParagraphStyle(
                    style_name,
                    parent=styles['Heading1'],
                    fontName='Verdana',
                    fontSize=20 - 2*i,
                    spaceAfter=12
                )
            )
        
        story = []
        
        def process_element(element):
            if verbose:
                print(f"Processing element: {element.name if element.name else 'text'}")
            
            try:
                if element.name and element.name.startswith('h') and element.name[1:].isdigit():
                    heading_level = int(element.name[1:])
                    text = escape(element.get_text())
                    para = Paragraph(text, styles[f'CustomHeading{heading_level}'])
                    story.append(para)
                elif element.name == 'p':
                    text = escape(''.join(str(child) for child in element.contents))
                    para = Paragraph(text, styles['Normal'])
                    story.append(para)
                
                for child in element.children:
                    if hasattr(child, 'name') and child.name:
                        process_element(child)
                        
            except Exception as e:
                if verbose:
                    print(f"Error processing element {element.name}: {str(e)}")
                    traceback.print_exc()
                raise
        
        if verbose:
            print("Processing HTML elements...")
        for element in soup.find_all(recursive=False):
            process_element(element)
            
        if verbose:
            print(f"Building PDF with {len(story)} elements...")
        doc.build(story)
        
        if verbose:
            print(f"PDF successfully created at {output_file}")
            
    except Exception as e:
        if verbose:
            print(f"Error creating PDF: {str(e)}")
            print("Full traceback:")
            traceback.print_exc()
        raise


def merge_pdfs_with_structure(pdfs_info: List[Dict[str, Any]], output_path: pl.Path) -> List[Dict[str, str]]:
    """Merge pdfs into a single pdf, intended to have RAG-friendly page and bookmark structure
    Perplexity:
      https://www.perplexity.ai/search/fix-the-bug-in-the-code-below-plw_2PR4TUWH6xqSZ7M_nQ#27"""

    writer = PdfWriter()
    
    # Add title page first
    pdf_files = [pdf_info['file'] for pdf_info in pdfs_info]
    create_title_page(writer, pdf_files)
        
    current_page = 1
    problematic_pdfs = []
    
    for i, pdf_path in enumerate(pdf_files, 1):
        is_valid, error_message = check_pdf_integrity(pdf_path)
        if not is_valid:
            print(f"Skipping {pdf_path} Error: {error_message}")
            problematic_pdfs.append(dict(pdf_path=pdf_path, error_message=error_message))
            continue

        pdf_basename = os.path.basename(pdf_path).split('.')[0]
        full_path = os.path.abspath(pdf_path)
        
        add_separator_page(writer, pdf_basename, full_path, pdfs_info[i-1]['metainfo'])
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

    return problematic_pdfs

def capitalize_first_word_if_needed(text: str) -> str:
    """
    Capitalizes the first letter of the first word in the given text if it is not already capitalized.

    Args:
        text (str): The input string to process.

    Returns:
        str: The original string if the first word contains any uppercase letters,
             otherwise a new string with the first letter of the first word capitalized.
    """
    first_word = text.split()[0] if text.strip() else ""
    if any(char.isupper() for char in first_word):
        return text  # Return the original string if the first word has capitals
    else:
        return text[0].upper() + text[1:] if text else text


def get_first_n_words(text: str, n: int, stop_phrase: Optional[str] = None) -> str:
    """
    Extracts the first n words from the given text, optionally stopping at a specified phrase.

    Args:
        text (str): The input text to process.
        n (int): The number of words to extract.
        stop_phrase (str, optional): A phrase at which to stop extraction if encountered.

    Returns:
        str: The first n words of the text, or the text up to the stop phrase if encountered.
    """
    if stop_phrase and stop_phrase in text:
        text = text.split(stop_phrase)[0]
    
    words = text.split()
    return ' '.join(words[:n])

def summarize_prompt(prompt: str, num_words: int, stop_phrase: str, heading_level) -> str:
    """Makes a heading that summarizes a prompt string."""
    prompt = get_first_n_words(prompt, num_words, stop_phrase)
    return make_atx_header(f'User: "{capitalize_first_word_if_needed(prompt)}..."', heading_level)
