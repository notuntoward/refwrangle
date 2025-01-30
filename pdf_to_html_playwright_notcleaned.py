#!/usr/bin/env python3
import pathlib as pl
import sys
import argparse

# Cleans non-RAG-friendly stuff out of an html file and converts it into a pdf.
# Does it in this command-line script because the playwright lib can't be run in a
# Jupyter notebook, or a vscode interactive shell.  I want to be able to develop the
# callers in a notebook; putting the playwrite-calling code in a command line script
# and running it as a subprocess is the easiest alternative.
#
# playwright_cleaned_test.py can be used to test this, and to debug the functions called here.

def main():
    parser = argparse.ArgumentParser(description='Convert HTML to PDF with cleaning')
    parser.add_argument('html_file', help='Input HTML file path')
    parser.add_argument('pdf_file', help='Output PDF file path')
    args = parser.parse_args()
    
    # this hardcoding is a bummer
    refwrangle_dir = pl.Path('~/ref/refwrangle').expanduser()
    sys.path.append(str(refwrangle_dir))
    import refwrangle as rfw

    cleaned_html = rfw.clean_html(args.html_file)
    rfw.html_to_pdf_playwright(cleaned_html, args.pdf_file)

if __name__ == "__main__":
    main()
