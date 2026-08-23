#!/usr/bin/env python3
"""Assemble the deck from _head.html + _slides_*.html, expanding {{glyph:name:px}}."""
import re, sys, pathlib
from _glyphs import svg

HERE = pathlib.Path(__file__).parent
PARTS = ["_slides_a.html", "_slides_b.html", "_slides_c.html"]

def expand(text):
    def sub(m):
        name, px = m.group(1), int(m.group(2))
        return svg(name, px)
    return re.sub(r"\{\{glyph:([a-z]+):(\d+)\}\}", sub, text)

def main():
    out = [(HERE / "_head.html").read_text()]
    out.append("<body>\n")
    for p in PARTS:
        f = HERE / p
        if f.exists():
            out.append(expand(f.read_text()))
    out.append("\n</body>\n")
    html = "".join(out)
    left = re.findall(r"\{\{[^}]+\}\}", html)
    if left:
        sys.exit(f"unexpanded placeholders: {sorted(set(left))}")
    n = html.count('<section class="s"')
    dest = HERE / "monstrous-deck.html"
    dest.write_text(html)
    print(f"{dest.name}: {n} slides, {len(html):,} bytes")

main()
