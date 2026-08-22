# Squad Darwin — 스스로 작아지는 Agent Squad

> **[갱신됨 2026-08-23 · 이 문서는 역사 기록이다]** 2026-08-22 발상 단계의 기록이고 최종 설계가 아니다. 현행은 `../../final_final_ideation/spec/`이다. 최종 스쿼드는 Router · Architect · Editor · Solver · Reviewer 5인이고, 여기 나오는 그 밖의 에이전트 이름은 채택되지 않았다.

> 연습 실행의 실제 점수와 token을 기준으로 agent·연결·model 배치를 진화시켜, 가장 작은 고득점 Squad 하나만 제출하는 주제.

## 간단한 설명

사람이 감으로 Squad 구조를 고정하지 않는다. 364개 visible practice item을 계층화된 학습군과 검증군으로 나누고, 기본 Squad에서 agent 삭제, 연결 삭제, prompt 축약, 저비용 model 교체라는 작은 변이를 만든다. 각 변이는 실제 practice grader로 다시 측정하며, 검증 점수를 유지하거나 높이면서 token을 줄인 변이만 다음 세대로 남긴다.

최종 산출물은 실험용 여러 Squad가 아니라, 이 과정을 통과한 단 하나의 Squad Template이다. 따라서 제출 규칙을 지키면서도 “왜 이 agent가 필요하고, 왜 이 연결은 제거했는가”를 실측값으로 설명할 수 있다.

## 핵심 동작

- Coding, Math, Generic을 고르게 포함한 holdout으로 과적합을 막는다.
- agent node와 통신 edge의 한계 기여도가 낮으면 제거하고, 단순 역할은 더 저렴한 model로 교체한다.
- 시각화는 Squad의 계보를 나무처럼 보여주고, 각 변이를 클릭하면 정확도·token·wall time의 실제 전후 차이를 연다.

## 1등을 노릴 수 있는 이유

Benchmark 40점은 검증 점수가 지키고, token efficiency 30점은 불필요한 agent와 edge를 실제로 제거해 공략한다. Visualization 30점에는 추정치가 아니라 practice A/B 실행 증거가 들어간다. 기존의 수동 설계 발표보다 재현성과 설득력이 강하다.

연구 근거: [GPTSwarm은 agent workflow를 최적화 가능한 graph로 정의했다](https://proceedings.mlr.press/v235/zhuge24a.html). [AgentSlimming은 불필요한 agent 제거와 저비용 model 교체로 평균 token cost를 최대 78.9% 줄이면서 성능을 보존할 수 있음을 보고했다](https://aclanthology.org/2026.acl-long.1387/).
