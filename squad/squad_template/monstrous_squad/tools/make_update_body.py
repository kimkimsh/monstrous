#!/usr/bin/env python3
"""Emit the `aigo squad update` body that sets what a Squad Template cannot.

The template schema has 9 per-agent fields and none of them is `settingsOverrides`,
so `maxTokens` (output cap) and `maxToolCalls` (tool rounds) cannot ship in the
submitted JSON. They live on `AgentConfig`, which `UpdateSquadRequest` accepts:

    UpdateSquadRequest = { name, description, workspacePath, agents, plannerAgentId }

read out of its serde field visitor at backend-ai-go:0x100be75f8. So the values go
in after the squad exists, through the same CLI, still as JSON.

    aigo squad show <SQUAD_ID> > squad.json          # or point at the app's copy in
                                                     # ~/Library/Application Support/
                                                     #   ai.backend.go/squads/<id>.json
    python3 tools/make_update_body.py squad.json > update.json
    aigo squad update <SQUAD_ID> "$(cat update.json)"

Agent identity is matched by name, so the ids the app generated are preserved.
"""

import json
import sys
from pathlib import Path

# Output cap per call. 8192 is not a tuned value — it is the smallest cap measured
# to produce zero unfinished answers. At 2,048, 49 of 450 math responses (10.9%)
# ended with no final answer; at 8,192, none did. A truncated answer is a
# team-owned zero, an oversized cap is only tokens, so the error is taken on the
# safe side until the max_tokens sweep (plan/03 §4) says otherwise.
MAX_TOKENS = 8192

# Tool rounds. Every agent runs with enabledTools: [] and gets no tools at all, so
# the workers' cap is a statement rather than a control — harmless whether the app
# reads 0 as "none" or as "unlimited". Router is different: create_task reaches it
# through the planner path, not through toolConfig, and plan A needs three of them.
MAX_TOOL_CALLS = {"Router": 8}
WORKER_MAX_TOOL_CALLS = 0

# Left null deliberately:
#   maxIterations               — BudgetConfig.maxAgentTurns already bounds turns
#   defaultTimeout              — BudgetConfig.taskTimeoutSecs already bounds time
#   contextCompressionThreshold — compression rewrites context, and a rewritten
#                                 anchor is a patch that no longer applies. Neither
#                                 the unit nor the default is known; see plan/03 §4
#   allowedPaths                — no file tool is enabled, so no path applies


def overrides_for(name):
    return {
        "maxIterations": None,
        "maxToolCalls": MAX_TOOL_CALLS.get(name, WORKER_MAX_TOOL_CALLS),
        "defaultTimeout": None,
        "contextCompressionThreshold": None,
        "maxTokens": MAX_TOKENS,
        "allowedPaths": None,
    }


def main():
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2

    raw = json.loads(Path(sys.argv[1]).read_text())
    # `aigo squad show` returns the squad; the workspace file wraps it in "config".
    squad = raw.get("config", raw)
    agents = squad.get("agents")
    if not agents:
        print(f"no agents in {sys.argv[1]}; is this a created squad?", file=sys.stderr)
        return 1

    template = json.loads((Path(__file__).resolve().parent.parent /
                           "squad-template.json").read_text())
    wanted = {a["name"]: a for a in template["agents"]}

    updated = []
    for agent in agents:
        name = agent["name"]
        if name not in wanted:
            print(f"warning: squad carries an agent the template does not: {name}",
                  file=sys.stderr)
            updated.append(agent)
            continue
        source = wanted[name]
        agent = dict(agent)
        agent["settingsOverrides"] = overrides_for(name)
        # Re-assert what the template already said, in case squad creation
        # materialised its own values. The model is the one this has been observed
        # to overwrite: two squads on this machine came out as unsloth/gpt-oss-20b
        # from templates that named no model at all.
        agent["toolConfig"] = source["toolConfig"]
        agent["modelPreferences"] = source["modelPreferences"]
        agent["memoryEnabled"] = source["memoryEnabled"]
        agent["systemPrompt"] = source["systemPrompt"]
        updated.append(agent)

    # Round-trip every field of UpdateSquadRequest, not just the ones being
    # changed. Whether a missing field means "leave it" or "set it to null" is not
    # established, and workspacePath is not a field worth finding out on.
    body = {"agents": updated}
    for field in ("name", "description", "workspacePath", "plannerAgentId"):
        if squad.get(field) is not None:
            body[field] = squad[field]
    for field in ("name", "workspacePath"):
        if field not in body:
            print(f"warning: source squad has no {field}; the update body omits it "
                  f"and the app may clear it", file=sys.stderr)

    json.dump(body, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")

    names = ", ".join(f"{a['name']}:{a['settingsOverrides']['maxToolCalls']}"
                      for a in updated if "settingsOverrides" in a)
    print(f"{len(updated)} agents, maxTokens {MAX_TOKENS}, maxToolCalls {names}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
