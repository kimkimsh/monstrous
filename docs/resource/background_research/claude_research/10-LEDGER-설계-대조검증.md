# 10. LEDGER 설계 대조 검증 — 무엇이 근거가 있고 무엇이 반대되는가

> `../../../ideation/final_ideation/주제.md`의 최종 설계(**LEDGER Squad**)를 이 폴더의 리서치와 항목별로 대조한 판정 문서다.
>
> 판정은 세 가지다:
> - ✅ **근거 있음** — 독립 연구가 이 선택을 지지한다
> - ⚠️ **근거 약함** — 반대 근거가 있거나 조건부다. 실측 필요
> - ❌ **근거가 반대** — 문헌이 이 선택을 명시적으로 반박한다. **변경 권장**
>
> 시간이 없으면 **2절(❌ 항목)과 5절(실험 계획)만** 읽으면 된다.

---

## 1. 전체 판정 요약

| # | 설계 요소 | 판정 | 근거 문서 |
|---|---|---|---|
| 1 | 에이전트 5명 + 프로그램 1개 (6~7명이 아니라) | ✅ | `01`, `02` |
| 2 | Router = Planner, JSON 한 줄 출력 | ✅ | `01` (Routing 패턴), AI:GO 강제 |
| 3 | Architect: 60,000자 → 요약이 아니라 **앵커** | ✅ **강함** | `06` (localization 15~17배 / +4.2~4.4%p) |
| 4 | Editor: 앵커 주변만 보고 SEARCH/REPLACE | ✅ **강함** | `06` (SWE-Edit +2.7~18.3%p) |
| 5 | Preflight: 프로그램 검증, LLM 호출 0 | ✅ **강함** | `03` (self-correction 실패 / GenRM 8배) |
| 6 | 포기 3층 = `max_tokens` / Budget Config / 러너 산수 | ✅ **강함** | `04` (s1 budget forcing) |
| 7 | 프롬프트 3층 캐시 경계 | ✅ | `05` |
| 8 | 장부를 채점되는 응답 본문 안에 | ✅ | `09` (바이트 동일성), 트랙 규칙 |
| 9 | 무료 반사실 재생 + 에이전트 제거 ablation | ✅ | `09` |
| 10 | 주최 열거형 + OTel 어휘 사용 | ✅ | `09` |
| 11 | 다수결이 검증자보다 낫다 (고정 예산) | ⚠️ **조건부** | `03`, `07` — generic·어려운 문항에서는 역효과 |
| 12 | Auditor: 무료 신호 두 개가 엇갈릴 때만 승급 | ⚠️ **약함** | `03` (LLM 검증자 효과 의심) |
| 13 | Solver: math·generic 전담 단일 에이전트 | ✅ | `01` (예산 맞추면 SAS 우위) |
| 14 | **generic 1턴 `--no-think` 최소 출력** | ❌ **반대** | `07` (MMLU-Pro CoT +19.1%p) |
| 15 | **`max_tokens`: generic 4 / math 32~64** | ❌ **반대** | `07`, `04` |
| 16 | 에이전트 프롬프트에 역할 정체성 부여 | ⚠️ | `02` (persona 무효과) |
| 17 | `--no-think`를 주력 레버로 | ⚠️ **일부 무의미** | `00` (주력 모델이 non-thinking 전용) |

**✅ 10개 / ⚠️ 5개 / ❌ 2개.** 뼈대는 옳고, 트랙별 파라미터 두 곳이 틀렸다.

---

## 2. ❌ 근거가 반대되는 것 — 반드시 고칠 것

### 2-1. generic 트랙 "1턴, 추론 없이 답 문자만" — 최대 19.1%p 손실

**초안**:
> MCQ PATH (generic): Wave 1 Solver — 보기 문자 하나만 출력. **웨이브 1개.**
> Solver: math·generic 전용. **1턴, `--no-think`, 최소 출력**
> generic: 답 문자가 한 번 나오면 즉시 종료

**반대 근거** ([MMLU-Pro, NeurIPS 2024](https://arxiv.org/abs/2406.01574), Table 3):

| 모델 | MMLU-Pro CoT | MMLU-Pro Direct | 차이 |
|---|---|---|---|
| GPT-4o | 72.6 | 53.5 | **+19.1** |
| GPT-4-Turbo | 63.7 | 48.4 | **+15.3** |
| Phi3-medium | 55.7 | 47.5 | +8.2 |
| Gemma-7B | 33.7 | 27.0 | +6.7 |
| Llama-3-8B | 35.4 | 31.5 | +3.9 |

논문 원문: *"MMLU-Pro **necessitates chain-of-thought** to achieve promising results... In contrast, CoT will actually **hurt** the performance of models on MMLU."*

**"객관식이니 추론이 필요 없다"는 직관은 MMLU(구버전)에서는 맞고 MMLU-Pro에서는 틀리다.** 그리고 우리 모델의 MMLU-Pro 78.4는 GPT-4o(72.6)보다 높으므로, CoT 이득 구간의 **상단**에 있을 가능성이 크다.

#### 이 지시가 지금 어느 파일에 들어 있는가

`../../example_task/prompts/generic.txt` (현재 활성 프롬프트, 439바이트):

> Only the letter is graded. Reasoning you print is neither read nor rewarded, so **print as little as you need to settle the choice — for most questions that is nothing.**

**고쳐야 할 파일이 이것이다.** "채점되지 않는다"와 "정답률에 기여하지 않는다"는 다른 명제이고, MMLU-Pro에서는 후자가 거짓이다.

그리고 `required_output.txt`가 이미 허락하고 있다 — *"Anything before it is **ignored, not penalised**."* **앞에 추론을 써도 감점이 없다.**

산수로 확인하면:
- generic 가중치 0.25 × 정확도 손실 10%p = **총점 2.5%p 손실**
- 아낀 토큰: hidden 698문항 × 약 200토큰 = 약 14만 출력 토큰

**총점 2.5%p를 14만 토큰과 바꾼 것이다. 나쁜 거래다.** 벤치마크 40점과 토큰 30점의 상대 가중을 생각하면 더 나쁘다.

#### 대안 — Chain of Draft

[Chain of Draft (arXiv 2502.18600)](https://arxiv.org/html/2502.18600): 각 추론 단계를 **최대 다섯 단어**로 제한.
- GSM8K: CoT 95%+/200토큰 → **CoD 91%/40토큰**
- Sports: CoT 93.2%/189.4토큰 → **CoD 97.3%/14.3토큰**
- 전반적으로 CoT의 **7.6~20% 토큰**으로 정확도 유지 또는 향상

**권장 generic 출력 형식**:
```
<5단어 이하 단계 3~6줄>
Answer: X
```
`max_tokens` 512~1,024. 추정 비용은 full CoT의 약 1/4, direct의 약 15배지만 **정확도 손실이 없다.**

**추가 안전장치**: 트랙 규칙 *"the last one is used. Anything before it is ignored, not penalised."* 덕분에 CoD 단계들이 앞에 와도 감점이 없다. **형식 제약과 자유 추론을 동시에 가질 수 있다** — [Let Me Speak Freely?](https://doi.org/10.48550/arxiv.2408.02442)가 경고한 "형식 제약으로 인한 추론 저하"를 구조적으로 회피한다.

### 2-2. `max_tokens` 극단 절약 — `extraction_failed`를 자초한다

**초안**:
> generic: `max_tokens: 4` 수준까지 가능 / math: `max_tokens: 32~64`

**문제**:
1. 위 2-1의 CoT를 원천 차단한다.
2. math에서 32~64토큰으로는 MATH level-5나 AIME를 풀 수 없다. Qwen 모델 카드는 **출력 길이 16,384토큰**을 권장한다.
3. 잘리면 `extraction_failed` = **팀 책임 0점**. 포털 원문: *"a silent zero hides a harness defect behind a team's score"* — 즉 이 분류는 팀 실수를 숨기지 않으려고 일부러 만든 것이다.

**권장값** (→ `04` 6절):

| 트랙 | 초안 | **권장** |
|---|---|---|
| generic | 4 | **512 ~ 1,024** |
| math | 32~64 | **1,024 ~ 2,048** |
| coding/swebench | 1,000~2,000 | **2,048 ~ 4,096 + 꼬리 예산 예약** |

**절약은 `max_tokens`가 아니라 프롬프트로 한다.** "설명 금지, 서두 금지" + CoD 제약. `max_tokens`는 폭주 방지용 안전 상한으로만.

---

## 3. ⚠️ 근거가 약한 것 — 실측으로 결정할 것

### 3-1. Auditor — 유일한 승급 호출

**초안**: *"Auditor — 유일한 승급 호출. Preflight가 실패했거나 무료 신호 두 개가 엇갈릴 때만"*

**우려**:
1. **LLM 검증자의 효과 자체가 의심스럽다.** [GenRM vs SC](https://arxiv.org/abs/2504.01005): GenRM은 단순 다수결을 따라잡는 데만 **최대 8배** 연산.
2. **자기검증은 성능을 깎는다.** [Huang et al.](https://arxiv.org/abs/2310.01798): GSM8K GPT-4 95.5 → 89.0. 그리고 *"when the prompt is already precise and explicit, self-correction degrades performance"* — 우리 출력 계약이 정확히 그 조건.
3. **"무료 신호 두 개가 엇갈릴 때"의 두 번째 신호(샘플 일치)가 신뢰할 수 없다.** [GPQA 실험](https://arxiv.org/html/2608.11403v1): 다수결 일치율 게이트와 토큰 엔트로피 게이트 **둘 다** 정확도를 개선하지 못했다(차이 0.002 미만).

**대안**: Auditor를 없애고 **"Editor 재시도 + Preflight 구체 신호"** 로 대체.

```
Editor → Preflight
  ├─ 통과 → 종료
  └─ 실패 → 실패 사유(블록 번호 + 안 맞는 줄 + 가장 가까운 후보)를 붙여 Editor 재호출 (최대 1회)
             └─ 재실패 → give_up
```

이건 Huang et al.이 배제한 intrinsic self-correction이 **아니다** — 외부 결정론적 피드백이 있기 때문이다. Aider의 `ApplyError` 되먹임이 검증된 실전 패턴이다([search-replace-py](https://pypi.org/project/search-replace-py/)).

**다만 트랙 요구사항 고려**: 문제 지문이 *"which ones **verify the results**"* 를 명시적으로 물었다. Reviewer 역할 에이전트가 아예 없으면 요구사항 미충족으로 보일 위험이 있다.

**추가 위험 — 마지막 웨이브 규칙**

`../../example_task/01-요청-합성-규칙.md` 3절의 실측:

> judge는 [실행 완료 상태 요약을] 답으로 인정하지 않고 **마지막 웨이브부터 거꾸로** 태스크 출력을 훑는다.
> **마지막 웨이브의 태스크 출력이 답 블록으로 끝나야 한다.** 마지막 웨이브가 리뷰나 요약을 하고 답 블록을 다시 안 실으면, 그 앞 웨이브가 정답을 냈어도 judge가 마지막 웨이브에서 먼저 읽어간다.

**Auditor가 마지막 웨이브가 되면, Auditor가 답 블록 전체를 다시 실어야 한다.** SEARCH/REPLACE 블록을 재출력하는 것은 그 자체로 출력 토큰이 크고, 재출력 과정에서 **형식이 깨질 새로운 기회**를 만든다. Auditor를 두는 비용이 호출 1회가 아니라 **호출 1회 + 답 재출력 + 재출력 실패 리스크**인 것이다.

이 사실이 Auditor 폐지 쪽 논거를 크게 강화한다.

**절충안 권장**:
- Auditor를 **템플릿에는 남기되**(`role: Reviewer`), 호출 조건을 극단적으로 좁힌다 — **Preflight 2회 실패 시에만**, coding 트랙에서만.
- Auditor가 호출되면 **반드시 최종 답 블록을 다시 실어야 한다**는 것을 systemPrompt와 Preflight 양쪽에서 강제한다.
- 시각화에서 "Auditor 호출률 = N%" 와 **"Auditor를 제거했을 때의 점수(무료 ablation)"** 를 나란히 보여준다. 이러면 요구사항도 만족하고 **"우리는 검증자를 뒀지만 그것이 밥값을 하는지도 측정했다"** 는 서사가 된다. 이건 오히려 insightfulness 점수다.

### 3-2. "고정 예산에서는 검증자보다 다수결이 낫다"

**초안이 인용한 근거는 정확하다** — [arXiv 2504.01005](https://arxiv.org/abs/2504.01005)의 "GenRM이 SC를 따라잡는 데 8배". 하지만 **조건이 붙는다**:

| 조건 | 다수결 적합성 |
|---|---|
| math / MATH-500 level-5 | ⚠️ 우리 모델 MATH-500 97.5 — **포화 구간**, 이득 거의 없음 |
| math / AIME | ✅ 61.3 — 이득 구간. 단 `run_repeats: 2`로 실질 4배 |
| generic / MMLU-Pro | ❌ [backfire 연구](https://arxiv.org/html/2608.11403v1): 작은 모델 + 어려운 문항에서 문항의 56~66%에서 **해로움** |
| coding | ❌ 입력 16~20k라 n배가 그대로 비용 n배 |

**권장**: 다수결은 **AIME 문항에만** 실험적으로. 나머지는 n=1.

### 3-3. persona / 역할 정체성 프롬프트

[persona 연구 두 편](https://aclanthology.org/2024.findings-emnlp.888/)([Wharton](https://doi.org/10.48550/arxiv.2512.05858)) — 162개 역할 × 4개 모델 × 2,410문항, 그리고 MMLU-Pro 300문항 × 6개 모델에서 **개선 없음**, 일부 악화, 도메인 불일치 시 **거부율 급증**.

**권장**: `role` 필드는 AI:GO 스키마 요건으로 채우되, `systemPrompt`에서 *"You are an expert..."* 류 문장을 빼고 **출력 계약과 구체적 작업 지시**로 채운다. 절약되는 토큰은 덤이다.

### 3-4. `--no-think` 레버

**초안은 이 레버를 크게 다뤘지만**, 확인된 주력 모델 `Qwen3-30B-A3B-Instruct-2507`은 [모델 카드](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507)가 명시하듯 **non-thinking 전용**이다:

> This model supports only non-thinking mode and **does not generate `<think>` blocks** in its output. Meanwhile, specifying `enable_thinking=False` is no longer required.

즉 **주력 모델에서 이 레버는 무의미하다.** 나머지 두 reasoning 모델을 쓰기로 한 경우에만 의미가 있고, 그때는 `--thinking-budget N`이 켜고 끄는 이분법보다 나은 지점을 만든다.

**피칭 시 주의**: "우리는 `--no-think`로 토큰을 아꼈다"는 주장은 심사위원(Lablup, 이 모델을 제공한 쪽)에게 **틀린 이해로 보일 수 있다.** 대신 **"reasoning 모델을 아예 쓰지 않는 정책"** 으로 표현하는 것이 정확하다.

---

## 4. ✅ 근거가 강한 것 — 피칭에 그대로 쓸 것

### 4-1. Architect / Editor 분리

가장 강한 근거를 가진 설계 결정이다. 세 갈래로 뒷받침된다.

| 근거 | 수치 |
|---|---|
| [파일 컨텍스트 효과](https://arxiv.org/html/2604.05481) | 컨텍스트 없음 3.6% → 파일 레벨 56~63% (**15~17배**) |
| [Loc2Repair](https://arxiv.org/html/2606.30963v1) | 명시적 localization으로 44.7% → 48.9~49.1%, gold는 52.4%. 경과시간도 감소 |
| [SWE-Edit](https://arxiv.org/pdf/2604.26102v2) | reasoning과 형식 생성 분리로 편집 성공률 **+2.7~18.3%p**, resolve **+1.4~2.1%p**, 비용 **−17.9%** |
| [RGFL](https://arxiv.org/html/2601.18044v1) | reasoning 기반 랭킹으로 파일 Hit@1 71.4% → 85%, Agentless 통합 시 end-to-end **+12.8%** |

그리고 우리 모델의 Aider-Polyglot 35.6(LiveCodeBench 43.2 대비)이 **"못 고치는 게 아니라 편집 형식을 못 낸다"** 는 진단을 뒷받침한다.

**피칭 문장**: *"우리는 이 모델의 약점이 코딩 능력이 아니라 편집 형식 준수(Aider-Polyglot 35.6)라는 걸 알고, 그 능력만 별도 에이전트로 떼어냈습니다. 같은 분리로 SWE-bench Verified에서 편집 성공률이 12.8~18.3%p 오른 선행 연구가 있습니다."*

### 4-2. 검증자를 LLM이 아니게 만든 것

[Huang et al. ICLR 2024](https://arxiv.org/abs/2310.01798)(자기검증이 성능을 깎음) + [GenRM 8배](https://arxiv.org/abs/2504.01005) + [SWE-Edit의 edit success rate](https://arxiv.org/pdf/2604.26102v2).

**피칭 문장**: *"문제 지문이 '누가 결과를 검증하는가'를 물었습니다. 우리 답은 '검증자는 LLM이 아니어도 된다'입니다. 외부 신호 없는 LLM 자기검증은 GSM8K에서 GPT-4를 95.5%에서 89.0%로 떨어뜨렸고, 별도 검증 모델은 단순 다수결을 따라잡는 데만 8배 연산이 듭니다. 우리 Preflight는 LLM 호출 0회입니다."*

### 4-3. 포기 = 산수

[s1 (arXiv 2501.19393)](https://arxiv.org/abs/2501.19393)의 budget forcing이 **디코딩 개입**이라는 점, 그리고 [캘리브레이션 문헌](https://arxiv.org/html/2604.01457v2)이 언어화 확신도가 정답 여부와 거의 무관하게 인플레이션된다고 보고한 점.

**피칭 문장**: *"문제 지문이 '누가 포기 시점을 판단하는가'를 물었습니다. 우리 답은 '아무도 판단하지 않는다, 산수가 결정한다'입니다. s1 논문이 실측했듯 모델은 자기 토큰을 못 세고, 하드 캡만 작동합니다."*

### 4-4. 장부를 응답 본문 안에

`09`의 4-1 표가 근거다. OTel이 기본적으로 내용을 캡처하지 않는다는 사실, 그리고 표준 도구들이 요청 경로 **밖에서** 수집한다는 사실이 대비를 만든다.

**피칭 문장**: *"이 화면이 렌더링하는 바이트는 채점기가 읽은 그 바이트입니다. 옆에서 수집한 트레이스는 실제 채점 실행과 어긋날 수 있고 심사위원은 검증할 방법이 없습니다. 우리 방식은 어긋남이 구조적으로 불가능합니다."*

### 4-5. 표준 도구가 못 하는 것을 우리가 한다

[5개 관측 도구 인과성 테스트](https://www.binarybox.org/p/i-tested-5-agent-observability-tools)에서 LangSmith·Phoenix·Langfuse 전부 근본원인 규명에 60~90분. *"They record the 'when,' not the 'why.'"*

**피칭 문장**: *"심사 기준 여섯 축 중 traceability, explainability, insightfulness 세 개가 '왜'를 묻습니다. 그런데 업계 표준 관측 도구 전부가 그걸 못 한다는 공개 비교가 있습니다 — 단일 트레이스 근본원인 규명에 60~90분입니다. 우리 화면은 그 빈틈을 겨냥했습니다."*

---

## 5. 실험 계획 — 무엇을 어떤 순서로 재는가

`../../track_resource/lableup/07-토큰-효율-전략.md` 10절의 계획을 이 리서치 결과로 재작성했다.
연습 세트 121문항(`../../example_task/`), test run은 1/5 과금.

### 우선순위 1 — ❌ 판정 항목 검증 (가장 큰 점수 차이)

| 실험 | 변수 | 측정 | 판정 기준 |
|---|---|---|---|
| **E1** | generic: direct / CoD / full CoT | 정확도, 출력 토큰, `extraction_failed` 비율 | CoD가 direct보다 유의하게 정확하면 **초안 철회 확정** |
| **E2** | `max_tokens`: generic 4 / 128 / 512 / 1024 | 잘림 비율, 정확도 | 잘림 0%가 되는 최소값 + 여유 |
| **E3** | math `max_tokens`: 64 / 512 / 1024 / 2048 | 정확도, 잘림 | 위와 같음 |

**E1이 이 리서치에서 나온 가장 중요한 실험이다.** generic 42문항이면 3개 조건 × 42 = 126회 호출로 끝난다.

### 우선순위 2 — 핵심 구조 검증

| 실험 | 변수 | 측정 |
|---|---|---|
| **E4** | Architect 유/무 (Editor가 60,000자 직접 vs 앵커 경유) | coding 정확도(패치 적용 가능성 대리 지표), 총 토큰, `cached_input_share` |
| **E5** | Preflight 유/무 | `extraction_failed` 비율, 재시도 횟수, 최종 정확도 |
| **E6** | 재시도 상한: 0 / 1 / 2회 | 정확도-비용 곡선 |
| **E7** | Auditor 호출 조건: 없음 / Preflight 1회 실패 / 2회 실패 | 정확도 증분 vs 토큰 증분 |

**E4와 E5가 우리 설계의 두 기둥을 검증한다.** 실패하면 구조를 바꿔야 한다.

### 우선순위 3 — 비용 최적화

| 실험 | 변수 | 측정 |
|---|---|---|
| **E8** | 프롬프트 순서: Layer 3을 앞/뒤 | **`cached_input_share`** (`GET /api/teams/me/dev-usage`) |
| **E9** | Layer 1 길이: 512 / 1,024 / 2,048 토큰 | `cached_input_share` — 캐시 최소 문턱 확인 |
| **E10** | `Max agent turns`: 2 / 4 / 6 / 8 | coding 정확도-비용 곡선 |
| **E11** | 동시 실행: 1 / 2 / 3 에이전트 | `cached_input_share` (병렬이 캐시를 깨는지 확인) |
| **E12** | 메모리 on/off (Planner만) | 정확도 + `cached_input_share` |

### 우선순위 4 — 선택적

| 실험 | 변수 | 측정 |
|---|---|---|
| **E13** | AIME 문항 n=1 / 3 | 정확도 이득 vs 4배 비용 (`run_repeats: 2` 포함) |
| **E14** | Layer 1에 django/matplotlib 관례 주입 유/무 | coding 정확도 |
| **E15** | livecodebench n=1 / 3 | 정확도 vs 비용 (입력이 짧아 상대적으로 쌈) |

### 판정 기준 — 모든 실험 공통

[Budget-Aware Evaluation](https://aclanthology.org/2024.emnlp-main.1112/)의 기준을 그대로 채택한다:

> a proposed reasoning strategy should be considered effective **only if its performance is better compared to a baseline of equivalent budget**.

즉 **"정확도가 올랐다"로는 부족하다.** 같은 토큰을 다른 데 썼을 때보다 나은지를 봐야 한다. 이 트랙은 토큰 효율이 30점이고 동점 처리 기준이므로, 이 기준이 곧 채점 구조다.

### Preflight 회귀 테스트 (실험이 아니라 필수 작업)

Preflight는 단일 실패점이다. 연습 세트 121문항으로:
- **false positive**(정상 출력을 반려) 비율 → **0에 가까워야 함**
- false negative(잘못된 출력을 통과) 비율 → 낮을수록 좋지만 FP보다는 덜 치명적

---

## 6. 최종 권장 설계 — 변경 반영본

```
                       ┌────────────────┐
  one-shot prompt ───▶ │  Router        │  role: Planner
  + item payload       │  JSON 한 줄     │  max_tokens 소량
                       └───────┬────────┘
                               │ payload.kind
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
  ┌───────────┐         ┌───────────┐          ┌───────────┐
  │ CODE      │         │ MATH      │          │ MCQ       │
  └───────────┘         └───────────┘          └───────────┘
   Architect              Solver                 Solver
   (앵커 2~3개+why)       (\boxed{}, CoT)        (CoD 3~6줄 + Answer: X)
        ↓                 max_tokens 1~2k        max_tokens 512~1k   ← ★변경
   Editor                      ↓                      ↓
   (SEARCH/REPLACE)      [Preflight M1~M3]      [Preflight G1~G3]
   max_tokens 2~4k             ↓                      ↓
        ↓                    종료                    종료
   [Preflight C1~C8]     (integer 위반 시 1회 재시도)
        ↓
   실패 → Editor 재호출(구체 신호) 최대 1회
        ↓
   2회 실패 → Auditor (coding 한정, 호출률 측정 대상)   ← ★조건 강화
        ↓
   [잔액 산수] 잔액 < 견적이면 다음 호출 안 함
```

**변경점 다섯 (★)**:
1. generic: direct → **Chain-of-Draft 짧은 CoT**
2. `max_tokens`: 극단 절약 → **잘림 0%를 보장하는 값 + 여유**
3. Auditor: "Preflight 실패 또는 신호 불일치" → **"Preflight 2회 실패, coding 한정"**
4. Preflight 검사 항목 4개 추가 (SEARCH 유일성 C5, 중복 블록, 마크다운 펜스, 앵커 줄범위) — `08` 참조
5. systemPrompt에서 persona 문장 제거, **출력 계약만**

---

## 7. 이 리서치가 우리 서사에 더해 주는 것

피칭에서 쓸 수 있는 "우리는 이걸 알고 설계했다" 목록이다. 각각 출처가 있다.

1. **멀티 에이전트는 3~10배 비싸고, 예산을 맞추면 단일 에이전트가 이긴다.** 그래서 우리는 에이전트를 늘리지 않고 요구사항을 만족시켰다.
2. **역할로 나누는 분업은 Anthropic이 실험으로 반박했다** — 서브에이전트가 실제 작업보다 조율에 토큰을 더 썼다. 우리는 컨텍스트 경계로 나눴다.
3. **persona 프롬프트는 정확도에 기여하지 않는다** (162개 역할 × 2,410문항, 그리고 MMLU-Pro 300문항). 우리 시스템 프롬프트에는 정체성 문장이 없다.
4. **LLM 자기검증은 성능을 깎는다** (GSM8K 95.5 → 89.0). 우리 검증자는 LLM이 아니다.
5. **모델은 자기 토큰을 못 센다** (s1). 우리 포기는 산수다.
6. **편집 형식 준수와 코딩 능력은 다른 능력이다** (SWE-Edit, 그리고 이 모델의 Aider-Polyglot 35.6). 우리는 그 둘을 분리했다.
7. **MMLU-Pro는 CoT를 요구한다** (+19.1%p). 우리는 CoT를 켜되 Chain-of-Draft로 토큰의 8~20%만 쓴다.
8. **표준 관측 도구는 "언제"만 기록하고 "왜"를 기록하지 않는다** (5개 도구 비교, 근본원인 60~90분). 심사 6축 중 셋이 "왜"를 묻는다.
9. **prefix cache는 순서가 전부다** (캐시 읽기 = 정가의 10%, 최소 1,024토큰). 우리 3층 배치는 그 위에 서 있다.
10. **우리는 우리 설계가 밥값을 하는지도 측정했다** — 무료 ablation(에이전트 제거 슬라이더).

10번이 특히 강하다. **설계를 자랑하는 팀은 많고, 자기 설계를 반증 가능한 형태로 측정해 보여주는 팀은 드물다.**

---

## 8. 남은 미확인 사항 — 실측·문의로만 해소됨

| # | 항목 | 왜 중요한가 | 확인 방법 |
|---|---|---|---|
| 1 | 평가 모델 3종 이름과 USD/Mtok 단가 | cascade 설계의 전제 | 온보딩 질문 |
| 2 | `per_run_token_cap`, `per_item_wallclock_seconds` | 잔액 산수의 상수 | 온보딩 / 실행 기록 |
| 3 | **평가 중 러너 레벨 후처리(Preflight·재시도)가 허용되는가** | **Preflight의 존폐** | 온보딩 **최우선** |
| 4 | 공유 서빙 스택의 prefix cache 실제 동작 (엔진, 최소 토큰, TTL) | 3층 배치의 실효 | `cached_input_share` 실측(E8, E9) |
| 4-b | **AI:GO가 각 squad 에이전트에게 원 요청 전문(60,000자 포함)을 넘기는가, planner가 만든 태스크 설명만 넘기는가** | **"문항 내 캐시 공유로 입력 1/4" 계산의 전제.** 에이전트별 systemPrompt가 item payload 앞에 오므로 이론상 순서(L1→L2→L3)를 만들 수 없다 (→ `05` 2절 단서) | 온보딩 / 로컬 실행 로그 확인 / E8·E11 |
| 5 | judge의 SEARCH/REPLACE 관용도 (공백 fuzzy 매칭 여부, 빈 SEARCH의 해석) | Preflight 엄격도 조정 | 온보딩 / 연습 세트 실험 |
| 6 | one-shot 프롬프트 주입 위치 | Layer 1 설계 | 온보딩 |
| 7 | generic grader가 MMLU-Pro 공식 추출기와 같은가 | 답 형식 결정 | `../../example_task/prompts/generic.txt` 재확인 |

**3번이 안 되면 Preflight를 프롬프트 안 체크리스트로 다운그레이드**해야 한다. 효과는 줄지만 0은 아니다 — SWE-Edit의 Editor 프롬프트가 그 체크리스트의 좋은 원형이다.

---

## 참고 문헌

이 문서의 모든 근거는 `01`~`09`에 출처와 함께 정리되어 있다. 가장 자주 인용된 것만:

- [MMLU-Pro (NeurIPS 2024)](https://arxiv.org/abs/2406.01574) — generic 전략 뒤집는 근거
- [Chain of Draft](https://arxiv.org/html/2502.18600) — 그 대안
- [SWE-Edit](https://arxiv.org/pdf/2604.26102v2) — Architect/Editor 분리 근거
- [On the Role of Fault Localization Context](https://arxiv.org/html/2604.05481) / [Loc2Repair](https://arxiv.org/html/2606.30963v1) — localization 정량 효과
- [Huang et al., LLMs Cannot Self-Correct Reasoning Yet](https://arxiv.org/abs/2310.01798) — 검증자 설계 근거
- [s1: Simple test-time scaling](https://arxiv.org/abs/2501.19393) — 포기=산수 근거
- [Anthropic, When to use multi-agent systems](https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them) — 구조 설계 근거
- [Why Do Multi-Agent LLM Systems Fail? (MAST)](https://arxiv.org/abs/2503.13657) — 실패 모드 체크리스트
- [Qwen3-30B-A3B-Instruct-2507 모델 카드](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507) — 모델 사실
