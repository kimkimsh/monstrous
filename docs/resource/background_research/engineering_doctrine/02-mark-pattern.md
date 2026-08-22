# 02. mark-pattern — 레포 분석

원본: `https://github.com/kimkimsh/mark_pattern`
이 PC의 설치본(`~/.claude/plugins/marketplaces/mark-pattern`, `~/.claude/plugins/cache/mark-pattern/`)과 **바이트 단위로 같다**(`diff -r` exit 0). 커밋 `10180ea`, 버전 1.0.0.

파일 12개. 훅 0개, 스크립트 0개, MCP 0개 — **순수 프롬프트 지시로만 된 플러그인**이다.

---

## 1. 무엇인가

> "**A design discipline for Claude Code.** One command turns it on; from then on, Claude designs, reviews, and refactors under it." — `README.md:3`

설계 의도가 이 문장에 다 들어 있다.

> "Those are not knowledge gaps. The model knows what coupling is. It will still hand you a factory with one implementation. **mark-pattern is built out of gates and required fields — things that are either filled or not — rather than advice, which is negotiable.**" — `README.md:12`

**조언이 아니라 채워야 하는 칸으로 만든다.** 이 방법론 선택 자체가 우리에게 가장 중요한 시사점이다. 그리고 레포가 그 이유를 실험으로 댄다.

> "**Prohibitions backfire.** In head-to-head tests, a "don't do X" instruction produced *more* of the unwanted output than a positive recipe — and trended worse than no guidance at all. Agents negotiate with "don't". A recipe leaves nothing to negotiate." — `README.md:186`

> "**Shouting does not help.** Current models follow the system prompt more literally, so `CRITICAL: YOU MUST` now causes *over*triggering rather than compliance. There is none of it in here." — `README.md:190`

## 2. 세 개의 Move

### Move 1 — 추천에는 두 칸이 붙는다 (`SKILL.md:35-60`)

```
This makes ______ worse, because ______.
This flips when ______.
```

첫 줄의 근거:

> "if you cannot name what gets worse, you have not understood the trade, you have written sales copy. Every structural choice buys something with something. An interface buys substitutability with indirection. … Find the payment. It is always there." — `SKILL.md:50`

둘째 줄의 근거: **관측 가능한 조건이어야 한다.**

| ❌ | ✅ |
|---|---|
| "This flips when requirements change." | "This flips when a second payment provider is added." |
| "…when scale increases." | "…when p99 write latency exceeds the 200ms budget in the SLO." |

> "An unfillable field is a hard stop, not a warning. If neither line can be written honestly, the recommendation is not ready to make." — `SKILL.md:60`

**우리에게 결정적인 예외 조항이 하나 있다.**

> "**It does not apply to a bug fix that restores obviously-correct behavior** — adding a timeout, checking `res.ok`, writing the missing `else`. *"Makes worse: you have to pick a number"* is not a trade-off, it is ceremony, and printing it beside a four-line fix teaches the reader to skim the fields that matter." — `SKILL.md:41`

SWE-bench 문항의 정답은 대부분 이 예외에 해당한다. **두 칸을 예외 없이 요구하면 네 줄짜리 정답에 의식(ceremony)을 붙이게 된다.**

### Move 2 — 구조는 더하기 전에 지운다 (`SKILL.md:62-106`)

> "Run these in order. Removal first, always. This ordering is not stylistic: it is what keeps the skill from becoming a pattern dispenser." — `SKILL.md:64`

**2a 제거.** 벌지 못한 추상의 정의:

> "An abstraction is unearned when **no call site ever receives more than one concrete implementation through it.** Count call sites, not declarations." — `SKILL.md:68`

오탐을 막는 제외 규정이 중요하다 — TypeScript `interface Props`·`interface User` 같은 **데이터 타입**은 다형성 이음매가 아니다(`:72`). Go에서 소비자 쪽에 선언된 인터페이스는 관용구다(`:73`).

사냥 목록(`:77-82`): 팔이 하나인 factory, 하위 클래스가 하나인 base, 로직 없는 wrapper, 모든 환경에서 값이 같은 config knob, 등록이 하나인 registry, 테스트 mock 때문에 만든 인터페이스.

**2b 추가.** 라이선스:

> "New structure is licensed by **a second variation point that exists in the code today.** Not planned. Not likely. Present." — `SKILL.md:90`

```
The axis that varies:        ______
Instance 1 (file:line):      ______
Instance 2 (file:line):      ______
What breaks if I don't:      ______
This makes ______ worse:     ______
```

> "If you can only cite one, the answer is to write the direct code and wait. The second instance is what tells you where the seam actually goes — guessing it from one example is how you get an abstraction whose shape fits nothing." — `SKILL.md:102`

> "**Do not use pattern names as a justification.** "This is the Strategy pattern" is a description, never a reason." — `SKILL.md:106`

### Move 3 — 파일이 아니라 경로를 따라간다 (`SKILL.md:108-182`)

> "This finds the defect class a diff cannot show you, because every file in it is individually fine and the system still fails at the seam between them." — `SKILL.md:110`

> "The unit of analysis is a **path**: a value crossing a boundary." — `SKILL.md:112`

홉마다 표를 채운다: `hop | file:line | on success | on absence | on error | can the caller tell "no" from "couldn't check"? | who finds out`. **빈 칸이 곧 발견이다.**

#### 부재 분기는 정책이다

> "Nobody wrote a bug here. The default fell out of the syntax. Empty input silently means "proceed as normal," and no one ever decided that. Write the `else`, and write one line naming the policy it encodes." — `SKILL.md:127`

#### 실패 방향에는 정답이 없다 — 유도한다

> "\"Fail closed\" and \"fail open\" are both correct, in different places, *in the same codebase*." — `SKILL.md:133`

두 질문으로 유도한다 — **되돌릴 수 있나(reversible)**, **피해 반경이 얼마나 넓나(blast radius)**.

|  | 반경 좁음 | 반경 넓음 |
|---|---|---|
| **되돌릴 수 있음** | 낮춰서 계속. 세어 둔다 | 낮춰서 계속, 알린다 |
| **되돌릴 수 없음** | 거부. 이유를 호출자에게 | 거부. 알린다. **이것만은 조용하면 안 된다** |

> "Write the answer down for that specific operation. Do not carry it to the next one — the same application will need all four cells." — `SKILL.md:145`

## 3. 실패 경로 카탈로그 (`references/failure-paths.md`)

우리 Architect가 그대로 쓸 수 있는 부분이다. 전부 **발췌만 읽고 판단 가능**하다.

| # | 실패 모드 | 원인 | 처방 |
|---|---|---|---|
| 1 | **부재 분기** | `if data:` 에 `else`가 없다. 파서가 정책을 대신 정한다 | else를 쓰고, 그것이 인코딩하는 정책을 한 줄로 적는다 |
| 2 | **실패 방향이 틀림** | 집 스타일이나 직전 연산의 답을 그대로 가져옴 | 되돌림 가능성 × 피해 반경으로 연산마다 유도 |
| 3 | **과적재 센티널** | 한 함수에서 `return null`이 두 번, 뜻이 반대인 경로에서 | 타입을 넓힌다. "확인했고 아니다"와 "확인할 수 없었다"를 **다른 값**으로 |
| 4 | **보간된 config** | 미설정 환경변수가 `"undefined"`로 문자열화 → 요청 실패 → **진짜 장애와 같은 catch에 떨어진다** | URL·경로·셸 문자열 안 `${...}`를 전부 훑는다 |
| 5 | **계산했는데 아무도 안 읽음** | `isAuthorized`의 읽기 지점이 전부 로깅·직렬화·UI | 읽기 지점을 decision / telemetry / presentation / serialization으로 분류. **decision 0건이면 그 검사는 존재하지 않는 것** |
| 6 | **부재를 영영 감지 못함** | 죽은 의존이 "나 죽었다"를 보내 줄 리 없다 | 장수 프로세스면 타이머, 요청/응답이면 **호출에 타임아웃** |
| 7 | **시계 오용** | 벽시계가 뒤로 점프하면 구간 계산이 음수가 된다 | 프로세스 내부는 monotonic, 서비스 간은 `{value, observedAt, ttl}` |
| 8 | **거짓말하는 열화** | fallback이 성공 모양 데이터를 계속 낸다 | "지금 이게 켜져서 일주일 유지되면 누가 알아채나?"에 답이 있어야 한다 |
| 9 | **짝 없는 연산** | 여는 것은 모든 경로에서 닫아야 하는데 **에러 경로만 안 닫는다** | opener/closer 개수를 센다. 새는 쪽은 거의 항상 에러 경로 |
| 10 | **retry가 멱등성을 몰래 가정** | 재시도를 다는 순간 idempotent라고 주장한 것인데 아무도 안 적는다 | "첫 시도는 성공했고 ack만 유실됐다면?"에 답한다 |

3번(과적재 센티널)을 레포는 *"The single most common cross-boundary type defect"*(`:84`)라고 부른다.

## 4. 리뷰 패스 7개 (`references/review-passes.md`)

**발견 하나라도 내기 전에 세 가지를 먼저 한다.**

1. 이미 강제되는 것을 읽는다 — 린터·포매터·타입체커·CI. *"Everything a tool already enforces is **settled**. Do not re-report it."*(`:9`)
2. **중앙값 파일이 아니라 기준 구현을 찾는다.** *"the default instruction every coding agent carries — "follow existing conventions" — is a trap in a codebase where nine modules out of ten are the disease and one is the cure."*(`:11`)
3. **기준선을 세운다.** *"Report a finding only at ≥80% confidence that it is real and worth the reader's time. Cap the list at ten and rank by consequence. **"No structural findings" is a legitimate and expected result** — say it plainly rather than manufacturing a tenth item."*(`:13`)

패스 목록:

| # | 이름 | 찾는 것 |
|---|---|---|
| 1 | Directory names are claims, not evidence | 이름이 거짓말하는 디렉터리 |
| 2 | Duplicated contracts, not duplicated code | 코드는 안 겹치는데 **한쪽이 갈라져도 둘 다 컴파일되는** 계약 |
| 3 | The backstop's configuration | 코드엔 있는데 config에서 꺼져 있는 안전장치 |
| 4 | Computed but never read | decision 읽기 0건인 술어 |
| 5 | The path, not the file | Move 3 전체 |
| 6 | Repeated mistakes are one false belief | 같은 실수 5건 = 발견 5개가 아니라 **잘못된 믿음 1개** |
| 7 | Structure that never earned its place | 제거 규칙. **리뷰에서는 추상을 새로 제안하지 않는다** |

거짓 양성 목록(`:65-74`)이 특히 유용하다 — 스타일·명명·주석 밀도·매직 넘버·**함수 길이**·"테스트 추가하세요"·생성 코드·이름만 보고 추론한 문제·`consider` / `you might want to` 같은 헤지 표현. 전부 **보고하지 않는다**.

> "A finding that cannot be given a file and a line you actually opened is a hypothesis. Go open the file, or drop it." — `review-passes.md:98`

## 5. 안티패턴 7개 (`SKILL.md:225-246`)

1. **"We'll need the interface later."** → 두 번째 구현은 존재하지 않는다. 나중에 추가하면 리팩터 한 번이고, 지금 모양을 추측하면 **영구히 잘못된 자리에 이음매**가 박힌다.
2. **"An interface here is just cleaner."** → 누구에게, 어느 호출 지점에서? 없으면 "clean"은 "familiar-looking"이라는 뜻이다.
3. **"추상이 나쁘니 구조를 아예 안 쓴다."** → 오늘 변이점이 둘이면 규칙은 **충족된 것**이지 위반이 아니다. 그때 구조를 거부하는 것은 반대 방향의 같은 실패다.
4. **"테스트가 통과하니 리팩터는 안전하다."** → 테스트는 누군가 주장할 생각을 한 것만 담는다. 순서·타이밍·동시성을 건드렸다면 아무도 주장하지 않았고 green은 아무 뜻이 없다.
5. **"린터/워치독/retry가 잡아 줄 거다."** → config를 열어라. **Presence is not enforcement.**
6. **"You're right, that's a much better approach."** → *"agreement that arrives immediately after a user's detailed argument is the single most measurable failure mode in this whole skill. Before conceding, state the strongest case against the new position."*
7. **가중치 점수표.** → 가중치도 점수도 지어낸 것이고 합계가 판단을 산술로 세탁한다.

## 6. 답하기 전 자기 점검 (`SKILL.md:252-260`)

> "Run this against your draft. It is for you, not for the user — none of it is printed."

- [ ] 첫 화면에 행동 가능한 것이 있다
- [ ] Move 이름·표·이 스킬 언급이 출력에 없다
- [ ] 모든 구조 제안에 "makes ___ worse" 줄이 있고, **버그 픽스에는 없다**
- [ ] 모든 "flips when"이 관측 가능한 것을 가리킨다
- [ ] 제거가 추가보다 먼저 돌았다
- [ ] 새 추상마다 실재 인스턴스 두 개를 file:line으로 인용했다
- [ ] 실패 방향을 연산마다 유도했다. 직전 것을 물려받지 않았다
- [ ] 레포 린터가 이미 잡는 것을 보고하지 않았다
- [ ] 모든 구조 주장이 **내가 실제로 연** 파일과 줄을 인용한다

## 7. 정신 모델

> "A structure is a loan. The interface, the layer, the queue, the abstraction — each one lends you flexibility now and charges interest forever, in indirection, in hops, in the number of files someone has to open to understand one behavior." — `SKILL.md:264`

## 8. 우리 조건으로 옮길 때

### Architect가 가져갈 것 (직행)

경로 단위 분석(`SKILL.md:112`), 부재 분기 정책(`:127`), 실패 방향 2×2(`:135-145`), 과적재 센티널, 보간 config, 짝 없는 연산, retry 멱등성, 시계, null 파라미터 테스트(`abstraction.md:65`), 두 상태를 boolean으로 접지 않기(`abstraction.md:108-128`), 상속의 override 테스트와 필드 섀도잉(`abstraction.md:96-100`), 구조는 대출(`SKILL.md:264`).

### Architect가 가져갈 것 (수정 필요)

| 원문 | 우리 조건에서의 수정 |
|---|---|
| Move 3 "open every file it passes through" | **발췌 경계에서 멈춘다.** 발췌 밖 홉은 "모름"으로 표시하고 추측하지 않는다. 이 단서가 없으면 **프롬프트 안에서 가장 큰 환각 원천**이 된다 |
| Move 2b "Instance 1/2 (file:line)" | 줄 번호를 **발췌 안에서** 인용한다. 발췌에 변이점 둘이 들어 있는 경우가 거의 없으므로, 이 라이선스는 사실상 **추상 추가를 거의 전부 거절한다** — 우리가 원하는 방향이다 |
| Move 1 "unfillable field is a hard stop" | 원샷에서는 "철회하고 묻는다"가 불가능하다. **"두 칸을 못 채우면 더 작은 직접 변경을 제안한다"**로 바꾼다 |
| 제거 전 문자열 grep(`:86`) | grep이 없다. **"발췌 안에 모든 참조가 보이지 않으면 삭제를 제안하지 않는다"**는 거절 규칙으로 뒤집는다 |
| "find the question it answers … Ask once"(`:196`) | 물을 상대가 없다. **가정을 한 절로 적고 진행한다** |

### Reviewer가 가져갈 것

**최고 가치 규칙은 승인 허가다.** *"≥80% confidence… **"No structural findings" is a legitimate and expected result** — say it plainly rather than manufacturing a tenth item."* 이것이 없으면 리뷰어는 **맞는 패치를 거짓 반려**한다.

그 다음으로 헤지 금지(`:74`), 리뷰 중 추상 제안 금지(`:63`), 아첨 거부(`SKILL.md:243`), 점수표 금지(`:246`), 스타일·길이는 발견이 아님(`:68-69`), "테스트 추가하세요"는 거짓 양성(`:70`), 심각도 유도 3문항(`:80-82`).

### 뒤집어야 하는 것 하나 — 중요

> "Whatever a tool already enforces is settled… do not re-report what they already catch" — `SKILL.md:205`

**우리 Reviewer에게는 이 규칙이 정확히 반대로 작동한다.** 우리에게는 린터가 없고, **출력 형식 검증이 Reviewer의 존재 이유 그 자체**다. 이 문장을 그대로 넣으면 리뷰어가 자기 직무를 억제한다. 대신 이렇게 바꾼다 — *"출력 형식 명세가 이 스쿼드의 강제 표준이다. 그 위반은 언제나 보고 대상이다."*

### 못 가져가는 것

`git log` 기반 전부(축이 진짜 변하는지 검증 `:104`, churn × complexity 타깃 선정 `refactor.md:5-19`), 커밋 두 개로 나누기(`refactor.md:59`), 결정 기록 템플릿(`decisions.md:22-52`), 디렉터리 트리 패스(`review-passes.md:17-21`), 그리고 **출력 렌더링 규칙 전부**(`SKILL.md:30`, `review-passes.md:88-96`) — 우리 답 형식은 채점기가 정한다.
