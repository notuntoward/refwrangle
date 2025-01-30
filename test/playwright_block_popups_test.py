from playwright.sync_api import sync_playwright
import pathlib
import os

# Convert a relative path of a local file into an absolute path
filePath = os.path.abspath(r"C:\Users\scott\OneDrive\share\ref\refwrangle\test\Dionne24hiddenVictoryProgrssiv.html")

# Derive the URL path of a local file to be opened in the browser
fileUrl = pathlib.Path(filePath).as_uri()

# Print the file as a PDF from Chromium browser using Playwright
with sync_playwright() as p:
    # Create a browser instance
    browser = p.chromium.launch()

    # Open a new tab in the browser
    page = browser.new_page()

    # Inject JavaScript to block popups before navigating to the page
    page.add_init_script("""
        // Override alert, confirm, and prompt to suppress popups
        window.alert = () => {};
        window.confirm = () => true; // Automatically "accepts" confirmations
        window.prompt = () => null; // Suppresses prompts and returns null

        // Override window.open to prevent opening new tabs/windows
        window.open = () => null;

        // Optionally, remove specific popup-related elements from the DOM
        document.addEventListener('DOMContentLoaded', () => {
            const popupElements = document.querySelectorAll('.popup, .modal, .ads'); // Example selectors for popups
            popupElements.forEach(el => el.remove());
        });
    """)

    # Go to the URL of the HTML page
    page.goto(fileUrl)

    # Change CSS media type to screen
    page.emulate_media(media="screen")

    # Print the HTML page as a PDF in the browser
    page.pdf(path="./tmp_nopoups.pdf", format="A4", landscape=True, margin={"top": "2cm"})

    # Close the browser
    browser.close()