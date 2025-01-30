# HTML to PDF with clickable link to original html in the header
# 
# THIS WORKS, although it leaves much extraneous links in WA post pages, and prints out fontconfig warnings all the time.

import pathlib as pl
from icecream import ic
import urllib.parse
import os
import refwrangle as rfw


# Set paths to GTK and Fontconfig
os.environ['FONTCONFIG_FILE'] = str(pl.Path('./fonts.conf').resolve())
os.environ['WEASYPRINT_DLL_DIRECTORIES'] = r"C:\Program Files\GTK3-Runtime Win64\bin"

# # fontconfig file required by weasyprint and others
# os.environ['FONTCONFIG_FILE'] = str(pl.Path(r'./fonts.conf').resolve()) # avoid error messages
# fontconfig_file = os.envairon.get('FONTCONFIG_FILE', None)
# if not pl.Path(fontconfig_file).exists():
#     raise Exception(f"fontconfig file doesn't exist at {fontconfig_file}")

# # Fontconfig success also requires GTK+: winget install --id=tschoonj.GTKForWindows -e
# if not any('gtk' in path.lower() for path in os.environ['PATH'].split(os.pathsep)):
#     raise Exception('GTK+ is not in path')

# These imports after fontconfig configuration
from weasyprint import HTML, CSS # after fontconfig setup to avoid error messages
from bs4 import BeautifulSoup

# def clean_html(html_file_path):
#     """
#     Cleans and extracts the main content from a downloaded HTML file by targeting
#     broader structures if specific tags or classes are not found.  From GPt-4o.
#     OK on my 3 test cases.a  WA post still has tons of textified links.

#     Args:
#         html_file_path (str or pathlib.Path): Path to the HTML file.

#     Returns:
#         str: Cleaned HTML content.
#     """
#     # Step 1: Load the HTML file
#     with open(html_file_path, 'r', encoding='utf-8') as file:
#         html_content = file.read()

#     # Step 2: Parse with BeautifulSoup
#     soup = BeautifulSoup(html_content, 'html.parser')

#     # Step 3: Try to locate the main content
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

#     # Step 4: Remove unwanted tags from the article content
#     for tag in article(['script', 'style', 'img', 'button']):
#         tag.decompose()

#     # Step 5: Simplify links by replacing <a> tags with their text content
#     for link in article.find_all('a'):
#         link.replace_with(link.text)

#     # Step 6: Remove empty tags
#     for tag in article.find_all():
#         if not tag.text.strip():
#             tag.decompose()

#     # Step 7: Return cleaned HTML as a string
#     return str(article)
# ------------------------------------------------------------------

def html_to_pdf(cleaned_html, output_pdf_path, basename, file_path):
    """
    Convert HTML to PDF with a clickable header link.

    Args:
        cleaned_html (str): Main HTML content.
        output_pdf_path (str): Output PDF file path.
        basename (str): Filename for header display.
        file_path (Path): Original file path for header link.

    Returns:
        The return value of weasyprint.HTML().write_pdf().
    """
    # URI format for clickable link
    file_uri = urllib.parse.urljoin('file:', urllib.parse.quote(str(file_path.absolute())))
    
    # Create the HTML content with running header containing the link
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            @page {{
                size: A4;
                margin: 1in;
            }}
            #header {{
                position: running(header);
                text-align: right;
                font-size: 10pt;
            }}
            #header a {{
                color: blue;
                text-decoration: underline;
            }}
            @page {{
                @top-right {{
                    content: element(header);
                }}
            }}
        </style>
    </head>
    <body>
# URI format for clickable link
    file_uri = urllib.parse.urljoin('file:', urllib.parse.quote(str(file_path.absolute())))
        
        <div id="header">
            <a href="{file_uri}">{basename}</a>
        </div>
        {cleaned_html}
    </body>
    </html>
    """
    
    HTML(string=html_content).write_pdf(output_pdf_path)

def html_to_clean_pdf(input_html_path, output_pdf_path):
    """
    Process HTML file to PDF with cleaning and conversion.

    Args:
        input_html_path (Path): Path to input HTML file.
        output_pdf_path (Path): Path for output PDF file.
    """
    cleaned_html = rfw.clean_html(input_html_path)
    #ic(cleaned_html)
    basename = input_html_path.stem
    html_to_pdf(cleaned_html, output_pdf_path, basename, input_html_path)
    #print(f"PDF successfully generated at {output_pdf_path}")

# Example usage
if __name__ == "__main__":
    #html_file_path = pl.Path(r"C:\Users\scott\OneDrive\share\ref\refwrangle\test\Dionne24hiddenVictoryProgrssiv.html")
    hpath = pl.Path(r'C:/Users/scott/OneDrive/share/ref/obsidian/Obsidian Share Vault/lit/lit_sources/')

    html_file_path = hpath / 'Tumulty24FrischLearnedDemsShould.html'  # complex WA post page works, but leaves much junk, links, etc.
    #html_file_path = hpath / 'Walther24barstoolConservatism.html'     # works
    #html_file_path = hpath / 'Yan24berkeleyFuncCallLeaderBrd.html'     # utf-8 fail

    output_pdf_path = pl.Path("./tmp_textonly.pdf")
    html_to_clean_pdf(html_file_path, output_pdf_path)