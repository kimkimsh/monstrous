# auto_test — AI:GO 스쿼드 자동 테스트

연습 문항을 스쿼드에 넣고, 토큰과 정확도를 한 화면에서 본다.

## 실행

```bash
cd auto_test
uv sync                    # 처음 한 번
uv run python app.py
```

`BACKEND_AI_GO_ENDPOINT` / `BACKEND_AI_GO_TOKEN` 환경 변수가 있으면 접속 칸에 미리 채워진다.

### 먼저 헤드리스 서버가 떠 있어야 한다

CLI도 이 GUI도 Management API의 클라이언트일 뿐이다. 서버가 없으면 아무것도 안 된다.
**앱 번들 안의 `aigo-server`는 프로세스를 못 띄우므로 릴리스에서 받은 것을 써야 한다.**
자세한 건 `docs/resource/example_task/04-CLI-운영.md` 4절.

```bash
osascript -e 'tell application "Backend.AI GO" to quit'
AIGO_MASTER_KEY=sk-master-... ./aigo-server \
  --data-dir "$HOME/Library/Application Support/ai.backend.go" \
  --port 8001 --models-dir "$HOME/backend_ai"
aigo loaded load "unsloth/gpt-oss-20b-gguf/gpt-oss-20b-q8_0.gguf" -c 32768 --gpu-layers=-1 --tool-calling --alias "unsloth/gpt-oss-20b"
```

## 쓰는 순서

1. **연결** — endpoint와 token을 넣고 누른다. 스쿼드 목록이 채워진다.
2. **스쿼드 선택** — 에이전트의 모델이 옆에 표시된다.
   **실행 방식**은 기본이 `스쿼드 전체 (discussion room)`다. 단일 에이전트는 프롬프트를 빠르게
   찔러볼 때만 쓰고, 그건 스쿼드 테스트가 아니다.
3. **문항 선택** — 트랙 체크박스로 걸러내고, id로 검색하고, 체크박스로 고른다. 여러 개 선택된다.
4. **검사** — LLM을 부르지 않는다. 서버 상태, 모델 로드 여부, 샘플 무결성, 선택 항목 중 채점 불가 개수를 확인한다. 무료라 원하는 만큼 눌러도 된다.
5. **실행** — 선택한 것을 순차로 돌린다. 행마다 결과·토큰·시간이 갱신된다.
6. **중지** — 진행 중인 문항이 끝나면 멈춘다. 이미 나온 결과는 남는다.

행을 클릭하면 아래에 프롬프트 원문, 모델 출력, 채점 상세가 뜬다.

결과는 실행 중에 `runs/<타임스탬프>.jsonl`로 한 줄씩 쌓인다. 창이 죽어도 남고,
터미널 채점기가 그대로 먹는 형식이다.

```bash
uv run python ../docs/resource/example_task/tools/grade.py runs/20260822-222846.jsonl
```

## 화면의 숫자가 뜻하는 것

```
채점 3/3 · 정확도 100.0% · 채점 불가 0 · 실행 실패 0 · 토큰 2,511 · 30.3s
```

**정확도와 토큰은 분모가 다르다.**

| 표시 | 들어가는 것 | 정확도 분모 |
|---|---|---|
| PASS | 정답 | 포함 |
| FAIL | 오답 | 포함 |
| FAIL (형식) | `FINAL ANSWER: \boxed{}` 같은 필수 형식을 못 맞춤 | **포함** |
| 채점 불가 | swebench — 로컬에 Docker 채점기가 없다 | 제외 |
| 실행 실패 | CLI 오류, 타임아웃, 서버 장애 | 제외 |
| 토큰 | 시도한 모든 문항 | — |

형식 실패를 분모에 넣는 건 포털이 그걸 0점으로 세기 때문이다. 형식을 못 맞추는 건 실제 실점이다.
실행 실패를 빼는 건 인프라 장애가 오답이 아니기 때문이다. 섞으면 서버가 흔들린 날의 점수가 프롬프트 품질처럼 보인다.

## 왜 discussion room 인가

judge가 쓰는 경로는 `squad execute` — 플래너가 요청을 태스크로 쪼개고 웨이브로 실행하는 쪽이다.
**그 경로는 헤드리스에서 안 돈다.** 실행은 접수되는데 플랜이 `created`에서 멈추고 태스크가 0개,
라우터 요청 수가 하나도 안 늘어난다. 플래너가 LLM을 아예 안 부른다.
헤드리스 부팅 로그에 `Squad event emitter initialized`가 0회, 데스크톱은 13회.

`squad discussion`은 헤드리스에서 돈다. 그래서 이게 **에이전트 전원이 참여하는 유일한 경로**다.

두 경로는 같은 기능의 두 모드가 아니라 다른 기계다.

| | 플래너 (`execute`, judge가 쓰는 것) | 사회자 (`discussion`, 우리가 쓸 수 있는 것) |
|---|---|---|
| 요청 | 태스크로 분해, 플래너가 문장을 다시 씀 | 그대로 던짐 |
| 일하는 사람 | 태스크당 배정된 1명 | 매 턴 전원 중 1명 |
| 끝나는 조건 | 모든 태스크 완료 | 합의 / 턴 예산 / 유휴 타임아웃 |
| 산출물 | 태스크별 결과 + 집계 | 대화록 + 합성한 결론 |
| 같은 문항 토큰 | 2,072 | 10,425 |

**그래서 여기서 나온 토큰 숫자를 제출 점수 예측에 그대로 쓰면 안 된다.** 스쿼드 설계가 트랙에
맞는지, 형식을 지키는지를 보는 용도다.

### 사회자 에이전트를 따로 만들 필요는 없다

`moderator`라는 단어는 서버 바이너리 전체에 한 번 나오고, 그것도 첫 발언자에게 주는 프롬프트
안의 조건절이다 — `— if your role is the moderator/coordinator — set a short agenda`.
방 객체에도 `moderatorAgentId` 같은 필드가 없다. 발언 순서는 전략이 정한다.

| 전략 | 다음 발언자 | LLM 호출 |
|---|---|---|
| **roundRobin** (기본) | `participants[turns_taken % count]` | 0 |
| brainstorm (레거시) | 발언 수가 가장 적은 에이전트 | 0 |
| moderated | 사회자 전략 + 3턴마다 합의 게이트 | 있음 |
| autonomous | 에이전트마다 "지금 말할까?" 자체 판정 | 턴당 참여자 수 |

roundRobin을 기본으로 둔 이유는 두 가지다. 발언자 선정에 토큰을 안 쓰고, 결정론적이라
점수가 변했을 때 프롬프트 때문인지 발언 순서가 달라져서인지 구분된다.

**첫 턴은 항상 첫 참여자가 연다.** `autonomous`조차 첫 턴은 게이트를 건너뛴다. 그래서
`participants` 배열의 첫 번째가 누구냐가 결과에 영향을 준다.

## 알아둘 것

**요청은 topic이 아니라 메시지로 넣는다.** topic 상한이 1,024바이트인데 121개 중 39개가
그걸 넘는다. 메시지 상한은 65,536바이트고 8개(전부 swebench)가 넘어서 줄 경계로 분할된다.

**채점 텍스트에서 요청은 제외한다.** 요청 원문에 `FINAL ANSWER: \boxed{<answer>}` 문자열이
그대로 들어 있어서, 포함시키면 질문에서 답을 뽑아 채점하게 된다. `author.type`이 `user`인
메시지를 걸러낸다.

**결론 합성 토큰은 따로 더한다.** `discussion analytics`의 `totalTokenUsage`는 에이전트 턴만
센다. 한 방에서 실측: analytics 6,315/3,712 인데 결론 합성이 2,168/978을 더 썼다.

**결론이 JSON 문자열로 오는 경우가 있다.** 사회자 LLM이 JSON으로 답하면 서버 파싱이 실패해서
`summary`에 원문이 통째로 들어가고 `keyPoints`/`decisions`/`actionItems`가 빈 배열로 저장된다.
그 경우 문자열을 다시 파싱해서 펼친다.

**단일 에이전트 모드에서는 문항마다 세션을 새로 판다.** 재사용하면 앞 문항의 질문과 답이 다음 프롬프트에 남는다.
math 3문항 실측으로 세션 공유 7,635 토큰 대 세션 격리 2,940 토큰. 토큰만 부푸는 게 아니라 앞 답이 새서 연습 점수가 무의미해진다.

**한 번도 안 쓴 에이전트는 세션 생성이 실패한다.** `squad session new`는 기존 세션을 회전시키는 명령이라,
세션이 없는 에이전트에서는 exit 7로 죽는다. 실행 시작 전에 자동으로 `session start`를 한 번 부르고,
그것도 실패하면 121번 실패하는 대신 시작 자체를 안 한다.

**livecodebench `functional` 문항의 FAIL은 믿지 마라.** 로컬 채점기가 파일을 프로그램으로 실행해서
stdout을 비교하는데, functional 케이스는 호출 인자와 반환값이다. 답이 맞아도 FAIL로 나온다.
해당 문항은 종류 칸에 `functional`로 표시되고, 검사 결과에도 경고가 뜬다.

**swebench 13문항은 정답 판정이 안 된다.** 실행은 되고 패치와 토큰은 기록되지만, 채점에는
저장소와 test_patch와 컨테이너가 필요하다. 종류 칸에 `채점 불가`로 표시되고 정확도 분모에서 빠진다.

**원격 모델로 바꾸는 UI는 없다.** 과금 대상이라 실수로 누를 수 있는 자리에 두지 않았다.
바꾸려면 AI:GO 앱이나 CLI에서 직접 해야 한다.

## 새 테스트 샘플 추가

규격과 손으로 쓰는 법은 `SAMPLE_SPEC.md`. 요약하면 `test_sample/<track>/<id>.json` 하나를 넣으면 끝이다.
검증은:

```bash
uv run python tools/build_samples.py --check
```

example_task에서 전량 다시 만들려면 `--check` 없이 실행한다.

## 구성

```
app.py            창 전체 (PySide6)
core/samples.py   샘플 로드·검증
core/runner.py    aigo CLI 래퍼 (세션 격리, 취소 가능)
core/grading.py   grade.py 어댑터 — 채점 로직은 한 곳에만 있다
core/session.py   실행 루프 + 집계
tools/            샘플 생성기, runner 스모크 테스트
tests/            31개
```

채점은 `docs/resource/example_task/tools/grade.py`를 그대로 부른다. 채점기가 둘이면 서로 다른 답을 내고,
어느 쪽이 맞는지 아무도 모르게 된다.

```bash
uv run python -m unittest discover tests
```

## 검증한 것

| | 결과 |
|---|---|
| 샘플 121개 (coding 20 / math 59 / generic 42) | sha256 전량 대조, 로드 실패 0 |
| `gradable: false` | 정확히 13개, 전부 swebench |
| 단위 테스트 | 31개 통과 |
| 단일 에이전트 3문항 | 3/3 PASS, 2,511 토큰, 30.3s |
| 터미널 `grade.py` 대조 | 같은 결과 (3/3, accuracy 1.0000) |
| **스쿼드 전체 2문항** | 1 PASS / 1 FAIL(형식), 3턴씩, 16,036 토큰, 209s |
| 발언 순서 (roundRobin) | 두 문항 모두 `bt1u2c5 → 3orflu2 → ztcvzv5` — 결정론적 |
