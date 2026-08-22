# 03. API로 스쿼드에 태스크 자동 주입하기

`example_task/`의 121문항을 AI:GO 스쿼드에 **HTTP API 호출로** 자동 투입할 수 있는지 조사한 결과다.
조사 시각 2026-08-22, AI:GO(Backend.AI GO) 1.12.1, macOS 데스크톱 앱.

---

## 결론

**가능하다. 코드를 새로 만들 필요도 없다. 다만 지금은 스위치 하나가 꺼져 있어서 연결이 거부된다.**

AI:GO는 Management API(관리 API)라는 REST 서버를 내장하고 있고, 스쿼드 실행·승인·이력·로그·예산·이벤트 스트림이 전부 그 위에 엔드포인트로 노출돼 있다.
`aigo-cli`도 결국 이 REST를 때리는 얇은 클라이언트다 — 즉 CLI로 되는 일은 전부 curl로도 된다.

막고 있는 것은 하나뿐이다.

```
~/Library/Application Support/ai.backend.go/settings.json
"managementApi": { "enabled": false, "port": 8001, "bindHost": "127.0.0.1", "authEnabled": false, ... }
```

`enabled`가 `false`라서 8001 포트가 열려 있지 않다. 실측으로 확인한 증상:

```
$ aigo-cli -o json squad list
{"code":8,"error":"Failed to connect to http://127.0.0.1:8001: error sending request for url (http://127.0.0.1:8001/api/v1/squads)"}
```

이 한 줄이 두 가지를 동시에 증명한다. ① REST 베이스 경로는 `/api/v1`이다. ② 서버가 안 떠 있다.

---

## 1. 켜는 법

앱에서 **API > 일반 > 관리 API 서버** 를 켠다. (매뉴얼 `api-server/external-access` 문서가 이 위치를 명시한다.
같은 화면의 Continuum Router TCP 서버(39080)와는 다른 항목이다. Router는 OpenAI 호환 추론용, Management API는 앱 제어용이다.)

다른 기기에서 붙일 게 아니면 **외부 액세스 허용은 끈 채로 둔다.** 기본 바인드가 `127.0.0.1`이라 이 상태로도 로컬 자동화에는 충분하다.

켠 뒤 확인:

```bash
curl -s http://127.0.0.1:8001/api/v1/health
aigo-cli -o json squad list
```

`aigo-cli`는 앱이 시작할 때 기록하는 discovery 파일(`~/Library/Application Support/ai.backend.go/mgmt-api.json`)을 읽어 엔드포인트를 자동으로 찾는다.
지금 그 파일이 없는 것도 서버가 안 떠 있기 때문이다. 켜면 생긴다.

인증은 현재 `authEnabled: false`다. 로컬에서는 헤더 없이 호출된다.
켤 경우 클라이언트는 `X-API-Key` 또는 `Authorization: Bearer`를 쓴다.

---

## 2. 스쿼드 관련 엔드포인트 전량

`aigo-server` 바이너리의 라우트 테이블에서 그대로 뽑은 목록이다. 모두 앞에 `/api/v1`이 붙는다.

### 실행

| 메서드 | 경로 | 용도 |
|---|---|---|
| POST | `/squads/{id}/execute` | **요청 제출.** 플래너가 플랜을 만들고 실행이 시작된다 |
| POST | `/squads/{id}/executions/{eid}/approve` | 플랜 승인 |
| POST | `/squads/{id}/executions/{eid}/reject` | 플랜 거부(피드백 첨부 가능) |
| GET | `/squads/{id}/executions/{eid}` | 실행 상태 조회 (폴링 대상) |
| POST | `/squads/{id}/emergency-stop` | 해당 스쿼드의 모든 실행 강제 중단 |

`execute`의 요청 본문은 두 필드다. CLI 바이너리의 문자열 테이블에서 `workspacePath` · `request` · `autoApprove` · `clear` · `turnBudget` 순으로 인접해 있는 것을 확인했다.

```json
{ "request": "<judge가 보내는 요청 바이트 그대로>", "autoApprove": true }
```

`autoApprove: true`면 승인 대기 단계를 건너뛴다. 배치 자동화에서는 필수다 — 안 주면 사람이 승인 버튼을 누를 때까지 실행이 멈춘다.

### 관측 · 트레이스 (시각화 30점의 원천)

| 메서드 | 경로 | 용도 |
|---|---|---|
| GET | `/squads/{id}/events` | **SSE 이벤트 스트림.** 실시간 추적 |
| GET | `/squads/{id}/history` | 실행 이력 목록 |
| GET | `/squads/{id}/history/{eid}` | 실행 하나의 상세 |
| GET | `/squads/{id}/history/{eid}/logs` | 실행 로그 |
| GET | `/squads/{id}/history/{eid}/report` | 마크다운 리포트 생성 |
| GET | `/squads/{id}/activity-log` | 활동 로그 |
| GET | `/squads/{id}/analytics` | 토큰·비용·처리량 집계 |
| GET | `/squads/{id}/tasks`, `/tasks/graph`, `/tasks/{task_id}` | 태스크와 의존성 그래프 |
| GET | `/sessions/events` | 전역 세션 이벤트 SSE (CLI 명령 없음, 직접 구독) |

`extract.py`가 지금 워크스페이스의 `logs/history.json`과 `logs/events.jsonl`을 직접 읽는데, 위 엔드포인트가 같은 내용을 준다.
파일을 읽는 쪽이 의존성이 적으므로 굳이 바꿀 이유는 없다. 다만 **시각화 산출물**은 SSE(`/squads/{id}/events`)를 쓰면 실시간으로 만들 수 있다.

### 예산 (토큰 효율 30점의 레버)

| 메서드 | 경로 |
|---|---|
| GET/PUT | `/squads/{id}/budget` |
| GET | `/squads/{id}/budget/usage` |

프롬프트 변종마다 예산을 바꿔가며 스윕하는 것을 스크립트로 돌릴 수 있다는 뜻이다.

### 스쿼드 · 템플릿 관리

| 메서드 | 경로 | 용도 |
|---|---|---|
| GET/POST | `/squads` | 목록 / 생성 (`CreateSquadRequest`, 최소 `name` + `workspacePath`) |
| GET/PUT/DELETE | `/squads/{id}` | 조회 / 수정 / 삭제 |
| POST | `/squads/{id}/save-as-template` | **템플릿으로 저장** |
| GET | `/squad-templates/{id}/export` | **템플릿 JSON 내보내기 — 제출물이 이것이다** |
| POST | `/squad-templates/import` | 템플릿 가져오기 |
| POST | `/squads/{id}/workspace/init` | 워크스페이스 초기화 |
| GET | `/squads/{id}/workspace/files`, `/files/content`, `/search` | 워크스페이스 파일 |

제출용 Squad Template JSON을 GUI의 Export 버튼 대신 API로 뽑을 수 있다.
**스쿼드 정의를 파일로 버전 관리하고 → import → 실행 → 채점까지 전부 무인화할 수 있다는 뜻이다.**

### 에이전트 단위

| 메서드 | 경로 |
|---|---|
| POST | `/squads/{id}/agents/{agent_id}/message` |
| GET | `/squads/{id}/agents/{agent_id}/response`, `/status`, `/conversation` |
| PUT | `/squads/{id}/agents/bulk-update-model` |

`bulk-update-model`은 스쿼드 전체 에이전트의 모델을 한 번에 바꾼다. 모델 비교 실험이 한 줄이 된다.

---

## 3. 바로 쓰는 형태

### curl 한 문항

```bash
SQUAD=36e6827e-4143-43fc-8815-329b243944bf
BASE=http://127.0.0.1:8001/api/v1

REQ=$(python3 tools/compose.py math-visible-0001)

EID=$(curl -s -X POST "$BASE/squads/$SQUAD/execute" \
  -H 'Content-Type: application/json' \
  --data "$(jq -n --arg r "$REQ" '{request:$r, autoApprove:true}')" \
  | jq -r '.executionId // .execution_id')

# 종료까지 폴링
while :; do
  ST=$(curl -s "$BASE/squads/$SQUAD/executions/$EID" | jq -r '.status')
  case "$ST" in completed|failed|cancelled) break;; esac
  sleep 2
done

curl -s "$BASE/squads/$SQUAD/history/$EID" > run.json
```

### 이미 있는 배치 러너

`tools/run_batch.py`가 이 일을 CLI 경유로 이미 한다.

```bash
python3 tools/run_batch.py <SQUAD_ID> <WORKSPACE_DIR> --tracks math --limit 10 --out run01.jsonl
python3 tools/grade.py run01.jsonl --report run01.report.jsonl
```

내부적으로 `aigo-cli squad execute <id> <request> --auto-approve --wait`를 부르는데,
이건 위의 `POST /squads/{id}/execute` + 2초 간격 폴링과 **같은 동작**이다. `--wait`가 그 폴링이다.

**즉 지금 당장 필요한 것은 새 코드가 아니라 Management API 토글 하나다.**
그걸 켜면 `run_batch.py`가 그대로 돈다. REST를 직접 쓸지 CLI를 쓸지는 취향 문제이며, 아래 기준으로 고르면 된다.

| | CLI (`aigo-cli`) | REST 직접 |
|---|---|---|
| 코드량 | 이미 있음 | 새로 씀 |
| 프로세스 비용 | 문항마다 프로세스 기동 | 없음 (연결 재사용) |
| 동시 실행 | 가능하지만 관리가 번거로움 | 쉬움 |
| 실시간 트레이스 | 불가 (SSE 명령 없음) | **가능** (`/squads/{id}/events`) |
| 에러 진단 | stdout/stderr 파싱 | HTTP 상태 코드 |

**권고** — 채점 루프는 `run_batch.py`(CLI)를 그대로 쓰고, 시각화 산출물만 REST의 SSE를 붙인다.
문항 121개는 프로세스 기동 비용이 문제 될 규모가 아니고, 이미 검증된 코드를 갈아엎을 이유가 없다.

---

## 4. 자동화하기 전에 알아야 할 것

**플래너를 거친다.** `execute`는 요청을 플래너 에이전트에게 넘기고, 플래너가 태스크로 쪼개고, 웨이브 단위로 실행한다.
벤치마크 한 문항은 "질문 하나 → 답 하나"인데 그 사이에 플래닝 LLM 호출이 한 번 더 끼는 구조다.
**토큰 효율 30점이 여기서 새어 나간다.** 플래너 프롬프트를 짧게 만들거나, 단일 태스크로 떨어지도록 유도하는 것이 스쿼드 설계의 실제 과제다.

**답은 실행 요약이 아니라 태스크 본문에 있다.** `**Execution complete** — N task(s) processed in M wave(s).` 줄은 런타임이 만든 상태 문구이고 judge는 그것을 답으로 인정하지 않는다. `01-요청-합성-규칙.md` 3절 참고.

**평가 중 스쿼드는 도구가 없다.** 로컬 실험에서 도구를 켜 두면 실제 평가와 다른 조건에서 측정하게 된다. 실험 스쿼드의 도구 설정을 평가 조건에 맞춰라.

**실패를 오답으로 착각하지 마라.** AI:GO는 연결 실패를 "실행 완료, 전 태스크 실패"로 보고한다. `run_batch.py`가 status를 그대로 기록하는 이유가 이것이다. 재실행 여부는 status를 보고 판단한다.

**과금.** 로컬 모델(현재 스쿼드는 `unsloth/gpt-oss-20b`)로 도는 동안은 팀 사용량에 잡히지 않는다.
주최 측 개발용 키로 공유 서빙 스택을 쓰면 test run으로 집계되며 기준 단가의 1/5로 과금된다. 제출 실행은 전액이다.

**보안.** 외부 액세스를 켜면 8001이 `0.0.0.0`에 바인드된다. 인증이 꺼진 채로 그러면 같은 네트워크의 누구나 스쿼드를 조작할 수 있다.
로컬 자동화만 할 거면 외부 액세스는 끈 채로 둔다.

---

## 5. 검증 상태

**실측으로 확인한 것**

- 라우트 목록 — `aigo-server` 바이너리의 라우트 문자열 테이블에서 추출
- 베이스 경로 `/api/v1` — `aigo-cli`가 뱉은 연결 실패 URL
- 요청 본문 필드 `request` / `autoApprove` — `aigo-cli` 바이너리 문자열 테이블
- `managementApi.enabled: false`, 포트 8001, `bindHost: 127.0.0.1`, `authEnabled: false` — `settings.json`
- CLI 하위 명령과 플래그 — `aigo-cli squad --help` 및 각 하위 명령
- 앱은 실행 중(PID 16170)이고 8001·39080 모두 리슨하지 않음 — `lsof`

**문서에서 가져온 것**

- 토글 위치 "API > 일반 > 관리 API 서버" — `go.backend.ai/ko/manual/api-server/external-access`
- 헤드리스 서버, 인증 헤더, discovery 파일 경로 — `advanced/headless-mode`, `advanced/cli-reference`
- 실행 라이프사이클과 웨이브 — `squad/execution`

**아직 확인 못 한 것**

- 실제 REST 왕복. Management API가 꺼져 있어 살아 있는 호출을 한 번도 못 했다.
- `execute` 응답 본문의 정확한 스키마. `run_batch.py`가 `executionId`와 `execution_id` 양쪽을 받도록 짜여 있으므로 둘 중 하나다.

이 둘은 토글을 켜는 즉시 5분 안에 확인된다.
