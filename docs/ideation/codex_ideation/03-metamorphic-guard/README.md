# Metamorphic Guard — 정답 없이 정답을 흔들어 보는 Squad

> **[갱신됨 2026-08-23 · 이 문서는 역사 기록이다]** 2026-08-22 발상 단계의 기록이고 최종 설계가 아니다. 현행은 `../../final_final_ideation/spec/`이다. 최종 스쿼드는 Router · Architect · Editor · Solver · Reviewer 5인이고, 여기 나오는 그 밖의 에이전트 이름은 채택되지 않았다.

> 답을 다시 풀기보다, 의미를 보존한 변형 뒤에도 답의 관계가 유지되는지 검사하는 변형 불변성 검증 주제.

## 간단한 설명

Metamorphic testing은 정답표를 모를 때도 입력을 일정하게 바꾸면 출력이 어떻게 변해야 하는지 아는 관계로 오류를 찾는 방법이다. Solver가 낸 답을 Verifier가 그대로 재풀이하지 않고, 문제별로 값싼 불변성 검사를 한 번 적용한다.

Math에서는 결과를 원식에 역대입하거나 동치식으로 바꿔 같은 값이 나오는지 본다. Generic에서는 선택지 순서를 바꾼 뒤 원래 문자로 되돌렸을 때 같은 의미의 선택지가 남는지 확인한다. Coding에서는 issue를 동치인 행동 조건으로 다시 표현하고, patch가 정상 동작 보존 조건과 반례 조건을 동시에 만족하는지 검사한다.

## 핵심 동작

- Planner가 track에 맞는 변형 관계 하나만 선택해 검증 비용을 제한한다.
- 불변성이 깨진 경우에만 대체 답이나 patch 수정을 요청한다.
- 시각화는 원문, 변형, 기대 관계, 실제 결과를 연결한 “Invariant Lattice”로 어느 조건에서 답이 무너졌는지 보여준다.

## 1등을 노릴 수 있는 이유

독립 재풀이보다 짧은 검증으로 우연한 정답, 위치 편향, patch의 숨은 regression을 잡아 Benchmark와 token efficiency를 함께 노린다. 정답이 맞다는 주장 대신 “어떤 변형에도 살아남았는가”를 보여주므로 Visualization의 explainability도 강하다.

연구 근거: [Metamorphic Prompt Testing은 ground truth 없이 LLM 생성 코드의 의미 일관성을 교차 검증해 HumanEval의 오류 프로그램 75%를 탐지했다고 보고했다](https://arxiv.org/abs/2406.06864). 이 수치는 코드 실험 결과이며, Math와 Generic으로의 확장은 visible practice set에서 별도로 검증해야 한다.
