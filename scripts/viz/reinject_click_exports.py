"""
reinject_click_exports.py
-------------------------
Re-injects the click-export snippet into all dashboard HTML files,
replacing any existing injection. Ensures:
  - Snippet is in <head> (not before </body>)
  - vegaEmbed .then() patch appears exactly once
  - No literal \\n escape sequences in the injected block

Run with:
    pixi run python scripts/viz/reinject_click_exports.py
"""

import pathlib

TARGETS = [
    "exports/plots/composition/xrf_distribution.html",
    "exports/plots/composition/compositional_distribution.html",
    "exports/plots/composition/xrf_variance_distribution.html",
    "exports/plots/composition/icp_distribution.html",
    "exports/plots/composition/proximate_distribution.html",
    "exports/plots/composition/proximate_distribution_dashboard.html",
    "exports/plots/composition/ultimate_distribution.html",
    "exports/plots/composition/xrd_distribution.html",
    "exports/plots/composition/moisture_vs_ash.html",
    "exports/plots/conversion/fermentation_distribution.html",
    "exports/plots/conversion/gasification_distribution.html",
    "exports/plots/conversion/pretreatment_distribution.html",
    "exports/plots/conversion/pretreatment_variance.html",
]

SNIPPET_MARKER = "dashboard_click_export.js"
SCRIPT_OPEN = "<script>"
SCRIPT_CLOSE = "</script>"
OLD_CHAIN = ".catch(error => showError(el, error));"
NEW_CHAIN = ".then(function(result) { attachClickExport(result.view); }).catch(error => showError(el, error));"

SNIPPET_PATH = pathlib.Path(__file__).parent / "dashboard_click_export.js"


def find_all_snippet_blocks(html: str) -> list:
    """Return list of (start, end) tuples for all injected script blocks."""
    blocks = []
    search_start = 0
    while True:
        open_idx = html.find(SCRIPT_OPEN, search_start)
        if open_idx == -1:
            break
        close_idx = html.find(SCRIPT_CLOSE, open_idx + len(SCRIPT_OPEN))
        if close_idx == -1:
            break
        block_end = close_idx + len(SCRIPT_CLOSE)
        if SNIPPET_MARKER in html[open_idx:block_end]:
            blocks.append((open_idx, block_end))
        search_start = block_end
    return blocks


def fix_vegaembed(html: str) -> str:
    """Ensure the vegaEmbed .then() patch appears exactly once."""
    # Remove all existing .then(attachClickExport) patches
    # by collapsing any number of them back to OLD_CHAIN
    import re
    # Replace one or more consecutive .then(function(result) { attachClickExport(result.view); }) chains
    pattern = r'(?:\.then\(function\(result\) \{ attachClickExport\(result\.view\); \}\))+'
    html = re.sub(pattern + r'\.catch\(error => showError\(el, error\)\);',
                  OLD_CHAIN, html)
    # Now apply exactly once
    if OLD_CHAIN in html:
        html = html.replace(OLD_CHAIN, NEW_CHAIN)
    return html


def process_file(path_str: str, snippet: str) -> None:
    p = pathlib.Path(path_str)
    if not p.exists():
        print(f"  SKIP (not found): {p.name}")
        return

    html = p.read_text(encoding="utf-8")

    # Remove ALL existing snippet blocks
    blocks = find_all_snippet_blocks(html)
    # Remove in reverse order to preserve indices
    for start, end in reversed(blocks):
        rf = start - 1 if start > 0 and html[start - 1] == "\n" else start
        rt = end + 1 if end < len(html) and html[end] == "\n" else end
        html = html[:rf] + html[rt:]

    # Fix vegaEmbed patch
    html = fix_vegaembed(html)

    # Build the script block — use explicit newlines, strip any trailing whitespace from snippet
    clean_snippet = snippet.rstrip()
    script_block = "<script>\n" + clean_snippet + "\n</script>"

    # Insert into <head>
    head_close = html.find("</head>")
    if head_close == -1:
        print(f"  ERROR: </head> not found in {p.name}")
        return
    html = html[:head_close] + "\n" + script_block + "\n" + html[head_close:]

    p.write_text(html, encoding="utf-8")

    # Verify
    final = p.read_text(encoding="utf-8")
    head_end = final.find("</head>")
    head_section = final[:head_end]
    body_section = final[head_end:]

    assert SNIPPET_MARKER in head_section, f"snippet not in <head>: {p.name}"
    assert SNIPPET_MARKER not in body_section, f"snippet in body: {p.name}"
    assert final.count(NEW_CHAIN) == 1, f"patch count={final.count(NEW_CHAIN)}: {p.name}"
    assert "window.attachClickExport" in head_section, f"window.attachClickExport missing: {p.name}"
    assert "DOMContentLoaded" in head_section, f"DOMContentLoaded missing: {p.name}"

    print(f"  ✓ {p.name}")


def main():
    if not SNIPPET_PATH.exists():
        print(f"ERROR: {SNIPPET_PATH} not found")
        return

    snippet = SNIPPET_PATH.read_text(encoding="utf-8")
    print(f"Snippet: {len(snippet)} chars, ends with: {repr(snippet[-20:])}")
    print("Re-injecting all HTML files...")

    for target in TARGETS:
        process_file(target, snippet)

    print("Done.")


if __name__ == "__main__":
    main()
