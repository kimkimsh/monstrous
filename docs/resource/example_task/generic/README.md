# generic 트랙 — 가중치 0.25

42문항. MMLU-Pro 14개 과목 × 3문항.
**hidden에서는 448~698문항으로 셋 중 가장 많은데 가중치는 0.25다.** 문항당 예산을 가장 빡빡하게 잡을 트랙이다.

| 항목 | 값 |
|---|---|
| 구성 | mmlu-pro 42 (14과목 × 3) |
| 가중치 | 0.25 |
| grader | `letter_match` — 대소문자 무시 |
| 요청 크기 | 최소 474 / 중앙값 918 / 최대 2,926 바이트 |
| 요청 합계 | 45,220 바이트 |
| 출력 형식 | `ANSWER: <letter>` |
| 샘플링 | MMLU-Pro 카테고리 기준 균등 층화, 시드 `20260819` 공개 |

과목: biology, business, chemistry, computer science, economics, engineering, health,
history, law, math, other, philosophy, physics, psychology.

---

## 채점 방식

> Hard multiple-choice questions drawn from across the academic subjects.
> **What is graded is the option the squad settled on, not the reasoning it printed.**

`letter_match`, 대소문자 무시. **추론 과정은 아예 채점하지 않는다.**

여기서 바로 나오는 결론 하나 — **가장 짧게 답만 뽑는 것이 정확도 손해 없이 토큰을 아끼는 지점이다.**
`ANSWER: B` 한 줄이면 채점상 완전하다.

---

## ★ 보기 개수가 문항마다 다르다

MMLU-Pro는 원래 10지선다지만 실제로는 3~10개로 들쭉날쭉하다.

| 보기 수 | 문항 수 |
|---|---|
| 10 | 36 |
| 9 | 2 |
| 8 | 1 |
| 7 | 1 |
| 4 | 1 |
| 3 | 1 |

10개가 아닌 6문항:

| item_id | 보기 수 | 과목 |
|---|---|---|
| `generic-visible-mmlu-pro-6065` | 3 | health |
| `generic-visible-mmlu-pro-11051` | 4 | philosophy |
| `generic-visible-mmlu-pro-5071` | 7 | other |
| `generic-visible-mmlu-pro-5107` | 8 | other |
| `generic-visible-mmlu-pro-10861` | 9 | philosophy |
| `generic-visible-mmlu-pro-1274` | 9 | law |

**"A부터 J 중에 고르라"고 프롬프트에 하드코딩하면 안 된다.**
보기가 3개인 문항에서 존재하지 않는 D~J를 고를 수 있고, 그건 그냥 오답이다.

요청 본문의 Options 블록에 실제 문자가 이미 나열돼 있다.

```
Options:
A. …
B. …
C. …
```

프롬프트는 **"위 Options 블록에 나열된 문자 중에서만 고르라"** 고 말하면 된다.
`prompts/generic.txt`가 그 문장을 쓰는 이유다.

---

## 예산 배분에서의 위치

`self-consistency`(같은 문제를 여러 번 풀어 다수결)는 객관식에 잘 듣는 대표적 기법이다.
그런데 여기서는 대개 손해다.

- 문항 수가 hidden에서 448~698개로 가장 많다 → n배 샘플링의 절대 비용이 가장 크다
- 가중치는 0.25다 → 정확도 1%p를 올려도 총점 기여는 0.25%p다
- 같은 토큰을 가중치 0.5짜리 coding에 쓰면 기여가 2배다

14개 과목이 균등하므로 **특정 과목에 최적화해도 이득이 1/14로 희석된다.** 범용 전략이 낫다.

---

## 추출 실패를 줄이는 것

```
ANSWER: <letter>
```

- 그 줄에는 **문자 하나만.** 설명이 붙으면 추출이 어긋난다.
- 여러 개가 나오면 **마지막 것**이 쓰인다.
- 대소문자는 무시된다.

`grade.py`의 추출기는 `^\s*ANSWER:\s*([A-Za-z])\s*$` 로 줄 전체를 잡고 마지막 것을 취한다 —
judge의 `letter_match`와 같은 동작이다.

---

## 파일

```
generic/
├── required_output.txt        289바이트, 바이트 그대로
├── index.json                 42문항 메타 — subject, 보기 수, 바이트 수, SHA-256
├── requests/<id>.txt          붙여넣기용 완성 요청 42개
├── tasks/<id>.txt             {{TASK}} 자리에 들어가는 질문 + Options 블록
└── gold/answers.jsonl         answer, answer_index, answer_text, num_options — 채점기만 읽는다
```
