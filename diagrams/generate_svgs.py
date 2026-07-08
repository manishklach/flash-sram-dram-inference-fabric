#!/usr/bin/env python3
"""Export Mermaid diagrams to SVG using the headings from docs/DIAGRAMS.md as filenames."""

import re
import sys
from pathlib import Path

DIAGRAMS_MD = Path(__file__).resolve().parents[1] / "docs" / "DIAGRAMS.md"
DIAGRAMS_DIR = Path(__file__).resolve().parents[1] / "diagrams"
OUTPUTS_DIR = DIAGRAMS_DIR

THEME_CFG = """{theme:'dark',themeVariables:{primaryColor:'#1f6feb',primaryTextColor:'#e6edf3',primaryBorderColor:'#58a6ff',lineColor:'#8b949e',secondaryColor:'#161b22',tertiaryColor:'#0d1117',mainBkg:'#161b22',nodeBorder:'#30363d',clusterBkg:'#0d1117',clusterBorder:'#30363d',edgeLabelBackground:'#161b22',nodeTextColor:'#e6edf3',titleColor:'#e6edf3'}}"""


def extract_diagrams(md: str) -> list[tuple[str, str]]:
    pattern = r"## (.+?)\n.*?```mermaid\n(.+?)```"
    matches = re.findall(pattern, md, re.DOTALL)
    results = []
    for heading, code in matches:
        name = heading.strip().lower().replace(" ", "_").replace("/", "_")
        name = re.sub(r"[^a-z0-9_]", "", name)
        results.append((name, code.strip()))
    return results


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9_]", "", name.lower().replace(" ", "_"))


def render_with_playwright(diagrams: list[tuple[str, str]]) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed. Install with: pip install playwright && python -m playwright install chromium")
        sys.exit(1)

    DIAGRAMS_DIR.mkdir(parents=True, exist_ok=True)

    html_template = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<style>body{margin:0;padding:16px;background:#0d1117}svg{max-width:100%;height:auto}</style>
<script>mermaid.initialize(THEME_CFG);</script>
</head><body>"""
    html_template = html_template.replace("THEME_CFG", THEME_CFG)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 960, "height": 800})

        for name, mermaid_code in diagrams:
            html = html_template + f'<pre class="mermaid">\n{mermaid_code}\n</pre></body></html>'
            html_path = DIAGRAMS_DIR / f"_{name}.html"
            html_path.write_text(html, encoding="utf-8")

            page.goto(html_path.as_uri(), wait_until="networkidle")
            page.wait_for_timeout(3000)

            svg_elements = page.locator("svg")
            count = svg_elements.count()
            if count == 0:
                print(f"  WARNING: no SVG for {name}")
                html_path.unlink(missing_ok=True)
                continue

            svg = svg_elements.first
            outer_html = svg.evaluate("el => el.outerHTML")
            output_path = DIAGRAMS_DIR / f"{name}.svg"
            output_path.write_text(outer_html, encoding="utf-8")
            print(f"  {output_path.name} ({len(outer_html)} bytes)")

            html_path.unlink(missing_ok=True)

        browser.close()


def main() -> None:
    md_content = DIAGRAMS_MD.read_text(encoding="utf-8")
    diagrams = extract_diagrams(md_content)
    print(f"Found {len(diagrams)} diagrams:")
    for name, _ in diagrams:
        print(f"  {name}")
    render_with_playwright(diagrams)
    print(f"\nAll SVGs in {DIAGRAMS_DIR}/")


if __name__ == "__main__":
    main()