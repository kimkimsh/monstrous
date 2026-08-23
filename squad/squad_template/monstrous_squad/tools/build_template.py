#!/usr/bin/env python3
"""Assemble squad-template.json from the three prompts in agent_prompts/.

The prompts live as .txt so that a diff shows prose, not JSON escapes, and so
that tools/validate_template.py can run the grader's own extractors over the
exact bytes that ship. Run this after editing any of them.

    python3 tools/build_template.py
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROMPTS = ROOT / "agent_prompts"

MODEL = "furiosa-ai/gpt-oss-120b"

# Dead in 1.12.1 — build_tools_for_agent returns early on an empty enabledTools
# and never reads either map. Kept as a record of intent in case a later build
# starts reading them; toolConfig.enabledTools is what actually holds.
DENIED = [
    "read_file", "write_file", "list_files", "list_directory", "search_files",
    "diff_files", "read_memory", "write_memory", "search_memory", "web_search",
    "fetch_url", "http_request", "diff_text", "calculator", "get_current_time",
    "get_system_info", "read_data", "write_data", "list_data", "search_data",
    "delete_data", "select_option",
]

AGENTS = [
    ("Router", "Planner", "router", "\U0001f5fa"),
    ("Coder", "Developer", "coder", "\U0001f527"),
    ("Solver", "Solver", "solver", "\U0001f9ee"),
]

DESCRIPTION = (
    "Three agents, one model, two model calls per benchmark item. Router reads the item, "
    "copies it verbatim into a single task, and assigns it by track; Coder answers repository "
    "and from-scratch coding items; Solver answers mathematics, multiple choice, and anything "
    "the harness sends that is neither. There is no second wave and no reviewer, because the "
    "grader reads only the last task output and every extra hop between the item and that "
    "output has been measured losing the answer. No agent holds a tool, so nothing can be "
    "written to a workspace file the grader never opens. No system prompt contains a string "
    "the grader's own extractors can read as an answer."
)


def agent(name, role, stem, icon):
    return {
        "name": name,
        "role": role,
        "systemPrompt": (PROMPTS / f"{stem}.txt").read_text().rstrip("\n"),
        "tools": [],
        "toolConfig": {
            "enabledTools": [],
            "disabledTools": list(DENIED),
            "toolPermissionOverrides": {t: "never_allow" for t in DENIED},
            "customToolConfigs": {},
        },
        "modelPreferences": {
            "preferredModelId": MODEL,
            "minContextWindow": None,
            "requiresToolCalling": False,
            "requiresVision": False,
        },
        "memoryEnabled": False,
        "icon": icon,
    }


def main():
    template = {
        "schemaVersion": 1,
        "id": "user-monstrous-squad-v2",
        "name": "Monstrous Squad",
        "description": DESCRIPTION,
        "icon": "\U0001f4d2",
        "category": "custom",
        "isBuiltin": False,
        "suggestedModels": [MODEL],
        "agents": [agent(*a) for a in AGENTS],
    }
    out = ROOT / "squad-template.json"
    out.write_text(json.dumps(template, indent=2, ensure_ascii=False) + "\n")
    print(f"{out.name}: {len(template['agents'])} agents, {out.stat().st_size} bytes")
    for a in template["agents"]:
        print(f"  {a['name']:<8} {len(a['systemPrompt']):>6} chars  {a['modelPreferences']['preferredModelId']}")


if __name__ == "__main__":
    main()
