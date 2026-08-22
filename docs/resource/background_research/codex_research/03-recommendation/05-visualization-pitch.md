# Visualization과 Pitch 설계

## 결론

30점 visualization은 예쁜 agent graph만 보여주는 문제가 아니다. Judge가 “왜 이 worker가 호출됐고, 무엇을 소비했으며, 어느 output이 정답으로 채택됐는지”를 한 화면에서 검증할 수 있어야 한다. 실제 trace를 source of truth로 쓰고 replay와 simulation을 명확히 구분한다.

## 권장 화면 구조

```text
┌ Run summary ─────────────────────────────────────────────────────┐
│ track · item · variant · model · result · cost · latency         │
├ Agent timeline ────────────────┬ Decision inspector ──────────────┤
│ Planner  [plan]                │ why routed to CodePatchSolver    │
│ Worker      [model call]       │ task packet / policy version     │
│ Grader                       []│ extracted final block / outcome  │
├ Token and cost waterfall ──────┴──────────────────────────────────┤
│ input · cache-read · reasoning · output · normalized cost         │
├ Failure / contract panel ─────────────────────────────────────────┤
│ parse checks · finish reason · owner · evidence                   │
└───────────────────────────────────────────────────────────────────┘
```

필수 interaction:

- run, track, agent, wave별 filter.
- graph node 선택 시 실제 child span과 task packet 표시.
- token waterfall에서 cached와 fresh input 분리.
- answer extraction source를 aggregated result 또는 wave/task로 표시.
- baseline과 candidate를 item-level paired view로 비교.
- 실패를 `model wrong` 하나가 아니라 taxonomy로 drill-down.

## Trace schema

OpenTelemetry GenAI는 현재 별도 repository의 Development 사양이다. [context·cache·observability](../02-evidence/04-context-cache-observability.md)에 정리한 표준 field를 우선 사용하고 contest 전용 값만 `jxc.*`에 둔다.

Span tree 예시:

```text
invoke_workflow (jxc.execution.id)
└─ invoke_agent: RouterPlanner
   ├─ plan
   │  └─ chat Qwen...
   └─ invoke_agent: CodePatchSolver
      └─ chat Qwen...
```

별도 grader event는 answer extraction과 correct/incorrect를 연결한다. `template_digest`, `prompt_digest`, `policy.variant`, schema version을 run metadata에 넣어 재현 가능성을 확보한다.

## Privacy 기본값

Default telemetry에는 full prompt, hidden problem, model reasoning, repository code를 저장하지 않는다.

| 계층 | 저장 내용 | 사용처 |
|---|---|---|
| 기본 | ID, hash, timing, token, model, outcome | production dashboard |
| 공개 demo | public practice prompt/output 원문 | expo와 pitch |
| 제한 저장 | hidden/private content | 명시적 access와 retention이 있을 때만 |

OTel의 input/output/system instruction content field도 Opt-In이다. 관객 browser에 hidden evaluation content가 내려가지 않도록 server-side redaction을 둔다.

## Replay와 simulation label

| 기능 | 의미 | 허용 표현 |
|---|---|---|
| Observed replay | 실제 event를 시간순 재생 | “이 run에서 실제 발생” |
| Prefix stop simulation | 실제 candidate sequence의 n번째에서 stop | “관측 prefix 기준 계산” |
| Policy simulation | output invariance 등 가정을 둔 계산 | “이 가정 아래 예상” |
| True ablation | 다른 configuration을 재실행 | “실측 비교” |

이미 reviewer까지 호출한 run에서 reviewer span을 화면상 숨긴 뒤 “reviewer 없이도 같은 답”이라고 주장하면 causal counterfactual을 위조한다. Reviewer가 없을 때 worker output 자체가 달라질 수 있으므로 true ablation은 재실행해야 한다.

## Demo story

한 coding item으로 90초 story를 만든다.

1. 10초: request가 coding으로 route되고 one-worker policy가 선택된다.
2. 20초: Planner task와 CodePatchSolver의 exact responsibility를 연다.
3. 20초: 60KB input, fresh/cache token, output token waterfall을 보여준다.
4. 20초: final SEARCH/REPLACE block이 어디서 추출됐는지와 deterministic contract checks를 보여준다.
5. 20초: fused/split true ablation의 accuracy·cost paired result를 비교한다.

Pitch headline:

> We do not add agents by default. We make every additional inference earn its place against measured accuracy and normalized cost.

## 30점 축과 화면 대응

| 평가 관점 | 화면 evidence |
|---|---|
| observability | complete span tree, token, latency, finish reason |
| interpretability | routing rule와 task responsibility |
| traceability | run/item/task/model/prompt digest 연결 |
| explainability | why-route와 failure ownership |
| clarity | summary→timeline→detail 3단 정보 계층 |
| insightfulness | item-level Pareto, handoff loss, cache share, failure distribution |

## 구현 우선순위

1. 실제 trace ingestion과 ID linkage.
2. run summary와 agent timeline.
3. token/cost waterfall.
4. answer extraction과 failure panel.
5. paired comparison.
6. animation과 polish.

Trace가 거짓이면 polish로 만회할 수 없다. 반대로 기본 timeline과 token table만 있어도 source와 ownership이 정확하면 설득력 있는 demo가 된다.
