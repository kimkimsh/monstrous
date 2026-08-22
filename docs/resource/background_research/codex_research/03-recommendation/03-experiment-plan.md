# 실험·예산 계획

## 결론

최종 squad는 문헌 선호가 아니라 최신 공개 121개에서 얻은 holdout 결과로 정한다. 한 번에 한 변수만 바꾸고, accuracy뿐 아니라 input/output/reasoning/cache token, wall-clock, parse failure를 같이 기록한다. 공개 gold를 prompt에 넣거나 holdout을 반복 튜닝하면 결과가 오염된다.

## 고정 split

최신 visible set을 seed와 ID가 고정된 stratified split으로 나눈다.

| track | 전체 | development | holdout | 층화 |
|---|---:|---:|---:|---|
| coding | 20 | 13 | 7 | SWE-bench 9/4, LiveCodeBench 4/3 |
| math | 59 | 39 | 20 | MATH-500 L5 32/16, AIME 7/4 |
| generic | 42 | 28 | 14 | 14과목별 2/1 |

Generic은 과목당 정확히 3개이므로 과목별 2개 development, 1개 holdout이 가능하다. Coding과 math는 ID를 정렬한 뒤 고정 seed로 층화하고 split manifest를 version control에 남긴다. 개발 중에는 development만 보고, architecture 결정을 마친 뒤 holdout을 한 번 사용한다.

20개 coding holdout 7개는 통계적으로 매우 작다. 결과 차이가 1문항이면 14.3 percentage point다. 그러므로 공개 coding 결과는 방향성 증거이며, 작은 차이를 확정적 우위로 표현하지 않는다.

## 단계별 ablation

### Phase 0: harness와 contract

| ID | 변경 | 확인값 |
|---|---|---|
| H0 | gold answer parser만 실행 | 121/121 parse 가능 |
| H1 | raw → composed request 재생성 | 공개 digest 121/121 일치 |
| H2 | model output extractor unit test | last-block, malformed, timeout cases |
| H3 | token/latency trace capture | field 누락률 0% |

로컬 `bash tools/verify.sh`는 H0/H1에 필요한 source 무결성과 digest를 이미 통과했다. Model run 및 AI:GO extraction replay는 별도로 검증해야 한다.

### Phase 1: architecture

| ID | Variant | 비교 목적 |
|---|---|---|
| A0 | Planner + one generic solver for all tracks | 가장 단순한 control |
| A1 | Planner + three track specialists | specialization의 순효과 |
| A2 | A1 + coding Architect→Editor | context reduction 대 handoff loss |
| A3 | A1 + unconditional reviewer | reviewer의 상한과 비용 측정 |
| A4 | A1 + conditional reviewer | trigger의 precision/cost 측정 |

A3가 좋더라도 바로 채택하지 않는다. Reviewer 없이 틀리고 reviewer로 맞은 문항, 맞았다가 reviewer로 틀린 문항, 그대로인 문항을 분리한다. Net correct delta와 추가 normalized cost를 함께 본다.

### Phase 2: prompt와 budget

| Track | 실험 |
|---|---|
| coding | fused/split, root-cause checklist 유무, output cap, SEARCH self-check wording |
| math | concise explicit derivation 대 very short direct, output cap, 1/2/3 sample |
| generic | private concise reasoning 대 direct answer, option cross-check, output cap |
| all | stable prefix order, `{{TASK}}` 위치, Planner task verbosity |

한 실험에서 agent topology, model, prompt, cap을 동시에 바꾸지 않는다. 변수가 섞이면 개선 원인을 알 수 없다.

## 수집 schema

각 item/variant/run마다 다음 값을 저장한다.

```text
run_id, variant_id, template_digest, prompt_digest
track, item_id, source_family, model
correct, parsed, failure_kind
input_tokens, output_tokens, reasoning_output_tokens
cache_read_input_tokens, cache_write_input_tokens
normalized_cost, latency_ms, finish_reason
agent_count_called, inference_call_count, wave_count
```

Failure taxonomy:

```text
format_parse
answer_mapping
localization
repair_semantics
reasoning
handoff
planner_route
token_cap
wall_clock_cap
infra
grader_environment
```

`wrong` 하나로 합치면 architecture가 고칠 수 있는 실패와 model 지식 실패를 분리할 수 없다. MAST의 14-mode taxonomy는 참고하되 현재 contest에서 관측 가능한 field로 축소한다.

## 핵심 metric

```text
benchmark = 0.50 × coding_accuracy
          + 0.25 × generic_accuracy
          + 0.25 × math_accuracy

cost_per_correct = total_normalized_cost / correct_items
parse_failure_rate = format_parse_count / items
handoff_loss = fused_correct_split_wrong - fused_wrong_split_correct
```

추가로 track별 Wilson interval과 paired bootstrap을 보고한다. Coding 7개 holdout에서 p-value를 과신하지 않고 item-level paired table을 반드시 함께 본다.

## 승급 기준

Baseline A1을 새 variant로 교체하려면 다음을 모두 만족한다.

1. development에서 결과가 재현된다.
2. holdout benchmark가 낮아지지 않는다.
3. parse failure가 증가하지 않는다.
4. token-efficiency 또는 benchmark 중 하나가 실질적으로 개선되고 다른 하나의 손실이 contest exchange rate 안이다.
5. infra/timeout worst case에서도 final answer budget이 남는다.
6. 변화 원인을 item-level diff로 설명할 수 있다.

가격식이 오기 전 임시 Pareto 판단:

- 다른 variant보다 accuracy도 낮고 token도 많은 variant는 제거한다.
- accuracy가 같으면 normalized token이 적은 variant를 선택한다.
- token이 같으면 benchmark가 높은 variant를 선택한다.
- 서로 trade-off면 organizer score 식 확보 전 둘 다 보존한다.

## Run budget

Test run도 1/5 cost이고 모든 실행이 누적된다. 따라서 순서를 고정한다.

1. 무료 Check와 local parser/test.
2. development subset smoke run.
3. development 전체 A/B.
4. 살아남은 2개 이하 variant만 holdout.
5. schema와 runtime을 freeze.
6. submission 전 1회 end-to-end rehearsal.
7. 최종 submission.

모든 model×track×variant grid를 무차별 실행하지 않는다. [기존 실험 운영안](../../../example_task/02-실험-운영.md)의 31~33행, 41~72행, 76~112행도 track별 분리와 token lever 기록을 요구한다.

## 아직 실행하지 못한 경계

이번 조사에서는 로컬 corpus 무결성과 live practice listing을 확인했지만 AI:GO에서 model inference를 대량 실행하지 않았다. 따라서 prompt별 accuracy, 실제 cached token, model price, end-to-end planner completion은 미측정이다. 이 문서의 architecture는 강한 baseline과 검증 계획이지, 미실행 성능 보장이 아니다.
