# PacketBus — 자연어 회의를 버린 Agent 통신 규약

> agent 사이의 장문 대화를 고정 schema의 작은 판단 packet으로 바꿔, 의미 변질과 token 중복을 동시에 줄이는 주제.

## 간단한 설명

모든 handoff를 자유로운 자연어가 아니라 `track`, `claim`, `evidence`, `constraints`, `confidence`, `dissent`, `next_action` 필드로 구성된 typed packet으로 제한한다. 각 필드의 길이는 practice 실행으로 정한 상한을 가지며, 이전 agent의 chain-of-thought나 60,000자 code context를 다시 복사하지 않는다. Coding은 excerpt ID와 patch hunk, Math는 식과 검산 결과, Generic은 option과 반증 근거만 전달한다.

마지막 agent는 packet을 grader가 요구하는 최종 형식으로 한 번만 compile한다. 이 구조는 agent가 앞선 문장을 제멋대로 재해석하는 semantic drift, 즉 전달 과정에서 의미가 변하는 문제도 줄인다.

## 핵심 동작

- 하나의 공통 schema를 세 track이 공유하되, track별 허용 field와 출력 계약만 다르게 둔다.
- schema 위반과 근거 없는 claim은 다음 wave로 전달하지 않는다.
- 시각화는 packet을 node와 edge로 복원해 근거 계보, 누락 field, agent별 fresh/forwarded token을 실시간으로 보여준다.

## 1등을 노릴 수 있는 이유

실제 token을 잡아먹는 agent 간 반복 문장을 구조적으로 없애 token efficiency를 직접 공략한다. 짧고 typed된 trace는 사람이 읽기도 쉽고 자동 집계도 쉬워 Visualization 완성도가 높다. 근거 ID와 제약이 보존되므로 압축 때문에 Benchmark가 무너지는 위험도 관리할 수 있다.

연구 근거: [G2CP는 자유문 대신 구조화된 graph operation을 사용해 inter-agent token 73% 감소와 더 높은 task completion을 보고했다](https://arxiv.org/abs/2602.13370). [AgentDiet은 누적 trajectory의 불필요·중복·만료 정보를 줄여 input token을 39.9~59.7% 절감하면서 성능을 유지했다](https://arxiv.org/abs/2509.23586).
