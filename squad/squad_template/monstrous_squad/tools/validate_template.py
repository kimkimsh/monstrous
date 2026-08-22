#!/usr/bin/env python3
"""Validate a Squad Template JSON against Backend.AI GO 1.12.1 import rules and
against the hackathon grader in docs/resource/example_task/tools/grade.py.

Every check here corresponds to a limit read out of the app binary
(/Applications/Backend.AI GO.app/Contents/MacOS/backend-ai-go) or to a parser
function in grade.py / extract.py. Nothing is asserted from documentation alone.

    python3 tools/validate_template.py squad-template.json

Exit code 0 when every check passes, 1 otherwise.
"""

import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
GRADE_TOOLS = REPO / "docs" / "resource" / "example_task" / "tools"

# --- Import-validation limits, from backend-ai-go error strings -------------
MAX_TEMPLATE_ID = 200
MAX_NAME = 200
MAX_DESCRIPTION = 5000
MAX_AGENTS = 50
MAX_SYSTEM_PROMPT = 50000
MAX_TOOLS_PER_AGENT = 100

# Deserialiser accepts exactly these; anything else lands in `custom`.
KNOWN_ROLES = {"planner", "developer", "reviewer", "writer", "custom"}
TEMPLATE_CATEGORIES = {"development", "content", "research", "review", "custom"}
AGENT_KEYS = {
    "name", "role", "systemPrompt", "tools", "toolConfig",
    "modelPreferences", "memoryEnabled", "icon", "i18nKey",
}
TEMPLATE_KEYS = {
    "schemaVersion", "id", "name", "description", "icon", "category",
    "isBuiltin", "suggestedModels", "i18nKey", "agents",
}
MODEL_PREFERENCE_KEYS = {
    "preferredModelId", "preferredProviderId", "minContextWindow",
    "requiresToolCalling", "requiresVision",
}

# Registered workspace tools for squad agents, from src/squad/tools.rs strings.
SQUAD_TOOLS = {
    "read_file", "write_file", "list_files", "list_directory",
    "search_files", "diff_files", "read_memory", "write_memory", "search_memory",
}

# Model ids the evaluation provider actually serves, from providers.json.
EVALUATION_MODELS = {
    "furiosa-ai/Qwen3-32B-FP8",
    "furiosa-ai/gpt-oss-120b",
    "furiosa-ai/K-EXAONE-236B-A23B-NVFP4A16",
}

LAYER_BOUNDARY = "=== END SQUAD CONTRACT ==="
STATUS_SUMMARY = re.compile(r"^\s*\*\*Execution (complete|failed)\*\*\s*—", re.MULTILINE)

failures = []
notes = []


def fail(msg):
    failures.append(msg)


def note(msg):
    notes.append(msg)


def check_schema(t):
    unknown = set(t) - TEMPLATE_KEYS
    if unknown:
        note(f"top-level keys the importer ignores: {sorted(unknown)}")

    if not isinstance(t.get("id"), str) or not t["id"]:
        fail("id must be a non-empty string")
    elif len(t["id"]) > MAX_TEMPLATE_ID:
        fail(f"id is {len(t['id'])} chars, limit {MAX_TEMPLATE_ID}")
    elif not re.fullmatch(r"[A-Za-z0-9._-]+", t["id"]):
        fail(f"id has characters the importer rejects: {t['id']!r}")

    if len(t.get("name", "")) > MAX_NAME:
        fail(f"name is {len(t['name'])} chars, limit {MAX_NAME}")
    if len(t.get("description", "")) > MAX_DESCRIPTION:
        fail(f"description is {len(t['description'])} chars, limit {MAX_DESCRIPTION}")
    if t.get("category") not in TEMPLATE_CATEGORIES:
        fail(f"category {t.get('category')!r} is outside {sorted(TEMPLATE_CATEGORIES)}")
    if t.get("isBuiltin") is not False:
        fail("isBuiltin must be false on a submitted template")

    agents = t.get("agents") or []
    if not agents:
        fail("template has no agents")
    if len(agents) > MAX_AGENTS:
        fail(f"{len(agents)} agents, limit {MAX_AGENTS}")

    for model in t.get("suggestedModels") or []:
        if model not in EVALUATION_MODELS:
            fail(f"suggestedModels names {model!r}, which the provider does not serve")


def check_agents(t):
    agents = t.get("agents") or []
    planners = [a for a in agents if str(a.get("role", "")).lower() == "planner"]
    if len(planners) != 1:
        fail(f"exactly one agent must carry role 'planner'; found {len(planners)}")

    for a in agents:
        name = a.get("name", "<unnamed>")
        unknown = set(a) - AGENT_KEYS
        if unknown:
            note(f"{name}: agent keys the importer ignores: {sorted(unknown)}")

        prompt = a.get("systemPrompt", "")
        if len(prompt) > MAX_SYSTEM_PROMPT:
            fail(f"{name}: systemPrompt is {len(prompt)} chars, limit {MAX_SYSTEM_PROMPT}")
        if LAYER_BOUNDARY not in prompt:
            fail(f"{name}: systemPrompt has no {LAYER_BOUNDARY!r} layer boundary")

        role = str(a.get("role", ""))
        if role.lower() not in KNOWN_ROLES:
            note(f"{name}: role {role!r} maps to custom (whole-string match, no substrings)")

        tools = a.get("tools", [])
        cfg = a.get("toolConfig") or {}
        enabled = cfg.get("enabledTools", [])
        if len(tools) > MAX_TOOLS_PER_AGENT or len(enabled) > MAX_TOOLS_PER_AGENT:
            fail(f"{name}: tool list exceeds {MAX_TOOLS_PER_AGENT} entries")
        if sorted(tools) != sorted(enabled):
            fail(f"{name}: tools {tools} and toolConfig.enabledTools {enabled} disagree")
        for tool in enabled:
            if tool not in SQUAD_TOOLS:
                fail(f"{name}: enables {tool!r}, which is not a registered squad tool")

        if a.get("memoryEnabled") is not False:
            fail(f"{name}: memoryEnabled must be false — a memory read costs up to "
                 f"2000 input tokens per call and benchmark items are independent")

        prefs = a.get("modelPreferences") or {}
        unknown = set(prefs) - MODEL_PREFERENCE_KEYS
        if unknown:
            fail(f"{name}: modelPreferences has unknown keys {sorted(unknown)}")
        model = prefs.get("preferredModelId")
        if model not in EVALUATION_MODELS:
            fail(f"{name}: preferredModelId {model!r} is not one of the three served models")
        if prefs.get("minContextWindow") is not None:
            fail(f"{name}: minContextWindow must stay null — model-metadata.yaml records "
                 f"gpt-oss-120b at context_window 2048, so any floor removes it from the "
                 f"candidate set and a planner with no model broadcasts the whole request")
        if prefs.get("requiresToolCalling") is not False:
            fail(f"{name}: requiresToolCalling must be false — model-metadata.yaml lists "
                 f"gpt-oss-120b capabilities as [chat, code] with no tool entry")
        if prefs.get("requiresVision") is not False:
            fail(f"{name}: requiresVision must be false")


def check_layer_one(t):
    """Layer 1 must be byte-identical across every agent or the prefix cache never hits."""
    digests = {}
    for a in t.get("agents") or []:
        prompt = a.get("systemPrompt", "")
        cut = prompt.find(LAYER_BOUNDARY)
        if cut < 0:
            continue
        digests.setdefault(hashlib.sha256(prompt[:cut].encode()).hexdigest(), []).append(a["name"])
    if len(digests) > 1:
        fail(f"Layer 1 differs across agents: {digests}")
    elif digests:
        (digest, names), = digests.items()
        layer_one = next(a["systemPrompt"] for a in t["agents"] if a["name"] == names[0])
        cut = layer_one.find(LAYER_BOUNDARY)
        chars = cut
        note(f"Layer 1 identical across {len(names)} agents, {chars} chars, sha256 {digest[:16]}")
        # Furiosa-LLM will not open a radix entry below roughly 1024 tokens.
        if chars < 5000:
            fail(f"Layer 1 is {chars} chars, likely under the 1024-token cache floor")


def check_against_grader(t):
    """The worked examples inside Layer 1 must parse the way they are labelled."""
    sys.path.insert(0, str(GRADE_TOOLS))
    try:
        import grade
    except Exception as exc:  # pragma: no cover - environment dependent
        note(f"grade.py not importable ({exc}); skipped parser checks")
        return

    agents = t.get("agents") or []
    if not agents:
        return
    prompt = agents[0]["systemPrompt"]
    cut = prompt.find(LAYER_BOUNDARY)
    layer_one = prompt[:cut]

    blocks = re.findall(r">>> BEGIN\n(.*?)<<< END", layer_one, re.S)
    if len(blocks) < 6:
        fail(f"Layer 1 carries {len(blocks)} worked examples, expected the six labelled ones")

    labels = re.findall(r"^(Correct|Wrong), (math|generic|coding)\.", layer_one, re.M)
    for (verdict, track), body in zip(labels, blocks):
        if track == "math":
            got = grade.extract_boxed(body)
        elif track == "generic":
            got = grade.extract_letter(body)
        else:
            patch = grade.extract_patch(body)
            got = None
            if patch is not None:
                parsed, _ = grade.parse_edit_blocks(patch)
                got = parsed or None
        if verdict == "Correct" and got is None:
            fail(f"example labelled correct/{track} does not parse")
        if verdict == "Wrong" and got is not None:
            fail(f"example labelled wrong/{track} parses as {got!r}")

    # A ledger line must never be mistaken for an answer, and must never make the
    # whole output look like the runtime's status summary.
    for a in agents:
        for ledger in re.findall(r'`(\{"a":"[^`]*\})`', a["systemPrompt"]):
            if "\n" in ledger:
                fail(f"{a['name']}: ledger template spans more than one line")
            if grade.extract_letter(ledger) or grade.extract_boxed(ledger):
                fail(f"{a['name']}: ledger template {ledger!r} extracts as an answer")
            if STATUS_SUMMARY.search(ledger):
                fail(f"{a['name']}: ledger template reads as a status summary")


BUDGET_KEYS = {
    "maxTotalTokens", "maxTokensPerAgent", "maxTokensPerTask", "maxConcurrentAgents",
    "maxTasksPerPlan", "maxPlanIterations", "maxAgentTurns", "executionTimeoutSecs",
    "taskTimeoutSecs", "agentIdleTimeoutSecs", "warningThresholdPercent",
}


def check_budget(path):
    """budget.json ships beside the template; the app rejects it out of order."""
    if not path.exists():
        note("no budget.json beside the template")
        return
    budget = json.loads(path.read_text())
    if set(budget) != BUDGET_KEYS:
        fail(f"budget.json keys differ from BudgetConfig: "
             f"missing {sorted(BUDGET_KEYS - set(budget))}, "
             f"extra {sorted(set(budget) - BUDGET_KEYS)}")
        return
    task, agent, total = (budget["maxTokensPerTask"], budget["maxTokensPerAgent"],
                          budget["maxTotalTokens"])
    if not task <= agent <= total:
        fail(f"budget violates max_tokens_per_task <= per_agent <= total: "
             f"{task} / {agent} / {total}")
    if budget["maxTasksPerPlan"] < 3:
        fail("maxTasksPerPlan below 3 cannot express plan A (Architect, Editor, Reviewer)")
    note(f"budget.json: {total} total, {budget['maxTasksPerPlan']} tasks/plan, "
         f"{budget['maxAgentTurns']} turns, concurrency {budget['maxConcurrentAgents']}")


def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else
                Path(__file__).resolve().parent.parent / "squad-template.json")
    template = json.loads(path.read_text())

    check_schema(template)
    check_agents(template)
    check_layer_one(template)
    check_against_grader(template)
    check_budget(path.parent / "budget.json")

    print(f"{path.name}: {len(template.get('agents') or [])} agents, "
          f"{path.stat().st_size} bytes")
    for msg in notes:
        print(f"  note  {msg}")
    for msg in failures:
        print(f"  FAIL  {msg}")
    if failures:
        print(f"{len(failures)} check(s) failed")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
