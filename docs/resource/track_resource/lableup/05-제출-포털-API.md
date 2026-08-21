# 05. 제출 포털 구조와 API 레퍼런스

> 대상: `https://submission.jxc.events.lablup.ai:8444`
> 서버 정체: FastAPI 애플리케이션. Swagger UI가 `/docs`, OpenAPI 스펙이 `/openapi.json`에 **인증 없이** 열려 있다.
> OpenAPI 제목: **"JunctionX Judging Pipeline — submission server"**, 버전 `0.1.0`
> 로컬 사본: `practice-sets/submission-server.openapi.json`
> 프론트: openresty 리버스 프록시, 서버 사이드 렌더링 HTML (JavaScript 번들 없음), CSRF 쿠키 `__Host-jpc_csrf`

---

## 1. 인증

- 팀 계정은 **주최 측이 만들어서 각 팀에 자격증명을 전달한다.** 자가 가입 없음.
  > "Team accounts are created by the event organizers, who hand each team its sign-in credential. No account yet, or unable to sign in? Speak to an organizer at the event desk."
- 로그인은 이메일 + 비밀번호. 세션 쿠키 기반.
- 별도로 **개발용 API 키(dev key)** 를 발급받는다. 이 키로 주최 측 공유 서빙 스택의 모델을 호출한다.
- **평가 실행은 주최 측이 보유한 키를 쓴다.** 우리 dev key 사용량과 별도 집계된다.

시간 표기는 전부 **UTC**다.

---

## 2. 웹 페이지 (사람이 쓰는 화면)

| 경로 | 인증 | 내용 |
|---|---|---|
| `/` | 필요 | 팀 홈. 미로그인 시 `/login`으로 303 리다이렉트 |
| `/login` | — | 로그인 폼 |
| `/leaderboard` | **불필요** | 공개 리더보드. 세션을 읽지 않고 쿠키도 심지 않음 |
| `/practice-sets` | **불필요** | 연습 세트 다운로드 페이지 |
| `/dev-keys` | 필요 | 개발용 키 목록. **페이지 어디에도 시크릿은 없음** |
| `/dev-usage` | 필요 | 모델별·키별 개발 사용량 |
| `/submit` | 필요 | 제출 폼 + 이번 제출이 팀에 얼마의 비용인지 |
| `/runs` | 필요 | 팀의 실행 목록, 최신순 |
| `/runs/{run_id}` | 필요 | 한 실행의 실시간 진행과 토큰 사용량 |
| `/runs/{run_id}/details` | 필요 | **에이전트/태스크/웨이브 단위 상세 분해** ★ 시각화 원천 |
| `/runs/{run_id}/progress` | 필요 | 진행 상황 프래그먼트만. 두 실행 페이지가 폴링하는 대상 |
| `/docs` | 불필요 | Swagger UI |
| `/openapi.json` | 불필요 | OpenAPI 3.1 스펙 전문 |

### 보안 설계 메모 (스펙 주석에서 확인)

- 모르는 실행과 다른 팀의 실행에 대해 **구분 불가능한 동일한 거부 응답**을 준다. 존재 여부를 알아낼 수 없게 하기 위함이다.
- 조직자 전용 엔드포인트는 **바디를 파라미터로 선언하지 않고 직접 읽는다.** FastAPI가 의존성 해석 단계에서 바디를 파싱하면, 익명 호출자에게 검증 오류로 조직자 전용 표면의 형태를 알려주게 되기 때문이다.
- CSP: `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'`

---

## 3. 팀 API

### `POST /api/teams/login`
팀 인증 및 세션 개설.
요청 `LoginRequest`: `{ "email": string(3~320), "password": string(1~1024) }`
응답 `TeamAccountResponse`: `{ slug, display_name, email, created_at, provisioned }`

### `POST /api/teams/logout`
세션 종료. 204.

### `GET /api/teams/me`
로그인한 팀의 계정 정보. `TeamAccountResponse`.

---

## 4. 개발용 키 API

### `GET /api/teams/me/dev-keys`
팀의 키 목록. **시크릿은 절대 포함되지 않는다.**

`DevKeyResponse` 필드: `key_id`, `label`, `created_at`, `rotated_at`, `revoked_at`, `active`, `last_used_ms`, `expires_at_ms`, `previous_secret_valid_until_ms`

### `POST /api/teams/me/dev-keys`
키 발급. 요청 `{ "label": string(1~60) }`
응답 `IssuedDevKeyResponse`: `{ key: DevKeyResponse, secret: string, notice: "This is the only time this key is shown. Store it now; if you lose it, rotate the key to get a new secret." }`

**시크릿을 담는 유일한 응답 형태다.** 한 번만 보여준다.

### `POST /api/teams/me/dev-keys/{key_id}/rotate`
키 ID는 유지하고 시크릿만 교체. 새 시크릿을 한 번 반환.
`previous_secret_valid_until_ms` 필드가 있으므로 **이전 시크릿에 유예 기간이 있다.** 무중단 교체가 가능하다.

### `POST /api/teams/me/dev-keys/{key_id}/revoke`
키 폐기. 멱등(idempotent).

---

## 5. 개발 사용량 API

### `GET /api/teams/me/dev-usage`
약 30초 캐시된 hub 폴링 결과.

`TeamUsageResponse`:

| 필드 | 설명 |
|---|---|
| `window_hours` | 윈도우 크기 (시간) |
| `window_label` | 표시용 라벨 |
| `since_ms` / `until_ms` | 윈도우 경계 (epoch ms) |
| `totals` | 전체 합계 (`UsageTotalsResponse`) |
| `hourly` | 시간당 합계 배열 |
| `by_model` | 모델별 분해 (`UsageGroupResponse[]`) |
| `by_key` | 키별 분해 (`UsageGroupResponse[]`) |
| `degraded` | 데이터 품질 저하 여부 |

`UsageTotalsResponse`:

| 필드 | 설명 |
|---|---|
| `requests` | 요청 수 |
| `input_tokens` | 입력 토큰 |
| `output_tokens` | 출력 토큰 |
| **`cached_input_tokens`** | **prefix cache에서 서빙된 입력 토큰** |
| `total_tokens` | 총 토큰 |
| **`cached_input_share`** | **캐시된 입력 비율** |
| `mean_latency_ms` | 평균 지연 |

> `cached_input_share`가 API로 노출된다는 것은 **이 수치를 우리가 자동으로 추적하며 프롬프트 구조를 최적화할 수 있다**는 뜻이다. 캐시 히트율을 올리는 실험을 스크립트로 돌려라. → `07-토큰-효율-전략.md`

---

## 6. 제출 API

### `POST /api/teams/me/submissions`
제출을 검증하고 평가 큐에 넣는다.

> **주의**: OpenAPI 스펙에 이 엔드포인트의 **요청 바디 스키마가 선언되어 있지 않다** (`requestBody: null`). 조직자 전용 엔드포인트와 같은 이유로 바디를 손수 읽는 구조이거나, 스펙 생성에서 빠진 것으로 보인다. **정확한 제출 JSON 형태는 로그인 후 `/submit` 페이지에서 확인해야 한다.**
>
> PDF와 포털 스크린샷에서 확인된 것: **Squad Template JSON 1개 + 트랙별 one-shot 프롬프트 1개씩.**

응답 `SubmissionResponse`:
```json
{
  "submission_id": "…",
  "run_id": "…",
  "state": "queued",
  "queue": { "position": 1, "queued_behind": 0, "eligible_at": "…" },
  "warnings": [ { "field": "…", "message": "…" } ]
}
```

### `POST /submit` (웹 폼)
두 버튼 모두 이 경로로 POST한다.

- **`check`** — 검증만 하고 멈춘다. **무료, 무제한.**
- **`submit`** — 같은 검증을 돌린 뒤에만 큐에 슬롯을 요청한다. **거부된 제출은 팀의 큐 상태를 건드리지 않는다.**
- 세 번째 결과: **이미 처리된 폼의 재전송은 둘 중 어느 것보다도 먼저 거부된다.** (과거에 동시 POST 2건이 한 번의 의도된 제출로 3개 슬롯 중 2개를 소모한 사고가 있어 가드가 추가됨)

---

## 7. 실행 조회 API ★ 시각화 데이터 소스

### `GET /api/teams/me/runs`
팀의 평가 실행 목록, 최신순.

`RunResponse`: `run_id`, `submission_id`, `state`, `detail`, `enqueued_at`, `dispatched_at`, `finished_at`

### `GET /api/teams/me/runs/{run_id}/status`
한 실행의 실시간 진행과 토큰 사용량.

### `GET /api/teams/me/runs/{run_id}/details`
**위와 같은 실행 + 에이전트별 / 태스크별 / 웨이브별 분해.**

두 엔드포인트 모두 `RunView`를 반환한다. 이것이 **시각화의 핵심 입력**이다.

#### `RunView` 전체 필드

| 필드 | 타입 | 설명 |
|---|---|---|
| `run_id` | string | |
| `submission_id` | string | |
| `state` | `RunState` | `queued` / `awaiting_runner` / `running` / `finished` / `failed` / `ended` |
| `detail` | string | 상태 설명 |
| `visibility` | `Visibility` | `visible` / `hidden` |
| `leaderboard_posted` | boolean | 리더보드 게시 여부 |
| `enqueued_at` | datetime | 큐 투입 시각 |
| `dispatched_at` | datetime? | 디스패치 시각 |
| `finished_at` | datetime? | 완료 시각 |
| `execution_seconds` | number? | 실행 시간 |
| `progress` | `ProgressView` | 진행 카운트 |
| `tokens` | `TokenUsageView` | 토큰 사용량 |
| `items` | `ItemOutcomeView[]` | **문항별 결과** |
| `breakdown` | `BreakdownRow[]` | **에이전트/태스크/웨이브/모델 단위 분해** |
| `diagnosis` | `DiagnosisView` | 실패 진단 요약 |
| `failure` | `RunFailureView?` | 실행 전체 실패 사유 |
| `score` | `ScoreView?` | 점수 (리더보드 게시 후에만 생성) |
| `withheld` | string[] | 보류된 필드 이름 목록 |
| `progress_as_of` | datetime? | 진행 정보 기준 시각 |

#### `ProgressView` — 카운트만

```json
{ "items_total": 0, "items_completed": 0, "per_track": {}, "status_counts": {} }
```
> "Counts, and only counts. Safe for a hidden run in flight." — 진행 중인 hidden 실행에서도 안전하게 노출되는 유일한 형태.

#### `BreakdownRow` ★★ 가장 중요한 스키마

```json
{
  "agent_id": "…",
  "task_id": "…",
  "wave_index": 0,
  "model_id": "…",
  "calls": 0,
  "input_tokens": 0,
  "output_tokens": 0
}
```

> Token usage for one `(agent, task, wave, model)` combination, summed over items. **Aggregated across items on purpose**: a per-item row would carry item identity into the one view that is available while a hidden run is still in flight.

**`(에이전트, 태스크, 웨이브, 모델)` 4중 키로 토큰이 집계된다.** 문항별로는 쪼개지지 않는다 — 진행 중인 hidden 실행에서 문항 정체가 새어나가는 것을 막기 위한 의도적 설계다.

이 구조가 시각화에 그대로 쓸 수 있는 형태다:
- `wave_index` → 타임라인의 세로 구간
- `agent_id` → 스윔레인
- `task_id` → 레인 안의 블록
- `model_id` → 색상 또는 배지
- `calls`, `input_tokens`, `output_tokens` → 블록 크기·툴팁

#### `TokenUsageView` / `ModelUsageView`

```json
{
  "total_input_tokens": 0,
  "total_output_tokens": 0,
  "total_requests": 0,
  "per_model": [ { "model_id": "…", "input_tokens": 0, "output_tokens": 0, "requests": 0 } ]
}
```

#### `ItemOutcomeView` — 문항별 결과

```json
{
  "item_id": "…",
  "status": "ok|capped_tokens|capped_wallclock|error",
  "failure_kind": "infrastructure|upstream_error|token_cap|wallclock_cap|runner|null",
  "owner": "team|policy|configuration|organizer",
  "question": "…"
}
```
> Built only once the guard allows item identities. — 문항 정체 공개가 허용된 뒤에만 만들어진다.

#### `DiagnosisView` — "무엇이 잘못됐고 누구 문제인가"

```json
{
  "record_status": "completed|capped|failed|null",
  "items_failed": 0,
  "groups": [ { "kind": "…", "owner": "…", "count": 0 } ],
  "unclassified": 0,
  "caps": { "recorded": false, "per_run_token_cap": null,
            "per_item_wallclock_seconds": null, "infra_retries": null },
  "notices": []
}
```
> This is what a team with forty failed items actually needs: the summary, said once.

`FailureGroupView`는 **개수만 담고 문항 목록은 절대 담지 않는다** (`extra="forbid"`로 강제). 진행 중인 hidden 실행에서도 안전하게 렌더링되도록.

#### `ScoreView` / `TrackScoreView`

```json
{
  "overall": 0.0,
  "tracks": [
    { "track": "coding", "accuracy": 0.0, "graded": 0, "total": 0, "excluded": 0,
      "outcomes": [ { "outcome": "graded", "count": 0 } ] }
  ]
}
```

#### `RunFailureView` — 실행 전체가 실패한 경우

```json
{ "owner": "…", "headline": "…", "detail": "", "remedy": null,
  "remedy_href": null, "remedy_label": null }
```
> Every string here is a module constant chosen by a closed enum. Nothing is assembled out of run data, so the explanation cannot itself become the leak.

---

## 8. 리더보드 API

### `GET /api/leaderboard`
**세션 불필요.** 공개.

`LeaderboardResponse`:

| 필드 | 설명 |
|---|---|
| `caps_note` | 비교 가능성 안내문 (기본값이 스펙에 하드코딩되어 있음 — 02번 문서 8절에 전문) |
| `caps_divergence` | 서로 다른 캡으로 실행된 행이 섞였을 때의 안내 |
| `exclusion_note` / `exclusion_summaries` / `excluded_track_note` | 제외 관련 안내 |
| `distinct_caps` | 등장한 서로 다른 캡 목록 |
| `attribution_notices` | 데이터셋 고지문 |
| `entries` | `LeaderboardEntryResponse[]` |

`LeaderboardEntryResponse`: `rank`, `team_name`, `posted_at`, `run`(`ScoredRunPublication`)

`ScoredRunPublication`:

| 필드 | 설명 |
|---|---|
| `run_id`, `team_id`, `submission_id` | 식별자 |
| `run_status` | `completed` / `capped` / `failed` |
| `started_at`, `completed_at`, `execution_seconds` | 시간 |
| `overall` | 종합 점수 |
| `tracks` | `TrackResult[]` — `track`, `accuracy`(0~1), `graded`, `total`, `excluded`, **`weight`** |
| `model_usage` | `ModelTokens[]` — `model_id`, `input_tokens`, `output_tokens`, `requests` |
| `items` | `PublicItemLine[]` — `disclosure: public`인 문항만 |
| `caps` | `PublishedCaps` |
| `attribution_notices` | 고지문 |

`PublicItemLine`: `item_id`, `track`, `outcome`, `score`(0~1), `subject?`, `disclosure`

> Emitted **exclusively for items whose disclosure level is `public`.** Everything else contributes to the counts on its track row and to nothing else.

> **활용 아이디어** — 리더보드 API가 인증 없이 열려 있고 각 행에 트랙별 정확도, 모델별 토큰, 캡, 문항별 결과까지 들어 있다. **대회 중 다른 팀의 실행 데이터를 폴링해 "우리 vs 전체" 비교 뷰를 시각화 산출물에 넣으면** 심사 기준의 `insightfulness`에 직접 꽂힌다. 단 팀 이름이 들어가므로 표현에 유의할 것.

### `PublishedCaps` — 네 가지 상태를 구분한다

| 상태 | 의미 |
|---|---|
| `recorded=false, readable=true` | 기록에 캡 블록이 없었음. **"not recorded"를 표시할 수 있는 유일한 상태** |
| `readable=false` | 캡 블록이 있었으나 읽지 못함. 리더 결함이거나 러너의 형태 변경 |
| `recorded=true`, 캡 값이 `null` | 블록은 있었고 그 캡은 적용되지 않았음 |
| `recorded=true`, 숫자 | 그 캡이 그 값으로 적용됐음 |

---

## 9. 조직자 전용 엔드포인트 (참고)

우리가 호출할 수 없지만, 시스템 이해에 도움이 된다.

### `POST /api/internal/runs/{run_id}/end`
한 실행을 조기 종료하고 팀의 동시성 슬롯을 반환한다. `EndRunResponse`: `run_id`, `team_slug`, `previous_state`, `state`, `changed`, `dry_run`, `actions`

### `POST /api/internal/runs/scored`
채점 집계가 끝나는 즉시 채점 결과를 게시한다.

쿼리 파라미터:
- `replace` — 이미 게시된 행을 덮어쓴다. 없으면 이미 보드에 있는 실행은 `409`로 거부된다.
- `dry_run` — 파싱·검증만 하고 게시하지 않으며, 실제 게시가 무엇을 할지 보고한다.
- `allow_ended` — 조직자가 조기 종료한 실행을 게시한다. 기본 꺼짐.

게시자 정보는 쿼리 문자열이 아니라 `X-JPC-Performed-By` 헤더로 전달된다 — 쿼리 문자열은 경로상의 모든 접근·프록시 로그에 남기 때문.

응답 `PublicationAccepted`: `run_id`, `posted`, `dry_run`, `replaced`, `would_replace`, `previously_posted_at`

---

## 10. 연습 세트 다운로드 엔드포인트

전부 인증 불필요.

```
GET /practice-sets                              # HTML 페이지
GET /practice-sets/coding/items.jsonl
GET /practice-sets/coding/manifest.json
GET /practice-sets/coding/context.jsonl
GET /practice-sets/coding/context.manifest.json
GET /practice-sets/math/items.jsonl
GET /practice-sets/math/manifest.json
GET /practice-sets/generic/items.jsonl
GET /practice-sets/generic/manifest.json
GET /practice-sets/set.manifest.json
GET /practice-sets/visible-sets.zip
GET /practice-sets/SHA256SUMS
```

---

## 11. 실전 자동화 스니펫

### 로그인하고 세션 쿠키 유지

```bash
BASE="https://submission.jxc.events.lablup.ai:8444"
COOKIES=/tmp/jpc.cookies

curl -sS -c "$COOKIES" -b "$COOKIES" \
  -H 'Content-Type: application/json' \
  -X POST "$BASE/api/teams/login" \
  -d '{"email":"팀이메일","password":"비밀번호"}'
```

### 개발 사용량 폴링 (캐시 히트율 추적)

```bash
curl -sS -b "$COOKIES" "$BASE/api/teams/me/dev-usage" \
  | jq '{requests: .totals.requests,
         input: .totals.input_tokens,
         cached: .totals.cached_input_tokens,
         cached_share: .totals.cached_input_share,
         output: .totals.output_tokens,
         latency_ms: .totals.mean_latency_ms}'
```

### 실행 상세를 시각화 입력으로 덤프

```bash
RUN_ID="…"
curl -sS -b "$COOKIES" "$BASE/api/teams/me/runs/$RUN_ID/details" \
  > traces/run-$RUN_ID.json

# 웨이브/에이전트별 토큰 집계 확인
jq '.breakdown | group_by(.wave_index)
    | map({wave: .[0].wave_index,
           agents: (map(.agent_id) | unique),
           input: (map(.input_tokens) | add),
           output: (map(.output_tokens) | add)})' \
   traces/run-$RUN_ID.json
```

### 리더보드 전체를 주기적으로 스냅샷

```bash
curl -sS "$BASE/api/leaderboard" > leaderboard/$(date -u +%Y%m%dT%H%M%SZ).json
```

> **주의** — 폴링 간격은 예의를 지킬 것. 리더보드 페이지 자체가 "채점은 수 분 걸린다"고 안내한다. 30~60초 간격이면 충분하다.
