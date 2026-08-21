# Ghost Test Lab — 실행할 수 없는 테스트를 먼저 설계하는 Coding Squad

> patch부터 쓰지 않고, issue가 요구하는 fail-to-pass 행동과 regression 금지 조건을 먼저 만든 뒤 그 조건을 가장 잘 만족하는 patch를 고르는 주제.

## 간단한 설명

Coding이 전체 benchmark 가중치의 절반이므로, 이 주제는 SWE-bench와 LiveCodeBench를 정면 공략한다. TestSmith가 issue와 제공된 code context에서 짧은 `Given / When / Then`, 예상 failure, 보존해야 할 기존 동작을 추출한다. PatchMaker가 이 ghost test card를 만족하는 최소 patch를 만들고, Mutation Prosecutor가 경계값이나 호출 순서를 한 번 비틀어 regression 가능성을 찾는다.

평가 중 Squad에는 실행 도구가 없으므로 ghost test를 실제 실행했다고 주장하지 않는다. 공식 실행에서는 행동 계약과 mental simulation으로만 사용하고, visible practice 단계에서는 같은 card를 실행 가능한 test로 구체화해 유효성을 사전 측정한다.

## 핵심 동작

- issue를 바로 patch로 번역하지 않고, 먼저 관찰 가능한 성공 조건과 보존 조건으로 바꾼다.
- 반례가 발견된 경우에만 patch 후보를 한 번 더 만들고, 그 외에는 첫 최소 patch를 제출한다.
- 시각화는 test card를 행, patch hunk를 열로 둔 coverage matrix를 보여주며, 각 판정에서 사용한 code excerpt까지 연결한다.

## 1등을 노릴 수 있는 이유

가중치 0.5인 Coding에서 “그럴듯한 diff”를 “행동 조건을 통과할 가능성이 높은 diff”로 바꾸는 주제다. test intent는 짧아서 token 부담이 작고, test-to-patch matrix는 비개발자도 patch의 이유와 위험을 즉시 이해하게 해 Visualization 점수도 노릴 수 있다.

연구 근거: [Agentless는 localization, repair, patch validation의 단순한 3단계로 SWE-bench Lite에서 강한 성능과 낮은 비용을 보였다](https://arxiv.org/abs/2407.01489). [e-Otter++는 SWE issue에서 fail-to-pass reproduction test를 생성하는 접근이 patch 문제 구체화와 선택에 유효함을 보였다](https://arxiv.org/abs/2508.06365).
