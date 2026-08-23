# add_prompt — 트랙별 one-shot 프롬프트 3개

제출물의 나머지 절반이다. 포털은 **Squad Template JSON 1개 + 트랙별 one-shot 프롬프트 3개**를 받는다.

| 파일 | 붙는 트랙 | 크기 |
|---|---|---|
| `coding.txt` | SWE-bench Lite + LiveCodeBench v6 (hidden 38문항, 가중치 0.5) | 1,266바이트 |
| `math.txt` | HMMT Feb 2026 + AIME 2026 (hidden 13문항, 가중치 0.25) | 523바이트 |
| `generic.txt` | MMLU-Pro + GPQA (hidden 96문항, 가중치 0.25) | 578바이트 |

**이 폴더가 원본이다.** `docs/resource/example_task/prompts/`의 같은 파일은 로컬 하네스
(`compose.py`)의 기본 경로이고, `tools/validate_template.py`가 두 벌이 어긋나면 실패한다.

## 왜 이렇게 짧은가

세 파일은 **플래너에게 보내는 지시서**이지 풀이 지침이 아니다. 풀이 지침은 전부
`agent_prompts/coder.txt`·`solver.txt`로 옮겼다.

이유는 비용이다. 스쿼드 런타임은 요청 전문을 플래너에게 주고, 플래너가 `create_task`로 만든
`description`만 워커가 본다. 그래서 one-shot 본문에 적힌 글자는 **세 번 청구된다** — 플래너가
읽고(input), 플래너가 description으로 다시 뱉고(output), 워커가 읽는다(input). 반면
systemPrompt에 적힌 글자는 그 에이전트가 호출될 때 **한 번** 청구된다.

초안은 세 파일에 풀이 지침을 그대로 뒀는데, 실제로 재보니 systemPrompt와 겹치는 분량이
coding 6,140자 / math 3,016자 / generic 2,698자였다. 문항 수를 곱하면 **약 398,000토큰**,
전체 입력 추정치의 4분의 1이다. 같은 문장을 두 군데 두고 세 번 낸 셈이다.

## `--- ITEM ---` 줄

```
PLANNER: <라우팅 + 복사 규칙>          ← 플래너용. 복사되지 않는다
--- ITEM ---                          ← 경계
{{TASK}}                              ← 문항. 이 아래만 복사된다
                                      ← 서버가 빈 줄 하나
=== REQUIRED OUTPUT ===               ← 서버가 붙이는 형식 계약. 복사된다
```

Router systemPrompt는 "`--- ITEM ---` 아래를 그대로 복사하라"고만 말한다. 경계를 문자열
하나로 만든 이유가 있다.

**초안은 "`## Repository context` 위쪽을 전부 복사하라"였고, 그건 버그였다.** 그 문자열이
초안 `coding.txt`의 설명문 안에도 있어서, 합성된 coding 요청에서 **232바이트 지점과 8,792바이트
지점, 두 번** 나왔다. 규칙을 곧이곧대로 따르는 플래너는 232자만 복사하고 문항을 통째로
버린다. 가중치 0.5짜리 트랙이 전멸한다. 같은 충돌이 `## How your solution is run`에도 있었다
(LiveCodeBench 요청에서 5,536 / 7,899 두 곳, 게다가 앞쪽 것은 정반대인 두 실행 방식을 **둘 다**
설명한다).

지금은 세 트랙 합성 요청 전부에서 `--- ITEM ---`이 **정확히 한 번** 나온다. 검사기가 개수와
`{{TASK}}`와의 순서를 확인한다.

## coding만 다른 것

repository-context가 붙은 문항은 65,060바이트(중앙값)라 복사가 안 된다. `coding.txt`의
PLANNER 문단이 잘라 담는 순서를 지정한다.

1. **REQUIRED OUTPUT 블록 먼저.** 요청에서는 맨 뒤지만 복사에서는 맨 앞이다. 예산이 모자랄 때
   잘려나가면 안 되는 유일한 부분이기 때문이다 — 계약을 잃으면 맞는 패치도 추출이 안 된다.
2. 이슈 본문 전체 (500~4,000자).
3. 남는 예산만큼 발췌를 통째로. 순위는 이슈가 직접 지목한 path → traceback의 path →
   이슈가 부르는 함수·클래스를 정의하는 발췌 → 그걸 호출하는 발췌.

발췌 하나가 최대 12,500자라 32,000자 예산에 실질 2개다. 발췌 **안**은 절대 자르지 않는다 —
SEARCH가 바이트 일치해야 하고 워커에게는 이 붙여넣기가 유일한 출처다.

## 되뱉기 안전성

모델이 지시문을 응답에 흘리면 그 안의 예시가 답으로 추출될 수 있다. **v1의 스쿼드
systemPrompt 다섯 개가 전부 여기에 걸렸다** — `grade.py`의 추출 함수를 그대로 먹이면
`letter=C`, `boxed=204800`이 나왔다.

지금 여섯 텍스트(one-shot 3 + systemPrompt 3)는 전부 아무것도 추출되지 않는다. 규칙 셋:

1. **`ANSWER:` + 한 글자로 끝나는 줄을 쓰지 않는다.** `LETTER_RE`는 줄 전체에 앵커돼 있어
   `ANSWER: C (isothermal work)`나 `**ANSWER: C**`는 안전하고 벌거벗은 `ANSWER: C`만 위험하다.
2. **`FINAL ANSWER:` 바로 뒤에 `\boxed{`를 붙이지 않는다.** `BOXED_RE`는 줄 앵커가 없어
   문장 한가운데서도 걸린다. 실측: `FINAL ANSWER: \boxed{<value>}`는 `<value>`를 뱉고,
   사이에 단어 하나만 끼우면 `None`이 된다. 그래서 형식은 **말로 설명하고** 리터럴은 서버가
   붙이는 REQUIRED OUTPUT 블록에 맡긴다.
3. **패치 바깥 마커 두 개를 쓰지 않는다.** `extract_patch`는 `rindex`로 마지막
   `PATCH START`를 찾는다. 프롬프트에 마커가 있으면 모델이 제대로 된 패치를 쓴 **뒤에**
   지시문을 흘리는 순간 그쪽이 채점 대상이 된다. 들여쓰기로 무력화해도 0블록 = 0점이라
   결과가 같다. 아예 안 쓰는 것이 유일하게 안전하다.

`tools/validate_template.py`가 세 추출 함수를 여섯 텍스트에 직접 돌려서 강제한다.

## 고칠 때

```bash
python3 ../tools/validate_template.py ../squad-template.json
```

`{{TASK}}` 개수·위치, `--- ITEM ---` 개수와 순서, `PLANNER:` 줄이 실제 존재하는 에이전트를
가리키는지, 세 채점기가 아무것도 추출하지 못하는지, 하네스 사본과 동기인지를 검사한다.
