"""Export HTML to PDF using xhtml2pdf with bundled fonts."""

from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path

from reportlab.lib.fonts import addMapping
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from xhtml2pdf import default as xhtml2pdf_default
from xhtml2pdf import pisa

log = logging.getLogger(__name__)

# Bundled font directory
_FONTS_DIR = Path(__file__).resolve().parent.parent / "fonts"

_fonts_registered = False


def _register_fonts() -> None:
    """Register bundled JetBrains Mono with reportlab and xhtml2pdf (once).

    Uses BytesIO to avoid Windows PermissionError with temp files.
    """
    global _fonts_registered
    if _fonts_registered:
        return

    fonts = [
        ("JetBrainsMono", "JetBrainsMono-Regular.ttf", 0, 0),
        ("JetBrainsMono-Bold", "JetBrainsMono-Bold.ttf", 1, 0),
        ("JetBrainsMono-Italic", "JetBrainsMono-Italic.ttf", 0, 1),
    ]

    for name, filename, bold, italic in fonts:
        font_path = _FONTS_DIR / filename
        if not font_path.exists():
            log.warning("Font file not found: %s", font_path)
            continue

        data = font_path.read_bytes()
        pdfmetrics.registerFont(TTFont(name, BytesIO(data)))
        addMapping("JetBrainsMono", bold, italic, name)
        log.debug("Registered font: %s", name)

    # Add to xhtml2pdf's font lookup so CSS font-family resolves
    xhtml2pdf_default.DEFAULT_FONT["jetbrains mono"] = "JetBrainsMono"
    xhtml2pdf_default.DEFAULT_FONT["jetbrains mono-bold"] = "JetBrainsMono-Bold"
    xhtml2pdf_default.DEFAULT_FONT["jetbrains mono-italic"] = "JetBrainsMono-Italic"

    _fonts_registered = True
    log.debug("All bundled fonts registered")


def html_to_pdf(html: str, output_path: Path) -> Path:
    """Render an HTML string to a PDF file.

    Returns the path the PDF was written to.
    """
    _register_fonts()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "wb") as f:
        result = pisa.CreatePDF(html, dest=f)

    if result.err:
        raise RuntimeError(f"PDF conversion failed with {result.err} error(s)")

    log.info("PDF written to %s", output_path)
    return output_path
