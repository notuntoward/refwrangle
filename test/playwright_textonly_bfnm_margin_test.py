'''HTML to PDF with html basename in the margin.  
But there is quite a bit of cruft in there from the original web page, and I guess, based on web searches, 
RAG doen't like that, so I went to the weasyprint methods in other files.'''

import asyncio
from playwright.async_api import async_playwright
from fpdf import FPDF
import pathlib as pl
import anyascii

class CustomPDF(FPDF):
    def __init__(self, basename, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.basename = basename  # Store the basename for use in headers/footers

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Set font for footer
        self.set_font("Arial", "I", 8)
        # Add the basename on the right margin
        self.cell(0, 10, f"{self.basename}", 0, 0, "R")

async def extract_article_text_and_save_to_pdf(html_file_path, output_pdf_path):
    async with async_playwright() as p:
        # Launch a headless browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Load the local HTML file
        html_file_url = f"file://{html_file_path}"
        await page.goto(html_file_url)

        # Wait for the page to load completely
        await page.wait_for_load_state("domcontentloaded")

        # Extract the article content using selectors (adjust as needed)
        try:
            # Look for the <article> tag or specific divs containing the main content
            article_element = await page.query_selector("article")
            if not article_element:
                raise Exception("No <article> tag found. Adjust your selector.")
            
            # Extract text content from the article
            article_text = await article_element.inner_text()
            
        except Exception as e:
            print(f"Error extracting article text: {e}")
            await browser.close()
            return

        # Close the browser after extraction
        await browser.close()

        # Get the basename of the HTML file
        basename = pl.Path(html_file_path).stem

        # Save the extracted text to a PDF with a custom footer
        save_text_to_pdf(article_text, output_pdf_path, basename)
        print(f"PDF saved at {output_pdf_path}")

def save_text_to_pdf(text, output_pdf_path, basename):
    # Create a PDF object using CustomPDF with the basename
    pdf = CustomPDF(basename=basename)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Add the extracted text to the PDF
    for line in text.split("\n"):
        line = anyascii.anyascii(line)  # Ensure non-latin-1 characters are converted properly
        pdf.multi_cell(0, 10, line)

    # Save the PDF to a file
    pdf.output(output_pdf_path)

# Paths to your input HTML file and output PDF file
html_file_path = pl.Path(r"C:\Users\scott\OneDrive\share\ref\refwrangle\test\Dionne24hiddenVictoryProgrssiv.html")
output_pdf_path = pl.Path("./tmp_textonly.pdf")

# Run the function asynchronously
asyncio.run(extract_article_text_and_save_to_pdf(html_file_path, output_pdf_path))