#!/usr/bin/env python3
"""Derive squad-template.min.json from squad-template.json.

squad-template.json is the submission artifact and the only place the five
systemPrompts live; edit it directly. The .min variant exists for one contingency:
`aigo squad template import` has never been run against a template that fills
disabledTools and toolPermissionOverrides, and neither field is read by the squad
execution path anyway (plan/01 §1-4). If the importer rejects them, the fallback
has to be the same template with those two fields emptied and nothing else
touched — which is why it is derived here rather than maintained by hand.

    python3 tools/make_min_template.py

Run it after any edit to squad-template.json. validate_template.py fails if the
two files have drifted apart in any other field.
"""

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent
FULL = OUT / "squad-template.json"
MIN = OUT / "squad-template.min.json"

# The two fields the importer has not been proven to accept. customToolConfigs is
# already {} in both, so emptying it would be a no-op and is not listed.
EMPTIED = {"disabledTools": [], "toolPermissionOverrides": {}}


def main():
    template = json.loads(FULL.read_text())
    for agent in template["agents"]:
        agent["toolConfig"].update(json.loads(json.dumps(EMPTIED)))
    MIN.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n")
    print(f"wrote {MIN.relative_to(OUT.parent.parent.parent)} "
          f"({MIN.stat().st_size} bytes, {len(template['agents'])} agents) "
          f"— emptied {', '.join(EMPTIED)} on each")


if __name__ == "__main__":
    main()
