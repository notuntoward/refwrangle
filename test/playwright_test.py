from playwright.sync_api import sync_playwright
import pathlib as pl
import sys
from icecream import ic

refwrangle_dir = pl.Path('~/ref/refwrangle').expanduser() # can't reliably get dir of your .ipynb 

sys.path.append(str(refwrangle_dir))
import refwrangle as rfw
from icecream import ic

test_dir = refwrangle_dir / 'test'
pdf_file = test_dir / 'tmp_playwright.pdf'

#html_file = test_dir / 'Dionne24hiddenVictoryProgrssiv.html'

hbasename = 'ODonnel24newsEngageTrumpWin.html'
hbasename = 'Yan24berkeleyFuncCallLeaderBrd.html'     # works now, used to fail on all b/c .html was corrupt
hbasename = 'Tumulty24FrischLearnedDemsShould.html'
html_file = rfw.lit_attachment_dir_shared / hbasename

html_file_uri = pl.Path(html_file).as_uri()

print(f'writing to {pdf_file}')

with sync_playwright() as p:
    # create a browser instance
    browser = p.chromium.launch()

    # open a new tab in the browser
    page = browser.new_page()

    # goto the URL of the HTML page
    page.goto(html_file_uri)

    # change css media type to screen
    page.emulate_media(media="screen")

    # print the html page as pdf in the browser
    page.pdf(path=pdf_file, format="A4",
             landscape=True, margin={"top": "2cm"})
    
    # close the browser
    browser.close()

print("Done.")