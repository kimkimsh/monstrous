# 01. ponytail — 레포 분석

원본: `https://github.com/dietrichgebert/ponytail`, 버전 4.9.0, 파일 159개.

---

## 1. 무엇인가

> "Lazy senior dev mode for AI agents. The best code is the code you never wrote." — `package.json:4`

> "You show him fifty lines; he looks at them, says nothing, and replaces them with one. Ponytail puts him inside your AI agent." — `README.md:42-44`

기계적으로는 **순수 프롬프트 주입**이다. 훅 다섯 개가 전부 시스템 프롬프트에 텍스트를 덧붙일 뿐, 사용자 코드를 막는 코드는 레포 어디에도 없다. 유일하게 차단하는 것은 CI 스크립트 하나인데, 그것도 **레포 자신의 규칙 문구가 어댑터 사이에서 어긋나는 것**을 막는다(`scripts/check-rule-copies.js:73`).

## 2. 사다리 — 붙잡히는 첫 칸에서 멈춘다

> "Before writing any code, stop at the first rung that holds:
> 1. Does this need to be built at all? (YAGNI)
> 2. Does it already exist in this codebase? Reuse the helper, util, or pattern that's already here, don't re-write it.
> 3. Does the standard library already do this? Use it.
> 4. Does a native platform feature cover it? Use it.
> 5. Does an already-installed dependency solve it? Use it.
> 6. Can this be one line? Make it one line.
> 7. Only then: write the minimum code that works." — `AGENTS.md:5-13`

2번은 이슈 #217로 나중에 추가됐다. 3~5번이 **프로젝트 밖**에서 재사용하는 규칙인데 "내가 이미 여기에 쓰지 않았나"를 덮는 칸이 없었다는 것이다.

사다리 효과의 대표 사례(`README.md:48-55`): 날짜 선택기를 요청하면 에이전트가 flatpickr를 설치하고 래퍼 컴포넌트를 쓰고 스타일시트를 넣고 타임존 논의를 시작한다. ponytail 답은 `<input type="date">`다. 실측 **404줄 → 23줄**.

## 3. 사다리보다 먼저 오는 것 — 이해

> "The ladder runs after you understand the problem, not instead of it: read the task and the code it touches, trace the real flow end to end, then climb." — `AGENTS.md:15`

> "Never lazy about understanding the problem. The ladder shortens the solution, never the reading. … Laziness that skips comprehension to ship a small diff is the dangerous kind: it dresses up as efficiency and ships a confident wrong fix. Read fully, then be lazy." — `skills/ponytail/SKILL.md:97-101`

이 조항은 이슈 #245("Dangerously lazy")에 대응해 들어갔다. **"가장 짧은 diff가 이긴다"는 반사가 에이전트로 하여금 가장 가까운 증상을 때우게 만든다**는 것이다.

## 4. 이 레포에서 우리에게 가장 중요한 규칙 — 근본 원인

> "Bug fix = root cause, not symptom: a report names a symptom. Grep every caller of the function you touch and fix the shared function once — one guard there is a smaller diff than one per caller, and patching only the path the ticket names leaves a sibling caller still broken." — `AGENTS.md:17`

문구 설계가 영리하다.

> "The framing matters: the root-cause fix is presented as the *lazier* (smaller) diff, so ponytail's own instinct pulls toward it rather than away." — `benchmarks/results/2026-06-22-issue-245-217-comprehension.md:26-27`

**재현 과제가 우리 트랙과 사실상 같다.** `transfer()`와 `withdraw()`가 공유 `_debit()`를 통해 출금하는 `bank.py`. 버그 리포트는 **transfer**만 말한다. 게으른 수정은 `transfer()`에만 가드를 넣고 `withdraw()`는 계속 초과 인출한다. 채점기는 **리포트에 한 번도 나오지 않은 withdraw**를 실행한다.

이것이 SWE-bench의 `fail_to_pass` + `pass_to_pass` 구조 그 자체다.

측정된 효과가 이 레포 전체에서 가장 크다.

| 모델 | 근본 원인 수정률 (n=6) |
|---|---|
| Sonnet 4.6 | **1/6 → 6/6** |
| Opus 4.8 | **1/6 → 6/6** (4회 반복 유지) |
| Haiku 4.5 | 0/6 → 0~2/6 (잡음) |

그리고 **문구가 결정적이라는 대조군이 있다.**

> "pre-fix ponytail and a plain-prose version ('trace the flow end to end') both scored 0/3 on Opus; only the grep-the-callers directive moved it to 6/6" — `:51-53`

"흐름을 끝까지 따라가라"는 산문은 **0/3**이었고, "네가 건드리는 함수의 호출자를 전부 훑어라"는 조작적 지시가 **6/6**을 만들었다. 지시는 절차여야 한다.

## 5. 나머지 규칙

- **불필요한 추상 금지** — *"no interface with one implementation, no factory for one product, no config for a value that never changes"*(`SKILL.md:58`)
- **조건부 최소화** — *"Fewest files possible. Shortest working diff wins — but only once you understand the problem. The smallest change in the wrong place isn't lazy, it's a second bug."*(`SKILL.md:61`)
- **같은 크기면 엣지 케이스가 맞는 쪽** — *"lazy means less code, not the flimsier algorithm"*(`AGENTS.md:27`). 골프 방지 조항이다
- **멈추지 않는다** — *"Ship the lazy version and question it in the same response … Never stall on an answer you can default."*(`SKILL.md:62`). v1이 코드 대신 숙고를 냈고, 이 조항으로 소요 시간이 31% 줄었다
- **`ponytail:` 천장 주석** — 의도적으로 자른 모서리에 한계와 승급 경로를 적는다
- **안전 바닥** — *"Never simplify away: input validation at trust boundaries, error handling that prevents data loss, security measures, accessibility basics, anything explicitly requested."*(`SKILL.md:92-95`)

안전 바닥 네 항목은 **CI가 문자열로 고정**한다(`scripts/check-rule-copies.js:49-56`). 리워딩으로 조용히 사라지지 못하게 만든 것이다. 어떤 규칙이 지지 구조인지를 레포가 스스로 표시한 셈이다.

## 6. 안전 바닥의 실측 근거 — 이 레포의 핵심 주장

`safe-path` 과제(신뢰할 수 없는 파일명을 기준 디렉터리에 붙이기):

> "**yagni-oneliner** wrote the fewest lines (6) and went unsafe **once in four**, a `../../` filename escaped the directory. **ponytail** wrote ~9.5 lines and was safe **4/4**. The ~3 lines ponytail kept *were the path-traversal check*." — `benchmarks/results/2026-06-18-agentic.md:139-147`

같은 이야기가 `csv-sum`에서 한 번 더 나온다. 5줄짜리 제너레이터 표현식은 잘못된 행 하나에 죽고, 8줄짜리는 `try/except`로 감싼다. **차이 3줄이 안전 바닥이다.** 그리고 결정적인 문장:

> "Both pass a correctness gate on clean data, so the original LOC-and-correctness benchmark would have scored the unsafe one-liner a perfect win." — `2026-06-17-agentic-safety.md:92-114`

**"줄 수를 줄여라"를 판단 없이 밀면 가드가 잘린다.** 이것이 우리가 Editor 프롬프트에서 "최소"를 어떻게 정의해야 하는지에 대한 직접적인 경고다.

## 7. 측정치 — 그리고 레포 자신이 철회한 것들

### 현재 헤드라인

> "~54% less code (up to 94%) · ~20% cheaper · ~27% faster · 100% safe" — `README.md:28`

방법: headless Claude Code, Haiku 4.5, `tiangolo/full-stack-fastapi-template`, 한 줄짜리 기능 티켓 12개, n=4, LOC는 `git diff` 추가 줄. 과제당 기준선 191 LOC / 349k 토큰 / $0.097 / 69초.

| arm | LOC | 토큰 | 비용 | 시간 | 안전 |
|---|--:|--:|--:|--:|--:|
| ponytail | −54% | −22% | −20% | −27% | 100% (20/20) |
| caveman | −20% | +7% | +3% | +2% | 100% |
| yagni-oneliner | −33% | −14% | −21% | −30% | **95% (19/20)** |

### 철회·수정된 것

- **80~94% LOC 감소**(단발 벤치마크)는 레포가 직접 깎았다 — *"the bare-model baseline pads its answer with prose and options, so that gap is partly a conversational-baseline artifact."*(`README.md:84`)
- **450세션짜리 agentic 실험 전체가 오염으로 철회**됐다 — *"the ponytail plugin's `SessionStart` hook fired on every arm, so the 'baseline' was secretly running ponytail."*(`2026-06-17-agentic-safety.md:3-9`)
- **비용 47~77%는 42~75%로 정정**됐고, OpenAI 추론 모델에서는 **방향이 뒤집힌다** — gpt-5.4-mini 26.2% 더 비쌈, gpt-5.5 38.7% 더 비싸고 **더 느림**(`2026-06-17-cost-verification.md:63-85`)
- **로컬 3.2B 모델에서는 ponytail이 더 나쁘다** — LOC 137 vs 기준선 109. *"Ponytail does not transfer to llama3.2."*(`2026-06-15-llama3.2-local.md:41`)

### 근거 없는 채로 남은 것

`/ponytail-gain` 명령이 **이미 철회된 숫자를 여전히 출력한다** — "▼ 80–94%", "▼ 47–77%"(`skills/ponytail-gain/SKILL.md:30-33`). README는 고쳤는데 사용자에게 보이는 명령은 안 고쳤다. 레포 자신의 출력 규율(§B9)을 어긴 자리다.

**반대로 훔칠 만한 것도 명확하다.** 이 레포는 자기 계측기를 먼저 검증한다 — 알려진 정답 참조와 알려진 "게으르게 틀린" 참조를 둘 다 통과시켜야 API 호출을 시작한다(`benchmarks/agentic/README.md:71-72`). 그리고 **"나쁜 참조는 happy path에서는 맞고 적대적 입력에서만 불안전하게"** 설계한다(`:60-61`). 이것이 정확히 pass-to-pass를 깨는 탐침을 만드는 방법이다.

## 8. 우리 조건으로 옮길 때

**가장 큰 구조적 불일치를 먼저 적는다.** ponytail은 *"얼마나 지을 것인가"*를 최적화하고, 우리 과제는 *"고칠 줄을 제대로 찾았는가"*를 요구한다. ponytail의 LOC 승리는 거의 전부 **그린필드 과잉 설계 함정**(날짜 선택기 404→23)에서 나오는데, 발췌에서 버그를 고치는 과제에는 그런 함정이 없다. 레포 자신이 그렇게 적는다 — *"On irreducible code the arms converge. Backend CRUD endpoints … are near-identical across all arms."*(`2026-06-18-agentic.md:109-111`)

**버그 픽스는 전부 irreducible code다. LOC 축에서 얻을 것은 거의 0이다.** 남는 것은 판단 쪽이고, 그쪽이 우리에게 정확히 맞는다.

| 규칙 | 판정 |
|---|---|
| 사다리 1번 YAGNI | **직행.** 원샷 패치 에이전트의 지배적 실패는 과잉 패치다 |
| 사다리 2번 "이미 이 코드베이스에 있나" | **직행. 이 조건에서 가장 값진 칸이다** — 발췌가 곧 코드베이스다 |
| 사다리 3~5번 stdlib / 플랫폼 / 설치된 의존성 | **수정 후 이식.** 순서를 뒤집는다 — 이미 import된 심볼 → 이미 import된 stdlib → 새 import(최후) → **서드파티는 절대 금지**. 새 import가 해석되는지 확인할 방법이 없다. 4번(네이티브 플랫폼)은 사실상 죽는다 |
| 사다리 6번 "한 줄로 만들어라" | **폐기. 그대로 넣으면 해롭다.** 이 레포가 측정한 유일한 안전 실패가 정확히 이 지시에서 나왔다. 그리고 우리는 LOC로 채점받지 않는다 |
| 사다리 7번 "동작하는 최소" | **직행.** 6번의 역할을 여기가 흡수한다 |
| 이해가 먼저 | **수정 후 이식 — 가장 중요.** "열어 볼" 파일이 없으므로 *"받은 발췌 전체를 먼저 읽고, 실패 테스트가 통과하는 호출 사슬을 추론하라"*로 바꾼다 |
| **근본 원인 / 호출자 전수** | **수정 후 이식 — 효과 크기가 가장 크다.** grep은 못 하지만 행동은 옮겨진다. *"리포트는 증상 하나를 말한다. 패치 전에 발췌 안에서 네가 바꿀 함수의 호출자를 전부 훑어라. 여러 경로가 공유 함수를 지나면 공유 함수를 한 번 고쳐라 — 그것이 더 작은 diff이면서 형제 호출자를 깨뜨리지 않는 수정이다."* 산문 버전은 0/3, 조작적 버전은 6/6이었다는 대조군을 기억할 것 |
| 불필요한 추상 금지 | **직행** |
| "Deletion over addition" | **위험. 그대로 쓰면 안 된다.** 그린필드에서 삭제는 "안 쓰는 것"이지만 패치에서 삭제는 **통과하던 테스트가 의존하는 코드를 없애는 것**이다. "새 줄을 더하기보다 있는 줄을 바꾸는 편을 택하라"로 바꾼다 |
| "Shortest working diff wins — but only once you understand the problem. The smallest change in the wrong place isn't lazy, it's a second bug." | **직행, 문장 그대로.** 이 레포에서 우리 목적에 가장 좋은 한 문장이다 |
| 멈추지 않는다 | **수정 후 이식.** "묻지 마라"만 남기고 "같은 응답에서 질문하라"는 버린다. 우리 출력은 패치뿐이다 |
| 같은 크기면 엣지 케이스가 맞는 쪽 | **직행, 그리고 지지 구조다.** 골프가 통과하던 테스트를 깨는 병리다 |
| `ponytail:` 천장 주석 | **폐기.** 주석 한 줄이 diff 표면을 늘리고 SEARCH 정확 일치를 깰 수 있다. 채점기는 이 관례를 모른다 |
| 출력 규율(코드 먼저, 3줄 이내) | **원리만 이식** — *"If the explanation is longer than the code, delete the explanation"*. 우리 출력 형식은 채점기가 정한다 |
| 안전 바닥 | **좁혀서 이식.** 접근성은 무의미하고 보안은 버그가 그것일 때만 관련된다. 옮길 것은 **모양**이다 — *"실패 테스트가 통과해야 할 것을 정의하고, 통과하던 테스트가 깨지지 않아야 할 것을 정의한다. 통과하던 테스트가 의존하는 것은 무엇도 단순화로 없애지 않는다."* |
| ONE runnable check | **폐기.** 채점기가 테스트를 준다. 우리가 테스트를 더하면 요청되지 않은 diff 표면이고 테스트 수집을 깰 수 있다 |
| 강도 lite/full/ultra | **폐기.** 한 턴짜리 에이전트에 강도는 하나다. 굳이 고르면 **ultra는 절대 아니다** — under-fix로 간다 |

## 9. 모델 의존성 경고

이 교리는 **모델이 다단계 절차를 실행할 여유가 있어야 작동한다.**

- Haiku 4.5는 근본 원인 탐침에서 **양쪽 arm 다 0/6**이었다 — *"it does not reliably execute the multi-step 'grep every caller, fix the shared function' instruction."*
- llama3.2 3.2B에서는 오히려 나빠진다.
- OpenAI 추론 모델에서는 비용이 반대로 간다.

우리 Patcher는 gpt-oss-120b이고 Architect도 같은 모델이다. **적어도 Haiku급은 아니지만, 이 규칙 묶음이 실제로 실행되는지는 §10-E6에서 재야 한다.**
