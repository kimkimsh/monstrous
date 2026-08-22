# Risk Register와 Open Questions

## 즉시 organizer 확인이 필요한 항목

| ID | 질문 | 영향 | 답변 전 fallback | 심각도 | Owner |
|---|---|---|---|---|---|
| Q1 | 세 model의 exact identifier는 무엇인가? | track별 model 선택과 재현성 | 확인된 Qwen 하나만 명시, 나머지 가정 금지 | Critical | Product/Ops |
| Q2 | input/output/reasoning/cache token의 USD/Mtok 식은 무엇인가? | 30점 token score, stop threshold | raw token type별 기록, absolute 점수 예측 금지 | Critical | Eval |
| Q3 | per-run/per-item token cap과 wall-clock cap은? | final answer 유실, concurrency | conservative output cap과 single path | Critical | Agent |
| Q4 | one-shot prompt는 Planner와 worker 중 어디에 주입되는가? | 60KB duplication과 cache | `{{TASK}}` 1회, Planner task 최소화 | High | Agent |
| Q5 | cached input의 exact 할인율·최소 prefix·TTL은 무엇이며 worker별로 실제 hit하는가? | multi-agent input cost | variant별 actual hit 전에는 saving을 budget에 0으로 반영 | High | Eval |
| Q6 | evaluation 중 deterministic output validator/retry hook이 허용되는가? | malformed output 회복 | local preflight만 사용, squad path에는 넣지 않음 | Critical | Product/Ops |
| Q7 | official trace source와 export schema는? | visualization truthfulness | own event envelope + source label | High | Trace |
| Q8 | Squad Template JSON schema/version과 AI:GO 1.12.1 호환은? | import/run 실패 | UI export 후 exact schema validation | Critical | Agent |
| Q9 | parallel task 실행이 billing/wall-clock에 어떻게 반영되는가? | fan-out trade-off | sequential single worker | Medium | Eval |
| Q10 | hidden prompt가 visible 합성 규칙과 같은가? | parser/output robustness | manifest contract를 authoritative로 사용 | High | Product/Ops |

## 구현·운영 risk

| ID | Risk | 조기 signal | 예방/대응 | 남는 경계 |
|---|---|---|---|---|
| R1 | Planner가 여러 task를 만들어 token fan-out | item당 inference call > 2 | exactly-one-task instruction, trace gate | AI:GO planner가 instruction을 어길 수 있음 |
| R2 | Coding full context가 worker마다 복제 | worker별 input token가 유사한 16~20k | fused baseline, split은 excerpt-only | runtime injection order 미확인 |
| R3 | Split handoff에서 exact SEARCH line 손실 | exact containment check 실패 | original lines를 verbatim packet에 포함 | evaluation hook 없으면 사후 감지만 가능 |
| R4 | Final answer가 status summary에 묻힘 | extractor가 answer 없음 | solver를 last relevant task로 배치 | runtime aggregation 동작 미확인 |
| R5 | Generic direct answer가 정확도 저하 | reasoning variant paired loss | concise private reasoning baseline | hidden distribution shift |
| R6 | Math second sample 비용 폭증 | disagreement 빈도 높음 | calibration 전 off | verbal confidence는 대체 trigger 아님 |
| R7 | Reviewer가 맞은 답을 뒤집음 | correct→wrong transition | unconditional reviewer off | sparse holdout의 불확실성 |
| R8 | Cache 절감 과대계상 | cache-read field 0 또는 누락 | fresh/cache/billed 분리 | provider billing field 미제공 가능 |
| R9 | Public set overfit | development 상승, holdout/hidden 하락 | fixed holdout, generic subject stratification | coding holdout 7개로 작음 |
| R10 | Test run 과소비 | run ledger와 portal cost 차이 | run 승인 gate, reserve | portal의 지연 집계 가능성 |
| R11 | Trace에 hidden content 노출 | payload/content가 browser 응답에 포함 | default hash-only, server-side redaction | organizer data-retention rule 미확인 |
| R12 | OTel schema drift | collector/UI field missing | schema version pin, adapter | 사양이 Development 상태 |
| R13 | Release server는 뜨지만 squad가 끝나지 않음 | planner pending/sidecar error | early E2E smoke, desktop fallback | headless batch completion 미검증 |
| R14 | Live portal/practice set 변경 | SHA/count 변동 | submission 전 manifest와 SHA 재확인 | event 운영 중 변경 가능 |

## 주장 risk

발표에서 다음 문장을 쓰지 않는다.

- “Multi-agent는 항상 single-agent보다 정확하다.”
- “Coding은 generic보다 문항당 10배 이상 중요하다.”
- “Qwen benchmark gap은 formatting 때문에 생겼다.”
- “Prefix cache로 input cost를 N분의 1로 줄였다.”
- “Reviewer를 제거해도 결과가 같다는 것을 replay로 증명했다.”
- “Preflight가 평가 중 자동으로 재시도한다.”

대신 다음처럼 measured boundary를 붙인다.

- “공개 holdout에서 A1이 A0보다 X point 높고 normalized token은 Y% 변했다.”
- “이 run의 observed cache-read share는 X%다.”
- “이 화면은 observed-prefix simulation이며 true ablation은 별도 run이다.”
- “현재 121-item public manifest와 live listing이 일치했다.”

## Go/No-Go gate

| Gate | Go | No-Go 시 처리 |
|---|---|---|
| Import | exported template가 target version에서 열림 | schema 최소화, known-good baseline 복귀 |
| Completion | 세 track E2E answer extraction 성공 | architecture 실험 중단, runtime fix |
| Correctness | fixed holdout이 baseline 이상 | baseline 유지 |
| Cost | portal/token trace reconcile | absolute cost claim 제거, raw usage만 표시 |
| Privacy | hidden content가 client payload에 없음 | content view disable |
| Demo | network 없이 recorded public replay 가능 | live-only dependency 제거 |
| Submission | artifact digest와 portal status 확인 | 재업로드 전에 diff와 cost 확인 |

## 현재 가장 큰 세 가지 불확실성

1. **가격·cap**: absolute optimal budget을 아직 계산할 수 없다.
2. **runtime composition**: Planner와 worker가 원문을 각각 받는지 확정되지 않았다.
3. **평가 hook**: deterministic preflight/retry를 production critical path에 둘 권한이 확인되지 않았다.

이 세 항목의 답이 올 때까지 architecture는 single-worker baseline을 유지한다. 이 선택은 unknown에 강하고, 이후 split/cascade를 추가하기도 쉽다.
