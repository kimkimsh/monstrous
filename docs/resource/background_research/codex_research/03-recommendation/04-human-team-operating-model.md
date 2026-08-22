# 4인 Hackathon Team 운영안

## 결론

최대 4인 team이면 산출물 경계에 맞춰 ownership을 네 개로 고정하는 편이 효율적이다. 사람도 모두 prompt를 동시에 만지는 squad가 되면 integration 시점에 기준선이 사라진다.

| 역할 | 단독 owner | 주요 산출물 | 교차 review |
|---|---|---|---|
| Agent/Runtime | AI:GO template, routing, final extraction | squad JSON, runtime runbook | Eval 담당 |
| Eval/Data | 121-item harness, split, grader, metrics | result table, regression gate | Agent 담당 |
| Trace/Frontend | trace schema, ingestion, UI | interactive visualization | Product 담당 |
| Product/Ops | problem framing, score model, demo, organizer 질문 | pitch, risk log, submission checklist | 전원 |

`Product/Ops`는 다른 세 명의 manager가 아니다. score 가정과 submission 상태를 한 곳에서 관리하는 hands-on owner다.

## 48시간 critical path

```text
T+0 ───────── T+6 ───────── T+18 ───────── T+30 ───────── T+40 ─── T+48
contract lock   baseline       ablations      integration    freeze     demo
```

### T+0~6: 계약 고정

- Agent: minimal 4-agent template와 한 item completion.
- Eval: `tools/verify.sh`, parser, fixed split manifest.
- Trace: run/event/token 최소 schema와 mock trace.
- Product: organizer 질문 8개 제출, score/risk board 생성.

Exit criterion: 세 track 각각 한 문항이 exact output contract로 끝나고 trace ID와 result ID가 연결된다.

### T+6~18: 기준선 측정

- A0/A1 development smoke 및 전체 run.
- actual token breakdown과 wall-clock 수집.
- visualization은 mock을 실제 trace source로 교체.
- demo story는 feature 수가 아니라 한 문항의 route→work→answer→grade로 고정.

Exit criterion: baseline result table, repeat 가능한 command/runbook, 실패 taxonomy.

### T+18~30: 고가치 ablation

- coding fused 대 split을 최우선 비교.
- generic concise reasoning 대 direct.
- math cap과 conditional second sample.
- reviewer는 unconditional 상한을 짧게 측정한 뒤 conditional trigger가 없으면 제거.

Exit criterion: Pareto frontier에 남은 2개 이하 candidate.

### T+30~40: 통합과 holdout

- candidate configuration freeze.
- fixed holdout 1회 평가.
- UI는 실제 latency/token/failure를 표시.
- timeout, malformed output, missing usage field를 fault injection.

Exit criterion: 한 configuration, 한 schema version, 한 submission artifact.

### T+40~48: freeze와 제출

- 새 architecture 실험 중단.
- end-to-end rehearsal와 artifact digest 기록.
- 3분/5분 pitch 길이에 맞춘 demo path 연습.
- final upload 후 portal에서 artifact identifier와 status 확인.

## 의사결정 규칙

- 한 file 또는 artifact에는 한 owner가 있다.
- 실험 제안은 `hypothesis / changed variable / expected metric / run cost / stop rule` 다섯 줄로 제출한다.
- 두 번 재현되지 않은 improvement는 final configuration에 넣지 않는다.
- T+30 이후에는 correctness blocker, submission blocker, demo blocker만 merge한다.
- owner가 없는 cross-cutting 문제는 Product/Ops가 직접 맡거나 즉시 owner를 지정한다.

## 매 3시간 checkpoint

```text
1. 현재 최고 benchmark와 normalized token은 무엇인가?
2. 마지막 checkpoint 이후 어떤 단일 변수가 바뀌었는가?
3. 새 failure가 어느 owner의 boundary에 속하는가?
4. 다음 run이 결정을 바꿀 수 있는가?
5. submission까지 남겨야 할 token/time reserve는 얼마인가?
```

결정을 바꿀 수 없는 run은 하지 않는다.

## 인원 부족 시

### 3명

- Agent + Eval을 분리 유지.
- Trace + Product를 합친다.
- UI polish보다 trace truthfulness와 demo stability를 우선한다.

### 2명

- 1명: Agent/Runtime + Eval.
- 1명: Trace/Frontend + Product/Ops.
- coding split, reviewer, policy simulator를 버리고 A1 baseline을 완성한다.

### 1명

- exact answer contract와 reproducible run이 먼저다.
- single-route squad, basic timeline/token table, 짧은 pitch로 scope를 제한한다.

## Hand-off artifact

구두 설명 대신 다음 artifact를 유지한다.

```text
configuration registry: variant ID → template/prompt/model/cap digest
experiment ledger: hypothesis → run IDs → result → decision
risk register: unknown → owner → deadline → fallback
release checklist: artifact digest → portal status → rehearsal result
```

이 구조는 agent architecture의 policy/mechanism/data 분리를 사람 team 운영에도 적용한다. 역할 간 공동 ownership보다 명확한 interface가 integration risk를 줄인다.
