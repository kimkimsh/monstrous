# math 트랙 — 가중치 0.25

59문항. 지문이 짧아서 **한 바퀴가 싸다.** 구조적 결함을 잡는 실험은 여기서 먼저 돌린다.

| 항목 | 값 |
|---|---|
| 구성 | math-500-level5 **48** + aime-2024 **11** |
| 가중치 | 0.25 |
| grader | `math_answer` — `integer_exact` 및/또는 `math_verify` |
| 요청 크기 | 최소 334 / 중앙값 491 / 최대 1,570 바이트 |
| 요청 합계 | 32,253 바이트 |
| **실행 반복** | **`run_repeats: 2`** — 같은 문제를 2회 돌려 평균 |
| 출력 형식 | `FINAL ANSWER: \boxed{<answer>}` |

---

## 채점 방식

> Competition mathematics. **Only the final answer is graded**, checked exactly rather than
> read, so a right answer reached badly still counts and a good attempt that lands on the
> wrong number does not.

**과정은 채점하지 않는다.** 답이 맞으면 과정이 엉망이어도 인정되고, 과정이 훌륭해도 숫자가 틀리면 0점이다.

답 형식에 따라 검사기가 갈린다.

| `answer_format` | 문항 수 | 검사 |
|---|---|---|
| `integer` | 35 | `integer_exact` **와** `math_verify` 둘 다 |
| `expression` | 24 | `math_verify` |

데이터셋별로 보면 이렇다.

| 데이터셋 | integer | expression | 합 |
|---|---|---|---|
| math-500-level5 | 24 | 24 | 48 |
| aime-2024 | 11 | 0 | 11 |

**AIME는 정의상 000~999의 정수다.** 정수 답 35문항은 추출과 검증이 훨씬 쉬우므로
별도 경로로 처리할 가치가 있다.

`math_verify`는 수식 동치를 판정하므로 `1/2`와 `\frac{1}{2}`와 `0.5`가 같게 처리될 가능성이 높다.
그래도 `gold` 형식(`\frac{11}{2}` 같은 순수 표현)에 맞추는 것이 안전하다.

---

## 토큰이 어디서 드나

지문이 중앙값 231바이트다. **입력 토큰이 거의 안 든다. 비용은 사실상 전부 출력 토큰이다.**

여기에 reasoning 모델을 붙이면 비용이 폭발한다.
평가 모델 3개 중 2개가 reasoning 모델이고 하나는 출력 예산의 97%를 사고에 쓴다는 측정이 공개돼 있다.
게다가 **`run_repeats: 2`라 실제 실행 횟수가 문항 수의 2배다.**
hidden에서 60~66문항이면 실행은 120~132회다.

→ 이 트랙은 **사고 토큰을 조이는 설정이 그대로 점수가 되는 자리다.**
`--no-think`, `--thinking-budget N`, `--reasoning-effort none`.

---

## 추출 실패를 줄이는 것

`gold_latex`가 `$\boxed{\frac{11}{2}}$` 형태다. REQUIRED OUTPUT 블록도 `\boxed{}`를 요구한다.

```
FINAL ANSWER: \boxed{<answer>}
```

- `\boxed{}` **안에 답만** 넣는다. 단위, 설명, 부호 설명이 같이 들어가면 추출이 어긋난다.
- 여러 개가 나오면 **마지막 것**이 쓰인다.
- 그 앞의 본문은 아예 읽지 않는다 — 정확도는 안 깎이지만 **토큰은 그대로 든다.**

`grade.py`의 추출기는 중괄호 짝을 세면서 읽으므로 `\frac{a}{b}`처럼 중첩된 답도 온전히 뽑는다.

---

## 파일

```
math/
├── required_output.txt        257바이트, 바이트 그대로
├── index.json                 59문항 메타 — dataset, answer_format, 바이트 수, SHA-256
├── requests/<id>.txt          붙여넣기용 완성 요청 59개
├── tasks/<id>.txt             {{TASK}} 자리에 들어가는 문제 지문
└── gold/answers.jsonl         gold, gold_latex, answer_format, checks — 채점기만 읽는다
```

`items_id`는 `math-visible-0001` ~ `math-visible-0052`와 `math-visible-0135` ~ `math-visible-0145`로
번호가 이어지지 않는다. visible 세트가 164 → 59문항으로 잘리면서 남은 번호를 그대로 쓰기 때문이다
(`raw/math.manifest.json`의 `trim` 블록). 결번이 아니라 정상이다.
