"""Copy rendered Markdown as rich text (RTF/HTML) to the Windows clipboard."""

from __future__ import annotations

import logging
import re

import win32clipboard

log = logging.getLogger(__name__)

# Windows clipboard format for HTML
_CF_HTML = win32clipboard.RegisterClipboardFormat("HTML Format")

# Inline styles for elements that Word/Outlook need (they ignore <style> blocks)
_INLINE_STYLES: dict[str, str] = {
    "<pre": '<pre style="font-family: Consolas, \'Courier New\', monospace; '
            'white-space: pre; font-size: 10pt; line-height: 1.4; '
            'margin-bottom: 12pt;"',
    "<code": '<code style="font-family: Consolas, \'Courier New\', monospace; '
             'font-size: 10pt;"',
    "<blockquote": '<blockquote style="border-left: 3px solid #3498db; '
                   'padding: 6pt 12pt; color: #555; margin: 0 0 12pt 0;"',
    "<table": '<table style="border-collapse: collapse; width: 100%; '
              'margin-bottom: 12pt;"',
    "<th": '<th style="border: 1px solid #ddd; padding: 6pt 8pt; '
           'text-align: left; font-weight: bold; background: #f8f8f8;"',
    "<td": '<td style="border: 1px solid #ddd; padding: 6pt 8pt; '
           'text-align: left;"',
    "<h1": '<h1 style="font-size: 20pt; font-weight: bold; '
           'margin-top: 16pt; margin-bottom: 8pt; '
           'border-bottom: 1px solid #ddd; padding-bottom: 4pt;"',
    "<h2": '<h2 style="font-size: 16pt; font-weight: bold; '
           'margin-top: 14pt; margin-bottom: 8pt; '
           'border-bottom: 1px solid #eee; padding-bottom: 3pt;"',
    "<h3": '<h3 style="font-size: 13pt; font-weight: bold; '
           'margin-top: 12pt; margin-bottom: 6pt;"',
}


def _inline_styles(html: str) -> str:
    """Add inline styles to HTML elements for clipboard compatibility.

    Word and Outlook ignore <style> blocks in pasted HTML, so critical
    styles must be on the elements themselves.
    """
    for tag, replacement in _INLINE_STYLES.items():
        # Replace bare tags: <pre> and <pre class="...">
        html = re.sub(
            rf'{re.escape(tag)}(\s|>)',
            lambda m, r=replacement: r + m.group(1),
            html,
        )
    return html


def _fix_pre_newlines(html: str) -> str:
    """Replace newlines with <br> inside <pre> blocks.

    Word and Outlook treat bare newlines in <pre> as paragraph breaks
    (adding unwanted spacing).  <br> is treated as a simple line break.
    """
    def _replace_in_pre(m: re.Match) -> str:
        content = m.group(1)
        content = content.replace("\n", "<br>")
        return f"<pre{m.group(0)[4:len(m.group(0))-len(m.group(1))-6]}{content}</pre>"

    # Simpler approach: find each <pre...>...</pre> and replace \n inside
    return re.sub(
        r"<pre[^>]*>(.*?)</pre>",
        lambda m: m.group(0).replace("\n", "<br>") if "</pre>" in m.group(0) else m.group(0),
        html,
        flags=re.DOTALL,
    )


def copy_html_to_clipboard(html_fragment: str) -> None:
    """Place an HTML fragment on the clipboard as CF_HTML.

    Applications like Word, Outlook, and Teams read this format
    and paste the content with formatting intact.
    """
    html_fragment = _inline_styles(html_fragment)
    html_fragment = _fix_pre_newlines(html_fragment)
    cf_html = _build_cf_html(html_fragment)

    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(_CF_HTML, cf_html.encode("utf-8"))
        log.info("Rich text copied to clipboard (%d bytes)", len(cf_html))
    finally:
        win32clipboard.CloseClipboard()


def _build_cf_html(fragment: str) -> str:
    """Build the CF_HTML envelope around an HTML fragment.

    CF_HTML requires a header with byte offsets to the HTML start/end
    and the fragment start/end.
    """
    header_template = (
        "Version:0.9\r\n"
        "StartHTML:{start_html:010d}\r\n"
        "EndHTML:{end_html:010d}\r\n"
        "StartFragment:{start_fragment:010d}\r\n"
        "EndFragment:{end_fragment:010d}\r\n"
    )
    # Compute with dummy offsets first to get header length
    dummy = header_template.format(
        start_html=0, end_html=0, start_fragment=0, end_fragment=0,
    )
    prefix = "<html><body>\r\n<!--StartFragment-->"
    suffix = "<!--EndFragment-->\r\n</body></html>"

    header_len = len(dummy.encode("utf-8"))
    prefix_len = len(prefix.encode("utf-8"))
    fragment_len = len(fragment.encode("utf-8"))
    suffix_len = len(suffix.encode("utf-8"))

    start_html = header_len
    start_fragment = header_len + prefix_len
    end_fragment = start_fragment + fragment_len
    end_html = end_fragment + suffix_len

    header = header_template.format(
        start_html=start_html,
        end_html=end_html,
        start_fragment=start_fragment,
        end_fragment=end_fragment,
    )

    return header + prefix + fragment + suffix
