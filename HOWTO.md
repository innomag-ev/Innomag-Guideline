# HOW TO

This repository is set up for use with quarto. Install quarto, then render english and german versions:
  - quarto render de
  - quarto rende en

They end up in respective _site/de and _site/en folders as
  - index.html
  - Innomag-Guideline-de.pdf

2 scripts for modification of the pfd:
  1. "script_pdf_image_compression": compresses to 220 dpi attempting to go below 5 MB on the web pdf document. This creates Innomag-Guideline-de-web.pdf in the /de folder. This script runs automatically with github workflow for offering the web-pdf
  2. "script_prepare_print_version.py": will take the existing quarto-formated pdf (should be high quality without compressed images) and bring it to "wir-machen-druck" requested print format. It is stored at top level as "Innomag-Guideline-de-print.pdf"