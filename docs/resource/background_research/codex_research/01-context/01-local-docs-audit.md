# 로컬 `docs/` 전수 감사

## 감사 범위

2026-08-22 최종 검증 시점에 `codex_research/` 자체를 제외한 `docs/`에는 351개 파일, 23,095,045바이트가 있다. 조사 도중 `claude_research/`가 갱신된 것을 감지해 최신 상태로 다시 읽고 이 수치를 갱신했다.

| 형식 | 수량 | 처리 |
|---|---:|---|
| Markdown | 61 | 전체 본문 판독 |
| TXT | 251 | 전체 UTF-8 decode 및 규칙·문항·prompt 판독 |
| JSON | 15 | schema, count, range, identifier 대조 |
| JSONL | 11 | 전 행 parse, ID와 track 분포 대조 |
| Python | 4 | compose/extract/grade/run flow 판독 |
| Shell | 1 | verification flow 판독 및 실행 |
| PDF | 1 | 29페이지 전체 text extraction 및 핵심 페이지 확인 |
| ZIP | 1 | 11개 entry 무결성 검사 및 구형 set 구조 확인 |
| 확장자 없음 | 6 | UTF-8 text로 판독 |
| `.DS_Store` | 3 | metadata binary로 분류 |

346개 파일은 UTF-8 text로 읽혔다. 나머지 5개는 `.DS_Store` 세 개, 29페이지 PDF, ZIP이다. PDF는 `uv run --with pypdf`로 29페이지를 추출했고, ZIP은 `unzip -t`를 통과했다.

## 무결성 확인

다음 명령을 실행했다.

```bash
cd /Users/mark-mac/workspace/monstrous/docs/resource/example_task
bash tools/verify.sh
```

결과:

- raw file checksum 전부 통과.
- coding 20, math 59, generic 42, 총 121개 composed request가 공개 digest와 일치.
- index/request/task/gold ID set가 각 track에서 동일하고 duplicate가 없음.
- live `/practice-sets/SHA256SUMS`의 논리 항목도 로컬 `raw/SHA256SUMS`와 동일. server와 local의 공백 개수 차이만 있고 hash pair는 같다.

로컬 근거는 [example_task README](../../../example_task/README.md)의 5~23행과 [요청 합성 규칙](../../../example_task/01-요청-합성-규칙.md)의 3~39행에 정리돼 있다.

## 현재 practice set 실측

| track | 문항 | 구성 | request bytes min / median / max | 총 bytes |
|---|---:|---|---:|---:|
| coding | 20 | SWE-bench 13 + LiveCodeBench 7 | 1,999 / 63,812 / 70,310 | 872,683 |
| math | 59 | MATH-500 L5 48 + AIME 2024 11 | 334 / 491 / 1,570 | 32,253 |
| generic | 42 | MMLU-Pro 14과목 × 3 | 474 / 918 / 2,926 | 45,220 |

추가 분포:

- math answer format: integer 35, expression 24.
- generic option count: 3개 1문항, 4개 1문항, 7개 1문항, 8개 1문항, 9개 2문항, 10개 36문항.
- coding은 context가 거의 상한을 채운다. 구형 자료의 60,000자 근거는 [benchmark 분석](../../../track_resource/lableup/04-벤치마크-데이터셋-분석.md)의 283~300행에 있다.

## 최신 자료와 구형 자료를 구분해야 한다

저장소에는 서로 다른 시점의 practice set 두 벌이 있다.

| 자료 | 문항 수 | 용도 |
|---|---:|---|
| `track_resource/lableup/practice-sets/visible-sets.zip` | 364 | 초기 공개 세트, 역사적 분석 |
| `example_task/` 및 live server | 121 | 현재 제출 서버가 공개하는 최신 세트 |

구형 세트는 coding 60, math 164, generic 140이다. 최신 세트는 coding 20, math 59, generic 42다. hidden item range와 score weight는 유지되지만, prompt tuning과 confidence interval은 반드시 최신 121개를 기준으로 해야 한다. [track resource README](../../../track_resource/lableup/README.md)의 36행은 364개를, [example_task README](../../../example_task/README.md)의 14~23행은 121개를 가리킨다.

## 병행 조사 자료 대조

`docs/resource/background_research/claude_research/`의 Markdown 12개, 2,687행, 194,354바이트도 최종 상태로 전부 읽었다. 이 자료와 본 조사는 다음에서 일치한다.

- generic은 direct-only가 아니라 concise reasoning을 실험해야 한다.
- 상시 debate와 LLM reviewer는 비용 대비 근거가 약하다.
- coding split은 exact original hunk를 보존해야 한다.
- runtime cap, 마지막 answer contract, trace privacy가 architecture 일부다.

차이는 evidence의 contest 전이 강도다.

- SWE-Edit의 tool-based Viewer/Editor 결과는 coding split의 **실험 우선순위**를 높이지만, tool이 없는 AI:GO에서의 승리를 입증하지 않는다.
- Qwen의 LiveCodeBench 43.2와 Aider-Polyglot 35.6은 strict editing risk 신호지만 formatting이 차이의 원인이라고 증명하지 않는다.
- Portal은 cached input이 존재하고 fresh input보다 싸다고 명시한다. 그러나 exact discount, minimum prefix, TTL, worker별 request order와 actual hit는 미확인이다. 상용 API의 약 10% 가격을 contest에 이식하지 않는다.
- Qwen RULER의 16k~32k 성능은 context capacity 신호이지, 60KB code-repair input이 “안전하다”는 증거가 아니다.
- Chain of Draft는 유망하지만 small model에서 CoT보다 낮아진 결과도 있다. “유일한 무손실 절감”으로 고정하지 않고 직접 A/B한다.
- 응답 본문 ledger는 별도 LLM logging call이 없을 뿐 output token 비용은 든다. 이전 answer block이 accuracy에서 무시돼도 token score에서는 무료가 아니다.

## 문서 간 상충과 판정

### 1. coding 출력 형식

- 일부 초기 ideation은 unified diff를 가정했다.
- 현재 121개 request는 모두 SEARCH/REPLACE contract다.
- 최종 판정: `*** PATCH START ***`와 `*** PATCH END ***` 사이의 SEARCH/REPLACE block만 사용한다. [요청 합성 규칙](../../../example_task/01-요청-합성-규칙.md)의 83~109행이 byte-level contract다.

### 2. Management API 자동화

- [03-API-자동화](../../../example_task/03-API-자동화.md)의 8~38행은 desktop setting toggle만 켜면 된다고 추정한다.
- 더 늦게 수행한 [04-CLI-운영](../../../example_task/04-CLI-운영.md)의 24~32행과 171~220행은 desktop app이 Management API를 띄우지 않으며 app bundle의 `aigo-server`도 headless sidecar spawn에 실패한다고 대조 실험했다.
- release ZIP의 `aigo-server`는 sidecar spawn에 성공했다. 그러나 [04-CLI-운영](../../../example_task/04-CLI-운영.md)의 367~383행처럼 planner call까지 포함한 squad 완주는 아직 확인되지 않았다.
- 최종 판정: automation은 **가능성 및 일부 control-plane 검증 완료**, end-to-end batch completion은 미검증이다.

### 3. generic reasoning

- 일부 로컬 전략은 generic을 `--no-think`, 1턴 minimal output으로 둔다.
- MMLU-Pro 원 논문은 해당 benchmark에서 CoT가 direct answer보다 GPT-4o +19.1pp, GPT-4 Turbo +15.3pp, Phi-3 Medium +8.2pp, Llama-3-8B +3.9pp, Gemma-7B +6.7pp였다고 보고한다.
- 최종 판정: visible rationale는 줄이되 reasoning 자체를 금지하지 않는다. `private concise reasoning → final letter`를 먼저 시험한다.

### 4. coding 문항 가치

[트랙 정리](../../../example_task/00-트랙-정리.md)의 52~60행은 coding 한 문항이 generic보다 “10배 넘게” 무겁다고 쓴다. 공개 range로 계산하면:

```text
minimum ratio = (0.5 / 240) / (0.25 / 448) = 3.733...
midpoint ratio = (0.5 / 190) / (0.25 / 573) = 6.032...
maximum ratio = (0.5 / 140) / (0.25 / 698) = 9.971...
```

coding 우선순위는 맞다. 다만 문항당 기여가 10배를 넘는다고 단정해서는 안 된다. 이 계산은 valid graded item 수가 target range와 같다는 근사이며, organizer 제외 항목이나 repeat aggregation 방식에 따라 달라질 수 있다.

### 5. Qwen formatting 원인

[최종 ideation](../../../../ideation/final_ideation/주제.md)의 18행은 LiveCodeBench 43.2와 Aider-Polyglot 35.6 차이를 formatting 원인으로 단정한다. 동일 model card에 있는 숫자는 맞지만 benchmark task, dataset, metric이 다르다. 인과 결론은 불가능하다. 안전한 결론은 “strict editing contract를 별도 측정해야 한다”이다.

### 6. evaluation-time Preflight

[최종 ideation](../../../../ideation/final_ideation/주제.md)의 50~55행은 programmatic Preflight를 핵심 구조로 둔다. 그러나 평가 중 squad에는 tools가 없고, runner-level post-processing/retry가 허용되는지는 확인되지 않았다. [최종 ideation](../../../../ideation/final_ideation/주제.md)의 112~118행도 이 한계를 인정한다.

최종 판정:

- local harness: format/extraction/SEARCH exactness Preflight 필수.
- evaluation squad: organizer가 runner hook을 확인해 줄 때만 deterministic program으로 사용.
- 미허용 시: solver prompt 내 checklist와 마지막-wave answer contract로 downgrade.

## 현재 구현 준비도의 실제 경계

다음은 확인됐다.

- 121개 request 합성과 digest.
- local answer extraction rule.
- math/generic local grader.
- LiveCodeBench 7개 execution grading.
- CLI 1.12.1 명령 surface와 Management API 일부 왕복.
- release `aigo-server`의 sidecar spawn.

다음은 확인되지 않았다.

- AI:GO 1.12.1에서 planner부터 final answer까지 한 squad execution 완주.
- evaluation 모델 세 종의 정확한 이름과 가격.
- cache의 exact 과금 배율, worker별 hit, request ordering.
- one-shot prompt injection 위치.
- runner-level Preflight 허용.
- SWE-bench 13개 full Docker resolution score.

따라서 이 리서치는 architecture recommendation을 제공하지만, 최종 template 확정은 [실험 계획](../03-recommendation/03-experiment-plan.md)의 gate를 통과해야 한다.
