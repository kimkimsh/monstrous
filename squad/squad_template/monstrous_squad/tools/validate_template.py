#!/usr/bin/env python3
"""Validate a Squad Template JSON against Backend.AI GO 1.12.1 import rules and
against the hackathon grader in docs/resource/example_task/tools/grade.py.

Every check here corresponds to a limit read out of the app binary
(/Applications/Backend.AI GO.app/Contents/MacOS/backend-ai-go), to a parser
function in grade.py / extract.py, or to a measured failure in a recorded run.

    python3 tools/validate_template.py squad-template.json

Exit code 0 when every check passes, 1 otherwise.
"""

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
REQUIRED_TEMPLATE_KEYS = (
    "id", "name", "description", "icon", "category", "isBuiltin",
    "suggestedModels", "agents",
)
REQUIRED_AGENT_KEYS = ("name", "role", "systemPrompt", "tools", "memoryEnabled", "icon")

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

# squad-template.min.json is the import fallback: the same template with these two
# fields emptied. Any other divergence means the fallback is not a fallback.
MIN_EMPTIED = ("disabledTools", "toolPermissionOverrides")
PROMPT_TRACKS = ("coding", "math", "generic")
STATUS_SUMMARY = re.compile(r"^\s*\*\*Execution (complete|failed)\*\*\s*—", re.MULTILINE)
# The planner reads this line first and it decides which agent answers the item.
PLANNER_LINE = re.compile(r"^PLANNER: .*?assign it to (\w+)", re.S)
# The planner copies from this line down; it is the only boundary between text addressed to
# the planner and text that has to reach the worker byte for byte.
ITEM_DELIMITER = "--- ITEM ---"

failures = []
notes = []


def fail(msg):
    failures.append(msg)


def note(msg):
    notes.append(msg)


def load_grader():
    sys.path.insert(0, str(GRADE_TOOLS))
    try:
        import grade
    except Exception as exc:  # noqa: BLE001 - the reason is reported, not swallowed
        return None, exc
    return grade, None


def grader_reads(grade, text):
    """What the three graders would pull out of `text` if a model echoed it.

    Returns a list of (track, extracted) for every extractor that fires. The whole
    point of the check is that this list is empty: a system prompt that contains a
    literal answer line hands the grader that line whenever a model reproduces any
    part of its own instructions, and the run that scored 0.0925 shipped five
    prompts that each yielded 'C' and '204800'.
    """
    hits = []
    letter = grade.extract_letter(text)
    if letter is not None:
        hits.append(("generic", letter))
    boxed = grade.extract_boxed(text)
    if boxed is not None:
        hits.append(("math", boxed))
    patch = grade.extract_patch(text)
    if patch is not None:
        blocks, _ = grade.parse_edit_blocks(patch)
        if blocks:
            hits.append(("coding", f"{len(blocks)} block(s)"))
    return hits


def check_schema(t):
    unknown = set(t) - TEMPLATE_KEYS
    if unknown:
        note(f"top-level keys the importer ignores: {sorted(unknown)}")

    for key in REQUIRED_TEMPLATE_KEYS:
        if key not in t:
            fail(f"top-level key {key!r} is missing")
    if t.get("schemaVersion") != 1:
        fail(f"schemaVersion is {t.get('schemaVersion')!r}; the importer rejects "
             f"anything newer than the version it supports")

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

    models = set()
    for a in agents:
        name = a.get("name", "<unnamed>")
        unknown = set(a) - AGENT_KEYS
        if unknown:
            note(f"{name}: agent keys the importer ignores: {sorted(unknown)}")
        for key in REQUIRED_AGENT_KEYS:
            if key not in a:
                fail(f"{name}: agent key {key!r} is missing")

        prompt = a.get("systemPrompt", "")
        if len(prompt) > MAX_SYSTEM_PROMPT:
            fail(f"{name}: systemPrompt is {len(prompt)} chars, limit {MAX_SYSTEM_PROMPT}")

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
        # build_tools_for_agent calls the model with no tools only while
        # effective_enabled_tools returns empty. One entry here re-opens the path
        # where the answer is written to a workspace file and the response carries
        # only a summary; two runs on this machine died that way.
        if enabled:
            fail(f"{name}: enabledTools must be empty, has {enabled}")

        if a.get("memoryEnabled") is not False:
            fail(f"{name}: memoryEnabled must be false — a memory read costs up to "
                 f"2000 input tokens per call, benchmark items are independent, and a "
                 f"recorded run memorised a wrong answer and reused it")

        prefs = a.get("modelPreferences") or {}
        unknown = set(prefs) - MODEL_PREFERENCE_KEYS
        if unknown:
            fail(f"{name}: modelPreferences has unknown keys {sorted(unknown)}")
        model = prefs.get("preferredModelId")
        if model not in EVALUATION_MODELS:
            fail(f"{name}: preferredModelId {model!r} is not one of the three served models")
        models.add(model)
        if prefs.get("minContextWindow") is not None:
            fail(f"{name}: minContextWindow must stay null — the resolver never reads it, "
                 f"and a planner left with no model broadcasts the whole request to "
                 f"every agent")
        if prefs.get("requiresToolCalling") is not False:
            fail(f"{name}: requiresToolCalling must be false")
        if prefs.get("requiresVision") is not False:
            fail(f"{name}: requiresVision must be false")

    if len(models) > 1:
        note(f"template spans {len(models)} models: {sorted(models)}. The submitted run that "
             f"assigned a second model saw it serve 6 of 1192 requests, so routing to it is "
             f"not reliable")


def check_planner_names_its_team(t):
    """create_task takes an agent id ("ID of the agent to assign this task to", from the tool
    schema in the app binary), and the planner reads that id off its team roster, which prints
    `**<name>** (ID: ...)`. So the routing instruction has to name the agent, or the planner has
    no way to pick the right line."""
    agents = t.get("agents") or []
    planner = next((a for a in agents if str(a.get("role", "")).lower() == "planner"), None)
    if planner is None:
        return
    prompt = planner.get("systemPrompt", "")
    workers = [a["name"] for a in agents if a is not planner]
    missing = [w for w in workers if w not in prompt]
    if missing:
        fail(f"{planner['name']}: systemPrompt never names {missing}, so the planner has no "
             f"instruction that routes work there")
    if ITEM_DELIMITER not in prompt:
        fail(f"{planner['name']}: systemPrompt never mentions {ITEM_DELIMITER!r}, which is the "
             f"boundary the one-shot prompts tell it to copy from")
    note(f"planner {planner['name']!r} routes to {workers}, copies from {ITEM_DELIMITER!r}")


def check_no_extractable_answer(t):
    """No system prompt may contain a string the grader itself reads as an answer.

    This is the invariant the previous template broke. Its five prompts each carried a
    worked example whose bare `ANSWER: C` line and boxed 204800 are matched by the
    grader's own regexes, so any model that echoed a fragment of its instructions
    handed those in as the answer.
    """
    grade, exc = load_grader()
    if grade is None:
        fail(f"grade.py not importable ({exc}); the parser checks did not run, so this "
             f"template is unvalidated against the grader")
        return
    for a in t.get("agents") or []:
        for track, value in grader_reads(grade, a.get("systemPrompt", "")):
            fail(f"{a.get('name')}: systemPrompt is read by the {track} grader as {value!r}; "
                 f"an echoed prompt would be submitted as the answer")
    note("no agent systemPrompt is extractable by any of the three graders")

    # A ledger line must never be mistaken for an answer, and must never make the
    # whole output look like the runtime's status summary.
    for a in t.get("agents") or []:
        for ledger in re.findall(r'(\{"a":"[^\n`]*?\})', a.get("systemPrompt", "")):
            if grader_reads(grade, ledger):
                fail(f"{a.get('name')}: ledger template {ledger!r} extracts as an answer")
            if STATUS_SUMMARY.search(ledger):
                fail(f"{a.get('name')}: ledger template reads as a status summary")


def check_tool_denials(t):
    """disabledTools and toolPermissionOverrides are a record, so keep them coherent."""
    for a in t.get("agents") or []:
        cfg = a.get("toolConfig") or {}
        denied, perms = cfg.get("disabledTools") or [], cfg.get("toolPermissionOverrides") or {}
        if set(denied) != set(perms):
            fail(f"{a.get('name')}: disabledTools and toolPermissionOverrides list "
                 f"different tools ({len(denied)} vs {len(perms)})")
        wrong = sorted(k for k, v in perms.items() if v != "never_allow")
        if wrong:
            fail(f"{a.get('name')}: toolPermissionOverrides not never_allow for {wrong}")


def check_one_shot_prompts(path, t):
    """add_prompt/ is the submitted set; the harness copy must not drift from it."""
    grade, _ = load_grader()
    src = path.parent / "add_prompt"
    harness = REPO / "docs" / "resource" / "example_task" / "prompts"
    names = {a.get("name") for a in t.get("agents") or []}
    if not src.is_dir():
        note("no add_prompt/ beside the template; one-shot prompts not checked")
        return
    for track in PROMPT_TRACKS:
        a = src / f"{track}.txt"
        if not a.exists():
            fail(f"add_prompt/{track}.txt is missing")
            continue
        text = a.read_text()
        if text.count("{{TASK}}") != 1:
            fail(f"add_prompt/{track}.txt has {text.count('{{TASK}}')} {{{{TASK}}}} "
                 f"placeholders; the composer substitutes every one, so two doubles the item")
        if not text.rstrip().endswith("{{TASK}}"):
            fail(f"add_prompt/{track}.txt does not end with {{{{TASK}}}}; the item has to "
                 f"land last so the stable prefix stays cacheable")
        if text.count(ITEM_DELIMITER) != 1:
            fail(f"add_prompt/{track}.txt has {text.count(ITEM_DELIMITER)} {ITEM_DELIMITER!r} "
                 f"lines; the planner copies from that boundary, so it must occur exactly once")
        elif text.index("{{TASK}}") < text.index(ITEM_DELIMITER):
            fail(f"add_prompt/{track}.txt puts {{{{TASK}}}} above {ITEM_DELIMITER!r}; the item "
                 f"would then sit in the half addressed to the planner and never be copied")
        match = PLANNER_LINE.match(text)
        if not match:
            fail(f"add_prompt/{track}.txt does not open with a PLANNER line naming an agent; "
                 f"the planner is the first and sometimes only reader of this text")
        elif match.group(1) not in names:
            fail(f"add_prompt/{track}.txt routes to {match.group(1)!r}, which is not an agent "
                 f"in this template ({sorted(names)})")
        if grade is not None:
            for kind, value in grader_reads(grade, text):
                fail(f"add_prompt/{track}.txt is read by the {kind} grader as {value!r}")
        b = harness / f"{track}.txt"
        if not b.exists():
            fail(f"docs/resource/example_task/prompts/{track}.txt is missing")
        elif b.read_text() != text:
            fail(f"docs/resource/example_task/prompts/{track}.txt differs from "
                 f"add_prompt/{track}.txt — the submitted prompt and the one the local "
                 f"harness measures are not the same text")
    note(f"one-shot prompts: {len(PROMPT_TRACKS)} tracks, one {{{{TASK}}}} each, PLANNER line "
         f"routes to a real agent, harness copy in sync, none extractable")


def check_min_variant(path):
    """The fallback must differ from the submission template in two fields, no more."""
    full, minimal = path.parent / "squad-template.json", path.parent / "squad-template.min.json"
    if path.name != full.name or not minimal.exists():
        return
    a, b = json.loads(full.read_text()), json.loads(minimal.read_text())
    for agent in b.get("agents", []):
        for field in MIN_EMPTIED:
            if agent.get("toolConfig", {}).get(field):
                fail(f"{agent.get('name')}: min variant still carries {field}")
    grafted = json.loads(minimal.read_text())
    for src, dst in zip(a.get("agents", []), grafted.get("agents", [])):
        for field in MIN_EMPTIED:
            dst["toolConfig"][field] = src["toolConfig"][field]
    if grafted != a:
        fail("squad-template.min.json differs from squad-template.json outside "
             f"{list(MIN_EMPTIED)} — rerun tools/make_min_template.py")
    else:
        note(f"min variant matches, emptying only {', '.join(MIN_EMPTIED)}")


BUDGET_KEYS = {
    "maxTotalTokens", "maxTokensPerAgent", "maxTokensPerTask", "maxConcurrentAgents",
    "maxTasksPerPlan", "maxPlanIterations", "maxAgentTurns", "executionTimeoutSecs",
    "taskTimeoutSecs", "agentIdleTimeoutSecs", "warningThresholdPercent",
}


def check_budget(path):
    """budget.json applies to a locally created squad only; the submission is the
    template plus the three prompts, so nothing here reaches the evaluation server."""
    if not path.exists():
        note("no budget.json beside the template")
        return
    budget = json.loads(path.read_text())
    if set(budget) != BUDGET_KEYS:
        fail(f"budget.json keys differ from BudgetConfig: "
             f"missing {sorted(BUDGET_KEYS - set(budget))}, "
             f"extra {sorted(set(budget) - BUDGET_KEYS)}")
        return
    for key, value in budget.items():
        if not isinstance(value, int) or isinstance(value, bool):
            fail(f"budget.json {key} is {value!r}, not an integer")
            return
    if not 0 <= budget["warningThresholdPercent"] <= 100:
        fail(f"warningThresholdPercent must be in [0, 100], got "
             f"{budget['warningThresholdPercent']}")
    task, agent, total = (budget["maxTokensPerTask"], budget["maxTokensPerAgent"],
                          budget["maxTotalTokens"])
    if not task <= agent <= total:
        fail(f"budget violates max_tokens_per_task <= per_agent <= total: "
             f"{task} / {agent} / {total}")
    if budget["maxTasksPerPlan"] > 2:
        fail(f"maxTasksPerPlan is {budget['maxTasksPerPlan']}; the plan is one task, and "
             f"headroom above two is headroom for the planner to split")
    if budget["maxPlanIterations"] != 1:
        fail("maxPlanIterations must be 1 — a re-plan re-reads the whole request")
    note(f"budget.json (local runs only): {total} total, {budget['maxTasksPerPlan']} tasks/plan, "
         f"{budget['maxAgentTurns']} turns, concurrency {budget['maxConcurrentAgents']}")


def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else
                Path(__file__).resolve().parent.parent / "squad-template.json")
    template = json.loads(path.read_text())

    check_schema(template)
    check_agents(template)
    check_planner_names_its_team(template)
    check_no_extractable_answer(template)
    check_tool_denials(template)
    check_one_shot_prompts(path, template)
    check_min_variant(path)
    check_budget(path.parent / "budget.json")

    print(f"{path.name}: {len(template.get('agents') or [])} agents, "
          f"{path.stat().st_size} bytes")
    for a in template.get("agents") or []:
        print(f"  {a.get('name'):<8} {len(a.get('systemPrompt','')):>6} chars  "
              f"role={a.get('role')}  {a.get('modelPreferences',{}).get('preferredModelId')}")
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
