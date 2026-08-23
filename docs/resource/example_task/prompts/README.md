# prompts — 트랙별 one-shot 프롬프트

> **[2026-08-23 갱신]** 이 세 파일은 `squad/squad_template/monstrous_squad/add_prompt/`의 사본이다.
> 원본은 그쪽이고, `validate_template.py`가 두 벌이 어긋나면 실패한다. 첫 줄이 `PLANNER:`로 시작하는 이유와
> 되뱉기 안전성 규칙 셋은 그 폴더의 `README.md`에 있다.


포털 Submit 탭이 요구하는 제출물이 **"Squad Template JSON 하나 + 트랙별 one-shot 프롬프트"** 다.
이 세 파일이 제출물의 절반이고, 실험에서 가장 자주 고치게 될 자리다.

```
coding.txt    math.txt    generic.txt    ← 도구가 읽는 활성 프롬프트
variants/                                ← 실험 변종 보관
```

---

## 지켜야 하는 규칙

### `{{TASK}}`를 정확히 한 번 쓴다

judge는 **모든** `{{TASK}}`를 문항 본문으로 치환한다. 두 번 쓰면 문항이 두 번 들어간다.
coding 트랙에서 이 실수는 입력 토큰을 그대로 2배로 만든다.

`compose.py`는 `{{TASK}}`가 없는 프롬프트를 거부한다 — 문항이 통째로 빠진 요청으로
전 문항 오답을 내는 사고를 막기 위해서다.

### `{{TASK}}`를 맨 뒤에 둔다

문항마다 달라지는 부분이 뒤로 가야 앞쪽 지시문이 안정 프리픽스가 되고, prefix cache가 걸린다.
포털이 직접 "긴 안정 프리픽스를 변하는 부분 앞에 두면 진짜 여유가 생긴다"고 안내한다.
현재 세 파일 모두 그 배치다.

### REQUIRED OUTPUT 블록을 복사해 넣지 않는다

judge가 어차피 뒤에 붙인다. 프롬프트에서 형식을 다시 설명하면 같은 지시를 두 번 보내는 것이다.
보강이 필요하면 한 줄로 족하다.

현재 세 파일이 쓰는 한 줄이 이것이고, 형식 반복이 목적이 아니라 **위치**를 강제하는 게 목적이다.

> The last line of your reply, and the last thing any agent in this squad emits, must be: …

### 답 블록이 마지막 웨이브에서 나와야 한다

judge는 집계 결과를 먼저 보고, 거기가 상태 요약이면 **마지막 웨이브부터 거꾸로** 태스크 출력을 훑는다.
마지막 웨이브가 리뷰나 요약을 하면서 답 블록을 다시 안 실으면, 앞 웨이브가 정답을 냈어도 못 읽어간다.
자세한 건 `../01-요청-합성-규칙.md` 3절.

---

## 현재 세 파일이 무엇을 하고 있나

기준선이지 정답이 아니다. 여기서부터 깎아 나가는 출발점이다.

| 파일 | 크기 | 핵심 지시 |
|---|---|---|
| `math.txt` | 731 B | 최단 경로로 값만 확정, 재검산 금지, 정수는 맨 정수로 |
| `generic.txt` | 439 B | 나열된 문자 중에서만 선택, 추론 출력 최소화 |
| `coding.txt` | 1,457 B | 도구 없음을 명시, SEARCH 바이트 복사, 최소 변경, 마지막에 한 번만 방출 |

`coding.txt`가 유일하게 긴 이유는, 이 트랙의 실패가 대부분 **형식과 과잉 수정**에서 나오고
그 둘 다 지시로 줄일 수 있기 때문이다. 나머지 둘은 짧을수록 좋다 — 어차피 과정을 채점하지 않는다.

---

## 실험할 때

프롬프트를 고치면 사본을 `variants/`에 같이 남긴다.

```
variants/
  math-01-baseline.txt
  math-02-no-restate.txt
  coding-03-format-first.txt
```

어떤 프롬프트가 어떤 점수를 냈는지 나중에 되짚을 수 없으면 돌린 토큰이 전부 낭비다.
`run_batch.py`가 행마다 `request_chars`를 기록하므로,
프롬프트를 길게 고쳤을 때 입력이 얼마나 늘었는지 정확도 변화와 나란히 볼 수 있다.

```bash
# 합성 결과 확인
python3 ../tools/compose.py math-visible-0001 --prompt math.txt | less

# 변종으로 돌리기
python3 ../tools/run_batch.py <SQUAD_ID> <WORKSPACE> \
        --tracks math --limit 10 --prompt-dir variants --out ../runs/math-02.jsonl
```

`--prompt-dir`는 그 디렉터리에서 `<track>.txt`를 찾는다. 변종을 돌리려면
`variants/math.txt`처럼 트랙 이름으로 두거나, 디렉터리를 나눠서 관리한다.
