# monstrous_squad — 제출용 Squad Template

JUNCTIONX Korea 2026 · Lablup + FuriosaAI 트랙 "Build the Ultimate Agent Squad"

제출물은 두 개다. **`squad-template.json` 하나**와 **`add_prompt/`의 트랙별 one-shot 프롬프트 세 개**.

```
squad-template.json      제출본 (agent_prompts/에서 tools/build_template.py가 조립)
squad-template.min.json  임포트 실패 시 대체본. disabledTools 두 필드만 비운 것
agent_prompts/*.txt      세 에이전트의 systemPrompt 원본. 여기를 고친다
add_prompt/*.txt         트랙별 one-shot 프롬프트 원본. 여기를 고친다
budget.json              로컬 스쿼드 예산. 제출물이 아니고 평가 서버에 가지 않는다
tools/build_template.py  agent_prompts/ → squad-template.json
tools/make_min_template.py  → squad-template.min.json
tools/validate_template.py  임포트 규칙 + 채점기 안전성 검사
```

고치는 순서는 항상 이렇다.

```bash
# agent_prompts/*.txt 또는 add_prompt/*.txt 수정 후
python3 tools/build_template.py
python3 tools/make_min_template.py
python3 tools/validate_template.py squad-template.json
```

---

## 이 버전이 왜 이렇게 생겼나 — 앞 버전이 23등을 한 이유

`v1`(5 에이전트: Router/Architect/Editor/Solver/Reviewer)이 hidden 세트에서 받은 점수다.
`https://submission.jxc.events.lablup.ai:8444/api/leaderboard`의 `monstorous-hidden-ed1ac5c6`.

| | 우리 (23등/24) | 1등 MISHULTA | 3등 TheresNoFree |
|---|---|---|---|
| overall | **0.0925** | 0.4261 | 0.4031 |
| coding | **0.053** (graded 32/38) | 0.211 | 0.263 |
| math | **0.077** (graded 12/13) | 0.538 | 0.385 |
| generic | **0.188** (graded 85/96) | 0.745 | 0.702 |
| input tokens | **5,368,135** (전체 최다) | 2,033,190 | 732,306 |
| requests | **1,192** = 8.1/문항 | 327 = 2.2/문항 | 279 = 1.9/문항 |
| wall clock | **2,971초** | 678초 | 2,434초 |

`squad/test_5/.squad.json`(제출 당시 워크스페이스 스냅샷)의 systemPrompt 다섯 개가
`squad-template.json` v1과 **바이트 단위로 같다.** 즉 이 점수는 그 템플릿의 점수다.

### 원인 1 — systemPrompt 안에 채점기가 읽는 정답이 들어 있었다

v1의 다섯 프롬프트는 전부 같은 15KB짜리 `SQUAD CONTRACT`로 시작했고, 그 안에
"올바른 예시"가 채점기 정규식에 **그대로 걸리는 형태**로 들어 있었다. `grade.py`의
추출 함수를 v1 프롬프트에 그대로 먹여보면 이렇게 나온다.

```
Router     letter=C   boxed=204800   Architect  letter=C   boxed=204800
Editor     letter=C   boxed=204800   Solver     letter=C   boxed=204800
Reviewer   letter=C   boxed=204800
```

모델이 자기 지시문 조각을 응답에 흘리면 그 순간 답은 `C` 또는 `204800`이 된다.
generic 정확도 0.188은 10지선다에서 한 글자로 찍은 것과 구별되지 않는 값이고,
math 1/13은 `204800`이 맞을 리 없는 값과 정확히 같다. 결정적 증거는 아니지만
**공짜로 없앨 수 있는 위험이었고, 없애지 않았다.**

이 판이 `tools/validate_template.py`의 `check_no_extractable_answer`다. 이제
어떤 프롬프트도 세 채점기 중 하나에 걸리면 빌드가 실패한다.

### 원인 2 — 입력 토큰의 81%가 우리 지시문이었다

v1 프롬프트 다섯 개는 12,773 ~ 15,682자, 평균 약 3,670토큰이다.
1,192 요청 × 3,670 = **4,374,640토큰**. 실제 청구된 입력 5,368,135토큰의 **81%**다.
문항 본문은 나머지 19%였다.

길게 쓴 이유는 "Layer 1이 1024토큰을 넘어야 prefix cache가 걸린다"였는데,
**캐시가 걸려도 입력 토큰은 그대로 청구된다.** 리더보드의 `input_tokens`가 그 증거다.
캐시는 지연시간을 줄이지 토큰 점수를 줄이지 않는다. 이 규칙은 폐기했다.

### 원인 3 — 플래너가 답 계약을 지워버렸다

로컬 실행 기록에 남은 태스크 파일은 74개다. 그중 답 형식을 한 번이라도 언급한 것은
**13개**이고, 그 13개는 전부 플래너가 실패해 런타임이 요청 전문을 그대로 태스크로
만들어버린 경우다(`squad/ikkim/tasks/`). **플래너가 실제로 쓴 나머지 61개는 0개**다
(`squad/{test,test_2,test_4}/tasks/*.json` 24개 전부 포함). 예를 들어

```json
"title": "Aggregate and produce final answer",
"description": "…produce the final answer in the required format."
```

**"the required format"이 무엇인지는 태스크 안에 없다.** 답을 써야 하는 에이전트가
써야 할 형식을 한 번도 본 적이 없는 상태로 호출된다.

### 원인 4 — 마지막 웨이브의 Reviewer가 정답을 덮어썼다

채점기는 `finalResult`를 상태 요약이라며 거부하고(28/28회 확인), 마지막 웨이브의
마지막 태스크 출력을 읽는다. v1은 그 자리에 Reviewer를 놓았는데, Reviewer는
**문제 본문을 받지 않는다** — 받는 것은 `=== REQUIRED OUTPUT ===` 블록과
`Options:` 블록과 앞 태스크 출력뿐이다. 문제를 못 본 채로 "내용을 판정하고 다시
써라"를 시킨 셈이다.

### 원인 5 — 요청이 문항당 8.1번

앱이 플래너에게 주는 기본 지시문 1번 규칙이 *"Break requests into the smallest
reasonable tasks"*이고, 6번이 *"produce a unified final response using
aggregate_results"*다. 우리 Router 프롬프트가 앞의 것만 뒤집었다. 그리고
`budget.json`은 **제출물이 아니다** — 평가 서버는 런타임 기본값
(`maxTasksPerPlan` 20, `maxAgentTurns` 20, `maxPlanIterations` 3)으로 돈다.
로컬 기록에는 한 수학 문항에 21회를 쓴 실행, 같은 제목의 태스크 5개를 만든 실행,
"다른 태스크 상태를 확인하는" 태스크를 LLM 호출로 만든 실행이 남아 있다.

### 원인 6 — 모델 두 개를 배정했지만 하나는 6번 돌았다

`preferredModelId`는 런타임이 읽는다. 그런데 Solver에 붙인 K-EXAONE은
1,192 요청 중 **6번** 호출됐다. math 13 + generic 96 = 109문항을 맡기려던
자리다. 배정이 아니라 라우팅이 안 된 것이고, 두 모델 구성은 그만큼 예측이 안 된다.

---

## v2가 바꾼 것

**에이전트 3명, 모델 1개, 문항당 모델 호출 2회.**

```
요청 ─→ Router (planner)  ─create_task 1회→  Coder   (coding)
                                        └→  Solver  (math / generic / other)
                                                  └→ 그 출력이 채점 대상
```

| 결정 | 값 | 근거 |
|---|---|---|
| 에이전트 수 | 3 | 마지막 웨이브 태스크는 하나여야 하고, 중간 홉마다 답이 사라졌다 |
| 웨이브 수 | 1 | Reviewer 제거. 마지막 태스크 = 답을 만든 태스크 |
| 모델 | `furiosa-ai/gpt-oss-120b` 세 자리 전부 | 1·2등이 이 모델 단독. 두 번째 모델은 6/1192만 돌았다 |
| K-EXAONE 배제 | 자리 0개 | Furiosa 지원 목록이 이 모델을 🟡 *Experimental — works, but not yet fully validated or tuned*로 표시하고 처리량·TTFT를 하나도 공개하지 않았다. 게다가 thinking을 끄면 AIME 2025가 92.8 → **44.6**, LiveCodeBench v6가 80.7 → 44.6으로 무너지는데(tech report Table 4), 평가 서버의 `reasoning_effort` 기본값을 우리는 모른다. 값이 `none`이면 배정 자체가 손해다 |
| systemPrompt 길이 | 3,503 / 6,946 / 5,885자 | v1 대비 약 1/4. 공유 Layer 1 없음 |
| 프롬프트 안 정답 예시 | 없음 | 세 채점기 모두 아무것도 추출 못 함 (검사기가 강제) |
| 도구 | 세 자리 모두 `enabledTools: []` | 도구가 있으면 답을 워크스페이스 파일에 쓰고 응답엔 요약만 낸다 |
| 메모리 | 세 자리 모두 `false` | 호출당 최대 2,000 입력 토큰, 그리고 기록에 오답을 기억한 사례가 있다 |
| Router의 복사 규칙 | 요청 전문 verbatim, coding만 약 32,000자로 제한 | 계약이 통째로 워커에게 도착해야 한다 |
| one-shot 프롬프트 첫 줄 | `PLANNER: … assign it to <Agent>` | 라우팅을 요청 본문에도 박아 두 번 말한다 |

### 예상 비용 (연습 세트 실측 크기 × hidden 문항 수)

| | v1 실측 | v2 추정 |
|---|---|---|
| requests | 1,192 | **294** |
| input | 5,368,135 | **약 1.56M** |
| output | 775,612 | **약 0.63M** |

추정의 근거: coding 문항 요청 중앙값 63,812바이트 + 프롬프트 6,843바이트,
math 3,788바이트, generic 3,958바이트. Router가 한 번 읽고, 복사분을 워커가 한 번 읽는다.

**추정이다. 실측이 아니다.** 다음 제출 결과로 갱신할 것.

---

## 남아 있는 미확인 사항

1. **워커가 원본 요청을 보는가.** 런타임의 태스크 프롬프트는
   `description` + `## Context from previous tasks:`로 조립된다(바이너리 문자열).
   원본 요청이 함께 들어가는지는 확인하지 못했다. v2는 **양쪽 모두에서 동작하도록**
   Router가 요청을 복사하게 되어 있다 — 워커가 원본도 본다면 중복이고, 못 본다면 유일한 통로다.
2. **`create_task` description의 최대 길이.** 바이너리에
   `Task description exceeds maximum length of <N> characters` 문자열이 있으나 N을 못 찾았다.
   Router 프롬프트는 그 오류를 받으면 발췌를 빼고 다시 호출하도록 적어 두었다.
3. **coding 복사 예산 32,000자가 적정한가.** 60,000자 컨텍스트의 절반이고, 발췌 하나가 최대 약 12,500자라 실질적으로 2~3개다.
   더 늘리면 정확도가 오를 수 있고 출력 토큰이 는다. 첫 실행 결과로 조정한다.
4. **`reasoning_effort`는 우리가 못 건드린다 — 그리고 프롬프트로도 안 된다.**
   템플릿에 그 필드가 없고(`ModelPreferences` 5필드, `AgentSettingsOverrides` 6필드 어디에도),
   앱 전역 설정 `inference.defaultReasoningEffort`만 존재한다. 시스템 프롬프트에
   `Reasoning: high`를 적는 우회로는 **작동하지 않는다**: harmony 템플릿이 그 줄을 *읽는* 게 아니라
   *쓰는* 쪽이고(`{{- "Reasoning: " + reasoning_effort + "\n\n" }}`), OpenAI 호환 API의 `system`
   메시지는 harmony의 system이 아니라 **developer 메시지**로 들어간다. 생략 시 기본값은 `medium`.
   gpt-oss-120b 공개 수치의 effort 의존성이 커서(GPQA Diamond low 67.1 / medium 73.1 / high 80.1,
   SWE-bench Verified 47.9 / 52.6 / 62.4) 이 값은 알아둘 가치가 있지만, 바꿀 수단이 없다.

5. **prefix cache는 토큰 점수를 못 줄인다 — 확인됨.** vLLM은 캐시 적중분도
   `usage.prompt_tokens`에 전액 계상하고(`prompt_tokens = len(final_res.prompt_token_ids)`),
   공식 문서도 *"APC only reduces the time of processing the queries (the prefilling phase)"*라고
   적는다. 캐시된 양은 `prompt_tokens_details.cached_tokens`로 따로 나올 뿐이다.
   v1이 "캐시를 걸려고" 프롬프트를 15KB로 키운 것은 그래서 순손실이었다.
