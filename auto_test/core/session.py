"""Runs selected samples through one squad agent and aggregates the outcome.

Kept free of Qt so the run loop and the arithmetic can be tested without a
display. The GUI drives `run_items` from a worker thread and receives plain
dataclasses; it never reaches into this module's state.

The aggregation is the part worth reading carefully. Accuracy and token totals
have different denominators, and collapsing them hides which one moved:

    accuracy      graded + extraction_failed      a format miss is a real zero on
                                                  the portal, so it counts against us
    ungradable    swebench, format_ok             no local grader exists; excluded
                                                  rather than guessed at
    failed        CLI error, timeout, no reply    an outage is not a wrong answer;
                                                  counting it as one would make a
                                                  bad server look like a bad prompt
    tokens        every attempted item            spent is spent, including failures
"""
import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

from .grading import grade
from .runner import AigoClient

# Bounds the worst-case delay between pressing stop and the run halting: the
# stop flag is read between items and between polls, but an in-flight CLI call
# runs to its own timeout first. See PLAN.md.
ITEM_TIMEOUT_SECONDS = 300.0


@dataclass
class ItemResult:
    item_id: str
    track: str
    kind: str
    gradable: bool
    status: str            # completed | no_reply | cancelled | error
    outcome: str           # graded | extraction_failed | format_ok | skipped | not_run
    correct: bool | None
    detail: str
    output: str
    prompt_tokens: int | None
    completion_tokens: int | None
    seconds: float
    squad_id: str
    agent_id: str
    model_id: str
    error: str | None = None

    @property
    def label(self):
        """What the table shows in the outcome column."""
        if self.status in ("error", "no_reply", "cancelled"):
            return "실행 실패" if self.status != "cancelled" else "취소됨"
        if self.outcome in ("skipped", "format_ok"):
            return "채점 불가"
        if self.outcome == "extraction_failed":
            return "FAIL (형식)"
        return "PASS" if self.correct else "FAIL"


@dataclass
class Aggregate:
    graded: int = 0
    correct: int = 0
    extraction_failed: int = 0
    ungradable: int = 0
    failed: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    seconds: float = 0.0
    conditions: set = field(default_factory=set)

    @property
    def scored(self):
        """Accuracy denominator: answers the judge would have scored."""
        return self.graded + self.extraction_failed

    @property
    def accuracy(self):
        return self.correct / self.scored if self.scored else None

    @property
    def total_tokens(self):
        return self.prompt_tokens + self.completion_tokens

    @property
    def mixed_conditions(self):
        """True when rows came from more than one squad/agent/model combination,
        which makes a single accuracy number meaningless."""
        return len(self.conditions) > 1


def summarize(results):
    agg = Aggregate()
    for r in results:
        agg.seconds += r.seconds
        agg.prompt_tokens += r.prompt_tokens or 0
        agg.completion_tokens += r.completion_tokens or 0
        agg.conditions.add((r.squad_id, r.agent_id, r.model_id))

        if r.status in ("error", "no_reply", "cancelled"):
            agg.failed += 1
        elif r.outcome in ("skipped", "format_ok"):
            agg.ungradable += 1
        elif r.outcome == "extraction_failed":
            agg.extraction_failed += 1
        else:
            agg.graded += 1
            if r.correct:
                agg.correct += 1
    return agg


class RunLog:
    """One JSONL file per run, appended as each item finishes.

    Written per item rather than at the end because a full sweep takes tens of
    minutes; a crash or a closed window at minute 30 would otherwise lose
    everything. Each row is the shape `example_task/tools/grade.py` reads, so a
    run can be re-graded from the terminal without the GUI.
    """

    FIELDS = ("item_id", "track", "output", "status", "prompt_tokens",
              "completion_tokens", "wallclock_seconds")

    def __init__(self, directory, stamp=None):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        stamp = stamp or datetime.now().strftime("%Y%m%d-%H%M%S")
        self.path = directory / f"{stamp}.jsonl"
        self._handle = None

    def append(self, result):
        if self._handle is None:
            self._handle = open(self.path, "a", encoding="utf-8")
        row = {k: v for k, v in asdict(result).items() if k in self.FIELDS}
        row["wallclock_seconds"] = round(result.seconds, 1)
        self._handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        self._handle.flush()

    def close(self):
        if self._handle is not None:
            self._handle.close()
            self._handle = None


def run_items(client: AigoClient, squad_id, agent_id, model_id, samples,
              run_log=None, cancel=None, on_start=None, on_finish=None,
              item_timeout=ITEM_TIMEOUT_SECONDS):
    """Run samples one at a time, grading each as it lands.

    Sequential on purpose: one local model server serves these, so concurrent
    requests contend for the same slots and only add latency.

    `cancel` is a threading.Event. It is checked before each item and passed
    down to the client so a poll loop can break out of a long wait.
    """
    problem = client.ensure_session(squad_id, agent_id)
    if problem:
        raise RuntimeError(
            f"에이전트 세션을 열 수 없다 — {problem}\n"
            f"이 상태로는 모든 문항이 같은 이유로 실패하므로 시작하지 않는다.")

    results = []
    for sample in samples:
        if cancel is not None and cancel.is_set():
            break
        if on_start:
            on_start(sample)

        started = time.time()
        ask = client.ask(squad_id, agent_id, sample.prompt,
                         timeout=item_timeout, cancel=cancel)

        if ask.status == "completed":
            verdict = grade(sample, ask.text)
            outcome, correct, detail = verdict.outcome, verdict.correct, verdict.detail
        else:
            outcome, correct, detail = "not_run", None, ask.error or ask.status

        result = ItemResult(
            item_id=sample.id, track=sample.track, kind=sample.kind,
            gradable=sample.gradable, status=ask.status, outcome=outcome,
            correct=correct, detail=detail, output=ask.text,
            prompt_tokens=ask.prompt_tokens, completion_tokens=ask.completion_tokens,
            seconds=ask.seconds if ask.seconds else time.time() - started,
            squad_id=squad_id, agent_id=agent_id, model_id=model_id,
            error=ask.error,
        )
        results.append(result)
        if run_log:
            run_log.append(result)
        if on_finish:
            on_finish(result)
    return results
