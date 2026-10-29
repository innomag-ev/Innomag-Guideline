
"""
Compress the INNOMAG Quarto PDF for online publication.

Examples:
    python innomag_compress_pdf.py --dpi 180
    python innomag_compress_pdf.py --dpi 150
    python innomag_compress_pdf.py --dpi 220

Requires Ghostscript installed on the computer.
"""

from pathlib import Path
import argparse
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent

SOURCE = ROOT / "_site/de/Innomag-Guideline-de.pdf"
TARGET = ROOT / "_site/de/Innomag-Guideline-de-web.pdf"


def find_ghostscript():
    for name in ("gs", "gswin64c", "gswin32c"):
        executable = shutil.which(name)
        if executable:
            return executable

    raise RuntimeError(
        "Ghostscript not found. Install Ghostscript "
        "and add it to PATH."
    )


def compress_pdf(source, target, dpi):
    if not source.is_file():
        raise FileNotFoundError(source)

    if source.resolve() == target.resolve():
        raise ValueError("Source and target must differ.")

    target.parent.mkdir(parents=True, exist_ok=True)

    gs = find_ghostscript()

    command = [
        gs,
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.6",
        "-dAutoRotatePages=/None",
        "-dNOPAUSE",
        "-dBATCH",
        "-dQUIET",
        "-dSAFER",

        # Preserve original color values where possible
        "-sColorConversionStrategy=LeaveColorUnchanged",

        # Image downsampling
        "-dDownsampleColorImages=true",
        "-dDownsampleGrayImages=true",
        "-dColorImageDownsampleType=/Bicubic",
        "-dGrayImageDownsampleType=/Bicubic",
        "-dColorImageDownsampleThreshold=1.0",
        "-dGrayImageDownsampleThreshold=1.0",
        f"-dColorImageResolution={dpi}",
        f"-dGrayImageResolution={dpi}",

        # JPEG compression for color and grayscale images
        "-dAutoFilterColorImages=false",
        "-dAutoFilterGrayImages=false",
        "-dColorImageFilter=/DCTEncode",
        "-dGrayImageFilter=/DCTEncode",

        # PDF optimization
        "-dDetectDuplicateImages=true",
        "-dCompressFonts=true",

        f"-sOutputFile={target}",
        str(source),
    ]

    subprocess.run(command, check=True)

    original_mb = source.stat().st_size / 1024**2
    compressed_mb = target.stat().st_size / 1024**2

    print(f"Image resolution: {dpi} dpi")
    print(f"Original PDF:     {original_mb:.2f} MB")
    print(f"Online PDF:       {compressed_mb:.2f} MB")
    print(
        f"Size reduction:   "
        f"{100 * (1 - compressed_mb / original_mb):.1f}%"
    )
    print(f"Saved to: {target}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dpi",
        type=int,
        default=180,
        help="Raster image resolution (default: 180 dpi)",
    )

    args = parser.parse_args()

    if not 72 <= args.dpi <= 600:
        parser.error("--dpi must be between 72 and 600")

    compress_pdf(SOURCE, TARGET, args.dpi)
