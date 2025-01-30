# WORKS.  But lots of link junk what would look like normal article text to a RAG

import asyncio
from playwright.async_api import async_playwright
from fpdf import FPDF
import pathlib as pl
import anyascii

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

        # Save the extracted text to a PDF
        save_text_to_pdf(article_text, output_pdf_path)
        print(f"PDF saved at {output_pdf_path}")

def save_text_to_pdf(text, output_pdf_path):
    # Create a PDF object using FPDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Add the extracted text to the PDF
    for line in text.split("\n"):
        # added to avoid the latin-1 ero
        # puts in '?' for non-latin-1
        #line = line.encode('latin-1', 'replace').decode('latin-1')
        # finds a better substitue for non-latin-1
        line = anyascii.anyascii(text)
        pdf.multi_cell(0, 10, line)

    # Save the PDF to a file
    pdf.output(output_pdf_path)


hpath = pl.Path(r'C:/Users/scott/OneDrive/share/ref/obsidian/Obsidian Share Vault/lit/lit_sources/')

html_file_path = hpath / 'Tumulty24FrischLearnedDemsShould.html'  # works, but complex WA post page has tons of extraneous link junk
#html_file_path = hpath / 'Walther24barstoolConservatism.html'     # works
#html_file_path = hpath / 'Yan24berkeleyFuncCallLeaderBrd.html'     # works now, used to fail on all b/c .html was corrupt

#html_file_path = "/path/to/your/downloaded.html"  # Replace with your HTML file path
output_pdf_path = pl.Path("./tmp_playwright_textonly.pdf")   # Replace with desired PDF output path

# Run the function asynchronously
asyncio.run(extract_article_text_and_save_to_pdf(html_file_path, output_pdf_path))