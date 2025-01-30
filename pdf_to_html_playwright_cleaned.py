#!/usr/bin/env python3
import pathlib as pl
import sys
import argparse

# this hardcoding is a bummer
refwrangle_dir = pl.Path('~/ref/refwrangle').expanduser()
sys.path.append(str(refwrangle_dir))
import refwrangle as rfw # assumed to be in same dir as this

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
    parser.add_argument('cleaning', help="'clean': clean html; 'noclean': don'tPDF file path")
    args = parser.parse_args()
    
    if args.cleaning == 'clean':
        html = rfw.clean_html(args.html_file) # might be broken now
    elif args.cleaning == 'noclean':
        html = rfw.read_html_file(args.html_file)
    else:
        print("Error: unknown cleaning argument: {args.cleaning}")
        sys.exit(64)  # EX_USAGE - command line usage error
    
    rfw.html_to_pdf_playwright(html, args.pdf_file)

if __name__ == "__main__":
    main()
