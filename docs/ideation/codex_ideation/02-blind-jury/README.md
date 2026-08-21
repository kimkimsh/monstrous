# Blind Jury — 서로의 답을 보지 않는 배심원 Squad

> agent들이 먼저 독립적으로 판단하고, 의견이 갈린 지점만 공개 반박하게 만들어 다수결의 집단 착각을 막는 주제.

## 간단한 설명

맹검(blind review)은 첫 판단 전에 다른 agent의 답을 보여주지 않는 방식이다. 각 specialist는 서로의 추론을 보지 않은 채 `정답 후보·핵심 근거·가장 위험한 반례·신뢰 구간`만 담은 짧은 sealed ballot을 제출한다. Planner는 익명 ballot이 일치하면 즉시 확정하고, 불일치할 때만 상충하는 근거 한 쌍을 Refuter에게 보낸다.

역할도 의도적으로 다르게 둔다. Math는 식 전개와 역산, Generic은 지식 회상과 오답 제거, Coding은 요구사항 해석과 regression 위험 탐색처럼 서로 다른 실패 모드를 보게 한다. 같은 답을 장문으로 반복하는 일반적인 multi-agent debate는 사용하지 않는다.

## 핵심 동작

- 첫 wave의 판단을 완전히 분리해 anchoring과 echo chamber를 줄인다.
- 합의된 문항은 추가 호출 없이 끝내고, 불일치한 주장만 sparse debate로 보낸다.
- 시각화는 sealed ballot 공개, 답변 다양성, 공통 misconception 후보, 최종 반박 경로를 배심 평결 화면으로 보여준다.

## 1등을 노릴 수 있는 이유

단순 다수결보다 오류 상관관계를 낮춰 Benchmark를 노리고, 짧은 ballot과 조건부 반박으로 token을 통제한다. 동시에 “누가 무엇을 믿었고 어느 반례가 판결을 바꿨는가”가 한 화면에서 드러나므로 trace가 곧 제품의 핵심 경험이 된다.

연구 근거: [NeurIPS 2024 연구는 비슷한 agent들이 공통 오개념을 공유하면 debate가 잘못된 다수 의견으로 수렴할 수 있음을 보였다](https://proceedings.neurips.cc/paper_files/paper/2024/hash/32e07a110c6c6acf1afbf2bf82b614ad-Abstract-Conference.html). [Sparse communication은 조밀한 debate와 비슷하거나 더 나은 성능을 더 낮은 비용으로 낼 수 있다](https://aclanthology.org/2024.findings-emnlp.427/).
