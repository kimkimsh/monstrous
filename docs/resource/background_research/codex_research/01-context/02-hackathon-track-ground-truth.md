# 해커톤과 참가 트랙 Ground Truth

## 행사

JUNCTIONX Korea 2026의 공식 일정은 2026-08-21~23, 포항이다. 공식 페이지는 48시간, 3개 track, 최대 4인 team을 안내한다.

- 공식 행사 페이지: [JunctionX Korea 2026](https://asia.hackjunction.com/)
- Junction platform 일정: [hackjunction.app 행사 페이지](https://hackjunction.app/hackathons/junctionx-korea-2026)
- 로컬 요약: [example_task/00-트랙-정리.md](../../../example_task/00-트랙-정리.md), 1~8행.

주요 시간표:

| 시각 KST | 이벤트 |
|---|---|
| 8/21 20:00 | track announcement |
| 8/21 21:00 | track partner workshop |
| 8/22 00:00 | Mission 1 |
| 8/22 09:00~18:00 | partner feedback |
| 8/23 00:00 | Mission 2 |
| 8/23 12:00 | Mission 3 |
| 8/23 13:00~16:00 | demo expo |
| 8/23 16:00~17:00 | final pitch |

## 참가 track

Partner는 Lablup + FuriosaAI이고 과제명은 **Build the Ultimate Agent Squad**다. local PDF `docs/resource/track_resource/lableup/3 LABL.pdf` 20페이지가 challenge를 설명한다.

필수 산출물:

1. 수학·코딩·generic 문제를 푸는 problem-solving AI agent squad.
2. 어느 agent가 무엇을 했고, 무엇을 검증했으며, 언제 멈췄는지를 보여주는 interactive trace visualization.
3. critical problem-solving path는 AI:GO의 agent squad 기능 위에서 실행.

[트랙 정리](../../../example_task/00-트랙-정리.md)의 12~27행은 portal에서 확인한 제출 단위를 `Squad Template JSON` 하나와 track별 one-shot prompt 세 개로 기록한다.

## 점수 구조

local PDF 24페이지 기준 총 100점:

| 축 | 배점 | 실전 의미 |
|---|---:|---|
| Benchmark | 40 | deterministic accuracy 순위 |
| Visualization | 30 | observability, interpretability, traceability, explainability, clarity, insightfulness |
| Token efficiency | 30 | 모델별 token과 기준 단가를 반영한 normalized cost |

Benchmark 내부 식:

```text
overall = 0.5 × accuracy(coding)
        + 0.25 × accuracy(generic)
        + 0.25 × accuracy(math)
```

로컬 manifest를 풀어 쓴 근거는 [평가·채점 규칙](../../../track_resource/lableup/02-평가-채점-규칙.md)의 59~74행과 [최신 트랙 정리](../../../example_task/00-트랙-정리.md)의 31~56행이다.

Token 규칙:

- AI:GO test run은 기준 cost의 1/5.
- submission run은 전액.
- 실행 횟수마다 전부 누적.
- benchmark tie는 total token, 그다음 wall-clock 순으로 해소.
- Check는 무료지만 queue run은 비용에 들어간다.

근거는 local PDF 25페이지와 [최신 트랙 정리](../../../example_task/00-트랙-정리.md)의 62~72행이다.

## 평가 workload

| track | hidden target | repeat | weight | grader |
|---|---:|---:|---:|---|
| coding | 140~240 | 1 | 0.50 | SWE-bench Docker 또는 LiveCodeBench tests |
| math | 60~66 | 2 | 0.25 | integer exact / symbolic math verify |
| generic | 448~698 | 1 | 0.25 | letter match |

Judge는 LLM을 사용하지 않는다. [최신 트랙 정리](../../../example_task/00-트랙-정리.md)의 76~100행처럼 answer extraction 실패와 token/wall-clock cap도 team-owned failure가 될 수 있다.

## request와 answer 계약

Judge는 track one-shot prompt의 모든 `{{TASK}}`를 item으로 치환하고, line ending과 trailing whitespace를 정규화한 뒤 REQUIRED OUTPUT block을 붙인다. `{{TASK}}`를 두 번 넣으면 coding 60KB context도 두 번 들어간다. 정확한 합성식은 [요청 합성 규칙](../../../example_task/01-요청-합성-규칙.md)의 9~50행에 있다.

정답 형식:

| track | 마지막 정답 |
|---|---|
| coding | `*** PATCH START ***`와 `*** PATCH END ***` 사이 SEARCH/REPLACE blocks |
| math | `FINAL ANSWER: \boxed{<answer>}` |
| generic | `ANSWER: <letter>` |

여러 answer block이 있으면 마지막 것만 사용한다. 앞부분은 accuracy grader가 무시하지만 token에는 포함된다. [요청 합성 규칙](../../../example_task/01-요청-합성-규칙.md)의 54~119행을 기준으로 구현해야 한다.

Answer extraction 순서도 중요하다.

1. aggregated result.
2. task output을 마지막 wave부터 역순 탐색.
3. runtime이 만든 `Execution complete` status summary는 정답으로 거부.

따라서 마지막 wave의 마지막 relevant task가 반드시 valid answer block으로 끝나야 한다. 근거는 [요청 합성 규칙](../../../example_task/01-요청-합성-규칙.md)의 123~173행이다.

## coding 특수 조건

평가 squad는 repository를 browse하지 않고 tool도 쓰지 않는다. Judge가 repository/commit을 바탕으로 code를 검색해 최대 60,000자 context bundle을 request에 넣는다. 공개 context 실측은 최소 59,634자, 중앙값 59,966자, 최대 60,000자였다. [benchmark 분석](../../../track_resource/lableup/04-벤치마크-데이터셋-분석.md)의 246행과 283~300행이 근거다.

이 조건이 squad 설계를 제약한다.

- 별도 repo-search agent는 평가 때 작동하지 않는다.
- 여러 agent가 full request를 각각 받으면 input token이 배수로 증가할 수 있다.
- 요약 handoff는 비용을 줄일 수 있지만 SEARCH line exactness를 훼손할 수 있다.
- judge가 이미 retrieval을 했으므로 agent가 할 localization은 “repository 탐색”이 아니라 “주어진 excerpts 안에서 target hunk 선택”이다.

## 확인된 평가 모델

현재 정확히 확인된 모델은 `Qwen3-30B-A3B-Instruct-2507-FP8` 하나다. 나머지 두 reasoning model 이름은 공개 자료에서 확인되지 않았다.

[공식 Qwen model card](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507)는 다음을 명시한다.

- 30.5B total / 3.3B activated MoE.
- native context 262,144.
- non-thinking only; `<think>` block을 생성하지 않는다.
- MMLU-Pro 78.4, AIME25 61.3, LiveCodeBench v6 43.2, Aider-Polyglot 35.6.
- 권장 sampling은 temperature 0.7, top-p 0.8, top-k 20.

단, organizer serving stack이 sampling knob를 모두 노출하는지와 model card setting을 그대로 쓰는지는 미확인이다.

## 지금 organizer에게 물어야 할 질문

1. 세 model의 정확한 identifier와 USD/Mtok normalization price.
2. input/output/reasoning/cache token을 각각 어떻게 집계하는가.
3. per-run token cap, per-item wall-clock cap.
4. one-shot prompt가 Planner에만 들어가는가, worker 요청에도 복제되는가.
5. cached input의 exact 할인율·최소 prefix·TTL은 무엇이고, Planner/worker 호출에서 실제로 hit하는가.
6. evaluation 중 runner-level deterministic validation/retry가 허용되는가.
7. trace의 공식 source는 portal, AI:GO event log, 둘 다인가.
8. Squad Template JSON schema/version과 AI:GO 1.12.1 compatibility.

이 값이 없으면 absolute budget은 정할 수 없다. 다만 architecture 간 상대 비교는 token breakdown을 직접 기록하면 가능하다.
