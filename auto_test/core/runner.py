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

STATUS_COMPLETED = "completed"
STATUS_NO_REPLY = "no_reply"
STATUS_CANCELLED = "cancelled"
STATUS_ERROR = "error"


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
