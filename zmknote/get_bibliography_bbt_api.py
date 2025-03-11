# This works.
# See: https://retorque.re/zotero-better-bibtex/exporting/json-rpc/index.html
# See: https://www.perplexity.ai/search/can-pyzotero-get-a-bibliograph-GOBZjDewTvOsa0uKBnB2Tw
# See: https://www.zotero.org/styles?q=idb%3Amodern-language-association

import sys
import pathlib as pl

# Define paths and credentials
refwrangle_dir = pl.Path('~/ref/refwrangle').expanduser()
sys.path.append(str(refwrangle_dir))
import refwrangle as rfw  # Import your custom refwrangle module

item_key = 'Dale19CompleteGuideBulgSquat'    
bib = rfw.get_bibliography_bbt_api(item_key)
print(f'{item_key=}: {bib=}')
