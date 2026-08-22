# 06. coding 트랙 전략 — 가중치 0.5짜리 승부처

> Q6-a: **coding 경로를 어떻게 짜야 하는가?**
>
> 결론 먼저: **localization이 최대 레버이고, 편집 형식 준수가 최대 리스크다.** 파일 컨텍스트 유무는 3.6% ↔ 56~63%를 가르고(15~17배), 우리 모델은 코드 편집 형식 준수(Aider-Polyglot 35.6)가 명확한 약점이다. 그래서 coding 경로는 **"어디를 고칠지 정하는 에이전트" + "형식을 정확히 쓰는 에이전트" + "프로그램 검증"** 3단이 근거 있는 최소 구성이다.

---

## 1. 이 트랙에서 coding이 실제로 무엇인가

| 항목 | 값 |
|---|---|
| 가중치 | **0.50** (점수의 절반) |
| hidden 문항 | 140~240 (SWE-bench Lite 150 + LiveCodeBench v6 40 추정) |
| visible 실측 | 20문항 = swebench-lite 13 + livecodebench-v6 7 |
| 요청 크기 | 최소 1,999 / 중앙값 **63,812** / 최대 70,310 바이트 |
| 컨텍스트 번들 | 중앙값 **59,966자** (상한 60,000자를 거의 채움), 발췌 10개, 후보 696개 |
| 저장소 분포 | django 2, matplotlib 2, 나머지 9개 프로젝트 각 1 |
| 출력 형식 | `*** PATCH START ***` + `<<<<<<< SEARCH / ======= / >>>>>>> REPLACE` |
| 채점 | swebench: Docker에서 test_patch 적용 후 pytest (fail→pass + pass→pass) / livecodebench: 공개 테스트로 stdin/stdout 대조 |
| 도구 | **없음** |

**핵심 성질**: 검색·탐색 능력을 겨루는 것이 아니라, **주어진 60KB 발췌만 보고 적용되는 패치를 쓰는 능력**을 겨룬다.

---

## 2. localization이 최대 레버라는 정량 근거

### 근거 1 — 파일 컨텍스트 유무가 15~17배를 만든다

[On the Role of Fault Localization Context for LLM-Based Program Repair (arXiv 2604.05481)](https://arxiv.org/html/2604.05481) (프리프린트)

SWE-bench Verified 500문항, GPT-5-mini, **61개 구성**(file/element/line 세 granularity 조합)을 전수 비교.

| 구성 | Resolved / 500 | 비율 |
|---|---|---|
| **컨텍스트 없음** (No files, No elements, No lines) | 18 | **3.6%** |
| 파일 레벨 컨텍스트 도입 | 280~315 | **56~63%** |

> *"introducing file-level context immediately increases resolution rates to approximately 56–63%, corresponding to a **15–17× improvement**."*

추가 발견 세 가지:
1. **"버그 파일만" 주는 것보다 "관련 파일까지 확장"하는 편이 낫다.** rule-based 확장은 20개 구성 중 14개에서, LLM-based 확장은 **19/20** 에서 buggy-only를 이겼다 (둘 다 Wilcoxon 유의).
2. **LLM 기반 파일 검색 > 규칙 기반.** 20개 구성 중 **17개**에서 우세 (p = 2.71e-4, 큰 효과크기).
3. 버그 파일의 평균 개수는 1.25개(범위 1~21), 토큰으로 약 12,131개.

> **우리 트랙 적용**: judge가 이미 파일 컨텍스트를 넣어주므로 우리는 "3.6%" 구간이 아니라 "56~63%" 구간에서 출발한다. **좋은 소식이다.** 문제는 그다음 — 발췌 10개 중 어디를 볼지 좁히는 단계다.

### 근거 2 — localization 품질을 올리면 resolve율이 더 오른다

[Loc2Repair (arXiv 2606.30963)](https://arxiv.org/html/2606.30963v1) (프리프린트)

SWE-bench Verified 500문항 × repair backbone 3종(Gemma4, GLM-4.7, Qwen3.5), localization만 바꿔 비교:

| 조건 | pooled resolved | 백본별 개선폭 |
|---|---|---|
| 명시적 localization 없음 (baseline) | **44.7%** | — |
| 예측 localization (Qwen4B) | **48.9%** | +4.6 / +3.8 / +4.4 %p |
| 예측 localization (Gemma4E4B) | **49.1%** | +2.0 / +6.2 / +5.2 %p |
| **gold localization** | **52.4%** | +6.6 / +9.2 / +7.4 %p |

그리고 **시간도 줄었다**: pooled 평균 경과시간 −100.94초(Qwen4B), −52.25초(Gemma4E4B), −154.45초(gold). 토큰 효과는 모델 의존적(−7,377 / +20,187 / −37,835).

두 가지 중요한 해석이 논문에 있다:
1. *"stronger standalone localization does **not** translate monotonically into larger downstream repair gains"* — localizer 자체 정확도와 최종 resolve율이 비례하지 않는다.
2. gold localization에서도 절반 가까이 미해결. *"repository-grounded repair still depends heavily on downstream factors such as **semantic patch synthesis**, multi-step debugging, validation behavior."* — **localization은 필요조건이지 충분조건이 아니다.**

### 근거 3 — localization 정확도를 실제로 올린 사례

[RGFL: Reasoning Guided Fault Localization (arXiv 2601.18044)](https://arxiv.org/html/2601.18044v1) (프리프린트)

| 지표 | 기존 SOTA | RGFL |
|---|---|---|
| SWE-bench Verified 파일 레벨 Hit@1 | 71.4% | **85%** |
| MRR | 81.8 | **88.8** |
| top-3 파일 내 element 레벨 Exact Match | 36% | **69%** |
| Agentless에 통합 시 end-to-end repair | — | **+12.8%** |

방법: 후보 파일에 대해 **버그 특화 구조적 설명(reasoning)** 을 생성한 뒤, LLM 신호 + 임베딩 신호를 결합한 2단 랭킹. 전 파일에 대해 reasoning을 돌리면 비용이 폭발하므로 **Agentless가 뽑은 top-k에만** reasoning을 적용한다.

> **우리 설계에 그대로 옮길 수 있는 아이디어**: Architect가 발췌 10개 각각에 대해 **"이 발췌가 이슈와 왜 관련 있는가"를 한 줄로** 쓰게 하고, 그 근거와 함께 순위를 매기게 한다. 우리 초안의 앵커에 `why` 필드가 있는 것이 이 방향과 일치한다.

---

## 3. Agentless — 도구 없는 3단 파이프라인이 이긴 사례

[Agentless: Demystifying LLM-based Software Engineering Agents (arXiv 2407.01489)](https://arxiv.org/abs/2407.01489) · [코드](https://github.com/openautocoder/agentless) · [ACM 게재본](https://dl.acm.org/doi/pdf/10.1145/3715754)

> Compared to the verbose and complex setup of agent-based approaches, Agentless employs a **simplistic three-phase process of localization, repair, and patch validation, without letting the LLM decide future actions or operate with complex tools.**

성적:
- SWE-bench Lite **32.00%** (96 fixes), 비용 **$0.70/문항** — 발표 당시 모든 오픈소스 SW 에이전트 중 **최고 성능이면서 최저 비용**
- 2024-12, Claude 3.5 Sonnet 결합: SWE-bench Lite **40.7%**, Verified **50.8%**

> **이번 트랙에 이보다 잘 맞는 선행 연구는 없다.** 트랙이 도구를 금지했고, Agentless는 도구 없이 최고 성적을 낸 접근이다. 우리 coding 경로는 사실상 **"Agentless의 localization 단계를 judge가 대신 해준 버전"** 이다.
>
> Agentless의 3단계를 우리 제약에 매핑하면:
> - **Localization** → judge가 파일 컨텍스트 제공 + 우리 Architect가 발췌 인덱스 좁히기
> - **Repair** → Editor가 SEARCH/REPLACE 생성. *Agentless는 여기서 문항당 다중 후보 패치를 샘플링한다*
> - **Patch validation** → 우리는 테스트 실행이 불가능하므로 **Preflight(형식·정합성 검증)로 대체**

관련해서 [DIRECTSOLVE / SELECTSOLVE](https://www.marktechpost.com/2025/05/17/swe-bench-performance-reaches-50-8-without-tool-use-a-case-for-monolithic-state-in-context-agents/) — 도구 없이 SWE-bench 50.8%를 낸 "monolithic state-in-context" 접근도 존재하며, *"outperforms complex agentic approaches like Agentless and CodeAct with minimal engineering"* 이라 보고한다. **단순한 구조가 이긴다는 방향이 반복된다.**

---

## 4. 최대 리스크 — 편집 형식 준수

### 우리 모델의 약점이 정확히 여기다

[Qwen3-30B-A3B-Instruct-2507 모델 카드](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507) 성적표에서:

| 벤치마크 | Qwen3-30B-A3B-Instruct-2507 | Qwen3-235B-A22B Non-Thinking | DeepSeek-V3-0324 | GPT-4o-0327 |
|---|---|---|---|---|
| LiveCodeBench v6 | **43.2** | 32.9 | 45.2 | 35.8 |
| MultiPL-E | **83.8** | 79.3 | 82.2 | 82.7 |
| **Aider-Polyglot** | **35.6** | **59.6** | **55.1** | **45.3** |

**LiveCodeBench(코드 생성) 43.2는 준수한데 Aider-Polyglot(코드 편집 형식) 35.6은 명백히 낮다.** 같은 표의 다른 모델들과 비교하면 이 격차가 이 모델 고유의 약점임이 드러난다.

Aider-Polyglot이 측정하는 것: 6개 언어(C++, Go, Java, JavaScript, Python, Rust)의 기존 코드를 **정해진 편집 형식으로** 수정. 이번 트랙 coding 출력이 요구하는 것과 정확히 같은 능력이다.

### 형식 오류가 얼마나 자주 나는가

[SWE-Edit (arXiv 2604.26102)](https://arxiv.org/pdf/2604.26102v2) (프리프린트)의 Edit Success Rate:

| 구성 | Edit 성공률 |
|---|---|
| Anthropic `str_replace_editor` baseline (SWE-bench Verified) | 93.4% |
| 다른 3개 모델의 baseline | **75.6 ~ 82.0%** |
| SWE-Edit(디커플링 적용) | 93.9 ~ 96.9% |

**모델에 따라 편집 시도의 18~25%가 형식 오류로 날아간다.** 그리고 논문의 지적:

> the cost of a single mis-formatted edit (**a wasted reasoning trajectory**) is hidden inside the resolve rate.

이번 트랙에서는 그게 숨지 않는다. `extraction_failed`로 **팀 책임**으로 기록된다.

### 무엇이 깨지는가 — 구체적 원인

| 원인 | 출처 |
|---|---|
| **단일 공백 불일치** | SWE-Edit: *"a single whitespace mismatch causes the edit to fail"* |
| **SEARCH 블록이 파일 안에서 유일하지 않음** | SWE-Edit Editor 프롬프트 규칙 4 |
| **줄 끝 개행 누락 / 공백 strip** | [SWE-bench issue #345](https://github.com/SWE-bench/SWE-bench/issues/345) — `model_patch`가 개행으로 끝나지 않아 `git apply` 실패. 개행을 붙이니 적용됨 |
| **모델이 코드를 기억으로 지어냄** | 우리 초안의 진단. Chroma의 context rot + distractor 결과와 정합 |
| 빈 줄 하나 누락 | [SWE-bench issue #145](https://github.com/SWE-bench/SWE-bench/issues/145) — "I found that I missed a blank line. It is solved." |

SWE-bench 채점 하네스는 세 가지를 순차 시도한다([issue #383](https://github.com/SWE-bench/SWE-bench/issues/383)):
```python
GIT_APPLY_CMDS = [
    "git apply --verbose",
    "git apply --verbose --reject",
    "patch --batch --fuzz=5 -p1 -i",
]
```
세 개 다 실패해야 "failed apply"다. 즉 약간의 fuzz는 허용된다. **다만 우리 트랙은 unified diff가 아니라 SEARCH/REPLACE이므로 judge 쪽 관용도는 별도 확인이 필요하다.**

### 형식별 성공률 — Aider 리더보드가 알려주는 것

[Aider code editing leaderboard](https://aider.chat/docs/leaderboards/edit.html)의 "Percent using correct edit format" 컬럼에서 읽히는 규칙성:

| 모델 급 | 주로 쓰는 형식 | 형식 준수율 |
|---|---|---|
| 오픈 중소형 (Qwen2.5-Coder 7B~32B, Llama 3.1, Codestral 등) | `whole` (파일 전체 재작성) | **거의 100%** |
| GPT-4 계열 | `diff`(SEARCH/REPLACE) / `udiff` | 92~98% |

Aider 문서의 한 줄: *"The **'whole' format is the easiest for an LLM to use**, but it uses a lot of tokens."*

그리고 [To Diff or Not to Diff? (arXiv 2604.27296)](https://arxiv.org/html/2604.27296v1) (프리프린트)의 형식별 비교표(6개 태스크 평균):

| 형식 | 평균 |
|---|---|
| MinUniDiff (최소 unified diff) | **19.34** |
| UniDiff | 30.28 |
| FullCode (전체 코드) | 51.83 |
| search/replace | **45.89 ~ 56.69** |
| FuncDiff (함수 단위) | 52.49 ~ 57.32 |

**unified diff가 압도적으로 나쁘다.** SEARCH/REPLACE와 전체 코드가 비슷한 수준이고, 함수 단위 diff가 가장 좋다.

> **트랙 규칙 확인**: 우리는 형식을 고를 수 없다 — SEARCH/REPLACE가 강제다. 다만 트랙 규칙에 *"an **empty SEARCH section creates a new file**"* 이 있고, SWE-Edit의 Editor 프롬프트에도 *"If the SEARCH block is empty... it means you want to **REWRITE THE ENTIRE FILE**"* 라는 관례가 있다. **주최 측 judge가 빈 SEARCH를 "전체 파일 재작성"으로 해석하는지 "신규 파일 생성"으로만 해석하는지 확인할 가치가 있다.** 전자라면 형식이 어려운 문항에서 `whole` 전략으로 탈출할 길이 생긴다. (온보딩 질문 목록에 추가 권장)

---

## 5. 다중 후보 샘플링 — 쓸 것인가

Agentless는 문항당 **여러 후보 패치를 샘플링**하고 검증으로 고른다. 우리는 검증(테스트 실행)이 불가능하므로 그 선별 신호가 없다.

가능한 대체 신호:
1. **Preflight 통과 여부** (이진, 무료) — 통과한 후보만 남긴다
2. **후보 간 일치** — 여러 샘플이 같은 위치·같은 변경을 제안하면 신뢰도↑
3. 위 둘의 결합

단, `03`에서 본 modal ceiling과 `02`의 backfire 결과를 고려하면 **coding에서 n을 크게 잡는 것은 위험**하다. 그리고 coding 문항당 입력이 이미 16~20k 토큰이라 n배는 비용이 그대로 n배다.

> **권고**: n = 1 기본, Preflight 실패 시에만 1회 재시도(구체 실패 신호 첨부). 여유 예산이 확인되면 **livecodebench 문항에서만** n = 2~3 실험(입력이 짧아 비용이 싸다).

---

## 6. coding 경로 설계 — 리서치 반영본

```
Wave 0  Router      payload.kind로 swebench / livecodebench 판별 (JSON 한 줄)
Wave 1  Architect   60,000자 발췌 10개를 읽고 앵커 산출
                    출력: [{excerpt_idx, path, start_line, end_line, why(한 줄)}] 상위 2~3개
                    ← 근거: 파일 컨텍스트 15~17배 효과 / Loc2Repair +4.2~4.4%p / RGFL의 reasoning 랭킹
Wave 2  Editor      앵커 주변 발췌만 보고 SEARCH/REPLACE 블록 작성
                    ← 근거: SWE-Edit 편집 성공률 +2.7~18.3%p (reasoning과 형식 생성 분리)
[프로그램] Preflight  C1~C8 검사 (→ 03)
                    실패 시 구체 신호를 붙여 Wave 2 재호출 (최대 1회)
                    ← 근거: Aider ApplyError 되먹임 패턴 / 외부 신호가 있으므로 self-correction 함정 회피
[프로그램] 잔액 체크   잔액 < 견적이면 다음 호출 안 함 (→ 04)
```

**livecodebench 문항은 컨텍스트가 없으므로 Architect를 건너뛴다** (Wave 0 → Wave 2 → Preflight).

### Architect의 출력을 "요약"이 아니라 "좌표"로 해야 하는 이유

- SEARCH 블록은 **원문 문자열이 글자 단위로 정확**해야 한다. 요약을 거치면 원문이 소실된다.
- Anthropic의 telephone game 경고가 정확히 이 지점을 가리킨다 — 핸드오프마다 정보가 열화된다.
- 따라서 packet은 **발췌 ID + 줄 범위 + 원문 hunk 그대로**를 나른다. 자연어 요약은 `why` 한 줄로만.

---

## 7. 저장소 편중 — visible 세트에서 읽히는 것

visible 20문항의 저장소 분포: django 2, matplotlib 2, 나머지 9개 프로젝트 각 1.
(구 364문항 세트에서는 django 15, sympy 10 편중이 관측됐다 — `../../track_resource/lableup/04-벤치마크-데이터셋-분석.md`)

SWE-bench Lite의 원 분포는 django가 압도적이다. hidden 150문항도 비슷할 가능성이 높다.

> **활용 가능성**: Layer 1 프리픽스(캐시되는 부분)에 **django·sympy·matplotlib의 코딩 관례**를 넣는 것을 검토할 수 있다. 예: django의 `apps.py` 등록 관례, `Meta` 클래스 위치, `_meta` API 사용, deprecation 경고 패턴 등.
>
> **단 주의**: `02`에서 본 persona 연구는 "전문가 역할 부여"가 효과 없다고 했다. 여기서 넣는 것은 persona가 아니라 **구체적 사실**(코드 관례)이므로 다른 범주다. 그래도 **연습 세트로 A/B 검증 없이 넣지 말 것** — Layer 1이 길어지면 모든 요청에 그 비용이 붙는다(캐시로 90% 흡수되지만 0은 아니다).

---

## 8. 이 문서의 결론

1. **localization이 최대 레버.** 파일 컨텍스트 유무는 3.6% ↔ 56~63%(15~17배). 우리는 이미 컨텍스트를 받으므로 그다음 단계(발췌 좁히기)가 우리 몫이고, 그 이득은 +4.2~4.4%p 수준으로 실측됐다.
2. **localization은 필요조건이지 충분조건이 아니다.** gold localization에서도 47.6%가 미해결. 남은 병목은 semantic patch synthesis.
3. **Agentless가 이번 트랙에 가장 잘 맞는 선행 연구.** 도구 없는 3단(localization/repair/validation)으로 SWE-bench Lite 32~40.7%, 비용 $0.70. 우리 구조는 그 변형이다.
4. **최대 리스크는 편집 형식.** 우리 모델의 Aider-Polyglot 35.6은 같은 표의 다른 모델 대비 명백한 약점이고, 모델에 따라 편집 시도의 18~25%가 형식 오류로 날아간다.
5. **그래서 Architect/Editor 분리가 정당화된다.** SWE-Edit이 이 분리로 편집 성공률 +2.7~18.3%p, resolve +1.4~2.1%p, 비용 −17.9%를 실측했다.
6. **Preflight는 선택이 아니라 필수.** 형식 오류 하나가 추론 궤적 하나를 버리고, 이번 트랙에서는 그게 팀 책임 0점이다.
7. **다중 샘플링은 신중하게.** 입력이 16~20k라 n배가 그대로 비용 n배. livecodebench에서만 실험.

---

## 참고 문헌

- Xia et al., [Agentless: Demystifying LLM-based Software Engineering Agents](https://arxiv.org/abs/2407.01489) · [코드](https://github.com/openautocoder/agentless) · [Demystifying LLM-Based Software Engineering Agents (ACM)](https://dl.acm.org/doi/pdf/10.1145/3715754)
- Sepidband, Pham, Hemmati, [On the Role of Fault Localization Context for LLM-Based Program Repair](https://arxiv.org/html/2604.05481) (프리프린트)
- [Loc2Repair: A Framework for Evaluating the Impact of File-Level Issue Localization](https://arxiv.org/html/2606.30963v1) (프리프린트)
- [RGFL: Reasoning Guided Fault Localization](https://arxiv.org/html/2601.18044v1) (프리프린트)
- [SWE-Edit: Rethinking Code Editing for Efficient SWE-Agent](https://arxiv.org/pdf/2604.26102v2) (프리프린트)
- [To Diff or Not to Diff? Structure-Aware and Adaptive Output Formats for Efficient LLM-based Code Editing](https://arxiv.org/html/2604.27296v1) (프리프린트)
- [Understanding Automated Program Repair Agents Through the Lens of Traceability](https://arxiv.org/html/2506.08311v2) (프리프린트)
- Aider, [Edit formats](https://aider.chat/docs/more/edit-formats.html) · [Leaderboard](https://aider.chat/docs/leaderboards/edit.html) · [Unified diffs make GPT-4 Turbo 3X less lazy](https://aider.chat/docs/unified-diffs.html)
- SWE-bench issues [#145](https://github.com/SWE-bench/SWE-bench/issues/145), [#345](https://github.com/SWE-bench/SWE-bench/issues/345), [#383](https://github.com/SWE-bench/SWE-bench/issues/383)
- Qwen, [Qwen3-30B-A3B-Instruct-2507 모델 카드](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507)
