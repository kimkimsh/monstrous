# add_prompt — 트랙별 one-shot 프롬프트 3개

제출물의 나머지 절반이다. 포털은 **Squad Template JSON 1개 + 트랙별 one-shot 프롬프트 3개**를 받는다.

| 파일 | 붙는 트랙 | 크기 |
|---|---|---|
| `coding.txt` | SWE-bench Lite + LiveCodeBench v6 (hidden 38문항, 가중치 0.5) | 6,843자 |
| `math.txt` | HMMT Feb 2026 + AIME 2026 (hidden 13문항, 가중치 0.25) | 3,435자 |
| `generic.txt` | MMLU-Pro + GPQA (hidden 96문항, 가중치 0.25) | 3,178자 |

**이 폴더가 원본이다.** `docs/resource/example_task/prompts/`에 같은 파일이 있는 것은 로컬
하네스(`compose.py`)의 기본 경로이기 때문이고, `tools/validate_template.py`가 두 벌이 어긋나면
실패한다. 고칠 자리는 여기 하나다.

## 서버가 조립하는 방식

세 파일 모두 **맨 끝에 `{{TASK}}`가 정확히 한 번** 있다. 서버는 이렇게 조립한다.

```
[이 파일 전문, {{TASK}}는 문항 본문으로 치환]
                                          ← 서버가 빈 줄 하나
=== REQUIRED OUTPUT ===
<트랙별 형식 지시, 바이트 그대로>
```

그래서 실제 순서는 **우리 프롬프트 → 문항 → REQUIRED OUTPUT 블록**이다.

- `{{TASK}}`를 두 번 쓰면 문항이 두 번 들어간다. coding에서 이 실수는 입력 토큰을 그대로 2배로 만든다.
- `{{TASK}}`가 맨 끝이라 우리 프롬프트가 통째로 안정 프리픽스다. 한 트랙 안에서 바이트가 같으므로
  prefix cache가 걸릴 수 있는 유일한 구간이다. **다만 캐시는 지연시간만 줄이지 청구되는 입력
  토큰을 줄이지 않는다** — 리더보드의 `input_tokens`가 캐시와 무관하게 전부 계상된다.
- REQUIRED OUTPUT 블록 원문은 서버가 붙이므로 여기 다시 적지 않는다. 세 파일은 그 블록을
  **가리키기만 하고**, 대신 "어디서 틀리는지"를 적는다.

## 첫 줄이 `PLANNER:`인 이유

이 텍스트를 **가장 먼저 읽는 것은 플래너**다. 스쿼드 런타임은 요청 전문을 플래너에게 주고,
플래너가 `create_task`로 만든 태스크의 `description`만 워커가 본다.

앞 제출본에서 이 지점이 무너졌다. 로컬 기록의 태스크 파일 74개 중 플래너가 직접 쓴 61개는
**답 형식을 한 번도 언급하지 않는다.** `"…produce the final answer in the required format."`
같은 문장만 남고 그 format이 무엇인지는 태스크 안에 없다. 답을 써야 하는 에이전트가 써야 할
형식을 본 적이 없는 채로 호출된다.

그래서 라우팅과 복사 규칙을 **두 곳에** 적는다. Router의 systemPrompt에 한 번, 그리고 요청
본문의 첫 줄에 한 번. 첫 줄은 어느 에이전트에게 보낼지까지 트랙별로 지정한다.

```
PLANNER: create exactly one task, assign it to Solver, and put this whole message …
```

워커도 이 줄을 읽게 되지만 `Everyone else: this line is not for you; …`로 닫아 둔다.

## 되뱉기 안전성 — 이번엔 0이다

모델이 지시문을 응답에 흘리면 그 안의 예시가 답으로 추출될 수 있다. **앞 버전의 스쿼드
systemPrompt 다섯 개는 전부 여기에 걸렸다** — `grade.py`의 추출 함수를 그대로 먹이면
`letter=C`, `boxed=204800`이 나왔다. generic 0.188, math 1/13이라는 점수와 모순되지 않는 값이다.

이번 여섯 개 텍스트(one-shot 3 + systemPrompt 3)는 전부 아무것도 추출되지 않는다.

| 파일 | `extract_letter` | `extract_boxed` | `extract_patch` |
|---|---|---|---|
| `coding.txt` | None | None | 마커 없음 |
| `math.txt` | None | None | 마커 없음 |
| `generic.txt` | None | None | 마커 없음 |
| `agent_prompts/router.txt` | None | None | 마커 없음 |
| `agent_prompts/coder.txt` | None | None | 마커 없음 |
| `agent_prompts/solver.txt` | None | None | 마커 없음 |

지키는 규칙 셋. `tools/validate_template.py`가 세 채점기를 직접 돌려서 강제한다.

1. **한 줄이 통째로 `ANSWER:` + 한 글자인 줄을 쓰지 않는다.** `LETTER_RE`는 줄 전체에 앵커돼
   있으므로 `ANSWER: C (isothermal work)`나 `**ANSWER: C**`는 안전하고, 벌거벗은 `ANSWER: C`만
   위험하다. `generic.txt`의 오답 예시가 전부 전자인 이유다.
2. **`FINAL ANSWER:` 바로 뒤에 `\boxed{`를 붙여 쓰지 않는다.** `BOXED_RE`는 줄 앵커가 없어서
   문장 한가운데서도 걸린다. 그래서 math의 형식은 **말로 설명하고**, 리터럴은 서버가 뒤에
   붙이는 REQUIRED OUTPUT 블록에 맡긴다.
3. **패치 바깥 마커 두 개를 쓰지 않는다.** `extract_patch`는 `rindex`로 **마지막** `PATCH START`를
   찾는다. 프롬프트 안에 마커가 있으면, 모델이 제대로 된 패치를 쓴 뒤에 지시문을 흘리는 순간
   그 뒤쪽 예시가 채점 대상이 된다. 들여쓰기로 무력화하는 방법도 있지만 그 경우 0블록 = 0점이라
   결과가 같다. 아예 안 쓰는 것이 유일하게 안전하다.

## 트랙별로 다르게 한 것과 그 근거

**`coding.txt`가 가장 길다(6,843자).** hidden 38문항에 가중치 0.5이고, 리더보드 24개 실행에서
**아무도 정확도 0.263을 못 넘었다.** 그 분포는 "고칠 줄 모른다"보다 "패치가 적용이 안 된다"에
가깝다. 그래서 파서가 실제로 강제하는 것 — 세 내부 마커의 0열 판정, SEARCH 바이트 일치, 파일 내
유일성, 블록 사이 산문이 조용히 path로 읽히는 것, `=` 7개 이상으로 시작하는 줄이 섹션을 끊는
것 — 을 전부 이름으로 적었다. 요청이 63KB라 이 길이는 잡음 수준이다.

**LiveCodeBench 실행 방식 두 가지를 다 싣는다.** 연습 7건 중 4건은 *"runs your file as a
program"*(stdin을 읽는다), 3건은 *"imports your file and calls the entry point"*(**stdin을 읽지
않는다**)다. 정반대이고, 틀리면 알고리즘이 맞아도 0점이다.

**`math.txt`는 간결 압박을 걸지 않는다.** hidden math는 13문항뿐인데 1문항이 총점 1.92%p로
generic 1문항(0.26%p)의 7.4배다. 2026년 대회 문제라 어느 모델의 학습 데이터에도 없다(1등도
0.538). 그래서 2단계로 **다른 경로의 검산**을 시키고, 답 형태 제약은 "형식 문제가 아니라 값이
틀린 것"으로 읽게 했다.

**`generic.txt`는 추론을 반드시 켠다.** 객관식이라 답만 뽑고 싶어지지만 이 종류에서 direct
answering은 CoT 대비 크게 진다. 보기 개수를 **하드코딩하지 않는다** — 연습 42문항에서
3·4·7·8·9·10개가 섞여 있었고 항상 A~J도 아니다.

**세 파일 모두 "무조건 답 줄을 쓴다"로 닫는다.** 앞 버전은 웨이브가 여러 개라 "빈 출력이 더
안전하다"(채점기가 건너뛰고 앞 웨이브를 읽는다)가 성립했다. **v2는 태스크가 하나뿐이라 그
안전망이 없다.** 빈 응답은 확정 0점이고, 찍은 답은 가끔 맞는다.

## 고칠 때

```bash
python3 ../tools/validate_template.py ../squad-template.json
```

`{{TASK}}` 개수·위치, `PLANNER:` 줄이 실제 존재하는 에이전트를 가리키는지, 세 채점기가 아무것도
추출하지 못하는지, 하네스 사본(`docs/resource/example_task/prompts/`)과 동기인지를 검사한다.
세 파일을 고치면 하네스 쪽에도 복사해야 통과한다.
