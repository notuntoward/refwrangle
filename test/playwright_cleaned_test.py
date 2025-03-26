
# %%
# Test playwright html --> pdf conversion with html clean preprocessing.
# Playwrite can't be run inside of a vscode interactive cell or a jupyter notebook
# (I have tired all the things, and the final answer is "NO.") so this also
# tests a standalone script which runs in a subprocess.

import pathlib as pl
import sys

# %%
refwrangle_dir = Path(__file__).resolve().parent.parent # works??
#refwrangle_dir = pl.Path('~/ref/refwrangle').expanduser() # can't reliably get dir of your .ipynb 
sys.path.append(str(refwrangle_dir))
import refwrangle as rfw

test_dir = refwrangle_dir / 'test'
pdf_file = test_dir / 'tmp_playwright_clean.pdf'

# a common theme is that the failures are from AP articles
#hpath = pl.Path(r'C:/Users/scott/OneDrive/share/ref/obsidian/Obsidian Share Vault/lit/lit_sources/')
hbasename = 'Dionne24hiddenVictoryProgrssiv.html'
hbasename =  'Tumulty24FrischLearnedDemsShould.html'  # works, but complex WA post page still has tons of extraneous link junk
hbasename = 'Walther24barstoolConservatism.html'     # works
hbasename = 'Yan24berkeleyFuncCallLeaderBrd.html'     # works now, used to fail on all b/c .html was corrupt
hbasename =  'Wong24harrisQuietStudentLoans.html' # couldn't fix.  Printed pdf
hbasename = 'Pastor24greatBidenEconHelpedTrump.html' # couldn't fix.  Printed pdf
hbasename = 'Brown24yngBlkLatMenTrump.html' # couldn't fix.  Printed pdf
hbasename = 'Sanders24demoGroups5Voted.html' # works after AP fix
hbasename = 'Blankinship24waElectSumryYouth.html' # couldn't fix, made pdf
hbasename = 'PBS24keyVoteGroupsInteract.html' # couldn't fix, made pdf
hbasename = 'Shamim24whyHarrisLoseWomen.html' # couldn't fix, made pdf
hbasename = 'Eiche24votersReadyHarrisSexist.html' # totally blank. couldn't fix, made pdf
hbasename = 'Balz24demsReckonRebuild.html'# mostlyf blank. couldn't fix, made pdf
hbasename = 'Kane24ColumnDemocratsDid.html'# mostlyf blank. couldn't fix, made pdf
hbasename = 'Bacon24harrisAdvisersBlame.html'# mostlyf blank. couldn't fix, made pdf
hbasename = 'Klein24itsCorruptionStupid.html'

html_file = rfw.lit_attachment_dir_shared / hbasename

print(f'\nReading "{html_file}"\n')
    
# %%

print(f'Writing to {pdf_file}')

test_subproc = True
cleaning = False
if test_subproc:
    rfw.convert_html_to_pdf_subproc(html_file, pdf_file, cleaning)
else:
    # Runs same code as is run in rfw.convert_html_to_pdf_subproc()
    # (easier to debug here than in a subprocess)
    cleaned_html = rfw.clean_html(html_file)
    rfw.html_to_pdf_playwright(cleaned_html, pdf_file)

print("Done.")

# %%
