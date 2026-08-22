# 03. andrej-karpathy-skills — 레포 분석

원본: `https://github.com/multica-ai/andrej-karpathy-skills`
대조본: `https://github.com/forrestchang/andrej-karpathy-skills` (이 PC에 플러그인으로 설치돼 있음)
분석 시점 커밋: `2c606141936f1eeef17fa3043a72095b4765b9c2`

---

## 0. 두 포크는 같은 파일이다

`diff -r --exclude=.git` 결과 **차이 없음.** 추적 파일 9개 전부 SHA-256이 같고, 두 원격 모두 위 커밋에 있다. 설치된 플러그인 캐시(`~/.claude/plugins/cache/karpathy-skills/`)도 같은 SHA다. 즉 `andrej-karpathy-skills:karpathy-guidelines` 스킬로 로드되는 텍스트가 아래 인용문 그대로다.

multica-ai 쪽 매니페스트가 여전히 `"name": "forrestchang"`(`.claude-plugin/plugin.json:6`)이고 설치 안내도 `forrestchang/...`를 가리킨다(`README.md:105`). 같은 저자의 두 위치다.

**레포 전체가 9개 파일, 그중 5개가 문서다. 교리 본문은 `CLAUDE.md` 65줄이 전부고, 그것이 세 곳에 복제돼 있다.**

## 1. 무엇인가, 그리고 저자 문제

> "A single `CLAUDE.md` file to improve Claude Code behavior, derived from [Andrej Karpathy's observations](https://x.com/karpathy/status/2015883857489522876) on LLM coding pitfalls." — `README.md:7`

**Karpathy가 쓴 것이 아니다.** 레포가 스스로 그렇게 적어 놨다 — 제목이 "Karpathy-**Inspired** Claude Code Guidelines"(`README.md:1`)이고, 매니페스트도 *"derived from Andrej Karpathy's observations"*(`.claude-plugin/plugin.json:3`)라고 쓴다. 출처는 **X 게시물 하나**뿐이다. 참고문헌도 데이터도 없다.

원 게시물에서 인용한 세 문장이 이 교리의 뿌리다.

> "The models make wrong assumptions on your behalf and just run along with them without checking. They don't manage their confusion, don't seek clarifications, don't surface inconsistencies, don't present tradeoffs, don't push back when they should." — `README.md:15`

> "They really like to overcomplicate code and APIs, bloat abstractions, don't clean up dead code... implement a bloated construction over 1000 lines when 100 would do." — `README.md:17`

> "They still sometimes change/remove comments and code they don't sufficiently understand as side effects, even if orthogonal to the task." — `README.md:19`

## 2. 교리 전문 (`CLAUDE.md`)

전제: *"Tradeoff: These guidelines bias toward caution over speed. For trivial tasks, use judgment."* (`:5`)

### §1 Think Before Coding — "Don't assume. Don't hide confusion. Surface tradeoffs." (`:9`)

- `:12` State your assumptions explicitly. If uncertain, ask.
- `:13` If multiple interpretations exist, present them - don't pick silently.
- `:14` If a simpler approach exists, say so. Push back when warranted.
- `:15` If something is unclear, stop. Name what's confusing. Ask.

### §2 Simplicity First — "Minimum code that solves the problem. Nothing speculative." (`:19`)

- `:21` No features beyond what was asked.
- `:22` No abstractions for single-use code.
- `:23` No "flexibility" or "configurability" that wasn't requested.
- `:24` No error handling for impossible scenarios.
- `:25` If you write 200 lines and it could be 50, rewrite it.
- `:27` Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### §3 Surgical Changes — "Touch only what you must. Clean up only your own mess." (`:31`)

- `:34` Don't "improve" adjacent code, comments, or formatting.
- `:35` Don't refactor things that aren't broken.
- `:36` Match existing style, even if you'd do it differently.
- `:37` If you notice unrelated dead code, mention it - don't delete it.
- `:40` Remove imports/variables/functions that YOUR changes made unused.
- `:41` Don't remove pre-existing dead code unless asked.
- `:43` **The test: Every changed line should trace directly to the user's request.**

### §4 Goal-Driven Execution — "Define success criteria. Loop until verified." (`:47`)

- `:50` "Add validation" → "Write tests for invalid inputs, then make them pass"
- `:51` "Fix the bug" → "Write a test that reproduces it, then make it pass"
- `:52` "Refactor X" → "Ensure tests pass before and after"
- `:54-59` 단계마다 `→ verify:` 를 붙인 짧은 계획
- `:61` Strong success criteria let you loop independently.

### 교리의 자기 진단 기준

> "These guidelines are working if: fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes." — `CLAUDE.md:65`

**이 줄이 `skills/karpathy-guidelines/SKILL.md`에는 빠져 있다.** 세 복제본을 손으로 맞추라고 `CURSOR.md:28`이 적어 놨는데 이미 어긋났고, 하필 빠진 것이 교리 자신의 성공 지표다. 강제 장치 없는 동기화가 어떻게 되는지 보여주는 사례다.

## 3. 안티패턴 표 (`EXAMPLES.md:500-505`)

| 원칙 | 안티패턴 | 고침 |
|---|---|---|
| Think Before Coding | Silently assumes file format, fields, scope | List assumptions explicitly, ask for clarification |
| Simplicity First | Strategy pattern for single discount calculation | One function until complexity is actually needed |
| Surgical Changes | Reformats quotes, adds type hints while fixing bug | Only change lines that fix the reported issue |
| Goal-Driven | "I'll review and improve the code" | "Write test for bug X → make it pass → verify no regressions" |

근본 진단:

> "The 'overcomplicated' examples aren't obviously wrong—they follow design patterns and best practices. The problem is **timing**: they add complexity before it's needed." — `EXAMPLES.md:509`

> "**Good code is code that solves today's problem simply, not tomorrow's problem prematurely.**" — `EXAMPLES.md:522`

## 4. 워크드 예제 7개에서 눈여겨볼 두 가지

**하나 — 정답의 4/7이 코드가 아니라 대화다.** §1의 두 예제와 §4의 두 예제에서 "옳은 응답"은 질문 목록이거나 계획이다(`EXAMPLES.md:40-55`, `:73-93`, `:390-411`, `:427-452`). few-shot 재료로 쓰면 **질문을 내라고 가르치는 셈**이다.

**둘 — 4.3 예제는 오답과 정답의 프로덕션 코드가 바이트 단위로 같다.** `:463`과 `:491` 모두 `return sorted(scores, key=lambda x: (-x['score'], x['name']))`이고, 차이는 앞에 재현 테스트를 썼는지뿐이다. 이 교리가 실제로 최적화하는 것이 **결과물이 아니라 과정**이라는 가장 선명한 진술이고, 동시에 **원샷·도구 없는 채점기가 관측할 수 없는 차이**다.

가장 인용할 만한 diff는 3.2 스타일 드리프트다(`:341-364`). 로깅을 추가하면서 따옴표·타입힌트·불리언 반환 형태를 **원래대로 유지한** 예시이고, 닫는 줄이 이것이다 — *"Matched: Single quotes, no type hints, existing boolean pattern, spacing style."*(`:366`)

## 5. 강제 장치 — 없다

- 훅 0개. `grep -ri "hook"` 결과가 `.git/hooks/*.sample`뿐이다.
- 스크립트·실행 파일 0개. 9개 파일 전부 `644`, `.py`/`.sh`/`.js` 없음.
- CI 없음, 린터 없음, 테스트 없음.
- `plugin.json`이 선언하는 것은 `"skills": [...]` 하나. `hooks` 키가 없다.

기계적인 것은 둘뿐이고 **둘 다 전달 장치이지 검사 장치가 아니다** — Cursor의 `alwaysApply: true`(`.cursor/rules/karpathy-guidelines.mdc:3`), 그리고 스킬 `description`의 자동 로드 트리거.

## 6. 우리 조건으로 옮길 때 — 원샷, 도구 0개, SEARCH/REPLACE

우리 Editor·Architect가 놓인 조건은 셋이다. ① 물어볼 상대가 없다. ② 실행해서 확인할 방법이 없다. ③ SEARCH 텍스트는 원문과 바이트 단위로 같아야 한다.

세 조건이 이 교리의 절반을 살리고 절반을 죽인다.

| 섹션 | 판정 |
|---|---|
| **§3 Surgical Changes** | **거의 통째로 이식된다.** ③ 때문에 `:36`("Match existing style")은 예절이 아니라 **적용 실패를 막는 기계적 규칙**이 된다. SEARCH 안에서 따옴표 하나를 "고쳐" 쓰면 패치가 안 붙는다. `:43`("Every changed line should trace directly to the user's request")은 `the user's request`를 **`the failing test's assertion`**으로 한 단어만 바꾸면 **도구 없이 자기 출력에 돌릴 수 있는 유일한 수용 검사**가 된다 |
| **§2 Simplicity First** | 대부분 직행. 둘만 손본다. `:24`("No error handling for impossible scenarios")는 **불가능을 증명할 수단이 없으므로** 위험하다 — 발췌 밖 호출자를 못 보는데 가드를 지우면 통과하던 테스트가 깨진다. `:25`("200줄을 50줄로")는 **단위를 패치로 바꿔야** 한다. 발췌를 통째로 다시 쓰라는 뜻이 되면 REPLACE 블록이 커지고 적용 실패율이 오른다 |
| **§1 Think Before Coding** | **동사를 뒤집어야 이식된다.** "state your assumptions"는 살고 "ask"는 죽는다. 특히 `:15`("If something is unclear, stop … Ask")는 **전제가 항상 참**이다 — 발췌만 있으면 언제나 불명확하다. 그대로 넣으면 매 문항에서 발동해 패치 대신 질문을 낸다 |
| **§4 Goal-Driven Execution** | **거의 버린다.** 관측 루프를 전제로 쓰인 섹션인데 우리에겐 루프가 없다. `:51`("Write a test that reproduces it")은 **과제 문구와 정확히 일치해서 가장 잘 발동하는데 산출물이 틀렸다** — 테스트 파일은 채점 대상이 아니다. `:52`("Ensure tests pass before and after")는 **돌리지도 않고 돌렸다고 쓰게 만든다** |

정리하면 23개 규칙 중 **9개 직행 / 9개 수정 후 이식 / 5개 폐기**이고, 폐기 5개 중 **4개는 넣으면 해롭다**(`:15`, `:50`, `:51`, `:52`).

## 7. 시스템 프롬프트에 그대로 넣을 문장

전부 직행 판정만 골랐다. 마지막 두 줄은 `EXAMPLES.md`에서 왔다.

```
Minimum code that solves the problem. Nothing speculative.
No features beyond what was asked.
No abstractions for single-use code.
No "flexibility" or "configurability" that wasn't requested.
Touch only what you must. Clean up only your own mess.
Don't "improve" adjacent code, comments, or formatting.
Don't refactor things that aren't broken.
Match existing style, even if you'd do it differently.
If you notice unrelated dead code, mention it - don't delete it.
Don't remove pre-existing dead code unless asked.
Every changed line must trace directly to the failing test's assertion.
Would a senior engineer say this is overcomplicated? If yes, simplify.
The problem is timing: they add complexity before it's needed.
Good code is code that solves today's problem simply, not tomorrow's problem prematurely.
```

11번째 줄만 원문의 `the user's request`를 `the failing test's assertion`으로 바꿨다. 나머지는 원문 그대로다.

## 8. 이 레포가 못 다루는 것

9개 파일 어디에도 **패치 형식, hunk 크기, 컨텍스트 줄, 정확 일치 요구, 테스트 파일 건드리지 않기, 고칠 자리가 발췌 밖일 때** 에 대한 언급이 없다. 우리 조건에서 가장 자주 나는 기계적 실패 넷이 정확히 그것들이다. 이 레포에서 가져올 수 없고 **처음부터 우리가 써야 하는 부분**이다.
