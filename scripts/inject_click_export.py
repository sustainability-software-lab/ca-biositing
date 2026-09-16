"""
inject_click_export.py
----------------------
Post-processes a saved Altair/Vega-Lite HTML file to inject the
click-to-export UI snippet.

Usage (from a viz script's main() function):

    from scripts.inject_click_export import inject_click_export
    dashboard.save(export_path)
    inject_click_export(export_path)

The function reads the JS snippet from scripts/dashboard_click_export.js,
wraps it in a <script> tag, and inserts it into <head> (before </head>).
It also patches the vegaEmbed() call to invoke attachClickExport(view)
after the chart renders.

IMPORTANT — placement in <head>:
    The snippet must be in <head>, not before </body>. The vegaEmbed()
    Promise resolves as a microtask, which fires before the browser parses
    the next <script> tag in the body. Placing the snippet in <head>
    ensures window.attachClickExport is defined before any body scripts
    execute. The snippet itself defers DOM manipulation to DOMContentLoaded
    so that document.body exists when it runs.

The file is modified in place.
"""

from pathlib import Path

# Resolve the JS snippet relative to this file so the import works
# regardless of the working directory.
SNIPPET_PATH = Path(__file__).parent / "dashboard_click_export.js"

# The exact string Altair generates at the end of the vegaEmbed() call.
# Verified across all 14 dashboards (Altair 5 / vega-embed 6).
_OLD_CHAIN = ".catch(error => showError(el, error));"

# Replacement: insert a .then() handler before the .catch() so we receive
# the resolved {view} object and can pass it to attachClickExport.
_NEW_CHAIN = (
    ".then(function(result) { attachClickExport(result.view); })"
    ".catch(error => showError(el, error));"
)


def inject_click_export(html_path: str) -> None:
    """
    Inject the click-to-export UI into a saved Altair HTML dashboard.

    Parameters
    ----------
    html_path : str
        Path to the HTML file produced by altair.Chart.save().
        The file is modified in place.

    Raises
    ------
    FileNotFoundError
        If the JS snippet file does not exist next to this module.
    RuntimeError
        If the vegaEmbed patch string was not found in the HTML (indicating
        the Altair HTML template may have changed) or if the injection
        verification fails.
    """
    html_path = Path(html_path)

    if not SNIPPET_PATH.exists():
        raise FileNotFoundError(
            f"JS snippet not found at {SNIPPET_PATH}. "
            "Ensure scripts/dashboard_click_export.js exists."
        )

    html = html_path.read_text(encoding="utf-8")
    js_snippet = SNIPPET_PATH.read_text(encoding="utf-8")

    # ── Step 1: Patch the vegaEmbed() call ───────────────────────────────────
    if _OLD_CHAIN not in html:
        raise RuntimeError(
            f"Could not find the vegaEmbed patch target in {html_path}.\n"
            f"Expected to find: {_OLD_CHAIN!r}\n"
            "The Altair HTML template may have changed. "
            "Update _OLD_CHAIN in inject_click_export.py to match."
        )

    html = html.replace(_OLD_CHAIN, _NEW_CHAIN)

    # ── Step 2: Inject the JS snippet into <head> ─────────────────────────────
    # IMPORTANT: The snippet must be in <head> (before the body <script> that
    # calls vegaEmbed), not before </body>. The vegaEmbed Promise resolves as
    # a microtask, which fires before the browser parses the next <script> tag
    # in the body. Placing the snippet in <head> ensures attachClickExport is
    # defined on window before any body scripts execute.
    snippet_tag = f"\n<script>\n{js_snippet}\n</script>\n"
    html = html.replace("</head>", snippet_tag + "</head>")

    # ── Step 3: Write back ────────────────────────────────────────────────────
    html_path.write_text(html, encoding="utf-8")

    # ── Step 4: Verify the injection succeeded ────────────────────────────────
    verification_html = html_path.read_text(encoding="utf-8")
    if "attachClickExport" not in verification_html:
        raise RuntimeError(
            f"Injection verification failed for {html_path}. "
            "'attachClickExport' not found in the output HTML. "
            "Check the patch logic in inject_click_export.py."
        )

    print(f"[inject_click_export] ✓ Injected click-export UI into {html_path}")
