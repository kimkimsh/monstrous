**Monstrous Squad** is a three-agent squad that answers AI:GO benchmark items, plus a single-file viewer that reads the run logs and says which runs would have scored.

## The squad

```
item ──► Router ──create_task──► Coder    repository patches, from-scratch programs
                             └─► Solver   math, multiple choice, anything else
                                            └─► this output is what gets graded
```

Three agents, one model (`furiosa-ai/gpt-oss-120b`), one wave, two model calls per item.

**Why one wave.** The grader reads exactly one thing: the output of the last task. The runtime's own `finalResult` is a status summary and gets rejected, 28 times out of 28. So the task that writes the answer must be the last task, and every hop we put after it was measured losing the answer. An agent holding tools saved its answer to a workspace file and replied "done", and the grader never opens the workspace. A reviewer placed last rewrote an answer for a question it had no path to receive.

**Why not one agent.** Only the planner sees the request body, so that seat stays. Router and Solver split over prompt length: the patch-format rules the parser enforces take 7,698 characters, which a merged agent would carry through all 109 non-coding items of a 147-item hidden set. Head count is also a blast radius: when the planner call fails the app hands the whole request, median 63,812 bytes on coding, to every agent.

## The four questions in the brief

**Who reads the code.** Router, copying the request into the task character for character. A coding item's 60,000-character excerpt bundle will not fit, so it ranks excerpts by how directly the issue reaches them and copies about 32,000 characters. It never trims inside an excerpt; it drops a whole one.

**Who modifies it.** Coder, holding no tools. Any path or line number not in the text it received is invented, and an invented patch does not apply.

**Who verifies.** Nobody as a separate hop. Verification moved into the same response, where it costs no extra call: Solver re-derives its value a second way, Coder checks the sibling callers of what it touched. And into the build, as a program. `tools/validate_template.py` runs the grader's own extractors (`extract_letter`, `extract_boxed`, `extract_patch`) against all six prompt files and refuses to emit a template if any of them pulls an answer out of our instructions. That check exists because v1 failed it: feed those prompts to the extractors and you get `letter=C` and `boxed=204800`.

**When to give up.** No agent can decide it, because the plan graph is fixed before execution and has no conditional branch. So it is four rules. Router creates exactly one task, never replans, and stops copying at 32,000 characters. The worker cuts a long derivation off and writes its best current value, since a truncated response carries no answer line. And empty responses are banned, because with one wave there is no earlier wave to fall back to.

## What v1 cost us

v1 placed 23rd of 24, overall 0.0925. The leaderboard API gave us the autopsy. 1,192 requests, 8.1 per item. 5,368,135 input tokens, the most of any team. Five system prompts averaging about 3,670 tokens, which is 81% of that input. Of 76 task files on disk, the 63 the planner actually wrote mention the required answer format zero times.

v2 answers those line by line: three agents, one model, no shared preamble, `enabledTools: []` on every seat, memory off. Running the practice set through the new prompts gives about 294 requests and 2.12M tokens. That is an estimate, not a result. We have no score for it yet.

## The viewer

One HTML file. No install, no server, zero external requests. Drop a workspace folder on it.

The top gauge is the question it was built for: **AI:GO success against gradable.** The app counts a run finished when its tasks finish; the submission server counts it when the response body carries the required answer format. The gap between those two numbers is where the score goes.

Zero is not one thing either. The viewer splits it four ways and prints who fixes each, in words and not color alone: call rejected (config), undecided (checker), no answer format (prompt), not an item (nothing to fix). The first three come out of the denominator.

It draws nothing that is not in the logs, so there is no cache-hit rate and no per-task token chart; both fields are zero-filled or absent. Estimates are labeled, and the cut-line experiment says on screen that its loss figure is an upper bound.

It also corrected us. A fifth zero class, "contract not sent", had been blaming the runner for 8 runs. On screen those requests ran 83 to 499 bytes, and the contract clause alone is about 250, so it was never there to send. We deleted the class and gradable went from 6/15 to 12/22. Nothing improved; we had been counting wrong.

The redesign replaced every screen and changed no data. Parsing, verdict, aggregation, load and export are 1,105 lines copied byte for byte from the old viewer, and the build diffs them every run and refuses to emit if one line differs. Same folder in, same JSON export out, byte identical.
