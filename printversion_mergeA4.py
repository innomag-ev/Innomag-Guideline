
"""Create INNOMAG hardcover print PDF from Quarto output.

Input:  _site/de/Innomag-Guideline-de.pdf
Output: Innomag-Guideline-de-print.pdf

Page 1:   Hardcover spread, 468 x 332 mm
Pages 2–77: 76 interior pages, 216 x 303 mm

Background colors are automatically extracted from
the original Quarto PDF.

Requires:
    python -m pip install pymupdf
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

BOTTOM_OVERLAP = 0.5
RIGHT_OVERLAP = 2.0


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


# -------------------------------------------------------
# Automatically detect cover colors
# -------------------------------------------------------

def get_cover_colors(back_page):
    """
    Extract the two background colors directly from
    the original PDF's back cover.

    Samples:
        Upper color: x=5%, y=10%
        Lower color: x=5%, y=90%

    These positions should contain only background.
    """

    pix = back_page.get_pixmap(
        matrix=fitz.Matrix(1, 1),
        colorspace=fitz.csRGB,
        alpha=False,
    )

    def pixel_at(x_fraction, y_fraction):
        x = round((pix.width - 1) * x_fraction)
        y = round((pix.height - 1) * y_fraction)

        red, green, blue = pix.pixel(x, y)[:3]

        return (
            red / 255,
            green / 255,
            blue / 255,
        )

    upper = pixel_at(0.05, 0.10)
    lower = pixel_at(0.05, 0.90)

    if max(
        abs(a - b)
        for a, b in zip(upper, lower)
    ) < 0.015:
        raise ValueError(
            "The two background color samples are "
            "almost identical. Check the original PDF."
        )

    return upper, lower


def draw_polygon(page, points, color):
    """Draw a filled polygon using millimeter coordinates."""

    shape = page.new_shape()

    coords = [
        fitz.Point(x * MM, y * MM)
        for x, y in points
    ]

    for a, b in zip(
        coords,
        coords[1:] + coords[:1],
    ):
        shape.draw_line(a, b)

    shape.finish(
        fill=color,
        color=None,
        closePath=True,
    )

    shape.commit(overlay=True)


# -------------------------------------------------------
# Cover background
# -------------------------------------------------------

def draw_cover_background(page, upper, lower):
    """
    Draw a continuous two-color cover background.

    Back:
        Horizontal boundary at 60%.

    Spine:
        Horizontal continuation.

    Front:
        Diagonal from 60% at the spine
        to 30% at the outside edge.

    Bleed:
        Continue the colors beyond the trim area.
    """

    spine_left = COVER_BLEED + PANEL_W
    front_left = spine_left + SPINE_W
    front_right = front_left + PANEL_W

    y_spine = COVER_BLEED + 0.60 * PANEL_H
    y_right = COVER_BLEED + 0.30 * PANEL_H

    slope = (y_right - y_spine) / PANEL_W

    y_outside = (
        y_right
        + slope * (COVER_W - front_right)
    )

    # Upper color across the complete cover
    page.draw_rect(
        rect_mm(0, 0, COVER_W, COVER_H),
        color=None,
        fill=upper,
    )

    # Lower color with horizontal and diagonal boundary
    draw_polygon(
        page,
        [
            (0, y_spine),
            (front_left, y_spine),
            (front_right, y_right),
            (COVER_W, y_outside),
            (COVER_W, COVER_H),
            (0, COVER_H),
        ],
        lower,
    )

    return front_right, y_right, slope


# -------------------------------------------------------
# Remove visible PDF rendering seams
# -------------------------------------------------------

def fix_cover_bleed(
    page,
    lower,
    front_right,
    y_right,
    slope,
):
    """
    Extend the lower background color into the
    bottom and right bleed areas.

    The upper background is not repainted,
    avoiding visible seams at the right edge.
    """

    # Bottom bleed
    bottom = COVER_BLEED + PANEL_H

    page.draw_rect(
        rect_mm(
            0,
            bottom - BOTTOM_OVERLAP,
            COVER_W,
            COVER_H,
        ),
        color=None,
        fill=lower,
        overlay=True,
    )

    # Right bleed: diagonal continuation
    start_x = front_right - RIGHT_OVERLAP

    start_y = (
        y_right
        + slope * (start_x - front_right)
    )

    outside_y = (
        y_right
        + slope * (COVER_W - front_right)
    )

    draw_polygon(
        page,
        [
            (start_x, start_y),
            (COVER_W, outside_y),
            (COVER_W, COVER_H),
            (start_x, COVER_H),
        ],
        lower,
    )


# -------------------------------------------------------
# Create print PDF
# -------------------------------------------------------

def create_print_pdf(source_file, target_file):

    if source_file.resolve() == target_file.resolve():
        raise ValueError("Input and output must differ.")

    with fitz.open(source_file) as original:

        if len(original) != 78:
            raise ValueError(
                "Expected 78 pages in the original Quarto PDF. "
                f"Found {len(original)}."
            )

        # Verify cover pages
        for page_number in (0, 77):
            size = original[page_number].rect

            if (
                abs(size.width / MM - 210) > 1
                or abs(size.height / MM - 297) > 1
            ):
                raise ValueError(
                    f"Cover page {page_number + 1} "
                    "must be A4 portrait."
                )

        # Detect colors from original back cover
        upper, lower = get_cover_colors(original[-1])

        print(
            "Upper RGB:",
            tuple(round(v * 255) for v in upper),
        )
        print(
            "Lower RGB:",
            tuple(round(v * 255) for v in lower),
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

            # Continuous background
            front_right, y_right, slope = (
                draw_cover_background(
                    cover,
                    upper,
                    lower,
                )
            )

            # Back cover: left
            cover.show_pdf_page(
                rect_mm(15, 15, 230, 317),
                original,
                77,
                keep_proportion=False,
            )

            # Front cover: right
            cover.show_pdf_page(
                rect_mm(238, 15, 453, 317),
                original,
                0,
                keep_proportion=False,
            )

            # Remove outer-edge rendering seams
            fix_cover_bleed(
                cover,
                lower,
                front_right,
                y_right,
                slope,
            )

            # -------------------------------------------
            # Pages 2–77: Interior
            # -------------------------------------------

            for page_number in range(1, 77):

                page = output.new_page(
                    width=216 * MM,
                    height=303 * MM,
                )

                page.show_pdf_page(
                    rect_mm(3, 3, 213, 300),
                    original,
                    page_number,
                    keep_proportion=False,
                )

            # -------------------------------------------
            # Save
            # -------------------------------------------

            output.set_metadata({
                "title": "INNOMAG Guideline - Druckfassung",
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

        assert abs(
            result[0].rect.width / MM - 468
        ) < 0.1

        assert abs(
            result[0].rect.height / MM - 332
        ) < 0.1

        for page in result.pages(1, 77):
            assert abs(page.rect.width / MM - 216) < 0.1
            assert abs(page.rect.height / MM - 303) < 0.1

    print(f"\nCreated: {target_file}")
    print("77 pages")
    print("Cover: 468 x 332 mm, 8 mm spine")
    print("Interior: 76 pages, 216 x 303 mm")


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
