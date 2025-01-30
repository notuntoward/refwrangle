# On wapost articles, I get popups blocking the article text.  This was an attempt to stop this, but I stll see the "for you" popup from wapost.

from playwright.sync_api import sync_playwright
import os
import pathlib

# Path to your local HTML file
file_path = os.path.abspath(
    r"C:\Users\scott\OneDrive\share\ref\refwrangle\test\Dionne24hiddenVictoryProgrssiv.html"
)
file_url = pathlib.Path(file_path).as_uri()

# List of ad-related domains or patterns to block (customizable)
ad_block_list = [
    "doubleclick.net",
    "googlesyndication.com",
    "adservice.google.com",
    "ads.youtube.com",
    "facebook.com/ads",
    "adroll.com",
    "taboola.com",
    "outbrain.com",
    "nytimes.com",
    "washingtonpost.com"
]

def is_ad_request(url):
    """Check if the request URL matches any domain in the ad block list."""
    return any(ad_domain in url for ad_domain in ad_block_list)

# Main script
with sync_playwright() as p:
    # Launch browser
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # Intercept and block ad-related requests
    page.route("**/*", lambda route: route.abort() if is_ad_request(route.request.url) else route.continue_())

    # Navigate to the local HTML file
    page.goto(file_url)

    # Perform operations (e.g., generate PDF)
    page.emulate_media(media="screen")
    page.pdf(path="./tmp_nopopups_noads.pdf", format="A4", landscape=True, margin={"top": "2cm"})

    # Close the browser
    browser.close()