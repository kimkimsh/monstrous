# Track별 Solver Playbook

## 공통 prompt 원칙

모든 one-shot prompt는 stable instruction을 먼저 두고 `{{TASK}}`를 마지막에 정확히 한 번 둔다. Judge가 REQUIRED OUTPUT block을 추가하므로 이를 prompt 안에 장황하게 복제하지 않는다. 아래는 실험 시작점이지, test 없이 그대로 최종 제출하라는 의미가 아니다.

공통 invariant:

1. supplied request만 사용한다.
2. 문제를 끝까지 푼 뒤 final contract를 정확히 한 번 출력한다.
3. final answer 이후 설명을 쓰지 않는다.
4. 실패해도 status summary가 아니라 parse 가능한 최선의 답을 남긴다.

## Coding

### 목표

주어진 repository excerpt 안에서 issue를 해결하는 최소 SEARCH/REPLACE patch를 만든다. Judge가 이미 retrieval을 수행하므로 “repository를 탐색하라”는 지시는 무효다.

### 내부 작업 순서

1. issue가 요구하는 observable behavior와 유지해야 할 invariant를 한 문장씩 잡는다.
2. 관련 file과 symbol을 supplied excerpt에서 찾는다.
3. 기존 control/data flow에서 root cause가 발생하는 지점을 식별한다.
4. 가장 작은 complete fix를 설계한다.
5. SEARCH text가 원문과 byte/line 단위로 일치하는지 눈으로 재대조한다.
6. 새 file이 아니라면 SEARCH를 비워 두지 않는다.
7. marker, path, block balance를 확인한 뒤 patch만 출력한다.

### Prompt skeleton

```text
You are the coding solver. Use only the supplied issue and repository excerpts.
Identify the root cause and produce the smallest complete fix.
Before finalizing, verify every SEARCH block is copied exactly from the supplied text,
the target path is correct, markers are balanced, and the replacement preserves
unrelated behavior. Do not emit a unified diff or commentary after the final patch.

{{TASK}}
```

### 실패 방지 checklist

- issue 설명만 고치고 mechanism은 남기는 symptom patch를 피한다.
- import, call site, signature를 함께 바꿔야 complete한 경우 한 hunk만 고집하지 않는다.
- context에 없는 file을 추측해 만들지 않는다.
- ellipsis, line number, Markdown fence를 SEARCH에 넣지 않는다.
- 같은 SEARCH가 여러 번 등장하면 replacement target이 모호해지지 않도록 더 넓은 unique anchor를 잡는다.
- final marker 밖의 prose를 제거한다.

### Fused 대 split

Fused가 기본이다. Split 후보에서 Architect는 solution prose가 아니라 `target_file`, `exact_search_block`, `replacement_intent`, `must_preserve`를 넘긴다. Editor가 original line을 다시 추측하게 하면 split 목적을 잃는다. Agentless와 SWE-Edit의 적용 가능성과 한계는 [track-specific evidence](../02-evidence/03-track-specific-evidence.md)에 있다.

## Math

### 목표

짧은 explicit derivation으로 계산·조건 오류를 줄이고 integer 또는 symbolic expression을 canonical하게 만든다.

### 내부 작업 순서

1. 구해야 할 quantity와 domain/constraint를 식별한다.
2. 핵심 식을 세우고 계산한다.
3. 부호, 정수성, 범위, extraneous root를 검산한다.
4. 문제의 requested representation으로 정리한다.
5. 마지막에 `FINAL ANSWER: \boxed{...}`만 둔다.

### Prompt skeleton

```text
You are the math solver. Solve the problem with concise explicit reasoning.
Check constraints, signs, arithmetic, and extraneous solutions before finalizing.
Return the requested canonical value and end with exactly one boxed final answer.

{{TASK}}
```

### 예산 정책

- 기본은 1 sample이다.
- 단순 정수 문제에도 reasoning을 완전히 끄지 않는다.
- max output은 visible set의 실제 분포로 단계적으로 낮춘다.
- second sample은 2-sample disagreement가 오답과 상관 있음을 holdout에서 확인한 뒤에만 쓴다.
- majority vote에는 최소 3 sample이 필요하므로 “2개가 다르면 하나 더” 정책의 전체 expected cost를 계산한다.

### 실패 방지 checklist

- 여러 boxed answer를 남기지 않는다.
- 근사값과 exact expression을 혼용하지 않는다.
- 문제에서 요구한 integer/expression contract를 바꾸지 않는다.
- decoder-level budget forcing을 prompt 한 줄로 구현했다고 주장하지 않는다.

## Generic

### 목표

질문과 모든 선택지를 비교한 뒤 정확한 option letter를 출력한다. 공개 MMLU-Pro형 문항 대부분은 10개 선택지이므로, 표면적으로 그럴듯한 첫 답을 고르는 전략은 취약하다.

### 내부 작업 순서

1. 질문이 요구하는 사실, 원리, 계산을 식별한다.
2. 가장 강한 후보를 만든다.
3. 가까운 distractor를 반례·정의·단위로 제거한다.
4. 선택한 option text와 letter mapping을 다시 확인한다.
5. `ANSWER: <letter>`로 끝낸다.

### Prompt skeleton

```text
You are the multiple-choice solver. Reason privately and concisely.
Compare the strongest alternatives, reject distractors using the question's exact
constraints, verify the option-to-letter mapping, and output only the required
answer line at the end.

{{TASK}}
```

### 왜 “reasoning 금지”가 아닌가

[MMLU-Pro](https://arxiv.org/html/2406.01574v3)는 평균 9.47개 선택지이고 83%가 10-choice다. 논문의 비교에서는 CoT가 direct answer보다 모든 model에서 높았으며 GPT-4o는 53.5%에서 72.6%로 +19.1 percentage point였다. 대회 model과 동일한 결과라는 뜻은 아니지만, 토큰을 아끼기 위해 추론 자체를 금지하는 기본값을 지지하지는 않는다.

### 실패 방지 checklist

- option text가 아니라 letter를 final로 쓴다.
- 3~10개의 실제 option 범위를 확인한다.
- “항상 A~J”라고 가정하지 않는다.
- explanation을 final answer 뒤에 붙이지 않는다.

## 최종 answer owner

각 track solver가 answer owner다. Planner가 solver 결과를 다시 요약하거나 rewrite하지 않는다. Request extraction은 aggregated result를 먼저 보고, 없으면 task output을 마지막 wave부터 역순으로 찾기 때문에 finalizer agent를 별도로 두면 새 failure surface와 token이 생긴다. 정확한 extraction contract는 [요청 합성 규칙](../../../example_task/01-요청-합성-규칙.md)의 123~173행에 있다.
