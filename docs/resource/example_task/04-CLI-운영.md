# 04. `aigo` CLI 운영 가이드

AI:GO를 터미널에서 조종하는 방법. 설치, 연결 구조, 스쿼드 명령 전량, 그리고 **지금 이 버전에서 막히는 지점**까지 정리한다.

조사·실측 시각 2026-08-22 20:10~20:30 KST · AI:GO 1.12.1 · macOS 26.5.1 · Apple M5 24GB

---

## 0. 먼저 알아야 할 구조

CLI는 **클라이언트일 뿐이다.** 자체적으로 아무것도 실행하지 않고, Management API(관리 API)라는 REST 서버에 HTTP 요청을 보낸다.

```
aigo (CLI)  ──HTTP──▶  Management API :8001  ──▶  런타임(스쿼드·모델풀·라우터)
```

그래서 **Management API가 떠 있지 않으면 CLI는 아무것도 못 한다.** 실제로 안 떠 있으면 이렇게 나온다.

```
$ aigo squad list
Error: Failed to connect to http://127.0.0.1:8001: error sending request for url (http://127.0.0.1:8001/api/v1/squads)
```

Management API를 띄우는 주체는 둘 중 하나다.

| 주체 | Management API | 로컬 모델 서빙 | GUI |
|---|---|---|---|
| 데스크톱 앱 (`backend-ai-go`) | **안 뜬다** (1.12.1 확인) | 된다 | 있다 |
| 헤드리스 서버 — 앱 번들 안의 `aigo-server` | 뜬다 | **안 된다** (프로세스 spawn 불가) | 웹 UI |
| 헤드리스 서버 — **릴리스 zip의 `aigo-server`** | 뜬다 | **된다** | 웹 UI |

근거는 4절에 있다. **세 번째 줄이 정답이다 — 앱 번들 안의 바이너리가 아니라 릴리스에서 받은 `aigo-server`를 써야 한다.**

---

## 1. 설치

릴리스에서 받는다. macOS Apple Silicon 기준:

```bash
curl -sL -o aigo-cli-macos-aarch64.zip \
  https://github.com/lablup/backend.ai-go-releases/releases/download/v1.12.1/aigo-cli-macos-aarch64.zip
curl -sL -o SHA256SUMS.txt \
  https://github.com/lablup/backend.ai-go-releases/releases/download/v1.12.1/SHA256SUMS.txt
shasum -a 256 -c <(grep aigo-cli-macos SHA256SUMS.txt)   # f311986e...42bc

unzip -q aigo-cli-macos-aarch64.zip     # 나오는 실행 파일 이름은 'aigo'
xattr -c aigo                            # 다운로드 격리 속성 제거
install -m 755 aigo ~/.local/bin/aigo
aigo --version                           # backend-ai-go 1.12.1
```

플랫폼별 자산 이름:

| 플랫폼 | 자산 |
|---|---|
| macOS Apple Silicon | `aigo-cli-macos-aarch64.zip` |
| Linux x86_64 | `aigo-cli-linux-x86_64.tar.gz` |
| Linux aarch64 | `aigo-cli-linux-aarch64.tar.gz` |
| Windows x64 | `aigo-cli-windows-x86_64.zip` |

앱 번들 안에도 같은 버전이 들어 있다: `/Applications/Backend.AI GO.app/Contents/MacOS/aigo-cli`.
바이너리 해시는 다르지만 `--version`은 같은 1.12.1이고 동작도 같다. 둘 중 아무거나 써도 된다.

---

## 2. 연결 설정

### 엔드포인트 결정 순서

1. `--endpoint` / `-e` 플래그, 또는 `BACKEND_AI_GO_ENDPOINT` 환경 변수
2. 설정 파일 값 (`aigo config set endpoint ...`)
3. 자동 발견 파일
4. 기본 폴백 `http://127.0.0.1:8001`

자동 발견 파일은 Management API 서버가 뜰 때 직접 쓴다. macOS 경로는
`~/Library/Application Support/ai.backend.go/mgmt-api.json`이고, 내용은 이렇다.

```json
{
  "endpoint": "http://127.0.0.1:8001",
  "pid": 56982,
  "instance_id": "e9a21f7b",
  "started_at": "2026-08-22T11:16:11.694995+00:00",
  "version": "1.12.1",
  "socket_path": ".../sockets/mgmt-api-e9a21f7b.sock"
}
```

**이 파일이 없으면 서버가 안 떠 있는 것이다.** CLI는 붙기 전에 PID 생존과 health를 확인하므로, 죽은 인스턴스가 남긴 낡은 파일은 조용히 무시된다.

CLI 설정 파일은 `~/.backend-ai-go/cli-config.yaml`에 있고 `aigo config list`로 본다.

### 전역 옵션

| 옵션 | 축약 | 환경 변수 |
|---|---|---|
| `--endpoint` | `-e` | `BACKEND_AI_GO_ENDPOINT` |
| `--token` | `-t` | `BACKEND_AI_GO_TOKEN` |
| `--output` | `-o` | `BACKEND_AI_GO_OUTPUT` (`console`/`json`/`yaml`) |
| `--quiet` | `-q` | |
| `--verbose` | `-v` | |
| `--no-verify-ssl` | | |

**자동화에서는 `-o json`을 항상 붙인다.** 기본 `console` 출력은 표 그림이라 파싱할 수 없다.

### 인증

헤드리스 서버는 기본값이 `require_api_key = true`다. 키 없이 부르면 이렇게 나온다.

```json
{"error":{"code":"UNAUTHORIZED","message":"Invalid or missing API key authentication"}}
```

**`--generate-admin-key`는 쓰지 마라.** 키를 출력은 하는데 `key_metadata.json`에 저장하지 않아서(`"key_ids": []`) 곧바로 거부된다. 실측으로 확인했다.

대신 서버를 띄울 때 마스터 키를 준다.

```bash
AIGO_MASTER_KEY=sk-master-... aigo-server ...
```

클라이언트는 `X-API-Key` 또는 `Authorization: Bearer` 둘 다 받는다. CLI는 `-t` 또는 `BACKEND_AI_GO_TOKEN`으로 넘긴다.

---

## 3. 헤드리스 서버 띄우기

데스크톱 앱을 **먼저 종료해야 한다.** 같은 데이터 디렉터리를 두 프로세스가 동시에 관리하면 `router_config.yaml`과 `settings.json`을 서로 덮어쓴다. 실제로 그렇게 만들어 봤고, 라우터 설정이 placeholder로 덮여서 모델 목록이 비었다.

```bash
osascript -e 'tell application "Backend.AI GO" to quit'

DD="$HOME/Library/Application Support/ai.backend.go"
AIGO_MASTER_KEY=sk-master-... \
./aigo-server \                      # ← 릴리스 zip에서 받은 것. 앱 번들 안의 것은 안 된다 (4절 (2))
  --data-dir "$DD" \
  --port 8001 \
  --models-dir "$HOME/backend_ai" \
  --pid-file /tmp/aigo-server.pid
```

`--data-dir`이 핵심이다. **빼면 헤드리스는 데스크톱과 다른 XDG 디렉터리를 쓰기 때문에 만들어 둔 스쿼드가 안 보인다.**

주요 플래그:

| 플래그 | 뜻 |
|---|---|
| `-H, --host` | 바인드 호스트 |
| `-p, --port` | Management API 포트 (기본 8001) |
| `-r, --router-port` | 라우터 포트 |
| `-D, --data-dir` | 데이터 디렉터리 ★ |
| `-m, --models-dir` / `-e, --engines-dir` | 모델·엔진 경로 |
| `--external` | `0.0.0.0` 바인드 |
| `--master-key` | 마스터 API 키 (`AIGO_MASTER_KEY`) |
| `--daemon` | 백그라운드 실행 |
| `--dry-run` / `--dump-config` | 설정만 검증 / 유효 설정 출력 (부작용 없음) |
| `--no-socket` | Unix 소켓 없이 TCP만 |

확인:

```bash
export BACKEND_AI_GO_ENDPOINT=http://127.0.0.1:8001
export BACKEND_AI_GO_TOKEN=sk-master-...
aigo system version        # Backend.AI GO 1.12.1
aigo squad list -o json    # 스쿼드가 나오면 성공
```

---

## 4. 1.12.1에서 막히는 두 지점

두 가지 다 실측이다. 추측이 아니다.

### (1) 데스크톱 앱은 Management API를 아예 안 띄운다

`settings.json`의 `managementApi.enabled`를 `true`로 바꾸고 앱을 재시작해도 8001이 열리지 않는다. 값 자체는 살아남는데(앱이 부팅 중 `Settings loaded successfully`를 12번 찍고 그 값을 그대로 다시 저장한다) 서버는 시작되지 않는다.

결정적 증거 — 앱 로그 이틀치에서 `management_api` 문자열이 **0회**다.

```
backend-ai-go.2026-08-21: 0
backend-ai-go.2026-08-22: 0
```

바이너리에는 코드가 들어 있다(`src/management_api/auth.rs`, `handlers/inference_proxy.rs`, `state.rs`, `Management API is bound to 0.0.0.0 without authentication` 경고 문자열까지). 부팅 경로가 그걸 부르지 않을 뿐이다. 환경 변수로도 못 켠다 — 바이너리의 `AIGO_*` 목록에 해당 스위치가 없다.

참고로 앱의 **API > 일반 > TCP 서버** 토글은 Management API가 아니라 Continuum Router(39080)를 켠다. 그것도 재시작하면 꺼진다. 로그에 `commands::router_settings: API server enabled - restarting router to apply` 뒤, 재기동 시 `api_server_enabled: false`로 돌아오는 게 찍힌다.

### (2) 앱 번들 안의 `aigo-server`는 프로세스를 못 띄운다 — 릴리스 바이너리를 써야 한다

`aigo-server`가 두 벌 존재하고, **둘이 다른 빌드다.**

| 위치 | 크기 | SHA-256 앞자리 | sidecar spawn |
|---|---|---|---|
| `/Applications/Backend.AI GO.app/Contents/MacOS/aigo-server` | 70.5 MB | `253edd73` | **실패** |
| 릴리스 `aigo-server-macos-aarch64.zip` 안의 `aigo-server` | 69.1 MB | `476b6570` | **성공** |

앱 번들 쪽으로 띄우면 자식 프로세스를 하나도 못 만든다.

```
WARN aigo_server: Failed to start continuum-router at boot:
     process error: Cannot spawn router without an initialized runtime

$ aigo loaded load "unsloth/gpt-oss-20b-gguf/gpt-oss-20b-q8_0.gguf" -c 32768 --gpu-layers=-1
Error: Cannot load models without an initialized runtime (status: 503)
```

같은 문구가 네 군데에 쓰인다: router, ACP server, processes, models. 전부 하나의 sidecar spawn 관문이다.
번들 바이너리는 Tauri 런타임 핸들(`AppHandle` / `runtime_handle` / `event_loop`)을 요구하는데 헤드리스에는 그게 없다.

**대조 실험으로 확정했다.** 같은 조건(빈 data-dir, 같은 포트 구성, 같은 모델 디렉터리)에서 바이너리만 바꿨다.

| 조건 | `Spawned sidecar` 로그 | `initialized runtime` 오류 |
|---|---|---|
| 릴리스 바이너리 + 새 data-dir | **1회** (`PID: 14308`) | 0회 |
| 번들 바이너리 + 새 data-dir | 0회 | **1회** |
| 번들 바이너리 + 실제 data-dir | 0회 | **1회** |

data-dir이 아니라 바이너리가 원인이다.

모델 로드가 어디까지 갔는지도 로그에 남는다. 준비는 다 끝내고 **spawn 직전에** 막힌다.

```
process::pool: Model alias: Some("unsloth/gpt-oss-20b") (user-provided: true, model_path: ...)
process::pool: Using Unix socket mode for model unsloth/gpt-oss-20b-gguf/gpt-oss-20b-q8_0.gguf
process::pool: Applying ModelConfig (saved or defaults) for model: ...
                                                    ← 여기서 503
```
헤드리스 로그에 `backend_ai_go_lib::sidecar` 타깃이 단 한 줄도 없는 것이 그 증거다. 데스크톱 로그에는 `Spawned sidecar 'continuum-router' with PID: 58584`가 찍힌다.

#### 해결

릴리스에서 헤드리스 서버를 따로 받아 그걸로 띄운다. zip 안에 `continuum-router`도 같이 들어 있다.

```bash
curl -sL -o aigo-server-macos-aarch64.zip \
  https://github.com/lablup/backend.ai-go-releases/releases/download/v1.12.1/aigo-server-macos-aarch64.zip
shasum -a 256 -c <(grep aigo-server-macos SHA256SUMS.txt)   # 0b9ab0de...68ef
unzip -q aigo-server-macos-aarch64.zip                       # aigo-server, continuum-router
xattr -c aigo-server continuum-router

osascript -e 'tell application "Backend.AI GO" to quit'      # data-dir 충돌 방지

AIGO_MASTER_KEY=sk-... ./aigo-server \
  --data-dir "$HOME/Library/Application Support/ai.backend.go" \
  --port 8001 --models-dir "$HOME/backend_ai"
```

#### 같이 걸린 함정 — Unix 소켓 경로 길이

macOS의 `sun_path`는 **104바이트**가 한계다. data-dir을 깊은 임시 경로에 두면 라우터가 소켓 바인드에 실패하고 exit 1로 죽는다.

```
ERROR continuum_router::infrastructure::socket::server: ...
WARN  continuum_router: Server error: Configuration error: Failed to bind to any configured address
WARN  router::manager: continuum-router process terminated with exit code 1
```

- 스크래치패드 경로 예시: 165바이트 → 실패
- 실제 data-dir: 96바이트 → 통과

data-dir은 짧은 경로에 둔다.

## 5. 스쿼드 명령 전량

`aigo squad --help`와 하위 명령을 3단계까지 전부 덤프한 것이 `reference/aigo-cli-1.12.1-help.txt`에 있다(478개 명령 노드, 5,739줄). 여기서는 이 트랙에 쓰는 것만 추린다.

### 실행

```bash
aigo squad list
aigo squad show <SQUAD_ID>
aigo squad execute [--auto-approve] [--wait] <SQUAD_ID> <REQUEST>
aigo squad approve <SQUAD_ID> <EXECUTION_ID>
aigo squad reject --feedback <TEXT> <SQUAD_ID> <EXECUTION_ID>
aigo squad execution <SQUAD_ID> <EXECUTION_ID>
aigo squad cancel <SQUAD_ID> <EXECUTION_ID>
aigo squad emergency-stop <SQUAD_ID>
```

`--auto-approve`가 없으면 사람이 승인할 때까지 멈춘다. **배치 자동화에는 필수다.**
`--wait`는 2초 간격 폴링이다. `execute`는 먼저 `{"executionId": "..."}`를 찍고, 그다음 실행 객체를 찍는다.

REST로는 같은 것이 이렇다.

```
POST /api/v1/squads/{id}/execute
{"request": "<요청 본문>", "autoApprove": true}
```

### 관측 — 시각화 30점의 원천

```bash
aigo squad activity <SQUAD_ID> [--persisted]   # --persisted 는 logs/events.jsonl 을 다시 읽어들인다
aigo squad history list <SQUAD_ID>
aigo squad history show   <SQUAD_ID> <EXECUTION_ID>
aigo squad history logs   <SQUAD_ID> <EXECUTION_ID>
aigo squad history report <SQUAD_ID> <EXECUTION_ID>   # 마크다운 리포트
aigo squad analytics <SQUAD_ID>                       # 토큰·비용·처리량
aigo squad task list|graph|show <SQUAD_ID> [TASK_ID]
```

`--persisted` 플래그의 설명이 중요하다 — 그게 없으면 **메모리 버퍼만** 돌려주므로 서버를 재시작한 뒤에는 비어 있을 수 있다.

실시간 스트림은 CLI에 명령이 없다. REST를 직접 구독한다: `GET /api/v1/squads/{id}/events` (SSE).

### 예산 — 토큰 효율 30점의 레버

```bash
aigo squad budget show  <SQUAD_ID>
aigo squad budget set   <SQUAD_ID> '<BODY_JSON>'
aigo squad budget usage <SQUAD_ID>
```

### 템플릿 — 제출물을 뽑는 경로

```bash
aigo squad template list
aigo squad template save   <SQUAD_ID> --name <NAME> [--description ...] [--icon ...]
aigo squad template export <TEMPLATE_ID> -o submission.json     # ★ 제출용 JSON
aigo squad template import <FILE>
aigo squad template delete <TEMPLATE_ID> [-y]
aigo squad template install --path <PATH> [--source-id <ID>]
```

**GUI의 Export 버튼 없이 제출 JSON을 파일로 뽑을 수 있다.** 스쿼드 정의를 git으로 버전 관리하고 import → 실행 → 채점까지 무인화하는 고리가 여기서 닫힌다.

### 워크스페이스·메모리·에이전트

```bash
aigo squad files  <SQUAD_ID> [PATH]
aigo squad cat    <SQUAD_ID> <FILE_PATH>
aigo squad search <SQUAD_ID> <QUERY>
aigo squad workspace init|status|clean|validate ...
aigo squad memory init|search|read|write|sections ...
aigo squad message      <SQUAD_ID> <AGENT_ID> <TEXT>
aigo squad conversation <SQUAD_ID> <AGENT_ID>
aigo squad session start|stop|status|list|new|show|delete ...
```

### CLI에 없어서 REST로 해야 하는 것

| 하려는 일 | 방법 |
|---|---|
| 에이전트 모델 일괄 교체 | `POST /api/v1/squads/{id}/agents/bulk-update-model` · 본문 `{"agentIds":[...],"modelRef":"<model>"}` |
| 라우터 정지 | `POST /api/v1/router/stop` + 헤더 `X-Confirm-Dangerous-Operation: true` |
| 모델 풀 기동 | `POST /api/v1/pool/start` + 본문 `{}` |
| provider 토글 | `POST /api/v1/providers/{id}/toggle` + 본문 `{"enabled":true}` |
| 실시간 이벤트 | `GET /api/v1/squads/{id}/events` (SSE) |

CLI가 본문 없이 POST를 보내서 `Failed to parse the request body as JSON: EOF` (400)로 실패하는 명령이 여럿 있다 — `aigo pool start`, `aigo provider toggle`이 그렇다. 그럴 때는 curl로 본문을 붙여 보낸다.

### 토큰 절약에 직결되는 `chat` 옵션

벤치마크 실험용은 아니지만 모델 동작을 확인할 때 쓴다. 평가 모델 중 reasoning 모델이 출력 예산의 대부분을 사고 토큰에 쓰므로 이 플래그들이 그대로 점수다.

| 옵션 | 효과 |
|---|---|
| `--no-think` | `chat_template_kwargs.enable_thinking=false` |
| `--thinking-budget <N>` | `<think>` 안에서 낼 수 있는 토큰 상한. `0`이면 사고 비활성화 |
| `--reasoning-effort <none\|low\|medium\|high\|xhigh>` | 추론 강도 |
| `--preserve-thinking` | 이전 턴 `<think>` 유지 (Qwen3.6+). KV 캐시 재사용에 유리 |

---

## 6. 실측으로 확인된 것 / 아닌 것

**확인됨**

- CLI 설치·checksum 일치·`--version` 1.12.1
- Management API 기동(헤드리스), 자동 발견 파일 생성, 마스터 키 인증
- `aigo squad list` / `squad show` / `squad execute` 접수 / `squad execution` 폴링
- `POST /squads/{id}/agents/bulk-update-model` 본문 형태와 200 응답 (`updatedCount: 4`)
- 데스크톱 앱이 Management API를 안 띄운다는 사실 (로그 0회)
- 헤드리스가 라우터·모델 프로세스를 spawn하지 못한다는 사실 (같은 오류 문자열 2종)
- 명령 표면 478개 노드 전량 (`reference/aigo-cli-1.12.1-help.txt`)

**미확인**

- 스쿼드가 실제로 답을 내는 것. 플래너 LLM 호출에서 멈춰서 완주를 못 봤다.
- `provider add`로 등록한 원격 엔드포인트를 에이전트가 라우터 없이 직접 부르는지.
- `squad execute` 응답 스키마의 나머지 필드. 접수 직후 형태만 봤다.
