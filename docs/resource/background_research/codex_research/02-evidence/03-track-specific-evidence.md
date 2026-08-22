# Track별 외부 근거와 적용 한계

## Coding

### Agentless가 보여준 것

[Agentless](https://arxiv.org/html/2407.01489v2)는 repository-level repair를 localization, repair, patch validation의 세 단계로 단순화했다. SWE-bench Lite 300개에서 96개, 32.0%를 해결했고 평균 비용은 $0.70, 78,166 token이었다.

세부 결과 중 전이 가능한 것:

- file localization prompt는 ground-truth file을 78.67% 찾았고 여러 신호를 합치면 81.67%였다.
- complete file보다 related code skeleton이 더 싸고 localization도 높았다: 58.33% 대 53.67%, 대략 $0.02 대 $0.15.
- repair sampling은 단순히 많이 늘린다고 계속 좋아지지 않았다. 4×10 sample 32.0% 대 greedy 40 sample 29.33%였다.
- simple diff가 작고 다루기 쉬웠다.

직접 전이되지 않는 것:

- Agentless는 repository retrieval, test reproduction, regression test를 사용한다.
- 이 track은 tool과 repo browsing이 없고 judge가 이미 context를 제공한다.
- 따라서 단계 구조와 minimal edit 원칙만 가져오고, tool result 수치는 예상 성능으로 쓰지 않는다.

### SWE-Edit가 보여준 것

[SWE-Edit](https://arxiv.org/html/2604.26102v2)는 Viewer와 Editor를 interface subagent로 분리했다. SWE-bench Verified 500개를 세 번 실행한 평균에서 resolve rate 69.9→72.0%, +2.1pp, cost $243.7→$200.1, −17.9%, edit success 93.4→96.9%였다.

그러나 이 성과의 mechanism은 이 track과 다르다.

- Viewer가 평균 7.49회 tool call을 하며 필요한 code만 추렸다.
- main agent non-cached input이 276.7K→181.3K, −34.5%가 됐다.
- smaller model subagents를 사용했다.
- full repository를 반복 탐색할 수 있었다.

우리 track에서는 judge가 10개 excerpt를 이미 골라 request에 넣고, worker가 tool로 clean context를 새로 만들 수 없다. `Architect → Editor`가 같은 60KB를 두 번 받는다면 SWE-Edit의 비용 mechanism과 반대가 된다.

따라서 coding split 채택 조건은 다음과 같다.

1. Editor에게 full request가 재주입되지 않거나 cache-read cost가 충분히 낮다.
2. Architect packet이 exact SEARCH line을 손실 없이 전달한다.
3. fused solver보다 resolve proxy 또는 LiveCodeBench accuracy가 오른다.
4. total normalized cost가 줄거나 증가분이 benchmark gain으로 정당화된다.

### Loc2Repair가 보여준 것

[Loc2Repair](https://arxiv.org/html/2606.30963)는 SWE-bench Verified에서 explicit file localization을 분리해 pooled resolved rate를 44.7% baseline에서 predicted localizer 48.9%/49.1%, gold localization 52.4%로 높였다. mean elapsed time도 줄었지만 token effect는 model별로 달랐다.

이 track에는 이미 judge-level repository localization이 있다. 남는 문제는 excerpt 안의 file/hunk localization이다. 별도 Architect가 필요한지, fused solver prompt 안의 “먼저 target hunk를 고정하라” instruction으로 충분한지는 실험해야 한다.

### Qwen model signal

[Qwen3-30B-A3B-Instruct-2507 model card](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507)는 LiveCodeBench v6 43.2, Aider-Polyglot 35.6을 보고한다. 이 차이는 strict edit task를 별도 측정할 이유는 되지만 formatting failure가 차이의 유일한 원인이라는 증거는 아니다.

필수 coding metric:

- valid patch extraction rate.
- SEARCH exact-match rate.
- file/path correctness.
- edit block count와 output token.
- LiveCodeBench pass rate.
- 가능하면 SWE-bench Docker resolve rate.

## Generic: MMLU-Pro

[MMLU-Pro](https://arxiv.org/html/2406.01574v3)는 14개 category, 최대 10개 option의 어려운 multiple-choice benchmark다. 전체의 83%가 10개 option이고 평균은 9.47개다. 현재 practice set도 42개 중 36개가 10개 option이다.

원 논문의 CoT 대 direct answer:

| model | CoT | Direct | 차이 |
|---|---:|---:|---:|
| GPT-4o | 72.6 | 53.5 | +19.1pp |
| GPT-4 Turbo | 63.7 | 48.4 | +15.3pp |
| Phi-3 Medium | 55.7 | 47.5 | +8.2pp |
| Llama-3-8B | 35.4 | 31.5 | +3.9pp |
| Gemma-7B | 33.7 | 27.0 | +6.7pp |

따라서 “letter만 출력하므로 reasoning은 필요 없다”는 결론은 틀리다. Judge가 rationale을 읽지 않는다는 것과 model이 reasoning을 할 필요가 없다는 것은 다르다.

권장 generic prompt 원리:

- question과 모든 option을 비교한다.
- 가장 강한 두 후보를 구분하는 constraint를 확인한다.
- reasoning은 concise/private하게 유지한다.
- 마지막 줄만 `ANSWER: <letter>`로 낸다.
- 3~10개로 달라지는 실제 `option_letters` 범위를 확인한다.

Visible reasoning을 길게 내면 token efficiency를 해친다. Reasoning mode 자체를 끄면 accuracy를 해칠 가능성이 있다. 두 효과를 model별로 A/B해야 한다.

## Math: MATH-500 Level 5와 AIME 2024

Practice set은 MATH-500 level 5 48개와 AIME 2024 11개다. Hidden math는 60~66개이며 각 2회 실행된다.

Math에서 중요한 구분:

- integer 35개는 exact integer와 symbolic verify가 걸린다.
- expression 24개는 LaTeX normalization을 포함한 symbolic equivalence가 핵심이다.
- 같은 prompt/model도 두 repeat에서 answer가 달라질 수 있으므로 stochastic variance가 score와 cost 양쪽에 나타난다.

[Self-Consistency](https://arxiv.org/abs/2203.11171)는 arithmetic reasoning에서 큰 gain을 보였지만 다수 sample 비용을 쓴다. [s1](https://arxiv.org/html/2501.19393)은 test-time compute 증가가 AIME에 도움 될 수 있지만 plateau와 반복도 있음을 보였다. [intrinsic self-correction 연구](https://arxiv.org/html/2310.01798)는 external feedback 없이 스스로 검토시키는 것이 오히려 나빠질 수 있음을 보였다.

따라서 math는:

1. 한 번의 충분한 derivation을 baseline으로 둔다.
2. arithmetic/sign/domain check를 같은 trajectory 안에서 끝낸다.
3. hard output cap을 둔다.
4. 2-sample/majority는 실제 disagreement calibration 후에만 사용한다.
5. final normalizer가 answer를 의미적으로 바꾸지 않게 한다.

## 공통: final answer contract

모든 track에서 grader는 last valid block을 쓴다. 이는 free scratchpad를 의미하지 않는다. Accuracy penalty가 없을 뿐, 앞의 token은 cost에 들어간다.

[Let Me Speak Freely?](https://arxiv.org/abs/2408.02442)는 JSON/XML 같은 structured format restriction이 여러 reasoning task에서 성능을 낮출 수 있고, 제약이 강할수록 저하가 커지는 경향을 보고했다. 이 대회의 exact final block은 피할 수 없으므로, 전체 reasoning trajectory를 구조화하기보다 문제를 푼 뒤 **마지막 boundary에서만** contract를 적용하는 설계가 합리적이다. 다만 논문은 AI:GO/Qwen과 동일한 output format을 시험하지 않았으므로 이것도 prompt A/B 대상이다.

추천 pattern:

```text
[short internal work or compact ledger]
[one final contract block]
```

금지 pattern:

```text
[multiple full drafts]
[review that emits another malformed answer]
[runtime summary after the real answer]
```

Answer는 마지막 wave에 있고, owner는 한 agent이며, local extractor로 exact contract를 확인해야 한다.
