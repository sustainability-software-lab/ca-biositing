"""
_fix_snippet_placement.py
--------------------------
One-time migration script: replaces the injected dashboard_click_export.js
<script> block in all composition HTML dashboards with the latest version,
ensuring it is placed in <head> (not before </body>), and ensures the
vegaEmbed().then() patch appears exactly once.

Run with:
    pixi run python scripts/_fix_snippet_placement.py
"""

import pathlib

# All HTML files that need to be updated
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
]

# The marker that uniquely identifies our injected block
SNIPPET_MARKER = "dashboard_click_export.js"
SCRIPT_OPEN = "<script>"
SCRIPT_CLOSE = "</script>"

# The vegaEmbed patch strings
OLD_CHAIN = ".catch(error => showError(el, error));"
NEW_CHAIN = ".then(function(result) { attachClickExport(result.view); }).catch(error => showError(el, error));"

# Read the latest JS snippet
SNIPPET_PATH = pathlib.Path("scripts/dashboard_click_export.js")


def find_snippet_block(html: str) -> tuple:
    """
    Find the start and end indices of the injected script block.
    Returns (-1, -1) if not found.
    """
    search_start = 0
    while True:
        open_idx = html.find(SCRIPT_OPEN, search_start)
        if open_idx == -1:
            return -1, -1
        close_idx = html.find(SCRIPT_CLOSE, open_idx + len(SCRIPT_OPEN))
        if close_idx == -1:
            return -1, -1
        block_end = close_idx + len(SCRIPT_CLOSE)
        block = html[open_idx:block_end]
        if SNIPPET_MARKER in block:
            return open_idx, block_end
        search_start = block_end


def fix_vegaembed_patch(html: str) -> str:
    """
    Ensure the vegaEmbed .then() patch appears exactly once.
    Handles cases where it was applied 0, 1, or 2+ times.
    """
    # First, collapse any doubled .then() patches back to the original .catch()
    # A doubled patch looks like: .then(...).then(...).catch(...)
    doubled = (
        ".then(function(result) { attachClickExport(result.view); })"
        ".then(function(result) { attachClickExport(result.view); })"
        ".catch(error => showError(el, error));"
    )
    if doubled in html:
        # Collapse to single patch
        html = html.replace(doubled, NEW_CHAIN)

    # Now ensure exactly one patch exists
    if NEW_CHAIN not in html:
        # Not patched yet — apply it
        if OLD_CHAIN in html:
            html = html.replace(OLD_CHAIN, NEW_CHAIN)

    return html


def fix_file(path_str: str, new_snippet: str) -> None:
    p = pathlib.Path(path_str)
    if not p.exists():
        print(f"  SKIP (not found): {p.name}")
        return

    html = p.read_text(encoding="utf-8")
    new_script_block = f"<script>\n{new_snippet}\n</script>"

    # ── Remove ALL existing snippet blocks (there may be multiple) ────────────
    while True:
        start, end = find_snippet_block(html)
        if start == -1:
            break
        remove_from = start
        remove_to = end
        if remove_from > 0 and html[remove_from - 1] == '\n':
            remove_from -= 1
        if remove_to < len(html) and html[remove_to] == '\n':
            remove_to += 1
        html = html[:remove_from] + html[remove_to:]

    # ── Fix vegaEmbed patch (ensure exactly once) ─────────────────────────────
    html = fix_vegaembed_patch(html)

    # ── Insert new snippet into <head> before </head> ─────────────────────────
    head_close = html.find("</head>")
    if head_close == -1:
        print(f"  ERROR: </head> not found in {p.name}")
        return

    html = html[:head_close] + "\n" + new_script_block + "\n" + html[head_close:]

    # ── Write back ────────────────────────────────────────────────────────────
    p.write_text(html, encoding="utf-8")

    # ── Verify ────────────────────────────────────────────────────────────────
    final = p.read_text(encoding="utf-8")
    head_end = final.find("</head>")
    head_section = final[:head_end]
    body_section = final[head_end:]

    assert "attachClickExport" in head_section, f"snippet not in <head> for {p.name}"
    assert SNIPPET_MARKER not in body_section, f"snippet still in body for {p.name}"
    assert NEW_CHAIN in final, f"vegaEmbed patch missing for {p.name}"
    assert final.count(NEW_CHAIN) == 1, f"vegaEmbed patch duplicated in {p.name}: count={final.count(NEW_CHAIN)}"
    assert "window.attachClickExport" in head_section, f"window.attachClickExport not in head for {p.name}"
    assert "DOMContentLoaded" in head_section, f"DOMContentLoaded not in head for {p.name}"

    print(f"  ✓ {p.name}")


def main():
    if not SNIPPET_PATH.exists():
        print(f"ERROR: {SNIPPET_PATH} not found")
        return

    new_snippet = SNIPPET_PATH.read_text(encoding="utf-8")
    print(f"Using snippet from {SNIPPET_PATH} ({len(new_snippet)} chars)")
    print("Updating HTML files...")

    for target in TARGETS:
        fix_file(target, new_snippet)

    print("Done.")


if __name__ == "__main__":
    main()
