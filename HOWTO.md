# HOW TO

This repository is set up for use with quarto. Render english and german versions:
- quarto render de
- quarto rende en

They end up in respective _site/de and _site/en folders like
- index.html
- Innomag-Guideline-de.pdf

On Github the workflow runs "script_pdf_image_compression" and compresses to 220 dpi attempting to go below 5 MB on the web pdf document. This will replace Innomag-Guideline-de.pdf

Locally one can choose to run "script_pdf_image_compression" for testing.

"script_book_mergeA4covers.py" will take the existing quarto-formated pdf (should be high quality without compressed images) and bring it to "wir-machen-druck" requested print format.