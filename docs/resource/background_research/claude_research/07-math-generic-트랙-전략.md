# 07. math · generic 트랙 전략 — 초안을 뒤집는 발견이 여기 있다

> Q6-b: **math와 generic 경로를 어떻게 짜야 하는가?**
>
> 결론 먼저: **generic(MMLU-Pro)에서 "답 문자만 뽑아라"는 우리 초안의 전략은 잘못됐다.** MMLU-Pro는 설계상 CoT를 요구하는 벤치마크이고, direct answering으로 바꾸면 GPT-4o 기준 **19.1%p**가 날아간다. 대신 **Chain-of-Draft로 짧은 CoT를 쓰는 것**이 정확도와 비용을 동시에 잡는 유일한 경로다.
>
> 이것이 이번 리서치에서 나온 가장 값비싼 발견이다.

---

## 1. generic 트랙의 정체 — MMLU-Pro

| 항목 | 값 |
|---|---|
| 데이터셋 | `TIGER-Lab/MMLU-Pro` (rev `b189ec765aa7ed75c8acfea42df31fdae71f97be`, MIT) |
| 가중치 | 0.25 |
| hidden 문항 | **448 ~ 698** (카테고리당 20문항, 14과목) |
| visible 실측 | 42문항 = 14과목 × 3 |
| 요청 크기 | 최소 474 / 중앙값 **918** / 최대 2,926 바이트 |
| 보기 개수 | **가변.** 10개가 36문항, 나머지는 3·4·7·8·9개 혼재 |
| 채점 | `letter_match` — 보기 문자 대조, 대소문자 무시 |
| 과목 | biology, business, chemistry, computer science, economics, engineering, health, history, law, math, other, philosophy, physics, psychology |

**문항 수가 가장 많다.** 그래서 여기서 아끼는 것이 총 비용에 가장 크게 기여한다 — 그것이 우리 초안이 "1턴, 답 문자만"으로 간 이유다. 그 판단이 틀렸다.

---

## 2. MMLU-Pro는 CoT를 요구하도록 설계됐다

[MMLU-Pro: A More Robust and Challenging Multi-Task Language Understanding Benchmark (NeurIPS 2024, arXiv 2406.01574)](https://arxiv.org/abs/2406.01574)

논문의 명시적 발견 #4:

> MMLU-Pro **necessitates chain-of-thought (CoT) to achieve promising results.** For instance, CoT can boost the performance of GPT-4o by **19%**. In contrast, **CoT will actually hurt the performance of models on MMLU.** This reflects the necessity to perform deliberate reasoning on MMLU-Pro.

논문 Table 3 원문 수치:

| 모델 | MMLU CoT | MMLU Direct | 차이 | **MMLU-Pro CoT** | **MMLU-Pro Direct** | **차이** |
|---|---|---|---|---|---|---|
| GPT-4o | 88.7 | 87.2 | +1.5 | **72.6** | **53.5** | **+19.1** |
| GPT-4-Turbo | 86.5 | 86.7 | −0.2 | **63.7** | **48.4** | **+15.3** |
| Phi3-medium-4k-instruct | 79.4 | 78.0 | +1.4 | 55.7 | 47.5 | **+8.2** |
| Llama-3-8B | 62.7 | 66.6 | −3.9 | 35.4 | 31.5 | **+3.9** |
| Gemma-7B | 62.4 | 66.0 | −3.6 | 33.7 | 27.0 | **+6.7** |

[Hugging Face 데이터셋 카드](https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro)도 같은 말을 한다: *"the performance dropped by as much as **19% without chain-of-thought reasoning**."*

### 이 표에서 읽어야 할 두 가지

1. **CoT 이득은 모델 능력에 비례한다.** 강한 모델일수록 CoT로 얻는 게 많다 (GPT-4o +19.1 vs Llama-3-8B +3.9). 우리 모델은 MMLU-Pro 78.4로 GPT-4o(72.6)보다도 높다 — **CoT 이득 구간의 상단에 있을 가능성이 높다.**
2. **MMLU(구버전)와 정반대다.** MMLU에서는 CoT가 오히려 해로웠다. "객관식이니 CoT 필요 없다"는 직관은 MMLU 시대의 것이고 MMLU-Pro에는 적용되지 않는다.

### 그리고 MMLU-Pro는 프롬프트에 둔감하다

같은 논문: 24가지 프롬프트 스타일 테스트에서 점수 변동이 MMLU의 4~5%에서 **MMLU-Pro는 약 2%** 로 줄었다 (최대 변동 10.98% → 3.74%).

> **함의**: 프롬프트를 정교하게 튜닝해서 얻을 이득은 작다(±2%). **반면 CoT를 켜고 끄는 것은 ±19%p다.** 튜닝 시간을 프롬프트 문구가 아니라 **CoT 길이 스윕**에 쓰는 것이 옳다.

---

## 3. 그럼 비용은? — Chain of Draft가 답이다

문제: CoT를 켜면 정확도는 오르지만 hidden 448~698문항 × 출력 토큰이 비용의 큰 몫이 된다.

해법: [Chain of Draft (arXiv 2502.18600)](https://arxiv.org/html/2502.18600) — **"각 추론 단계를 최대 다섯 단어로 제한"**.

| 태스크 | Standard | CoT | **CoD** |
|---|---|---|---|
| GSM8K (GPT-4o, Claude 3.5 Sonnet) | 53.3% / 64.6% | 95%+ / **~200토큰** | **91% / ~40토큰** |
| Date understanding (GPT-4o) | 90.0% / 1.0토큰 | 95.9% / 28.7토큰 | **98.3% / 15.0토큰** |
| Sports (Claude 3.5 Sonnet) | 90.6% / 1.0 | 93.2% / **189.4** | **97.3% / 14.3** |
| Symbolic (coin flip) | 73.2 / 85.2% | 100% | **100%**, 토큰 −68~86% |

**CoD는 direct answering보다 훨씬 정확하고, CoT의 8~20% 토큰만 쓴다.** 그리고 두 개 태스크에서는 CoT보다도 정확했다.

### generic 트랙 권장 출력 구조

```
<한 줄 5단어 이하 추론 단계들, 3~6줄>
Answer: X
```

`max_tokens` 는 **512~1,024** 정도. 초안의 `max_tokens: 4`는 CoT 자체를 불가능하게 만들므로 철회.

비용 추정 (hidden 698문항 기준, 대략치):
- direct 4토큰: 약 2,800 출력 토큰 — 그런데 정확도가 최대 19%p 낮다
- CoD 약 60토큰: 약 42,000 출력 토큰
- full CoT 약 250토큰: 약 175,000 출력 토큰

**CoD는 full CoT 대비 13만 토큰을 아끼면서 정확도 대부분을 지킨다.** 이게 generic 트랙의 정답이다.

---

## 4. 답 추출 — 이게 틀리면 정답도 0점이다

### MMLU-Pro 공식 추출 절차

논문 원문:

> To extract answers from the model-generated reasoning content, we initially use the regular expression `answer is \(?\([A-J]\)?\)` to match the format specified in the prompt instructions and few-shot examples. If this regex fails to retrieve a valid answer, possibly due to formatting deviations by the model, we employ a secondary regex `\.*\[aA\]nswer:\s*\([A-J]\)` for a second attempt. If both fail, **a fallback mechanism is implemented where a random option from the answer choices is selected.**

세 가지 실무 함의:

1. **`answer is (X)` 또는 `Answer: X` 형태를 쓰는 것이 가장 안전하다.** 공식 하네스가 이 두 패턴을 찾는다.
2. **주최 측 grader는 `letter_match`라고만 명시됐다.** MMLU-Pro 공식 추출기와 같은지 확인이 필요하다. `../../example_task/prompts/generic.txt`와 `../../example_task/01-요청-합성-규칙.md`의 실제 요청 본문 문구를 따라야 한다.
3. **fallback이 random이라는 점.** 추출 실패 시 이번 트랙에서는 `extraction_failed`(팀 책임)로 별도 분류되므로 random fallback보다 더 나쁘다.

### 보기 개수가 가변이라는 함정

visible 42문항 실측: 10개가 36문항, 나머지는 3·4·7·8·9개.

> **"A부터 J 중에 고르라"고 하드코딩하면 보기가 3개인 문항에서 존재하지 않는 보기를 고른다.** 요청 본문의 Options 블록에 실제 문자가 나열돼 있으니 **거기서만 고르게** 해야 하고, Preflight가 **답 문자 ∈ 그 문항의 option_letters** 를 검사해야 한다 (→ `03` G1).

### Qwen 모델 카드의 공식 권장 문구

[Qwen3-30B-A3B-Instruct-2507](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507) Best Practices:

> **Multiple-Choice Questions**: Add the following JSON structure to the prompt to standardize responses: `"Please show your choice in the answer field with only the choice letter, e.g., "answer": "C"."`

**모델 제작사가 직접 권장하는 형식이다.** 다만 `03`에서 본 [Let Me Speak Freely?](https://doi.org/10.48550/arxiv.2408.02442) 결과(형식 제약이 추론을 깎는다)를 고려하면, **JSON 강제를 추론 전체에 걸지 말고 마지막 줄에만** 거는 편이 낫다. 트랙 규칙("마지막 것만 사용, 앞은 감점 없음")이 이걸 허용한다.

---

## 5. self-consistency를 generic에 붓지 마라

`02`·`03`에서 본 근거를 generic 조건에 대입한다.

| 근거 | 수치 | generic 적용 |
|---|---|---|
| [When Self-Consistency Backfires](https://arxiv.org/html/2608.11403v1) | GPQA Diamond에서 Qwen2.5-7B는 문항의 **56.6%**, Llama-3-8B는 **65.7%** 에서 다수결이 정확도를 낮춤 | GPQA는 MMLU-Pro보다 어렵지만 방향은 같다. 그리고 **일치율 게이트·엔트로피 게이트 둘 다 실패** |
| [Diminishing Returns](https://arxiv.org/html/2511.00751v2) | 강한 모델에서 SC 이득 1.6%p에 15배 비용, 15샘플 이후 **하락** | 우리 모델의 MMLU-Pro 78.4는 "강한 모델" 구간 |
| [Modal ceiling](https://export.arxiv.org/pdf/2606.28661) | selection은 modal-hit rate에 수렴. 최빈 답이 틀린 문항은 샘플을 늘릴수록 **더 확실히 틀린다** | 객관식은 답 공간이 3~10개로 작아 최빈 답 수렴이 특히 빠르다 |

그리고 산수: hidden 698문항 × n=3이면 출력 토큰이 3배. 가중치 0.25짜리 트랙에서 이 비용은 coding으로 갔어야 할 예산이다.

> **결론: generic은 n=1, CoD, 1웨이브.** 검증 웨이브도 붙이지 않는다(답 문자가 유효 집합 안에 있으면 프로그램이 즉시 통과시킨다).

---

## 6. math 트랙

| 항목 | 값 |
|---|---|
| 데이터셋 | `HuggingFaceH4/MATH-500` (level-5 subset, MIT) + `HuggingFaceH4/aime_2024` |
| 가중치 | 0.25 |
| hidden 문항 | **60 ~ 66**, 단 **`run_repeats: 2`** — 같은 문제를 2회 실행해 평균 |
| visible 실측 | 59문항 = math-500-level5 48 + aime-2024 11 |
| 답 형식 | integer 35 / expression 24 |
| 요청 크기 | 최소 334 / 중앙값 **491** / 최대 1,570 바이트 |
| 채점 | integer: `integer_exact` + `math_verify` / expression: `math_verify` (LaTeX 정규화 포함) |

**지문이 매우 짧다 → 비용은 거의 전부 출력 토큰이다.** 그리고 `run_repeats: 2`이므로 실질 비용은 2배.

### Qwen 모델 카드의 math 권장 문구

> **Math Problems**: Include `"Please reason step by step, and put your final answer within \boxed{}."` in the prompt.

모델 카드 성적: **AIME25 61.3**, 그리고 Artificial Analysis 측정으로 **MATH-500 97.5**([Benchmark Atlas](https://atlas.kevinhu.io/models/qwen3-30b-a3b-instruct-2507)).

> **중요한 시사점**: MATH-500이 97.5라면 **level-5 subset이라도 대부분 1패스로 맞힌다**는 뜻이다. self-consistency의 이득 구간이 아니다([Diminishing Returns]가 정확히 이 상황을 다룬다 — 98% 베이스라인에서 15샘플로 +1.6%p).
>
> 반면 **AIME25 61.3은 self-consistency 이득 구간**이다. 30문항 정도이므로 여기에만 n을 쓰는 것은 검토할 만하다. 다만 `run_repeats: 2`가 이미 걸려 있어 실질 4배가 된다.

### math 경로 권장

```
Wave 0  Router   answer_format 판별 (integer / expression)
Wave 1  Solver   "Please reason step by step, and put your final answer within \boxed{}."
                 max_tokens 1,024~2,048
[프로그램] Preflight  M1~M3 (→ 03)
                 integer 문항인데 수식/단위/쉼표가 나오면 1회 재시도
```

**웨이브를 늘리면 2배로 비싸진다**(`run_repeats: 2`). 최소로 유지.

self-consistency는 **AIME 문항에 한해** 실험하되, 연습 세트에서 "n=1 대비 n=3의 정확도 이득 vs 비용"을 실측한 뒤 결정. 판정 기준은 [Budget-Aware Evaluation](https://aclanthology.org/2024.emnlp-main.1112/)의 기준을 그대로 쓴다 — **같은 예산의 베이스라인보다 나을 때만 채택**.

### 답 추출 함정

- `math_verify`는 LaTeX 정규화를 포함하므로 `\frac{1}{2}`와 `0.5` 같은 동치를 처리한다.
- `integer_exact`는 **정수 정확 일치**다. `1,000`(쉼표), `1000 units`(단위), `\frac{2000}{2}`(수식)는 위험하다.
- `\boxed{}`가 여러 개면 **마지막 것**이 쓰인다 → 중간 계산에 `\boxed{}`를 쓰지 말라고 명시해야 한다.

---

## 7. 두 트랙 설정 요약표 — 초안 대비 변경점

| 항목 | 초안 | **리서치 반영** | 변경 근거 |
|---|---|---|---|
| generic 추론 | 없음 (답 문자만) | **CoD 짧은 CoT** | MMLU-Pro CoT +3.9~19.1%p |
| generic `max_tokens` | 4 | **512~1,024** | 위 + 잘림 방지 |
| generic 웨이브 | 1 | **1** (유지) | 검증은 프로그램 |
| generic 샘플 수 | 1 | **1** (유지) | backfire·modal ceiling |
| generic 예산 (Max total) | 3,000 | **6,000** | CoD 여유 |
| math 추론 | \boxed{} 형식 | **모델 카드 권장 문구 그대로** | 제작사 권장 |
| math `max_tokens` | 32~64 | **1,024~2,048** | 32토큰으로는 풀 수 없다 |
| math 샘플 수 | 1 | **1 기본, AIME만 n=3 실험** | MATH-500 97.5는 포화 / AIME 61.3은 이득 구간 |
| 보기 문자 검증 | 있음 | **있음 + 문항별 option_letters 집합 대조** | 보기 3~10개 가변 |

---

## 8. 이 문서의 결론

1. **MMLU-Pro는 CoT를 요구하는 벤치마크다.** direct answering으로 바꾸면 최대 19.1%p 손실. "객관식이니 답만 뽑자"는 MMLU 시대의 직관이며 여기 적용되지 않는다.
2. **Chain-of-Draft가 정확도와 비용을 동시에 잡는 유일한 경로다.** CoT의 8~20% 토큰으로 정확도 대부분 유지, 일부 태스크에서는 CoT보다 우수.
3. **MMLU-Pro는 프롬프트 문구에 둔감하다(±2%).** 튜닝 시간을 문구가 아니라 CoT 길이 스윕에 쓸 것.
4. **답 추출 규칙을 공식 하네스에 맞춰라.** `answer is (X)` / `Answer: X`. 그리고 보기 개수가 가변임을 프로그램이 검사.
5. **generic에 self-consistency를 붓지 마라.** backfire, modal ceiling, 그리고 예산 기회비용.
6. **math는 출력 비용이 전부이고 2회 반복된다.** 웨이브 최소화. MATH-500은 포화 구간, AIME만 샘플링 이득 구간.
7. **모델 카드의 권장 프롬프트 문구를 그대로 쓴다.** 제작사가 벤치마크 재현에 쓴 문구다.

---

## 참고 문헌

- Wang et al., [MMLU-Pro: A More Robust and Challenging Multi-Task Language Understanding Benchmark](https://arxiv.org/abs/2406.01574), NeurIPS 2024 · [데이터셋](https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro) · [코드](https://github.com/TIGER-AI-Lab/MMLU-Pro) · [발표 슬라이드](https://neurips.cc/media/neurips-2024/Slides/97435.pdf)
- Xu et al., [Chain of Draft: Thinking Faster by Writing Less](https://arxiv.org/html/2502.18600) · [코드](https://github.com/sileix/chain-of-draft) · [AWS 재현](https://aws.amazon.com/blogs/machine-learning/move-beyond-chain-of-thought-with-chain-of-draft-on-amazon-bedrock/)
- Qwen, [Qwen3-30B-A3B-Instruct-2507 모델 카드](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507) · [Benchmark Atlas](https://atlas.kevinhu.io/models/qwen3-30b-a3b-instruct-2507)
- [When Self-Consistency Backfires](https://arxiv.org/html/2608.11403v1) (프리프린트)
- [Diminishing Returns and Rising Costs in Modern LLMs](https://arxiv.org/html/2511.00751v2) (프리프린트)
- [When More Sampling Hurts: The Modal Ceiling](https://export.arxiv.org/pdf/2606.28661) (프리프린트)
- Wang et al., [Reasoning in Token Economies](https://aclanthology.org/2024.emnlp-main.1112/), EMNLP 2024
- Tam et al., [Let Me Speak Freely?](https://doi.org/10.48550/arxiv.2408.02442)
