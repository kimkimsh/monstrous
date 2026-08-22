# Routing, Budget, Verification 근거

## 결론

효율은 긴 prompt로 절약을 부탁하는 데서 나오지 않는다. 이 track에서는 다음 순서가 가장 안전하다.

1. deterministic track route.
2. track별 한 solver.
3. runtime hard cap.
4. local deterministic extraction/format check.
5. 추가 call은 calibrated trigger가 실험으로 검증됐을 때만.

## Routing은 agent를 늘리는 기술이 아니다

[RouteLLM](https://arxiv.org/html/2406.18665)은 strong/weak model 중 하나만 호출하는 router를 학습했다. 원 논문의 보수적인 headline은 “품질을 거의 유지하며 2배 이상 cost 절감”이다. 특정 setup의 router는 random보다 strong-model call을 크게 줄였지만, out-of-domain에서는 augmentation 없이 random보다 나쁜 경우도 있었다.

[FrugalGPT](https://arxiv.org/html/2305.05176)은 학습된 LLM cascade가 best individual model 성능을 유지하며 dataset별 50~98% cost reduction을 보였고, HEADLINES에서는 98.3%였다. 그러나 여러 provider, 가격차, 학습용 labeled data가 전제다.

대회 적용:

- `payload.kind`는 이미 coding/math/generic으로 명시되므로 LLM classifier가 필요 없다.
- model 세 종의 price/capability가 공개되면 track별 model 선택 또는 conditional escalation을 실험할 수 있다.
- 가격과 calibration data가 없을 때 “cheap first, expensive later” cascade는 오답을 자신 있게 내는 easy-looking item에서 실패할 수 있다.
- Router가 하는 일은 complexity 예측이 아니라 **track dispatch와 single-task plan**으로 축소한다.

## Reasoning token을 줄이는 법

### Chain of Draft

[Chain of Draft](https://arxiv.org/html/2502.18600)은 concise intermediate reasoning으로 일부 task에서 CoT accuracy를 유지하거나 넘으면서 최소 7.6% token만 사용했다고 보고한다. 하지만 small model 실험에서는 CoD가 CoT보다 정확도가 낮은 경우도 명시한다. 예를 들어 Qwen2.5-3B GSM8K는 CoT 59.1%, CoD 43.1%였다.

전이 가능한 원칙:

- “reasoning 금지”보다 concise scratchpad를 유도한다.
- final answer contract와 intermediate draft를 분리한다.
- Qwen3-30B-A3B-Instruct-2507과 organizer reasoning model에서 직접 A/B한다.

### s1 budget forcing

[s1](https://arxiv.org/html/2501.19393)은 custom model/runtime에서 end-of-thinking delimiter를 억제하거나 `Wait`를 삽입해 test-time compute를 조절했다. AIME 2024에서 s1 without budget forcing 50.0%, `Wait` 4회 56.7%였다. 계속 늘리면 반복 loop와 plateau도 생겼다.

중요한 경계:

- 이 결과는 prompt에 “N token 안에 끝내라”라고 쓰는 기법이 아니다.
- decoder/runtime가 stop token을 직접 제어했다.
- AI:GO가 agent template에서 같은 mechanism을 노출한다고 가정할 수 없다.

따라서 실제 통제는 `max_tokens`, thinking budget, max agent turns, wall-clock cap처럼 runtime이 집행하는 값이어야 한다.

## Self-consistency와 debate

[Self-Consistency](https://arxiv.org/abs/2203.11171)는 다양한 reasoning path를 sample하고 최빈 answer를 선택해 GSM8K +17.9, SVAMP +11.0, AQuA +12.2, StrategyQA +6.4, ARC-Challenge +3.9 point를 보고했다. 이득은 여러 completion을 소비한다.

[Large Language Models Cannot Self-Correct Reasoning Yet](https://arxiv.org/html/2310.01798)은 external feedback 없는 intrinsic self-correction이 reasoning accuracy를 흔히 낮추며, 같은 response 수에서 multi-agent debate가 self-consistency보다 낫지 않았다고 보고한다.

대회 적용:

- math/generic은 deterministic answer space라 majority extraction이 쉽다.
- 그러나 generic hidden 문항은 448~698개여서 3-sample은 전체 비용을 크게 늘린다.
- math는 60~66개가 2회 반복되므로 추가 sampling 비용도 사실상 반복된다.
- self-consistency는 어려운 subset에만 적용해야 한다. 그런데 reliable difficulty/confidence trigger가 아직 없다.
- model verbal confidence는 calibration 근거가 없으므로 trigger로 바로 쓰지 않는다.

권장 순서:

1. one-sample strong baseline.
2. track/model별 2-sample agreement 실험.
3. disagreement가 실제 error risk와 상관 있는지 reliability diagram으로 확인.
4. precision/recall과 token cost가 확인될 때만 third sample 또는 reviewer.

## Verification은 feedback source에 따라 가치가 달라진다

강한 verification:

- compiler/test execution.
- exact schema/parser.
- symbolic equivalence.
- option letter membership.
- SEARCH string exact containment.

약한 verification:

- 같은 model에게 “다시 검토하라”.
- 근거 없이 confidence를 다시 물음.
- critic이 더 길게 설명함.

Self-correction 논문은 execution/test 같은 external feedback이 있을 때 code correction이 도움 된다고 구분한다. 이 대회 평가 중에는 tool이 없으므로 semantic code verification은 불가능하다. 가능한 것은 format contract와 주어진 context에 대한 exact anchor check다. 그것도 runner hook이 허용될 때만 evaluation loop에 넣을 수 있다.

## Deterministic gate와 LLM reviewer의 책임 분리

Local harness gate:

| track | 0-token check |
|---|---|
| coding | markers, path line, marker balance, SEARCH non-empty/new-file rule, SEARCH exact occurrence, whole-line boundary |
| math | last boxed block extraction, integer/expression contract, parser acceptance |
| generic | last letter extraction, letter가 해당 item의 option set에 포함 |
| all | final answer가 마지막 wave에 존재, capped/infra failure 분리 |

LLM reviewer가 할 수 있는 것:

- patch가 issue intent를 해결하는지 반례 찾기.
- math reasoning의 alternative derivation.
- generic distractor 간 의미 차이 검토.

LLM reviewer가 보장할 수 없는 것:

- code가 test를 통과함.
- symbolic answer가 gold와 동치임.
- 자신의 critique가 최초 answer보다 정확함.

## Stop rule

최종 stop policy는 감상이 아니라 measured threshold여야 한다.

```text
stop if final contract is valid
and no experimentally validated escalation trigger fired.

escalate only if:
  expected_score_gain(trigger, track, model)
  > normalized_cost(next_call) × configured_exchange_rate
and hard remaining budget can pay for finalization.
```

현재 exchange rate와 model price가 미확인이므로 production formula의 숫자는 채울 수 없다. 먼저 per-variant accuracy, cost, latency를 수집한 뒤 Pareto frontier로 결정한다.

## track별 기본 권고

| track | 기본 sample | reasoning | reviewer |
|---|---:|---|---|
| coding | 1 | 충분히 허용, patch는 최소화 | default off, split A/B |
| math | 1 | concise explicit derivation | disagreement calibration 후 conditional |
| generic | 1 | private concise CoT | default off |

추가 sample은 scoring weight만 보고 배분하지 않는다. 예상 item 수, repeat, input 크기, model price, 실제 marginal accuracy gain을 함께 계산한다.
