# Deck — Monstrous Squad

Presentation for the JUNCTIONX Korea 2026 Lablup + FuriosaAI track,
built from [`../00-발표-구성.md`](../00-발표-구성.md).

19 slides, English, 16:9 (1280×720 CSS px → 960×540 pt in the PDF).

## Build

```bash
./build.sh          # assembles the HTML, runs the layout gate, writes ../build/monstrous-deck.pdf
```

Or the two halves on their own:

```bash
python3 build.py                    # _head.html + _slides_*.html → monstrous-deck.html
node check.js monstrous-deck.html   # layout gate, needs playwright
```

## Files

| File | What it holds |
|---|---|
| `_head.html` | Design tokens and every component rule. Lifted from `viz_revise_program/src/app.html:18-195` |
| `_slides_a.html` | Slides 01–05 — cover, the shape, the grader, why not one, the four questions |
| `_slides_b.html` | Slides 06–11 — Router, Coder, Solver, verification, giving up |
| `_slides_c.html` | Slides 12–19 — the viewer, the demo, the two appendices |
| `_glyphs.py` | The 12×12 dot glyphs, expanded into SVG at build time |
| `build.py` | Concatenates the parts and expands `{{glyph:name:px}}` |
| `check.js` | Refuses a slide whose content collides with the title, the footer, or its own page box |

**Edit the parts, never `monstrous-deck.html`.** It is generated and the next build overwrites it.

## The layout gate

A slide that overflows still renders — it just prints with the title underneath a panel,
and that is not visible in a browser tab where the page can scroll. `check.js` runs in
print emulation and fails the build on four conditions:

- the page box is not exactly 1280×720
- content is taller than the page
- the body runs under the title
- the body runs into the footer

## Design

The palette, type scale, spacing grid, hard edges, offset block shadows, cell gauges and
verdict stamps come from the trace viewer, so the slides and the tool being demonstrated
read as one object. The deck runs the viewer's **light** palette because it is printed and
projected; the dark palette appears once, on the meter strip on slide 12, which is the tool's
own ground.

Rules carried over from `docs/viz_revise/spec/00-디자인-토큰.md`:

- `border-radius` is 0 everywhere
- shadows are `5px 5px 0`, never blurred
- spacing comes from the 6px grid only
- numbers are `tabular-nums`
- no meaning is carried by colour alone

## Numbers

The 39-run measurements on slides 12–13 were taken by running the shipped
`viz_revise_program/trace-visualizer.html` against the current `squad/` folder, rather than
carried forward from an earlier count. Re-measure before presenting if `squad/` has grown:
open the viewer, drop the folder in, and read the four meters.
