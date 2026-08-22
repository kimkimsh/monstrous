"""AI:GO client for the harness — one squad agent, one item, one fresh session.

Everything goes through the `aigo` CLI with `-o json`. The planner path
(`aigo squad execute`) is deliberately unused: headless it accepts the
execution, writes an empty plan and never calls a model. `ask` drives the agent
directly instead.

    aigo squad session new  <squad> <agent>
    aigo squad message      <squad> <agent> <prompt>     -> turnId, not the answer
    aigo squad conversation <squad> <agent>              polled until it lands

`session new` rotates an agent's active session, it does not create the first
one: an agent that has never been started answers it with exit 7, "No active
session for agent ...", and every item then fails the same way. Start the agent
once before a batch.

The fresh session per item is mandatory. A reused session carries every earlier
question and answer into the next prompt: prompt tokens grow item over item, and
an earlier answer can leak into a later question. Measured over three math
items, 7,635 tokens shared against 2,940 isolated. That isolation is also why
AskResult's token counts are per item rather than cumulative — tokenUsage spans
the session, and the session holds this one exchange.

The polling trap: for a moment after `session new`, `squad conversation` still
serves the *previous* session, messages and tokenUsage included. Waiting for the
message count to grow therefore blocks until the timeout — observed as the full
300 s on every item. A turn counts as landed only when the conversation reports
the session id `session new` handed back, some user message starts with the
first MATCH_PREFIX_CHARS characters of the prompt, and the last message is the
assistant's.

`ask` never raises for an operational failure. A non-zero exit, unparseable
output or a timeout comes back as status "error" carrying the stderr tail, so a
batch records it and moves on. "error" and "no_reply" stay distinct: no_reply is
an assistant turn with empty content, error is a call that did not complete —
collapsing them scores an outage as a wrong answer.
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

POLL_SECONDS = 2.0
READ_TIMEOUT_SECONDS = 30.0
MATCH_PREFIX_CHARS = 60
ERROR_TAIL_CHARS = 400

# Discussion-room limits, both enforced server-side and both hit by real items.
# The request always goes in as a message, never as the topic: 39 of the 121
# practice requests are longer than the topic cap, and a single path is easier to
# reason about than a per-track branch.
DISCUSSION_TOPIC_MAX = 1024
DISCUSSION_MESSAGE_MAX = 65536
DISCUSSION_TERMINAL = ("completed", "cancelled", "error", "awaitingUser")
DISCUSSION_STRATEGIES = ("roundRobin", "brainstorm", "moderated", "autonomous")

STATUS_COMPLETED = "completed"
STATUS_NO_REPLY = "no_reply"
STATUS_CANCELLED = "cancelled"
STATUS_ERROR = "error"


def _chunk(text: str, limit_bytes: int) -> list[str]:
    """Split on line boundaries so a chunk never lands mid-token.

    Eight of the practice requests are longer than the server's message cap, all of
    them swebench context bundles. Splitting changes what the squad sees compared
    with one message, so it is worth knowing which items it happened to.
    """
    if len(text.encode("utf-8")) <= limit_bytes:
        return [text]
    chunks, current, size = [], [], 0
    for line in text.splitlines(keepends=True):
        line_size = len(line.encode("utf-8"))
        if size + line_size > limit_bytes and current:
            chunks.append("".join(current))
            current, size = [], 0
        current.append(line)
        size += line_size
    if current:
        chunks.append("".join(current))
    return chunks


def _conclusion_text(summary: Any) -> str:
    """Flatten the synthesized conclusion into the transcript's tail.

    The server stores whatever the synthesizing agent returned. When that agent
    answers with a JSON object instead of prose, the parse fails server-side and
    the whole blob lands in `summary` as a string while `keyPoints`, `decisions`
    and `actionItems` come back empty. Observed on discussion
    2356df2d-c098-427a-8706-ba61d033fb2b, whose summary string held the answer.
    """
    if isinstance(summary, str):
        summary = _maybe_json(summary)
    if not isinstance(summary, dict):
        return str(summary or "")

    inner = summary.get("summary")
    if isinstance(inner, str):
        parsed = _maybe_json(inner)
        if isinstance(parsed, dict):
            summary = {**summary, **parsed}

    lines = []
    if isinstance(summary.get("summary"), str):
        lines.append(summary["summary"])
    for key in ("keyPoints", "decisions"):
        for entry in summary.get(key) or []:
            lines.append(f"- {entry}")
    for item in summary.get("actionItems") or []:
        lines.append(f"- {item.get('description', '')}" if isinstance(item, dict)
                     else f"- {item}")
    return "\n".join(lines)


def _maybe_json(text: str) -> Any:
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text


def _conclusion_tokens(summary: Any) -> tuple[int, int]:
    """Synthesis is billed separately: `discussion analytics` reports only the
    per-agent turns, so its total misses the conclusion call entirely. Measured on
    one room: analytics said 6,315/3,712 while the conclusion cost another
    2,168/978 on top."""
    usage = summary.get("tokenUsage") if isinstance(summary, dict) else None
    if not isinstance(usage, dict):
        return 0, 0
    return usage.get("promptTokens") or 0, usage.get("completionTokens") or 0


class AigoCliError(RuntimeError):
    """A CLI call that failed or returned something other than JSON."""


@dataclass
class SquadInfo:
    id: str
    name: str
    agent_count: int
    status: str


@dataclass
class AgentInfo:
    id: str
    name: str
    role: str
    model_id: str


@dataclass
class AskResult:
    text: str
    prompt_tokens: int | None
    completion_tokens: int | None
    seconds: float
    status: str
    error: str | None
    discussion_id: str | None = None
    turns: int | None = None
    speakers: tuple = ()


def _tail(text: str | None) -> str:
    return (text or "").strip()[-ERROR_TAIL_CHARS:]


def _label(value: Any) -> str:
    """Squad status and agent role arrive as {"type": ...} or {"type": "custom", "value": ...}."""
    if isinstance(value, dict):
        return value.get("value") or value.get("type") or ""
    return value or ""


def _wait(cancel: threading.Event | None, seconds: float) -> bool:
    """The poll sleep and the cancellation check are the same wait; True means cancelled."""
    if cancel is None:
        time.sleep(seconds)
        return False
    return cancel.wait(seconds)


def _turn_landed(conversation: dict, messages: list, session_id: str | None, head: str) -> bool:
    if not messages or messages[-1].get("role") != "assistant":
        return False
    reported = conversation.get("sessionId")
    if session_id and reported and reported != session_id:
        return False
    return any(m.get("role") == "user" and (m.get("content") or "").startswith(head)
               for m in messages)


class AigoClient:
    """Wraps the `aigo` CLI against one Management API endpoint.

    Endpoint and token are passed to the CLI as environment variables so the
    token never reaches the process argument list. Either one left empty is left
    out, which hands that choice back to the CLI's own flag/config/discovery
    chain.
    """

    def __init__(self, endpoint: str, token: str, cli: str = "aigo"):
        self._cli = cli
        self._env = dict(os.environ)
        if endpoint:
            self._env["BACKEND_AI_GO_ENDPOINT"] = endpoint
        if token:
            self._env["BACKEND_AI_GO_TOKEN"] = token

    def health(self) -> dict:
        return self._run("system", "health", timeout=READ_TIMEOUT_SECONDS)

    def squads(self) -> list[SquadInfo]:
        rows = self._run("squad", "list", timeout=READ_TIMEOUT_SECONDS)
        return [SquadInfo(id=row.get("id", ""),
                          name=row.get("name", ""),
                          agent_count=row.get("agentCount", 0),
                          status=_label(row.get("status")))
                for row in rows]

    def agents(self, squad_id: str) -> list[AgentInfo]:
        squad = self._run("squad", "show", squad_id, timeout=READ_TIMEOUT_SECONDS)
        agents = []
        for row in squad.get("agents") or []:
            preferences = row.get("modelPreferences") or {}
            agents.append(AgentInfo(id=row.get("id", ""),
                                    name=row.get("name", ""),
                                    role=_label(row.get("role")),
                                    model_id=preferences.get("preferredModelId") or ""))
        return agents

    def loaded_models(self) -> list[str]:
        payload = self._run("loaded", "list", timeout=READ_TIMEOUT_SECONDS)
        return [model.get("alias") or model.get("id", "")
                for model in payload.get("loaded") or []]

    def ensure_session(self, squad_id: str, agent_id: str) -> str | None:
        """Give the agent a session if it has none, so `ask` can rotate one per item.

        `squad session new` rotates an existing session; on an agent that has never
        been started it exits 7 with "No active session for agent ...". Every item
        would then fail. Call this once before a batch. Returns None on success, or
        the error text when the agent cannot be started at all.
        """
        try:
            self._run("squad", "session", "status", squad_id, agent_id,
                      timeout=READ_TIMEOUT_SECONDS)
            return None
        except AigoCliError:
            pass
        try:
            self._run("squad", "session", "start", squad_id, agent_id,
                      timeout=READ_TIMEOUT_SECONDS)
            return None
        except AigoCliError as error:
            return str(error)

    def run_discussion(self, squad_id: str, topic: str, prompt: str,
                       turn_budget: int, timeout: float,
                       strategy: str = "roundRobin", conclude: bool = True,
                       cancel: threading.Event | None = None,
                       on_poll: Callable[[float], None] | None = None) -> AskResult:
        """Run one request through the whole squad and return what the agents said.

        This is the squad-wide path. `squad execute` — the planner path the judge
        actually uses — accepts an execution headless and then never runs the
        planner: the plan stays `created` with zero tasks and the router request
        counter does not move. A discussion room is the only multi-agent surface
        that works outside the desktop app.

        `strategy` defaults to roundRobin because it picks the next speaker with
        `participants[turns_taken % count]` and spends no tokens doing it. moderated
        adds a consensus-gate call every third turn and autonomous adds one call per
        participant per turn, both of which also make the speaking order depend on a
        model's judgment — so a score change can no longer be attributed to the
        prompt alone.

        The returned text contains agent messages only. The request is posted as a
        user message, and it carries the REQUIRED OUTPUT block verbatim, including
        the literal `FINAL ANSWER: \\boxed{<answer>}` line; feeding that back to the
        grader would extract the answer out of the question.
        """
        started = time.monotonic()

        def elapsed():
            return time.monotonic() - started

        if cancel is not None and cancel.is_set():
            return AskResult("", None, None, 0.0, STATUS_CANCELLED, None)

        try:
            room = self._run("squad", "discussion", "create", "--json", json.dumps({
                "squadId": squad_id,
                "topic": topic[:DISCUSSION_TOPIC_MAX],
                "turnBudget": turn_budget,
            }), timeout=READ_TIMEOUT_SECONDS)
            discussion_id = room["id"]
        except (AigoCliError, KeyError, TypeError) as error:
            return AskResult("", None, None, elapsed(), STATUS_ERROR, str(error))

        try:
            self._run("squad", "discussion", "strategy", discussion_id, strategy,
                      timeout=READ_TIMEOUT_SECONDS)
            for chunk in _chunk(prompt, DISCUSSION_MESSAGE_MAX):
                self._run("squad", "discussion", "post", discussion_id,
                          "--message", chunk, timeout=READ_TIMEOUT_SECONDS)
            self._run("squad", "discussion", "start", discussion_id,
                      timeout=READ_TIMEOUT_SECONDS)
        except AigoCliError as error:
            return AskResult("", None, None, elapsed(), STATUS_ERROR, str(error),
                             discussion_id=discussion_id)

        room = None
        while True:
            if _wait(cancel, POLL_SECONDS):
                return AskResult("", None, None, elapsed(), STATUS_CANCELLED, None,
                                 discussion_id=discussion_id)
            if on_poll:
                on_poll(elapsed())
            try:
                room = self._run("squad", "discussion", "show", discussion_id,
                                 timeout=READ_TIMEOUT_SECONDS)
            except AigoCliError as error:
                return AskResult("", None, None, elapsed(), STATUS_ERROR, str(error),
                                 discussion_id=discussion_id)
            if room.get("status") in DISCUSSION_TERMINAL:
                break
            if elapsed() > timeout:
                return AskResult("", None, None, elapsed(), STATUS_ERROR,
                                 f"discussion still {room.get('status')} after {timeout:.0f}s",
                                 discussion_id=discussion_id)

        parts, speakers = [], []
        for message in room.get("messages") or []:
            author = message.get("author") or {}
            if author.get("type") != "agent":
                continue
            speakers.append(author.get("agentId", "?"))
            parts.append(str(message.get("content", "")))

        conclusion_in = conclusion_out = 0
        if conclude:
            try:
                summary = self._run("squad", "discussion", "conclude", discussion_id,
                                    timeout=timeout)
                parts.append(_conclusion_text(summary))
                conclusion_in, conclusion_out = _conclusion_tokens(summary)
            except AigoCliError:
                pass

        prompt_tokens = completion_tokens = None
        try:
            stats = self._run("squad", "discussion", "analytics", discussion_id,
                              timeout=READ_TIMEOUT_SECONDS)
            usage = stats.get("totalTokenUsage") or {}
            prompt_tokens = (usage.get("promptTokens") or 0) + conclusion_in
            completion_tokens = (usage.get("completionTokens") or 0) + conclusion_out
        except AigoCliError:
            pass

        text = "\n\n".join(part for part in parts if part.strip())
        return AskResult(
            text, prompt_tokens, completion_tokens, elapsed(),
            STATUS_COMPLETED if text.strip() else STATUS_NO_REPLY, None,
            discussion_id=discussion_id, turns=room.get("turnsTaken"),
            speakers=tuple(speakers),
        )

    def ask(self, squad_id: str, agent_id: str, prompt: str, timeout: float,
            cancel: threading.Event | None = None,
            on_poll: Callable[[float], None] | None = None) -> AskResult:
        """One prompt on a session of its own; token counts cover this item alone.

        `cancel` is checked before the first CLI call and again on every poll,
        so a stop request costs at most one in-flight `squad conversation`.
        `on_poll` receives the elapsed seconds each time round the loop. The
        deadline is tested once per poll, so a timeout overruns by up to
        POLL_SECONDS.
        """
        started = time.monotonic()
        if cancel is not None and cancel.is_set():
            return AskResult("", None, None, 0.0, STATUS_CANCELLED, None)

        try:
            session = self._run("squad", "session", "new", squad_id, agent_id, timeout=timeout)
            self._run("squad", "message", squad_id, agent_id, prompt, timeout=timeout)
        except AigoCliError as error:
            return AskResult("", None, None, time.monotonic() - started, STATUS_ERROR, str(error))

        session_id = session.get("sessionId")
        head = prompt[:MATCH_PREFIX_CHARS]
        deadline = started + timeout
        while True:
            if _wait(cancel, POLL_SECONDS):
                return AskResult("", None, None, time.monotonic() - started,
                                 STATUS_CANCELLED, None)
            if on_poll is not None:
                on_poll(time.monotonic() - started)
            try:
                conversation = self._run("squad", "conversation", squad_id, agent_id,
                                         timeout=timeout)
            except AigoCliError as error:
                return AskResult("", None, None, time.monotonic() - started,
                                 STATUS_ERROR, str(error))

            messages = conversation.get("messages") or []
            if _turn_landed(conversation, messages, session_id, head):
                usage = conversation.get("tokenUsage") or {}
                text = messages[-1].get("content") or ""
                return AskResult(text,
                                 usage.get("promptTokens"),
                                 usage.get("completionTokens"),
                                 time.monotonic() - started,
                                 STATUS_COMPLETED if text.strip() else STATUS_NO_REPLY,
                                 None)
            if time.monotonic() >= deadline:
                return AskResult("", None, None, time.monotonic() - started, STATUS_ERROR,
                                 f"no assistant reply within {timeout:g}s")

    def _run(self, *args: str, timeout: float) -> Any:
        try:
            proc = subprocess.run([self._cli, "-o", "json", *args], capture_output=True,
                                  text=True, timeout=timeout, env=self._env)
        except subprocess.TimeoutExpired:
            raise AigoCliError(f"`{' '.join(args[:3])}` timed out after {timeout:g}s")
        except OSError as error:
            raise AigoCliError(f"{self._cli}: {error}")

        if proc.returncode != 0:
            raise AigoCliError(_tail(proc.stderr) or _tail(proc.stdout)
                               or f"exit code {proc.returncode}")
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError:
            raise AigoCliError(_tail(proc.stderr) or _tail(proc.stdout) or "empty output")
