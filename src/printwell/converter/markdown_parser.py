"""Convert Markdown text to styled HTML."""

from __future__ import annotations

import logging

import markdown2
from pygments.formatters import HtmlFormatter

log = logging.getLogger(__name__)

# markdown2 extras to enable
_EXTRAS = [
    "fenced-code-blocks",
    "tables",
    "header-ids",
    "strike",
    "task_list",
    "cuddled-lists",
    "code-friendly",
    "footnotes",
    "numbering",
]


def md_to_html(markdown_text: str) -> str:
    """Convert raw Markdown to an HTML fragment."""
    html = markdown2.markdown(markdown_text, extras=_EXTRAS)
    log.debug("Converted %d chars of Markdown to HTML", len(markdown_text))
    return html


def wrap_html(body: str, title: str = "Printwell Document") -> str:
    """Wrap an HTML fragment in a full document with CSS styling."""
    pygments_css = HtmlFormatter(style="monokai").get_style_defs(".codehilite")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
{_BASE_CSS}
{pygments_css}
</style>
</head>
<body>
<article>
{body}
</article>
</body>
</html>"""


_BASE_CSS = """\
/* Reset and base */
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: Helvetica, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #222;
    max-width: 800px;
    margin: 0 auto;
    padding: 20mm;
}

article { max-width: 100%; }

/* Headings */
h1, h2, h3, h4, h5, h6 {
    margin-top: 1.4em;
    margin-bottom: 0.6em;
    font-weight: bold;
    line-height: 1.3;
}
h1 { font-size: 1.8em; border-bottom: 2px solid #ddd; padding-bottom: 0.3em; }
h2 { font-size: 1.4em; border-bottom: 1px solid #eee; padding-bottom: 0.2em; }
h3 { font-size: 1.2em; }
h4 { font-size: 1.05em; }

/* Paragraphs and text */
p { margin-bottom: 0.8em; }
strong { font-weight: bold; }
em { font-style: italic; }

/* Links */
a { color: #2563eb; text-decoration: none; }
a:hover { text-decoration: underline; }

/* Lists */
ul, ol { margin-bottom: 0.8em; padding-left: 1.8em; }
li { margin-bottom: 0.3em; }

/* Code */
code {
    font-family: "JetBrains Mono", Consolas, "Courier New", monospace;
    font-size: 0.9em;
    padding: 0.15em 0.4em;
}
pre {
    background: #ffffff;
    color: #222;
    padding: 1em;
    border: none;
    margin-bottom: 1em;
    line-height: 1.4;
}
pre code {
    background: none;
    padding: 0;
    color: inherit;
    font-size: 0.85em;
}

/* Tables */
table {
    border-collapse: collapse;
    width: 100%;
    margin-bottom: 1em;
}
th, td {
    border: 1px solid #ddd;
    padding: 0.5em 0.8em;
    text-align: left;
}
th {
    background: #f8f8f8;
    font-weight: bold;
}
tr:nth-child(even) { background: #fafafa; }

/* Blockquotes */
blockquote {
    border-left: 4px solid #3498db;
    margin: 0 0 1em 0;
    padding: 0.5em 1em;
    color: #555;
    background: #f9f9f9;
}

/* Horizontal rules */
hr {
    border: none;
    border-top: 1px solid #ddd;
    margin: 1.5em 0;
}

/* Images */
img { max-width: 100%; height: auto; }

/* Task lists */
ul.task-list { list-style: none; padding-left: 0; }
li.task-list-item { padding-left: 1.5em; text-indent: -1.5em; }

/* Footnotes */
.footnote { font-size: 0.85em; color: #666; }
"""
