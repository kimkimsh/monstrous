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
2. **스쿼드·에이전트 선택** — 에이전트의 모델이 옆에 표시된다.
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

## 알아둘 것

**문항마다 세션을 새로 판다.** 재사용하면 앞 문항의 질문과 답이 다음 프롬프트에 남는다.
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
| 실서버 3문항 | 3/3 PASS, 2,511 토큰, 30.3s |
| 터미널 `grade.py` 대조 | 같은 결과 (3/3, accuracy 1.0000) |
