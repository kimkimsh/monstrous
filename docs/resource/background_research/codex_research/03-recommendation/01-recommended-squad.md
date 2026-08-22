# 권장 AI:GO Squad

## 결론

첫 제출 baseline은 **4-agent template, 문항당 2-call path**로 고정한다. Template에는 정확히 한 명의 `RouterPlanner`와 `CodePatchSolver`, `MathSolver`, `GenericSolver`를 둔다. Planner는 `payload.kind`만 보고 해당 solver 하나를 호출하며, 한 문항 안에서 debate, fan-out, self-review를 기본 실행하지 않는다.

```text
request
   │
   ▼
RouterPlanner ── coding ──▶ CodePatchSolver ──▶ final answer
              ├─ math ────▶ MathSolver ──────▶ final answer
              └─ generic ─▶ GenericSolver ───▶ final answer
```

이 구조는 agent 수를 줄이기 위한 미학이 아니다. 현재 workload에는 이미 정확한 track label이 있고, coding request는 중앙값 63,812 bytes이며, 모든 grader가 deterministic이다. 따라서 classifier, repo-search agent, 상시 reviewer가 새 정보를 만들지 못하면서 input/output token과 failure edge만 늘릴 가능성이 크다.

## 역할과 책임

| Agent | 입력 | 해야 할 일 | 하면 안 되는 일 | 출력 |
|---|---|---|---|---|
| `RouterPlanner` | 전체 request와 `payload.kind` | track을 읽고 단일 solver task 생성 | 문제 풀이, 장문 요약, 여러 worker fan-out | 한 task packet |
| `CodePatchSolver` | coding request 전체 | issue 해석, excerpt localization, 최소 patch 작성, format 자체 점검 | repository browse 가정, unified diff, 설명문 추가 | SEARCH/REPLACE answer |
| `MathSolver` | math request 전체 | 풀이, 조건 검산, 답 canonicalization | 근거 없는 재시도, 다중 답 후보 노출 | boxed answer |
| `GenericSolver` | generic request 전체 | 선택지 비교, distractor 제거, letter 확인 | reasoning 금지, option text를 final로 출력 | letter answer |

AI:GO는 정확히 한 Planner를 요구한다. 로컬 가이드는 [AI:GO Squad 완전가이드](../../../track_resource/lableup/03-AIGO-Squad-완전가이드.md)의 124~133행에서 이 계약을 설명한다. 평가 중 tool 사용 불가 조건은 같은 문서의 532~541행과 [track ground truth](../01-context/02-hackathon-track-ground-truth.md)에 정리돼 있다.

## Planner를 최대한 얇게 두는 이유

Planner의 output은 plan이 아니라 **routing envelope**여야 한다.

```json
{
  "task_id": "solve",
  "assignee": "CodePatchSolver | MathSolver | GenericSolver",
  "track": "coding | math | generic",
  "objective": "Produce the exact final-answer contract for this request.",
  "constraints": [
    "Use only the supplied request.",
    "Return one final answer block as the last relevant output."
  ]
}
```

실제 AI:GO schema가 이 JSON과 같다는 뜻은 아니다. 전달해야 할 정보의 논리 schema다. 원문 request가 runtime에서 worker에게 이미 보이면 Planner가 60KB를 다시 요약하지 않는다. 보이지 않으면 원문 전체를 task packet에 그대로 넣되, coding에서 SEARCH anchor가 필요한 부분을 lossy summary로 바꾸지 않는다.

## 문항당 실행 정책

```text
1. Planner reads payload.kind.
2. Planner creates exactly one task assigned to the matching solver.
3. Solver reasons once and emits the exact answer contract.
4. Runtime returns the solver output as the last relevant task output.
5. No extra wave unless an experimentally validated trigger fires.
```

필수 invariant:

- `{{TASK}}`는 one-shot prompt에 정확히 한 번, 가능한 한 끝에 둔다.
- 마지막 wave의 마지막 relevant task가 valid answer block으로 끝난다.
- Planner 또는 runtime status summary가 solver의 정답 뒤를 덮지 않는다.
- 모델의 설명은 final delimiter 뒤에 오지 않는다.
- timeout 전에 finalization할 token budget을 별도 확보한다.

## Coding split은 baseline이 아니라 실험 후보

`Architect → Editor` 분리는 다음 조건에서만 승급한다.

1. Architect가 file path, exact original lines, intended change, 관련 invariant를 손실 없이 전달한다.
2. Editor가 60KB 원문을 다시 받지 않아 input 비용이 실제로 감소한다.
3. holdout의 patch parse rate와 grader accuracy가 fused solver보다 낮아지지 않는다.
4. 두 번째 call 비용을 포함해 Pareto frontier가 개선된다.

권장 packet:

```text
target_file
exact_search_block
replacement_intent
must_preserve
output_contract
```

별도 reviewer를 붙이더라도 “looks good” 같은 의견은 trigger가 아니다. SEARCH block이 원문에 없거나, patch가 issue의 핵심 invariant와 충돌한다는 구체적 반례를 찾아야 한다. 평가 중 compiler/test feedback이 없으므로 reviewer가 test pass를 보증한다고 표시해서는 안 된다.

## Stop rule

현재는 model 가격, cache 과금, per-run cap이 미확인이다. 따라서 숫자 threshold를 임의로 박지 않고 측정된 값으로 결정한다.

```text
stop if:
  final contract is valid
  and no validated escalation trigger fired

escalate if:
  measured expected score gain on holdout
  > measured normalized cost of the next call × exchange rate
  and enough hard budget remains to finalize
```

`exchange rate`는 benchmark point와 token-efficiency point 간 실제 contest trade-off다. organizer 식이 확보되기 전에는 accuracy만 높거나 token만 적은 variant를 최종안이라고 부르지 않는다.

## 채택 순서

| 단계 | 구성 | 상태 |
|---|---|---|
| B0 | Planner + generic single solver | smoke test용 |
| B1 | Planner + track specialist 3명 | **권장 baseline** |
| C1 | B1 + coding Architect/Editor split | A/B 후보 |
| C2 | B1 + conditional coding reviewer | C1과 별도 A/B 후보 |
| C3 | B1 + conditional math second sample | disagreement calibration 후 후보 |
| C4 | B1 + generic second sample/debate | 기본적으로 기각; 큰 holdout gain 필요 |

Nature의 controlled study, fixed-token single-vs-multi-agent 연구, BenchAgent 결과를 함께 보면 “더 많은 agent”는 독립적인 성공 변수가 아니다. 근거와 수치는 [single-agent 대 multi-agent](../02-evidence/01-single-vs-multi-agent.md)에 정리했다.

## 최종 권고와 기존 5-agent 안의 관계

기존 ideation의 5-agent 구성은 [주제 문서](../../../../ideation/final_ideation/주제.md)의 24~37행에 있다. 이를 삭제하거나 틀렸다고 단정하지 않는다. 다만 현재 공개 evidence로는 5명을 모든 문항에 호출할 이유가 없다.

- Template에 reviewer가 존재해도 기본 route에는 넣지 않는다.
- Coding split은 별도 variant로 측정한다.
- Visualization은 구성도보다 실제 호출 수와 token을 보여준다.
- 최종 제출에는 holdout을 이긴 variant만 남긴다.
