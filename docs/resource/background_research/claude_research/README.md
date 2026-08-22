# 효율적인 에이전트 스쿼드 구성 — 심층 리서치 자료 모음

> JUNCTIONX Korea 2026 · Lablup + FuriosaAI 트랙 **"Build the Ultimate Agent Squad"** 대응.
> 이 폴더는 "**어떤 스쿼드 구성이 실제로 효율적인가**"를 웹의 1차 자료(논문, 벤더 엔지니어링 블로그, 공식 문서, 모델 카드, 리더보드)로 조사해 정리한 것이다.
>
> 조사 시각: 2026-08-22 · 도구: firecrawl search, Exa search, WebFetch
> 모든 수치에는 출처 URL을 붙였다. **출처 없는 문장은 우리 팀의 해석이며 그렇게 표시했다.**

---

## 이 폴더가 답하려는 질문

트랙은 참가자에게 네 가지를 직접 정하라고 요구한다 — 누가 **코드를 읽고**, 누가 **고치고**, 누가 **검증하고**, 누가 **포기 시점을 판단**하는가. 그리고 점수는 벤치마크 40 + 시각화 30 + 토큰 효율 30이다.

그래서 이 자료 모음의 질문은 하나로 좁혀진다:

> **고정된 토큰 예산 안에서, 에이전트를 몇 명 · 어떤 역할로 · 어떤 순서로 배치해야 정확도가 최대가 되는가?**

---

## 30초 요약 — 리서치가 내놓은 결론 일곱

| # | 결론 | 근거 (대표) |
|---|---|---|
| 1 | **멀티 에이전트는 기본적으로 비싸다.** 같은 과제에서 단일 에이전트 대비 3~10배, 채팅 대비 약 15배 토큰을 쓴다 | [Anthropic](https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them), [Anthropic Research](https://www.anthropic.com/engineering/multi-agent-research-system) |
| 2 | **토큰 예산을 맞추면 단일 에이전트가 멀티를 이기거나 비긴다.** 보고된 멀티 우위의 상당수는 "더 많이 쓴 것"의 효과였다 | [arXiv 2604.02460](https://arxiv.org/abs/2604.02460v1), [EMNLP 2024](https://aclanthology.org/2024.emnlp-main.1112/) |
| 3 | **역할(planner/implementer/tester/reviewer)로 나누는 분업은 대표적인 안티패턴.** Anthropic 실험에서 서브에이전트들이 실제 작업보다 조율에 더 많은 토큰을 썼다. 나누려면 **역할이 아니라 컨텍스트 경계**로 나눠야 한다 | [Anthropic](https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them) |
| 4 | **예외는 "블랙박스 검증자".** 검증은 컨텍스트 전달이 거의 필요 없어서 분리해도 손실이 없다. 그리고 프로그램으로 되는 검증은 LLM에게 시키면 안 된다 | [Anthropic](https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them), [arXiv 2310.01798](https://arxiv.org/abs/2310.01798) |
| 5 | **포기·예산은 프롬프트로 부탁하면 안 지켜진다.** 디코딩/파라미터 레벨의 하드 캡만 작동한다 | [s1, arXiv 2501.19393](https://arxiv.org/abs/2501.19393) |
| 6 | **coding 트랙의 최대 레버는 localization이다.** 파일 컨텍스트가 없으면 3.6%, 있으면 56~63%. gold localization은 예측 localization보다 3.5%p 더 준다 | [arXiv 2604.05481](https://arxiv.org/html/2604.05481), [arXiv 2606.30963](https://arxiv.org/html/2606.30963v1) |
| 7 | **generic(MMLU-Pro)에서 CoT를 끄면 크게 손해다.** GPT-4o 기준 direct 53.5 → CoT 72.6 (+19.1). "보기 문자만 뱉게 하라"는 우리 초안의 판단은 **재검토가 필요하다** | [MMLU-Pro, NeurIPS 2024](https://arxiv.org/abs/2406.01574) |

7번이 이 리서치에서 나온 **가장 값비싼 발견**이다. 그리고 그 잘못된 지시가 지금 어느 파일에 들어 있는지도 특정했다 — `../../example_task/prompts/generic.txt`의 *"print as little as you need to settle the choice — for most questions that is nothing."* 자세한 것은 `07`과 `10`.

**두 번째로 값비싼 발견**은 캐시 쪽이다 — 에이전트별 `systemPrompt`가 item payload **앞**에 오는 AI:GO 구조에서는, 원 전략 문서가 계산한 "문항 내 4에이전트 캐시 공유 → 입력 비용 1/4"이 **성립하지 않을 가능성이 크다.** → `05` 2절 단서, `10` 8절 항목 4-b.

---

## 문서 목록

| # | 문서 | 무엇이 들어 있나 | 언제 읽나 |
|---|---|---|---|
| 00 | [해커톤·트랙 정밀 파악](00-해커톤과-트랙-정밀파악.md) | 대회·트랙·배점·제약을 리서치 관점에서 재정리. "설계 자유도가 실제로 어디까지인가" | 가장 먼저 |
| 01 | [멀티 에이전트를 언제 쓰는가](01-멀티에이전트-언제-쓰는가.md) | 멀티 vs 단일의 비용·성능 실측, orchestrator-worker, 컨텍스트 중심 분해, 예산 통제 비교 실험 | 구조 확정 전 |
| 02 | [에이전트 수와 역할 설계](02-에이전트-수와-역할-설계.md) | 몇 명이 적정인가, 역할 분업의 함정, persona 프롬프트 무용론, 앙상블 규모의 수확 체감 | 에이전트 목록 확정 전 |
| 03 | [검증자 설계 — 프로그램 대 LLM](03-검증자-설계.md) | self-correction 실패, SC vs GenRM 8배, 형식 검증의 실측 효과(SWE-Edit), 다수결의 한계 | Preflight/Auditor 설계 시 |
| 04 | [포기와 예산 정책](04-포기와-예산-정책.md) | budget forcing, 하드 캡, cascade(FrugalGPT), 조기 종료, 확신도 캘리브레이션 | GiveUp 층위 설계 시 |
| 05 | [토큰 효율 — 캐시와 컨텍스트](05-토큰효율-캐시와-컨텍스트.md) | prefix cache 동작 원리·가격·최소 토큰·TTL, context rot, compaction, Chain-of-Draft | 프롬프트 레이아웃 확정 전 |
| 06 | [coding 트랙 전략](06-coding-트랙-전략.md) | Agentless, localization의 정량 효과, 편집 형식별 성공률, SEARCH/REPLACE 실패 원인 | coding 경로 설계 시 |
| 07 | [math·generic 트랙 전략](07-math-generic-트랙-전략.md) | MMLU-Pro는 CoT 필수, 답 추출 정규식, self-consistency 포화점, Qwen3 권장 설정 | 두 경로 설계 시 |
| 08 | [실패 모드 체크리스트](08-실패모드-체크리스트.md) | MAST 14개 실패 모드를 우리 스쿼드에 1:1 대응시킨 표 | 설계 리뷰 시 |
| 09 | [트레이스와 시각화 표준](09-트레이스와-시각화-표준.md) | OpenTelemetry GenAI semconv 실제 속성명, 관측 도구 지형, "타임라인은 언제를 기록할 뿐 왜를 기록하지 않는다" | 시각화 30점 설계 시 |
| 10 | [LEDGER 설계 대조 검증](10-LEDGER-설계-대조검증.md) | 우리 최종 설계의 항목별 판정 — 근거 있음 / 근거 없음 / **근거가 반대** | **반드시 읽을 것** |

---

## 읽는 순서 추천

```
00 (트랙 재확인)
 └─▶ 10 (우리 설계 판정)  ← 여기서 먼저 결론을 보고
        ├─▶ 01, 02  (구조 근거)
        ├─▶ 03, 04  (검증·포기 근거)
        ├─▶ 05      (비용 근거)
        ├─▶ 06, 07  (트랙별 근거)
        └─▶ 08, 09  (리스크·시각화)
```

시간이 20분뿐이면 **10번만** 읽으면 된다. 나머지는 10번의 각주다.

---

## 이 리서치의 한계 — 미리 밝혀둠

1. **대부분의 논문이 frontier 모델(GPT-4o, Claude, Gemini)에서 측정됐다.** 우리가 쓰는 것은 `Qwen3-30B-A3B-Instruct-2507` 급 오픈 모델이다. 방향은 대체로 같지만 크기는 다를 수 있고, 특히 "형식 준수 실패율"은 작은 모델에서 **더 나쁘다**(→ `06`).
2. **AI:GO Squad 자체에 대한 외부 연구는 없다.** Backend.AI GO는 신제품이라 3자 벤치마크가 존재하지 않는다. AI:GO 관련 사실은 전부 공식 매뉴얼(`../../track_resource/lableup/03-AIGO-Squad-완전가이드.md`)에서 왔다.
3. **트랙의 hidden 세트 성격은 추정이다.** visible 121문항 실측(`../../example_task/00-트랙-정리.md`)에 기반한다.
4. 2026년에 출판된 arXiv 프리프린트 중 일부는 **동료 심사를 거치지 않았다.** 해당 항목은 본문에 `(프리프린트)`로 표시했다.
