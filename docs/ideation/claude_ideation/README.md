# Lablup 트랙 주제 5개 — 요약

JUNCTIONX Korea 2026 · "Build the Ultimate Agent Squad" (Lablup + FuriosaAI)
배점: 벤치마크 40 + 시각화 30 + 토큰 효율 30

---

## 다섯 주제 한눈에

| # | 주제 | 한 줄 | 가장 세게 먹히는 축 |
|---|---|---|---|
| 1 | [답은 맨 끝에](01-답은-맨-끝에/주제.md) | 토론 과정을 채점되는 응답 본문 안에 적는다. 마지막 블록만 채점되므로 앞의 초안은 공짜다 | 시각화 (traceability) |
| 2 | [토큰 경제 스쿼드](02-토큰-경제-스쿼드/주제.md) | 스쿼드에 화폐를 도입한다. 파산이 곧 포기 판단 | 토큰 효율 |
| 3 | [확신도 계단](03-확신도-계단/주제.md) | 의심스러울 때만 비싸게 간다. 주인공은 캘리브레이션 | 토큰 효율 + 벤치마크 |
| 4 | [가지 않은 길](04-가지-않은-길/주제.md) | 한 번 녹화하고 모델 없이 무한히 되돌린다. 심사위원이 슬라이더를 끈다 | 시각화 (insightfulness) |
| 5 | [설계자와 편집자](05-설계자와-편집자/주제.md) | 점수의 절반인 coding만 정조준. 읽기와 고치기를 나누고 사이에 결정론적 검사 | 벤치마크 |

---

## 이 주제들이 딛고 선, 다른 팀은 모를 사실 여섯

1. **제출 서버가 judge의 요청 원문 364건을 전부 공개하고 있다.**
   `https://submission.jxc.events.lablup.ai:8444/practice-sets/requests` — 인증 없이 열린다.
   문항별 `request.txt`에 judge가 보내는 바이트가 그대로 있다.

2. **프롬프트 합성 규칙이 공개되어 있다.**
   우리 one-shot 프롬프트의 `{{TASK}}`가 문항 내용으로 치환되고, 그 뒤에 트랙의 `REQUIRED OUTPUT` 블록이 원문 그대로 붙는다.
   → `{{TASK}}` **앞**에 쓰는 글은 그 트랙 전 문항에서 동일하다 = prefix cache 구간.

3. **세 트랙 모두 "마지막 것이 쓰이고, 그 앞은 무시되며 감점되지 않는다".**
   응답 본문의 앞부분이 완전한 자유 공간이다. (주제 1)

4. **coding 출력 형식은 unified diff가 아니라 SEARCH/REPLACE 블록이다.**
   기존 팀 자료 `09-스쿼드-설계-전략.md`의 가정이 틀렸다. SWE-bench와 LiveCodeBench 양쪽 다 이 형식이다.

5. **컨텍스트 번들은 항상 60,000자 상한에 붙어 있고, 후보 파일 696개 중 10개만 골라 준다.**
   (연습 세트 40건 직접 집계: 중앙값 59,966자 / 발췌 10개 / 후보 696개)
   위치 특정은 여전히 우리 몫이다.

6. **저장소가 같아도 문항 간 컨텍스트 재사용은 없다.** (django 2.7%, 나머지 0%)
   커밋이 전부 다르기 때문. 캐시 이득은 **한 문항 안에서 여러 에이전트가 같은 60,000자를 볼 때**만 나온다.

---

## 이 트랙을 보는 관점 하나 — 토큰 효율은 "덤"이 아니다

공개된 비용 정규화 리더보드들이 같은 말을 한다. 피칭에서 그대로 인용 가능한 숫자들이다.

| 사례 | 숫자 |
|---|---|
| **ARC Prize** 공개 리더보드 | Gemini 3.7 Flash (High)와 Gemini 3 Deep Think이 **똑같이 84.6%**인데 과제당 **$0.249 vs $13.62 — 54.7배** |
| **SWE-bench bash-only** | MiniMax M2.5 **75.80% / $0.07** vs Claude 4.5 Opus **76.80% / $0.75** — 1.0%p에 **10.7배** |
| **HAL** (Princeton, arXiv:2510.11977) | 첫 문장이 "에이전트는 1% 더 잘하려고 **100배** 비쌀 수 있다". 9개 벤치마크 중 최고가 모델이 파레토 경계에 오른 건 **1개뿐**. 사고 강도를 올린 **36개 실행 중 21개는 정확도가 안 올랐다** |
| **Efficient Agents** (arXiv:2508.02694) | GAIA 성능 **96.7% 유지**하며 비용 **42.7% 절감**. 단일 지표 이름은 **cost-of-pass** |
| **Anthropic 멀티 에이전트 보고** | 멀티 에이전트는 채팅의 **약 15배** 토큰을 쓴다. 그리고 **"대부분의 코딩 과제는 잘 맞지 않는다"** |

마지막 줄이 특히 중요하다. **에이전트를 많이 늘어놓는 것 자체는 점수가 아니다.** 다섯 주제 모두 "왜 이 에이전트가 존재해야 하는가"에 답할 수 있게 짜여 있고, 가능한 곳에서는 LLM 대신 결정론적 프로그램을 쓴다.

---

## 조합에 대하여

다섯 주제는 서로 배타적이지 않다. 실제 제출물은 하나이므로, 무엇을 **간판**으로 세울지가 결정 사항이다.

- 시각화 30점을 간판으로 → **4번**(반사실 재생기)이 가장 강하다. 채점 6축 중 가장 어려운 `insightfulness`를 직접 생산한다.
- 벤치마크 40점을 간판으로 → **5번**(설계자와 편집자). 가중치 0.5짜리 트랙을 정조준한다.
- 토큰 효율 30점을 간판으로 → **2번** 또는 **3번**.
- **1번은 어느 조합에도 얹을 수 있는 토대**에 가깝다. 계측 비용이 0이므로 먼저 깔아두면 나머지가 편해진다.

가장 자연스러운 결합: **5번을 엔진으로, 4번을 간판으로, 1번을 배관으로.**
(coding에서 점수를 벌고, 그 과정을 반사실 재생기로 보여주고, 트레이스는 응답 본문에서 공짜로 나온다.)

---

## 모든 주제에 공통으로 걸린 미확인 사항

온보딩 세션(21:00 Lablup / 21:30 FuriosaAI)에서 반드시 확인할 것.

| # | 항목 | 왜 필요한가 |
|---|---|---|
| 1 | 평가 모델 3종의 이름과 **USD/Mtok 단가** | 모르면 토큰 효율 30점을 계획할 수 없다 |
| 2 | `per_run_token_cap`, `per_item_wallclock_seconds` 실제 값 | 예산 설계의 상한 |
| 3 | one-shot 프롬프트가 스쿼드에 **어떻게 주입되는가** | planner에게만? 전원에게? |
| 4 | "1/5로 과금되는 test run"의 정확한 정의 | PDF와 포털 설명이 서로 안 맞는다 |
| 5 | Trace 로그를 **어느 경로로** 확보하는가 | 포털 `breakdown`은 문항 단위로 안 쪼개진다 |
| 6 | 평가 실행 중 **러너 레벨 검사·재시도**가 가능한가 | 주제 5의 Preflight가 여기 달려 있다 |
| 7 | `docs/contracts/patch-format.md` 위치 | 실패 코드 전체 목록이 들어 있다고 명시됨 |

---

## 근거 자료

- 트랙 원본 자료 9종: `../../resource/track_resource/lableup/`
- 연습 세트 실물 364문항: `../../resource/track_resource/lableup/practice-sets/`
- 공개 요청 원문: `https://submission.jxc.events.lablup.ai:8444/practice-sets/requests`
- 모델 스펙: `https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507`
- 적응형 조기 종료 연구: ReASC (Findings of ACL 2026), CAS (`arxiv.org/html/2607.01612`), REFRAIN (ACL 2026 Long), SeerSC (Findings of ACL 2026)
- 편집 형식 실측: Diff-XYZ (`arxiv.org/abs/2510.12487`), Aider architect mode (`github.com/Aider-AI/aider/issues/2401`)
- 비용 정규화 리더보드: ARC Prize (`arcprize.org/leaderboard`), SWE-bench bash-only (`swebench.com/bash-only`), HAL (`hal.cs.princeton.edu`, arXiv:2510.11977), Terminal-Bench 3 (`frontierbench.ai`)
- 캐스케이드·라우팅: FrugalGPT (arXiv:2305.05176, TMLR 2024), RouteLLM (arXiv:2406.18665, ICLR 2025)
- 예산 집행의 함정: s1 budget forcing (arXiv:2501.19393, EMNLP 2025)
- 검증 대 다수결: "When To Solve, When To Verify" (arXiv:2504.01005)
- 컨텍스트 부패: Chroma Research, 2025-07 (`trychroma.com/research/context-rot`)
- 비용 대비 성능 프레임워크: Efficient Agents (arXiv:2508.02694)
- 멀티 에이전트 실패 분류: MAST — "Why Do Multi-Agent LLM Systems Fail?" (`arxiv.org/pdf/2503.13657`)
- 에이전트 시각화 선행 연구: AgentLens (IEEE TVCG 2025, `arxiv.org/abs/2402.08995`)
