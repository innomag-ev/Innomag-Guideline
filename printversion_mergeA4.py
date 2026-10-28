"""
Create INNOMAG hardcover print PDF from Quarto output.

Input:
    _site/de/Innomag-Guideline-de.pdf

Output:
    Innomag-Guideline-de-print.pdf

Page 1:
    Hardcover spread: 468 x 332 mm
    Back cover + 8 mm spine + front cover
    15 mm bleed

Pages 2-77:
    76 interior pages: 216 x 303 mm
    3 mm bleed

Install:
    python -m pip install pymupdf

Run:
    python innomag_make_print_pdf.py
"""

from pathlib import Path
import sys
import pymupdf as fitz

# -------------------------------------------------------
# Files
# -------------------------------------------------------

ROOT = Path(__file__).resolve().parent

SOURCE = ROOT / "_site" / "de" / "Innomag-Guideline-de.pdf"
TARGET = ROOT / "Innomag-Guideline-de-print.pdf"

# -------------------------------------------------------
# Dimensions (mm)
# -------------------------------------------------------

MM = 72 / 25.4

COVER_BLEED = 15
PANEL_W = 215
PANEL_H = 302
SPINE_W = 8

COVER_W = 2 * COVER_BLEED + 2 * PANEL_W + SPINE_W
COVER_H = PANEL_H + 2 * COVER_BLEED

INNER_W = 210
INNER_H = 297
INNER_BLEED = 3

# Seam overlaps to hide PDF rendering edges
BOTTOM_OVERLAP = 0.5
RIGHT_OVERLAP = 2.0

# -------------------------------------------------------
# Colors
# -------------------------------------------------------

PINK = (248 / 255, 226 / 255, 223 / 255)
MINT = (221 / 255, 243 / 255, 240 / 255)

# -------------------------------------------------------
# Helpers
# -------------------------------------------------------

def rect_mm(x0, y0, x1, y1):
    return fitz.Rect(
        x0 * MM,
        y0 * MM,
        x1 * MM,
        y1 * MM,
    )

def draw_polygon(page, points, color, overlay=True):
    """Draw a filled polygon using coordinates in mm."""
    shape = page.new_shape()

    coords = [
        fitz.Point(x * MM, y * MM)
        for x, y in points
    ]

    for a, b in zip(coords, coords[1:] + coords[:1]):
        shape.draw_line(a, b)

    shape.finish(
        fill=color,
        color=None,
        closePath=True,
    )

    shape.commit(overlay=overlay)

# -------------------------------------------------------
# Cover geometry
# -------------------------------------------------------

def cover_geometry():
    """Calculate cover boundaries and transition positions."""

    spine_left = COVER_BLEED + PANEL_W
    front_left = spine_left + SPINE_W
    front_right = front_left + PANEL_W

    # Horizontal transition across back and spine
    y_back = COVER_BLEED + 0.60 * PANEL_H

    # Diagonal transition on front
    y_front_right = COVER_BLEED + 0.30 * PANEL_H

    slope = (y_front_right - y_back) / PANEL_W

    return (
        spine_left,
        front_left,
        front_right,
        y_back,
        y_front_right,
        slope,
    )

# -------------------------------------------------------
# Cover background
# -------------------------------------------------------

def draw_cover_background(page):
    """
    Draw continuous background behind the cover artwork.

    Back cover:
        Horizontal color transition at 60%.

    Spine:
        Horizontal transition at same height.

    Front cover:
        Diagonal transition from 60% to 30%.

    Bleed:
        Continue colors beyond the trim area.
    """

    (
        spine_left,
        front_left,
        front_right,
        y_back,
        y_front_right,
        slope,
    ) = cover_geometry()

    y_bleed_right = y_front_right + slope * (COVER_W - front_right)

    # Pink background everywhere
    page.draw_rect(
        rect_mm(0, 0, COVER_W, COVER_H),
        fill=PINK,
        color=None,
        overlay=True,
    )

    # Mint area below the transition
    draw_polygon(
        page,
        [
            (0, y_back),
            (front_left, y_back),
            (front_right, y_front_right),
            (COVER_W, y_bleed_right),
            (COVER_W, COVER_H),
            (0, COVER_H),
        ],
        MINT,
        overlay=True,
    )

# -------------------------------------------------------
# Remove cover-edge seams
# -------------------------------------------------------

def fix_cover_bleed(page):
    """
    Extend the mint background into the bottom
    and right bleed without creating a pink seam.
    """

    (
        spine_left,
        front_left,
        front_right,
        y_back,
        y_front_right,
        slope,
    ) = cover_geometry()

    # Bottom bleed: solid mint
    bottom = COVER_BLEED + PANEL_H

    page.draw_rect(
        rect_mm(
            0,
            bottom - BOTTOM_OVERLAP,
            COVER_W,
            COVER_H,
        ),
        color=None,
        fill=MINT,
        overlay=True,
    )

    # Right bleed: extend only the mint area.
    # Pink is already present in the original background.
    x_start = front_right - RIGHT_OVERLAP

    y_start = y_front_right + slope * (
        x_start - front_right
    )

    y_outer = y_front_right + slope * (
        COVER_W - front_right
    )

    draw_polygon(
        page,
        [
            (x_start, y_start),
            (COVER_W, y_outer),
            (COVER_W, COVER_H),
            (x_start, COVER_H),
        ],
        MINT,
        overlay=True,
    )

# -------------------------------------------------------
# Create print PDF
# -------------------------------------------------------

def create_print_pdf(source_file, target_file):

    if source_file.resolve() == target_file.resolve():
        raise ValueError("Input and output files must differ.")

    with fitz.open(source_file) as original:

        if len(original) != 78:
            raise ValueError(
                "Expected 78 pages in the original Quarto PDF. "
                f"Found {len(original)}."
            )

        output = fitz.open()

        try:

            # -------------------------------------------
            # Page 1: Hardcover cover
            # -------------------------------------------

            cover = output.new_page(
                width=COVER_W * MM,
                height=COVER_H * MM,
            )

            # Full background including bleed and spine
            draw_cover_background(cover)

            # Back cover: left
            cover.show_pdf_page(
                rect_mm(
                    COVER_BLEED,
                    COVER_BLEED,
                    COVER_BLEED + PANEL_W,
                    COVER_BLEED + PANEL_H,
                ),
                original,
                len(original) - 1,
                keep_proportion=False,
            )

            # Front cover: right
            front_x = COVER_BLEED + PANEL_W + SPINE_W

            cover.show_pdf_page(
                rect_mm(
                    front_x,
                    COVER_BLEED,
                    front_x + PANEL_W,
                    COVER_BLEED + PANEL_H,
                ),
                original,
                0,
                keep_proportion=False,
            )

            # Correct seams at outer edges
            fix_cover_bleed(cover)

            # -------------------------------------------
            # Pages 2-77: Interior
            # -------------------------------------------

            for page_number in range(1, 77):

                page = output.new_page(
                    width=(INNER_W + 2 * INNER_BLEED) * MM,
                    height=(INNER_H + 2 * INNER_BLEED) * MM,
                )

                page.show_pdf_page(
                    rect_mm(
                        INNER_BLEED,
                        INNER_BLEED,
                        INNER_BLEED + INNER_W,
                        INNER_BLEED + INNER_H,
                    ),
                    original,
                    page_number,
                    keep_proportion=False,
                )

            # -------------------------------------------
            # Save
            # -------------------------------------------

            output.set_metadata({
                "title": "INNOMAG Guideline - Druckfassung",
                "subject": (
                    "Hardcover cover 468 x 332 mm; "
                    "76 interior pages 216 x 303 mm"
                ),
            })

            output.save(
                str(target_file),
                garbage=4,
                deflate=True,
            )

        finally:
            output.close()

    # -------------------------------------------
    # Verify result
    # -------------------------------------------

    with fitz.open(target_file) as result:

        assert len(result) == 77

        assert abs(result[0].rect.width / MM - 468) < 0.1
        assert abs(result[0].rect.height / MM - 332) < 0.1

        for i in range(1, 77):
            assert abs(result[i].rect.width / MM - 216) < 0.1
            assert abs(result[i].rect.height / MM - 303) < 0.1

    print(f"\nCreated: {target_file}")
    print("Pages: 77")
    print("Cover: 468 x 332 mm, 8 mm spine")
    print("Interior: 76 pages, 216 x 303 mm")
    print("Bleed: 15 mm cover, 3 mm interior")

# -------------------------------------------------------
# Main
# -------------------------------------------------------

if __name__ == "__main__":

    input_file = (
        Path(sys.argv[1]).resolve()
        if len(sys.argv) > 1
        else SOURCE
    )

    if not input_file.is_file():
        raise FileNotFoundError(
            f"Quarto PDF not found: {input_file}"
        )

    create_print_pdf(input_file, TARGET)