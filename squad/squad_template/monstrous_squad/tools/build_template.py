#!/usr/bin/env python3
"""Build monstrous_squad's submission templates from the spec template.

The five systemPrompt strings are carried across byte for byte; only the JSON
configuration layer is rewritten. Running this is how the claim "the prompts are
unchanged from the spec" stays checkable instead of being asserted.

    python3 tools/build_template.py

Writes squad-template.json (full) and squad-template.min.json (fallback with the
three unverified toolConfig fields emptied). See
docs/ideation/final_final_ideation/plan/01-JSON-필드-결정표.md for why each value
is what it is.
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
REPO = HERE.parents[3]
SPEC = REPO / "docs" / "ideation" / "final_final_ideation" / "spec" / "squad-template.json"

TEMPLATE_ID = "user-monstrous-ledger-squad-v1"
TEMPLATE_NAME = "LEDGER Squad"
TEMPLATE_ICON = "📒"
TEMPLATE_CATEGORY = "custom"

DESCRIPTION = (
    "Five agents answering benchmark items whose entire score is one regular "
    "expression applied to the last thing the squad writes. Router plans and "
    "distributes verbatim excerpts, Architect decides what changes and where, "
    "Editor writes the patch, Solver answers math and multiple choice, and "
    "Reviewer owns the final wave alone: it judges the answer on content and on "
    "form, then emits the graded block. Every agent opens with a one-line ledger "
    "in the space the grader ignores, which is the only trace that survives a run "
    "whose workspace we never see. No agent holds a tool, because the answer has "
    "to reach the response body and a file written to the workspace is a zero. "
    "Verification is a parser plus a bounded verdict, never a fabricated score; "
    "giving up is a named verdict, never a silence."
)

# gpt-oss reads its reasoning effort from one line of the harmony system message,
# and medium is the default. Whether this app's systemPrompt reaches that message
# rather than the developer message is untested — plan/02 §1-2 has the experiment
# and the token-cap precondition. Set to "Reasoning: high" to run it; the line goes
# at the head of Layer 3 so Layer 1 stays byte-identical across all five agents.
REASONING_LINE = {}

# Agent name -> model id. Reasoning in plan/02-모델-배정-분석.md.
MODELS = {
    "Router": "furiosa-ai/gpt-oss-120b",
    "Architect": "furiosa-ai/gpt-oss-120b",
    "Editor": "furiosa-ai/gpt-oss-120b",
    "Solver": "furiosa-ai/K-EXAONE-236B-A23B-NVFP4A16",
    "Reviewer": "furiosa-ai/gpt-oss-120b",
}

# Every tool this app can actually hand a squad agent. is_workspace_escaping_tool
# refuses the other fourteen by name, so listing those would close nothing.
# Order follows the registry modules in the binary.
DENIED_TOOLS = [
    # workspace-sandboxed (is_workspace_sandboxed_tool)
    "read_file", "write_file", "list_files", "list_directory", "search_files",
    "diff_files", "read_memory", "write_memory", "search_memory",
    # web + extended: not workspace-escaping, so not blocked by name
    "web_search", "fetch_url", "http_request", "diff_text",
    # utility
    "calculator", "get_current_time", "get_system_info",
    # Data Hub
    "read_data", "write_data", "list_data", "search_data", "delete_data",
    # interactive: reachable, then fails at runtime with no user to prompt
    "select_option",
]

EMPTY_TOOL_CONFIG = {
    "enabledTools": [],
    "disabledTools": [],
    "toolPermissionOverrides": {},
    "customToolConfigs": {},
}

DENYING_TOOL_CONFIG = {
    "enabledTools": [],
    "disabledTools": list(DENIED_TOOLS),
    "toolPermissionOverrides": {name: "never_allow" for name in DENIED_TOOLS},
    "customToolConfigs": {},
}


LAYER_BOUNDARY = "=== END SQUAD CONTRACT ==="


def system_prompt_for(agent):
    """The spec's prompt, optionally with a reasoning line at the head of Layer 3."""
    prompt = agent["systemPrompt"]
    line = REASONING_LINE.get(agent["name"])
    if not line:
        return prompt
    cut = prompt.index(LAYER_BOUNDARY) + len(LAYER_BOUNDARY)
    return prompt[:cut] + "\n\n" + line + prompt[cut:]


def build(tool_config):
    spec = json.loads(SPEC.read_text())
    agents = []
    for agent in spec["agents"]:
        name = agent["name"]
        agents.append({
            "name": name,
            "role": agent["role"],
            "systemPrompt": system_prompt_for(agent),
            "tools": [],
            "toolConfig": json.loads(json.dumps(tool_config)),
            "modelPreferences": {
                "preferredModelId": MODELS[name],
                "minContextWindow": None,
                "requiresToolCalling": False,
                "requiresVision": False,
            },
            "memoryEnabled": False,
            "icon": agent["icon"],
        })

    # Order the suggestions by seat count so the UI's first offer is the model
    # four of the five agents run on.
    suggested = sorted(set(MODELS.values()),
                       key=lambda m: (-sum(v == m for v in MODELS.values()), m))

    return {
        "schemaVersion": 1,
        "id": TEMPLATE_ID,
        "name": TEMPLATE_NAME,
        "description": DESCRIPTION,
        "icon": TEMPLATE_ICON,
        "category": TEMPLATE_CATEGORY,
        "isBuiltin": False,
        "suggestedModels": suggested,
        "agents": agents,
    }


def write(path, template):
    path.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n")
    print(f"wrote {path.relative_to(REPO)} ({path.stat().st_size} bytes, "
          f"{len(template['agents'])} agents)")


def main():
    write(OUT / "squad-template.json", build(DENYING_TOOL_CONFIG))
    write(OUT / "squad-template.min.json", build(EMPTY_TOOL_CONFIG))

    # The prompts must be identical between the two builds, and identical to the
    # spec wherever REASONING_LINE did not deliberately add a line. Otherwise the
    # fallback is not a fallback and "unchanged from the spec" stops being true.
    full = json.loads((OUT / "squad-template.json").read_text())
    minimal = json.loads((OUT / "squad-template.min.json").read_text())
    spec = json.loads(SPEC.read_text())
    for a, b, c in zip(full["agents"], minimal["agents"], spec["agents"]):
        assert a["systemPrompt"] == b["systemPrompt"], a["name"]
        if a["name"] not in REASONING_LINE:
            assert a["systemPrompt"] == c["systemPrompt"], a["name"]
    if REASONING_LINE:
        print(f"systemPrompts match the spec except {sorted(REASONING_LINE)}, "
              f"which carry an added reasoning line")
    else:
        print("systemPrompts identical to the spec template in both builds")


if __name__ == "__main__":
    main()
