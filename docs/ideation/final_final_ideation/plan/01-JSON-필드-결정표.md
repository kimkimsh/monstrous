# 부록 1 — Squad Template JSON 필드 결정표

이 문서는 `squad/squad_template/monstrous_squad/squad-template.json`의 **모든 필드**에 대해 "무슨 값을 넣었고, 그 값을 고른 근거가 무엇이며, 반대 선택지를 왜 버렸는지"를 한 줄도 빠짐없이 적는다.

근거는 네 종류뿐이고, 표기를 구분한다.

| 표기 | 뜻 |
|---|---|
| **[바이너리]** | `/Applications/Backend.AI GO.app/Contents/MacOS/backend-ai-go`(77.8MB, arm64, 심볼 9만 개)의 문자열과 **디스어셈블리** |
| **[디스크]** | 이 PC의 실제 파일 — 앱이 쓴 `.squad.json`, `providers.json`, `model-metadata.yaml`, `settings.json`, 실행 로그 |
| **[공식]** | Lablup 공식 매뉴얼 `https://go.backend.ai/ko/manual/` 및 공개 레포 `lablup/agent-catalog`의 JSON Schema |
| **[문서]** | 이 저장소의 트랙 자료·스펙 문서. 실측이 아니므로 단독 근거로 쓰지 않는다 |

**공식 스키마 문서가 존재한다.** [Squad Templates](https://go.backend.ai/ko/manual/squad/templates/)가 템플릿 JSON 스키마를 그대로 싣고, 뒷단 코드 파일명(`src-tauri/src/squad/templates.rs`, `src/types/squad/templates.ts`)까지 밝힌다. 소스 레포 `lablup/backend.ai-go`는 비공개(404)지만 `lablup/agent-catalog`는 공개이고 실제 JSON Schema를 담고 있다. 아래 결정은 **[공식]과 [바이너리]가 일치하는 지점**만 확정으로 취급하고, 어긋나는 곳은 그 사실을 적었다.

---

## 0. 먼저 — 스키마의 실제 크기

**에이전트 객체가 받는 키는 정확히 9개다.** 그 밖의 키는 **에러 없이 조용히 버려진다.**

```
name · role · systemPrompt · tools · toolConfig · modelPreferences · memoryEnabled · icon · i18nKey
```

**[바이너리]** `struct AgentTemplate with 9 elements`. **[디스크]** 앱이 번들한 빌트인 템플릿 5개(`/Applications/Backend.AI GO.app/Contents/Resources/squad-templates/builtin/*.json`)에서 뽑은 키 합집합이 정확히 이 9개다.

최상위는 **12개**다. **[바이너리]** `0x100bdebc0`의 serde field visitor. 우리가 쓰는 것은 앞의 10개이고, 나머지 둘(`sourceUrl`, `installedAt`)은 레지스트리에서 설치했을 때 앱이 채우는 출처 정보라 제출 파일에는 넣지 않는다.

```
schemaVersion · id · name · description · icon · category · agents · isBuiltin
· suggestedModels · sourceUrl · installedAt · i18nKey
```

`author` · `isCommunity` · `translations` · `tags`는 **여기 없다.** 그 넷은 `AgentProfile`의 필드이고, 인터넷 예시를 베끼면 섞이기 쉽다.

### 여기서 나오는 첫 번째 결론 — 못 싣는 것 세 가지

**타입이 둘이라는 것이 핵심이다.** `AgentTemplate`(스쿼드 템플릿 안의 에이전트, 9개 키)과 `AgentProfile`(단독 에이전트 프로필, 훨씬 넓다)은 서로 다른 타입이고, 인터넷에서 찾을 수 있는 `settingsOverrides` 예시는 전부 후자다. 생성된 스쿼드(`squad/test_2/.squad.json`의 `config.agents[]`)에는 있지만 **템플릿에는 실을 수 없는** 필드가 셋이다. 넣어도 버려진다.

| 필드 | 생성된 스쿼드에서의 값 | 우리가 원했을 값 | 대응 |
|---|---|---|---|
| `settingsOverrides` | `null` (8/8 에이전트) | `maxTokens`(출력 상한), `maxToolCalls` | **`aigo squad update`로 넣는다** — 단 스쿼드 실행이 그 값을 읽는지는 미확인이다. §6 전체가 이 이야기다 |
| `instructions` | `""` (8/8 에이전트) | 출력 계약 한 벌 | 같음. `systemPrompt`가 대신 담는다 |
| `executionMode` | `"in_process"` (8/8) | `in_process` — 기본값이라 손댈 필요 없음 | 없음 |

`settingsOverrides`의 실제 형태는 빌트인 **에이전트 프로필**에서 확인했다 — **[디스크]** `~/Library/Application Support/ai.backend.go/agent_profiles/30342ec0-….json`:

```json
"settingsOverrides": {
  "maxIterations": 10, "maxToolCalls": 25, "defaultTimeout": 90,
  "contextCompressionThreshold": null, "maxTokens": null, "allowedPaths": null
}
```

**즉 `maxTokens`(출력 상한)는 존재하는 손잡이인데 템플릿으로는 못 준다.** 다른 경로가 있고, 그 경로가 실제로 먹는지까지 §6에서 갈라 적었다.

---

## 1. `tools` / `toolConfig` — 가장 크게 바뀐 자리

### 1-1. 결정

```json
"tools": [],
"toolConfig": {
  "enabledTools": [],
  "disabledTools": [ …22개, 아래 §1-4… ],
  "toolPermissionOverrides": { …같은 22개를 전부 "never_allow"… },
  "customToolConfigs": {}
}
```

**`enabledTools: []`가 작동하는 유일한 손잡이다. 나머지 둘은 스쿼드 실행 경로에서 아무 일도 하지 않는다 — 디스어셈블리로 확인했다.** 그래도 채운 이유는 §1-4에 있고, "보험"이라는 말로 뭉개지 않고 정확히 무엇이 참인지 적는다.

### 이것이 왜 확실한가 — 도구 결정 경로 전문

**[바이너리]** `squad::agent_turn::build_tools_for_agent` (`0x101d920fc`)가 에이전트의 도구를 정하는 함수 전부다. 세 줄로 요약된다.

1. `0x101d92128` — `squad::execution::effective_enabled_tools`를 호출한다.
2. `0x101d9212c` — **그 결과가 빈 목록이면 곧장 반환한다. 도구 0개로 모델을 부른다.**
3. `0x101d92138` — 비어 있지 않을 때만 레지스트리(`commands::tools::get_available_tools`)를 가져와, **레지스트리 쪽을 훑으며** 이름이 목록에 있는 항목만 남긴다.

그리고 `effective_enabled_tools`(`0x101da2d98`)는 **문자열 슬라이스 하나만 받는다.** 원소마다 `is_workspace_escaping_tool`을 호출해 참인 것을 버릴 뿐이고, **`disabledTools`를 읽는 명령이 한 줄도 없다.**

방향도 중요하다 — 필터는 우리 목록이 아니라 **레지스트리**를 훑는다. 그래서 **레지스트리에 없는 이름을 `enabledTools`에 적으면 에러 없이 그냥 무시된다.**

### 1-2. 스쿼드 에이전트가 가질 수 있는 도구 — 실제 목록

**[바이너리]** `src/squad/tools.rs`의 문자열에서 워크스페이스 도구 9개를 확인했다.

| 도구 | 하는 일 |
|---|---|
| `read_file` · `write_file` | 워크스페이스 상대경로 읽기·쓰기 |
| `list_files` · `list_directory` | 디렉터리 나열. 공식 매뉴얼은 앞이 뒤의 옛 이름이라고 적지만, **[바이너리]** 둘 다 워크스페이스 경로 재작성 대상으로 따로 등록돼 있다 |
| `search_files` | 패턴 검색 |
| `diff_files` | 두 파일 비교 (`path1`, `path2`) |
| `read_memory` · `write_memory` · `search_memory` | 에이전트 메모리 뱅크 |

**[바이너리]** `squad::execution::is_workspace_escaping_tool`(`0x101da3690`)이 이름만으로 거부하는 것은 **정확히 14개**다. 문자열 길이로 분기하는 함수라 목록이 완전하게 읽힌다.

| 길이 | 이름 |
|---|---|
| 9 | `move_file` `run_shell` |
| 10 | `pdf_reader` `csv_reader` `json_query` `image_info` `run_python` |
| 11 | `delete_file` `run_command` |
| 14 | `execute_python` `search_content` |
| 15 | `image_to_base64` |
| 16 | `audio_transcribe` `create_directory` |

이 이름들을 주면 다음 문자열로 거부된다.

> `Tool '…' is not available to squad agents: it operates on the host outside the squad workspace and is blocked for safety.`

**이것은 허용 목록이 아니라 차단 목록이다.** 그리고 **[바이너리]** 위 함수에서 **길이 12와 13은 분기 없이 `false`로 떨어진다.** 그래서 `fetch_url`(9)·`web_search`(10)·`http_request`(12) 셋은 자기 길이의 분기에 이름이 없어 **차단되지 않는다.** 공식 매뉴얼([Tool Calling](https://go.backend.ai/ko/manual/core-features/tool-calling/))이 8개 범주 31개 도구를 나열하는데, **네트워크 도구 셋은 스쿼드 에이전트에게 줄 수 있다.** 우리는 주지 않고, 명시적으로 막는다.

**옛 이름 세 쌍도 같은 문서에 있다** — `execute_python`→`run_python`, `list_files`→`list_directory`, `run_shell`→`run_command`. 앞의 둘과 넷째는 위 차단 목록에 이미 있다.

**그리고 빌트인 템플릿 하나에 존재하지 않는 도구 이름이 들어 있다.** **[디스크]** `research-team.json`의 Researcher는 `"brave_search"`를 켜는데, 그런 이름의 도구는 없다 — **[바이너리]** `brave_search`는 `brave_search_api_key` 같은 **설정 키**로만 나타나고, 실제 도구는 `web_search`(Brave를 백엔드로 쓴다)다. 빌트인을 베끼면 이런 죽은 문자열까지 따라온다.

Planner 전용 도구 6개(`create_task`, `check_task_status`, `read_task_result`, `update_plan`, `aggregate_results`, `send_feedback`)는 **[바이너리]** 별도 경로에서 주입되며 `toolConfig`와 무관하다. **즉 Router의 `enabledTools`가 비어 있어도 Router는 태스크를 만든다.** 이것이 이 결정을 가능하게 하는 사실이다.

### 1-3. 왜 전부 비우는가 — 근거 넷

**① 평가 실행 중에는 도구가 애초에 0개다.** 주최 문면 **[문서]**: *"your squad has no tools during a run and never browses a repository."* 그러니 평가에서 도구는 얻을 것이 없다.

**② 도구를 선언하면 매 호출 프롬프트가 길어진다.** **[디스크]** 실제 세션 파일 `squad/test/sessions/agent-1787387157647-ztcvzv5/03e5fe7a-….json`의 `messages[0].content`에 이 블록이 그대로 들어 있다.

```
Available tools: read_file, write_file, list_directory
…
## Important: File Tool Paths
All file tool paths (read_file, write_file, list_files, list_directory, search_files,
diff_files) must be RELATIVE to the workspace root. Do NOT use absolute paths.
- Correct: "src/index.html", "artifacts/output.txt"
- Wrong: "/workspace/src/index.html", "/src/index.html"
Use list_files with path "." to see the workspace root contents.
```

같은 이름들이 **[바이너리]** Planner의 팀 명단 줄(`Tools: …`)에도 한 번 더 실린다. 도구 0개면 이 텍스트가 사라지거나 비어서, 889회 실행 × 3~4 호출에서 매번 조금씩 아낀다.

**③ 그리고 도구는 실측에서 답을 죽였다 — 이것이 결정적이다.** **[디스크]** `squad/test_2` 실행 `13a35667`은 정답을 워크스페이스 파일에 썼다.

```
squad/test_2/artifacts/final_answer.txt → "Final amount: **≈ $32,328**"
같은 실행의 응답 본문 → \boxed{} 없음. extraction_failed.
```

`squad/test`의 `5e3813da`도 같다 — 완결된 `solution.py`(908바이트)를 워크스페이스에 쓰고, 응답에는 마크다운 코드 펜스만 냈다. 패치 마커는 없었다.

> **채점기는 응답 본문을 읽지, 워크스페이스를 열지 않는다.** `write_file`이 열려 있으면 모델은 "산출물을 만들었다"고 판단하고 응답에는 요약만 쓴다. 이 PC의 실행 6건 전수 조사에서 채점 가능한 출력이 **0건**이었던 사고의 절반이 여기서 나온다.

**④ Qwen3-32B는 도구를 켜면 계획만 하고 실행하지 않는 비율이 약 60%다.** **[문서]** [QwenLM/Qwen3#1817](https://github.com/QwenLM/Qwen3/issues/1817). 5회 중 2회는 "검색했다"고 응답 텍스트가 지어냈다. 절약 계단 S1에서 Reviewer를 Qwen3-32B로 되돌리면 이 경로가 살아난다.

### 1-4. `disabledTools`와 `toolPermissionOverrides` — 22개를 채웠고, 둘 다 스쿼드 실행에서 무효다

먼저 **채운 목록**이다. 이 앱이 스쿼드 에이전트에게 실제로 줄 수 있는 도구 **전부**이고, 그 밖은 §1-2의 이름 차단에 걸린다.

| 묶음 | 이름 |
|---|---|
| 워크스페이스 (9) | `read_file` `write_file` `list_files` `list_directory` `search_files` `diff_files` `read_memory` `write_memory` `search_memory` |
| 웹·확장 (4) | `web_search` `fetch_url` `http_request` `diff_text` |
| 유틸리티 (3) | `calculator` `get_current_time` `get_system_info` |
| Data Hub (5) | `read_data` `write_data` `list_data` `search_data` `delete_data` |
| 대화형 (1) | `select_option` — 줄 수는 있지만 실행 시점에 *"requires interactive user selection"*로 실패한다 |

§1-2의 차단 14개는 목록에 넣지 않았다. **이미 닫힌 문에 자물쇠를 더 다는 것이라 아무것도 닫지 않는다.**

### 채운 이유, 그리고 채우지 **않은** 이유

`toolPermissionOverrides`의 실제 형태는 **[디스크]** 빌트인 에이전트 프로필에서 확인했다 — **키는 도구 이름, 값은 권한 문자열**이다.

```json
"toolPermissionOverrides": {
  "read_file": "always_allow", "web_browse": "always_allow",
  "web_search": "always_allow", "write_file": "ask_once"
}
```

권한 값 열거형은 넷이다. 공식 JSON Schema에 그대로 있다 — [`lablup/agent-catalog/schemas/agent-profile.schema.json`](https://raw.githubusercontent.com/lablup/agent-catalog/main/schemas/agent-profile.schema.json):

```json
"ToolPermission": { "type": "string",
  "enum": ["always_allow", "ask_once", "ask_always", "never_allow"] }
```

**[바이너리]** 네 문자열이 전부 1.12.1 바이너리에 있다. 공개 카탈로그 프로필 46개에서 관례는 읽기 → `always_allow`, 쓰기 → `ask_once`, 셸 → `ask_always`이고, **`never_allow`는 46개 중 0개에서 쓰인다.** 우리가 그 값을 처음 쓰는 셈이다 — 열거형에는 있으므로 파싱은 되지만, 실사용 전례가 없다는 사실을 §1-5의 대비책 근거로 삼는다.

- **스쿼드 실행에서는 둘 다 무효다.** `disabledTools`는 위 §1-1에서 본 대로 읽히지 않는다. `toolPermissionOverrides`도 마찬가지다 — **[바이너리]** 권한 판정은 `agent::tools::permission::PermissionManager`(`get_permission`, `check_with_permission`, `default_permission_for_tool`)에 있고, 그것은 **사람에게 승인을 묻는 데스크톱 채팅 경로**다. 스쿼드 태스크 실행에는 물을 사람이 없고, `build_tools_for_agent`는 이 맵을 보지 않는다.
- **그래도 채우는 이유 셋.** ① 비용이 0이다 — 프롬프트에 실리지 않는 설정값이라 토큰을 쓰지 않는다. ② **데스크톱 채팅 경로에서는 유효하다.** 측정·디버깅 중에 사람이 개별 에이전트와 대화할 때 §1-3 ③의 사고가 재발하지 않는다. ③ 제출물이 그 자체로 의도를 말한다 — 심사자가 JSON을 열었을 때 "도구를 안 쓴다"가 빈 배열 하나가 아니라 명시된 22줄로 보인다.
- **그러니 이렇게 읽어야 한다.** 이 두 필드는 **방어선이 아니라 기록**이다. 방어선은 `enabledTools: []` 하나이고, 그것 하나로 충분하다는 것이 §1-1의 디스어셈블리다.
- **`customToolConfigs`는 비운다** — **[공식]** 스키마가 *"Tool-specific configuration as arbitrary JSON"* + `additionalProperties: true`로만 정의한다. 공개 카탈로그 프로필 46개와 빌트인 템플릿 5개 **전부에서 `{}`**이고, 이 값을 읽는 코드 경로도 확인되지 않았다. 형태를 모르는 필드에 값을 넣는 것은 임포트 실패 위험만 산다.

### 1-4-1. 임포트한 뒤 앱 화면에서 도구가 하나도 안 골라진다 — 실측 보고

임포트 후 UI에서 빌트인 도구를 체크할 수 없다는 관측이 있었다. `squad-template.min.json`(세 필드를 비운 판)으로 해도 같았다.

**이것은 우리 설계가 원하는 상태다.** `enabledTools: []`가 하는 일이 정확히 그것이고(§1-1), 도구 0개가 목표다. 다만 **"템플릿이 제대로 들어갔는지"를 UI로 확인할 수는 없다**는 뜻이므로, 확인은 파일로 한다.

```bash
python3 -m json.tool ~/Library/Application\ Support/ai.backend.go/squads/<SQUAD_ID>.json \
  | grep -A6 enabledTools
```

**화면이 잠긴 이유는 아직 못 짚었다.** 후보가 셋이고, 셋 다 30초짜리 확인이 있다.

| 후보 | 확인 방법 |
|---|---|
| `requiresToolCalling: false`가 도구 칸을 잠근다 | 한 에이전트만 `true`로 바꿔 임포트해 보고 칸이 풀리는지 본다 |
| 전역 도구 설정이 목록을 비운다 — **[디스크]** `settings.json`의 `tools.enabledTools`가 `["calculator", "get_current_time"]` 둘뿐이고, **둘 다 스쿼드 에이전트에게 차단되는 이름**이다(§1-2) | 앱 설정 → 도구에서 `read_file` 등을 켜고 목록이 채워지는지 본다 |
| 모델이 tool calling 능력을 광고하지 않는다 — **[디스크]** `model-metadata.yaml`이 `gpt-oss-120b`를 `["chat","code"]`로 적는다 | K-EXAONE(유일하게 `tool`·`function_calling`을 가진 모델)을 쓰는 Solver만 칸이 풀리는지 본다 |

**어느 쪽이든 제출물은 바뀌지 않는다.** 우리가 원하는 값이 이미 파일에 들어 있고, 실제로 도구를 정하는 것은 UI가 아니라 `enabledTools`다.

### 1-5. 임포트 거부에 대비한다

`disabledTools`·`toolPermissionOverrides`를 채우는 것이 임포트 검증을 통과하는지는 **아직 안 돌려 봤다.** 확인된 검증은 개수 제한(`도구 목록 각 ≤100개`)뿐이고 이름 검증은 확인되지 않았다.

그래서 같은 폴더에 **`squad-template.min.json`**을 함께 둔다 — 세 필드를 전부 비운 판이고, 나머지는 바이트 단위로 같다. 제출 포털의 `check`는 **무료·무제한**이므로 주 템플릿을 먼저 넣어 보고, 거부되면 즉시 이쪽으로 바꾼다.

---

## 2. `modelPreferences` — 채우면 안 되는 두 필드의 증거

```json
"modelPreferences": {
  "preferredModelId": "<에이전트별, §2-1>",
  "minContextWindow": null,
  "requiresToolCalling": false,
  "requiresVision": false
}
```

**[바이너리]** `ModelPreferences`는 5개 키다(`0x100bd4954`의 serde field visitor): `preferredModelId`, `preferredProviderId`, `minContextWindow`, `requiresToolCalling`, `requiresVision`.

### 2-0. 먼저 — 다섯 중 넷은 아무 일도 하지 않는다

이것을 확인하는 데 시간을 가장 많이 썼고, 결론이 초안을 뒤집었다.

**[바이너리]** 모델 배정 경로 전체가 함수 둘이다.

`squad::readiness::resolve_agent_readiness` (`0x101da3db4`):
- `0x101da3dd8` — `ldr x8, [x0, #0x1b0]`. `Option` 판별자 **한 번** 검사. `None`이 아니면 그 문자열을 복사해 반환하고 끝.
- `0x101da3e18` — `None`이면 앱 기본 모델로 `model_resolution::resolve_model_id_with_source` 호출.
- `0x101da3e84` — 그래도 없으면 143바이트짜리 에러: *"No model is configured for … , and no default agent model is set."*

`model_resolution::resolve_model_id_with_source` (`0x101cfa88c`): 후보 문자열 둘을 각각 trim하고, 빈 것과 리터럴 `"default"`를 걸러(7바이트 비교, `0x101cfa8d4`) 살아남은 첫 번째를 반환한다.

> **두 함수 어디에도 컨텍스트 창을 읽거나, 능력 레코드를 조회하거나, tool-calling 플래그를 검사하는 명령이 없다.** `preferredModelId`는 검증 없이 그대로 쓰인다.

즉 `minContextWindow` · `requiresToolCalling` · `requiresVision` · `preferredProviderId` **넷 다 1.12.1에서 무효다.** 초안 스펙(`spec/01-플랫폼-사실.md:151`)이 *"`minContextWindow`보다 작은 모델은 선택되지 않는다"*고 적은 것은 **틀렸다.**

**그럼에도 값을 신중하게 고른다.** 무효인 필드에 값을 넣는 것은 두 가지 중 하나다 — 아무 일도 안 하거나, **앱이 업데이트되어 배선되는 순간 그 값대로 작동하거나.** 아래 셋은 "배선되면 어떻게 되는가"를 기준으로 정했고, 그 조건에서 안전한 쪽을 골랐다.

### 2-1. `preferredModelId` — 채운다

**[디스크]** 문자열의 출처는 `~/Library/Application Support/ai.backend.go/providers.json`이다. 이 PC에 등록된 provider는 하나이고(`junction`, `continuum_router`, `base_url: https://submission.jxc.events.lablup.ai:8445/`), `catalogSource: "live"`로 모델 셋을 실제로 받아 왔다.

```
furiosa-ai/K-EXAONE-236B-A23B-NVFP4A16
furiosa-ai/Qwen3-32B-FP8
furiosa-ai/gpt-oss-120b
```

에이전트별 배정과 그 근거는 **`02-모델-배정-분석.md`** 전체가 다룬다.

### 2-2. `minContextWindow: null` — 배선되는 날 스쿼드를 죽이는 값이다

이 필드의 선언된 의미는 "이 값보다 작은 컨텍스트의 모델은 제외한다"이다. §2-0대로 지금은 무효지만, **배선된다면 후보를 줄이는 방향으로만** 작동한다.

문제는 **앱이 우리 모델의 컨텍스트를 잘못 알고 있다는 것**이다. **[디스크]** `~/Library/Application Support/ai.backend.go/model-metadata.yaml`:

| 모델 | `limits.context_window` | `capabilities` |
|---|---|---|
| `gpt-oss-120b` | **2048** | `["chat", "code"]` |
| `qwen3` (32B가 alias로 붙는 항목) | 38000 | `["chat", "code", "reasoning"]` |
| `k-exaone-236b-a23b` | 262144 (`max_output: 16384`) | `["chat","reasoning","code","function_calling","tool"]` |

그리고 **[디스크]** 앱의 능력 캐시 `capabilities.db`는 표 두 개(`provider_capabilities`, `model_capabilities`) 모두 **행이 0개다**. 실제로 조회해 확인했다.

> `minContextWindow`를 2,048보다 큰 값으로 두면, 이 카탈로그를 근거로 판단하는 코드가 **생기는 순간** gpt-oss-120b가 후보에서 빠진다. 우리 스쿼드는 다섯 자리 중 넷이 gpt-oss-120b이고, 그중 하나가 **Planner**다.

Planner의 모델이 해석되지 않으면 어떻게 되는지는 실측돼 있다. **[디스크]** `squad/test/logs/events.jsonl`:

```
"plannerWarning": "The planner call failed (…), so the request was not decomposed.
                   Each agent was given the whole request instead."
```

같은 로그에서 63,475자 요청이 3명에게 각각 통째로 갔다. 5명이면 약 100K 토큰이 한 문항에서 증발한다. **얻을 것이 0이고 잃을 것이 최악이므로 비운다.**

**반대 방향의 실측도 정직하게 적는다.** 같은 로그에서 `minContextWindow: null`인 채로 14,082토큰 요청이 4,096토큰 서버로 그대로 날아가 HTTP 400을 맞았다.

```
"request (14082 tokens) exceeds the available context size (4096 tokens), try increasing it"
```

`squad/test` 실행 `76bb50f0`·`51c68753`가 그 사례이고, 세 워커가 각각 13,887 / 15,715 / 13,941 토큰으로 같은 400을 받았다. **coding 문항 100%가 이렇게 죽는다.**

**그러나 이 필드로 막을 수 있는 사고가 아니었다.** §2-0대로 앱은 애초에 컨텍스트를 대조하지 않고, 설령 대조했더라도 그 실행의 모델(로컬 `unsloth/gpt-oss-20b`)의 실제 컨텍스트를 몰랐다. 값을 넣었어도 "조건을 만족하는 모델이 없다"로 떨어져 같은 브로드캐스트가 났을 뿐이다.

> **필터로 막을 문제가 아니라 모델 선택으로 막을 문제다.** 그것이 `02-모델-배정-분석.md`의 배치별 컨텍스트 표가 하는 일이다.

### 2-3. `requiresToolCalling: false` — 스키마 기본값이 `true`라서 반드시 명시한다

**[문서]** 이 필드의 기본값은 `true`다. **[디스크]** 이 PC에서 만들어진 실제 스쿼드 8개 에이전트 전부가 `true`다. 빌트인 템플릿 20개 에이전트도 전부 `true`다.

그런데 **[디스크]** `model-metadata.yaml`은 `gpt-oss-120b`의 capabilities를 `["chat", "code"]`로, `qwen3`를 `["chat", "code", "reasoning"]`로 적어 두었다. **둘 다 `tool`이 없다.** `tool`/`function_calling`을 가진 것은 `k-exaone-236b-a23b` 하나뿐이다.

> `requiresToolCalling: true`를 그대로 두면, 이 카탈로그로 판단하는 코드가 생기는 순간 **세 모델 중 둘이 후보에서 빠지고 K-EXAONE만 남는다.** Router·Architect·Editor·Reviewer 넷이 모델을 잃고, 그중 Planner가 있으므로 §2-2와 같은 브로드캐스트가 난다.

§1의 결정(도구 0개)과도 일관된다. **도구를 쓰지 않는 에이전트가 tool calling을 요구하는 것은 그 자체로 거짓 선언이다.** 값이 지금 무효라는 사실이 거짓 선언을 남길 이유가 되지는 않는다.

### 2-4. `requiresVision: false`

세 트랙 전부 텍스트다. 이미지 입력이 없다. 배선되면 `true`는 세 모델 전부를 탈락시킨다.

### 2-5. `preferredProviderId` — 넣지 않는다

**[디스크]** 이 PC의 provider id는 `408e1428-e9d4-4c6d-a7da-d3c36207da79`다. **이 UUID는 설치할 때 생성된 로컬 값이다.** 심사자의 기기에는 같은 id가 없다.

**[바이너리]** 빌트인 템플릿 5개와 이 PC의 실제 스쿼드 파일 어느 것도 이 필드를 쓰지 않는다. provider가 하나뿐이라 모호성도 없다. **지정해서 얻는 것이 0이고, 배선되는 날 잃을 것은 전부다.**

---

## 3. `memoryEnabled: false`

**[디스크]** 빌트인 템플릿 20개 에이전트 전부가 `true`다. 실제로 만들어진 스쿼드 8개도 전부 `true`다. **그 기본값을 물려받지 않는다.**

### 3-1. 비용

**[디스크]** `~/Library/Application Support/ai.backend.go/settings.json`:

```
memory.enabled                      = true
memory.maxTokens                    = 2000
memory.perAgentReadbackMode         = multiplier
memory.perAgentReadbackMultiplier   = 1.0
memory.autoExtractionEnabled        = false
memory.extractionTriggerInterval    = 5
memory.layerABudgetFraction         = 0.6
```

읽기 배수 1.0에 상한 2,000이므로 **태스크 시작마다 최대 2,000 입력 토큰**이 붙는다. 889회 실행 × 3~4 호출 × 2,000 × 배율 2 = 최악 **10M 이상**이다. §4-4 총액 40.0M의 4분의 1이다.

**입력 토큰만 드는 것이 아니다 — LLM 호출이 추가로 나간다.** 공식 매뉴얼 [Workspace & Memory](https://go.backend.ai/ko/manual/squad/workspace-memory/) 원문:

> 에이전트에 `memory_enabled`가 설정되면 백엔드가 `trigger_interval`마다 LLM 추출을 실행합니다.

즉 N턴마다 추출 전용 LLM 호출이 한 번 더 붙고, 그 호출이 사실을 Layer A(경험, 스쿼드 간 공유)와 Layer B(프로젝트 범위, `{workspace}/memory/{agent}.md`)로 분류해 양쪽에 쓴다. **[디스크]** `autoExtractionEnabled`는 지금 `false`지만 **설정 하나로 되살아나고**, 그러면 5턴마다(`extractionTriggerInterval: 5`) 이 호출이 나간다.

메모리 도구 셋(`read_memory`·`write_memory`·`search_memory`)은 도구 레지스트리에서 **desktop-integration 범주**에 속하고 `available_in_headless: false`다. 헤드리스에서는 어차피 못 쓴다.

### 3-2. 얻을 것이 없다 — 그리고 실측에서는 해로웠다

벤치마크 문항은 서로 독립이다. 앞 문항의 기억이 뒤 문항에 도움이 될 여지가 없다.

**[디스크]** 오히려 실측에서 메모리는 오염을 영구화했다. Discussion Room의 `topic`이 `math-visible-0001`이라는 문자열이었고, 에이전트들이 그것을 프로젝트 이름으로 오해했다. 그 오해가 메모리 파일에 그대로 저장됐다.

```
squad/test/memory/backend-developer.md:
- [2026-08-22] Project math-visible-0001: goal to expose or make visible certain
  mathematical data or results within the application… [#project #math-visible-0001 #feature]

squad/test_2/memory/researcher.md:
- [2026-08-22] Project name: math-visible-0145 [#project #planning]
```

`memoryEnabled: true`였기 때문에 이 환각이 **다음 실행에서 다시 읽힌다.**

§1의 `read_memory`/`write_memory`/`search_memory` 금지와 짝이다 — 메모리를 끄고, 메모리 도구도 막는다.

### 3-3. "Planner만 켜면 낫지 않나" — 아니다. 하필 Planner가 가장 나쁜 자리다

직관은 이해가 간다. 계획하는 에이전트가 앞 문항에서 배운 것을 기억하면 좋아 보인다. **그런데 이 스쿼드에서는 세 가지가 정확히 반대로 작동한다.**

**① 메모리는 시스템 프롬프트 안으로 들어간다 — 프리픽스 캐시가 그 자리에서 끝난다.**

**[바이너리]** 함수 이름이 그대로 말한다: `squad::memory_readback::assemble_agent_chat_system_prompt`. 그 안의 `assemble_prompt`(`0x101d923b0`)가 참조하는 문자열이 이것이다.

```
## Agent Memory
Use the following accumulated memory to inform your responses. Layer A is your
cross-project experiential memory; Layer B is your workspace-scoped memory bank
for this squad.
### Layer A — Experiential Memory
### Layer B — Workspace Memory
```

즉 메모리 블록은 별도 메시지가 아니라 **시스템 프롬프트 문자열의 일부**가 된다. 그런데 이 스쿼드의 캐시 설계 전체가 *"다섯 에이전트의 시스템 프롬프트 Layer 1이 바이트 단위로 같다"*에 걸려 있다(`sha256 126b9dab…`). **메모리는 문항마다 달라진다.** 켜는 순간 그 에이전트의 시스템 프롬프트가 매 문항 달라지고, 프리픽스 캐시는 달라지는 지점부터 전부 재계산된다.

**② Planner는 889회 전부 도는 자리다 — 비용이 가장 크다.**

읽기 상한 2,000 × 배수 1.0이므로 호출당 최대 2,000 입력 토큰이다. Router는 coding·math·generic 전 트랙에서 돌므로:

```
889 실행 × 2,000 토큰 × 배율 2 = 약 3.56M
```

§6의 총액 40.0M의 **약 9%**다. 절약 계단 S3(Architect 제거)가 아끼는 2.28M보다 크다. **한 자리만 켠다면 하필 가장 비싼 자리를 켜는 것이다.**

**③ 벤치마크 문항은 서로 독립이고, 실측에서는 오히려 오염됐다.**

문항 N에서 배운 것이 문항 N+1에 쓸모 있으려면 두 문항이 관련돼야 한다. hidden 세트는 SWE-bench 저장소가 제각각이고, MMLU-Pro는 14개 과목이 섞여 있고, MATH-500은 문제마다 독립이다.

그리고 **[디스크]** 실제로 저장된 것은 도움이 아니라 환각이었다.

```
squad/test/memory/backend-developer.md
- [2026-08-22] Project math-visible-0001: goal to expose or make visible certain
  mathematical data or results within the application… [#project #feature]

squad/test_2/memory/researcher.md
- [2026-08-22] Project name: math-visible-0145 [#project #planning]
```

에이전트들이 **문항 ID를 프로젝트 이름으로 착각**했고, `memoryEnabled: true`라 그 착각이 다음 실행의 시스템 프롬프트에 다시 실린다. Planner에서 이런 일이 생기면 **오분류가 그 뒤 문항 전부로 번진다.**

> **결론: 메모리는 다섯 자리 전부 끈다.** 문항이 서로 이어지는 과제였다면 다른 결론이었을 것이고, 그 조건을 여기 적어 둔다 — **같은 저장소의 여러 문항을 연속으로 푸는 실행이라면 Layer B(워크스페이스 범위)만 켜는 것이 값을 할 수 있다.** 지금 hidden 세트는 그 모양이 아니다.

---

## 4. 최상위 필드

| 필드 | 값 | 근거 |
|---|---|---|
| `schemaVersion` | `1` | **[바이너리]** 상위 버전이면 *"declares schema version … which is newer than the supported version"*로 거부 |
| `id` | `user-monstrous-ledger-squad-v1` | **[바이너리]** ≤200자, 제한된 문자셋. 폴더 이름(`monstrous_squad`)과 스쿼드 정체성(LEDGER)을 둘 다 담는다 |
| `name` | `LEDGER Squad` | **[바이너리]** ≤200자. 제출 카피(`docs/ideation/final_ideation/submission-copy.md`)가 이 이름으로 쓰여 있다 |
| `description` | 아래 | **[바이너리]** ≤5,000자 |
| `icon` | `📒` | 장부(ledger) |
| `category` | `custom` | **[문서]** 닫힌 열거형 `development` / `content` / `research` / `review` / `custom`. **[디스크]** 빌트인 5개가 앞의 넷을 쓴다. 우리는 어느 쪽도 아니다 |
| `isBuiltin` | `false` | **[문서]** 임포트가 어차피 `false`로 덮어쓴다. 명시해 둔다 |
| `suggestedModels` | 실제로 배정한 모델만 | **[문서]** 정보성 필드로, 여기에 모델을 적는다고 배정되지 않는다. 배정은 `preferredModelId`만 한다 |
| `i18nKey` | **넣지 않는다** | **[디스크]** 빌트인 전용 번역 키다. 사용자 템플릿이 없는 키를 가리키면 UI에 이름이 비어 보일 수 있다. 얻을 것이 없다 |

---

## 5. 에이전트별 필드

### 5-1. `role` — 부분 일치가 안 된다

**[바이너리]** 앱은 `role` 문자열을 소문자로 바꾼 뒤 **전체 일치**로 본다. 받는 값은 `planner` / `developer` / `reviewer` / `writer` / `custom` 다섯이고, 나머지는 전부 `{"type":"custom","value":"<원문>"}`이 된다.

**[디스크]** 실제 임포트 결과가 이것을 증명한다 — `"Frontend Developer"` → `{"type":"custom","value":"Frontend Developer"}`. `Developer`가 들어 있는데도 custom이다.

| 에이전트 | `role` | 매핑 | 왜 |
|---|---|---|---|
| Router | `Planner` | `planner` | **강제다.** 스쿼드에 planner가 정확히 하나 있어야 `plannerAgentId`가 정해진다 |
| Architect | `Architect` | custom | 알려진 다섯에 해당하는 것이 없다 |
| Editor | `Developer` | `developer` | 하는 일이 그대로 "writes and modifies code"다 |
| Solver | `Solver` | custom | 이름이 곧 설명이다 |
| Reviewer | `Reviewer` | `reviewer` | §5-2에서 다시 본다 |

### 5-2. 알려진 role은 Planner 프롬프트에 설명 한 줄을 덧붙인다 — 새로 확인한 사실

**[바이너리]** 팀 명단 빌더 근처에 role 설명 네 줄이 리터럴로 박혀 있다. 바로 옆에 `No description`과 `No agents available.`이 있어 같은 함수가 쓴다는 것이 드러난다.

```
Coordinator — decomposes and distributes tasks
Developer   — writes and modifies code
Reviewer    — reviews code and ensures quality
Writer      — creates documentation and content
```

**즉 `role: "Reviewer"`를 쓰면 Planner의 팀 명단에 "reviews code and ensures quality"가 실린다.** 우리 Reviewer는 math·generic 문항에서도 마지막 웨이브를 혼자 맡는데, 그 문항들에는 코드가 없다.

**그럼에도 `Reviewer`를 유지한다.** 이유 셋이다.

1. Router의 Layer 3이 세 플랜 모두에서 `T -> Reviewer`를 **명시적으로** 지정한다. 명단 한 줄보다 강한 지시다.
2. custom으로 바꾸면 설명이 "틀린 한 줄"에서 **`No description`**으로 바뀔 뿐, 우리가 원하는 문장이 들어가지는 않는다. 위 리터럴 넷 밖의 값을 넣을 통로가 없다.
3. 바꾸는 것 자체가 되돌리기 쉬운 한 단어짜리 변경이라, **먼저 재고 나서 바꾸는 것이 옳다.** 점검표 15번이 그 측정이다.

### 5-3. `icon`

Router 🗺 / Architect 📐 / Editor 🔧 / Solver 🧮 / Reviewer 📤. 시각화에서 웨이브별 담당자를 눈으로 구분하는 데만 쓴다. 토큰 비용 없음.

### 5-4. `systemPrompt` — 3층 배치를 바이트 단위로 유지한다

**[바이너리]** 상한은 에이전트당 50,000자다. 현재 최대는 Architect 14,019자.

Layer 1(공통 계약)은 **9,510자**이고 다섯 에이전트가 **바이트 단위로 같다** — `sha256` 앞 16자리 `126b9dab97c5231e`. `tools/validate_template.py`가 매번 이것을 검사한다.

프롬프트 본문은 `docs/ideation/final_final_ideation/spec/squad-template.json`에서 **한 글자도 바꾸지 않고** 가져왔다. 이 문서의 작업 범위는 JSON 설정 계층이고, 프롬프트는 스펙의 산출물이다. 프롬프트에 대한 제안은 `00-기획안.md` §6에 **제안으로만** 적었다.

---

## 6. 템플릿 밖 — 넣는 경로는 있다. 먹는다는 증거는 아직 없다

**먼저 결론 셋을 갈라 적는다. 셋의 확실성이 서로 다르다.**

| 주장 | 상태 |
|---|---|
| `maxTokens`·`maxToolCalls`를 **템플릿 JSON에는 못 넣는다** | **확정.** `AgentTemplate`은 9개 키뿐이고 `settingsOverrides`가 없다 |
| `aigo squad update`로 **값을 넣을 수는 있다** | **확정.** `UpdateSquadRequest.agents`가 `Vec<AgentConfig>`이고(심볼 확인), `AgentConfig`에 `settingsOverrides`가 있다 |
| 스쿼드 실행이 그 값을 **읽는다** | **미확인. 오히려 안 읽을 가능성이 크다** — §6-4 |

### 6-0. 왜 "안 읽을 가능성이 크다"인가

**[바이너리]** `AgentSettingsOverrides`는 `squad::`가 아니라 **`agent_profile::types`**에 있다. 그리고 `squad::` 네임스페이스에서 설정을 해석하는 함수는 딱 하나다.

```
backend_ai_go_lib::squad::execution::effective_enabled_tools
```

`effective_max_tokens`도, `effective_settings`도, `resolve_agent_settings`도 없다. **`disabledTools`·`toolPermissionOverrides`가 무효였던 것과 정확히 같은 모양이다** — 구조체에 자리가 있고, JSON을 왕복하고, 실행 경로가 안 읽는다.

**확정은 아니다.** 이름 붙은 함수 없이 인라인으로 읽을 수도 있다. 그래서 §6-4에 확인 방법을 적었고, 그 전까지는 **넣되 믿지 않는다.**

### 6-1. 넣는 경로 — `aigo squad update`가 `agents` 배열을 통째로 받는다

**[바이너리]** `UpdateSquadRequest`의 serde field visitor(`0x100be75f8`)를 디스어셈블해 필드 이름을 문자 단위로 복원했다. 다섯 개다.

```
name · description · workspacePath · agents · plannerAgentId
```

그리고 여기 실리는 에이전트는 템플릿의 `AgentTemplate`(9개 키)이 아니라 **`AgentConfig`(14개 키)**다 — `settingsOverrides`, `toolConfig`, `modelPreferences`, `instructions`, `executionMode`를 전부 포함한다.

```
aigo squad update <ID> <BODY_JSON>     # BODY_JSON matching `UpdateSquadRequest`
```

**즉 순서가 이렇게 된다.**

```bash
# 1. 템플릿으로 스쿼드를 만든다 (프롬프트·모델·도구·메모리가 들어간다)
aigo squad template import squad-template.json
aigo squad create '{"name":"LEDGER Squad","workspacePath":"…","templateId":"user-monstrous-ledger-squad-v1"}'

# 2. 만들어진 스쿼드를 읽어 update 본문을 만든다
aigo squad show <SQUAD_ID> > squad.json
python3 tools/make_update_body.py squad.json > update.json

# 3. 템플릿이 못 실은 것을 넣는다
aigo squad update <SQUAD_ID> "$(cat update.json)"

# 4. 예산은 또 다른 명령이다
aigo squad budget set <SQUAD_ID> "$(cat budget.json)"
```

`tools/make_update_body.py`는 **이름으로 에이전트를 맞춰** 앱이 만든 id를 보존하고, `settingsOverrides`를 넣으면서 **템플릿이 이미 말한 것을 다시 못 박는다** — 모델·도구·메모리·시스템 프롬프트. 생성 시점에 덮어써지는 것이 관측된 값이 있기 때문이다(§7 확인 2번).

### 6-2. 넣는 값과 그 근거

| 키 | 값 | 근거 |
|---|---|---|
| `maxTokens` | **8192** (전원) | 튜닝값이 아니라 **잘림 0%가 관측된 최소 상한**이다. 상한 2,048에서 수학 응답 450건 중 **49건(10.9%)이 최종 답 없이 끝났고**, 8,192에서는 0건이었다. 잘린 답은 `extraction_failed`, **팀 책임 0점**이고 여유분은 토큰일 뿐이라 안전한 쪽으로 틀었다. `03-검증과-배포.md`의 스윕이 내린다 |
| `maxToolCalls` | Router **8**, 나머지 **0** | 넷은 `enabledTools: []`라 도구가 애초에 0개다. 그래서 0은 통제가 아니라 **선언**이고, 앱이 0을 "없음"으로 읽든 "무제한"으로 읽든 결과가 같다. Router만 다르다 — `create_task`는 `toolConfig`가 아니라 **Planner 전용 경로**로 들어오고, 플랜 A가 3개를 만든다. 여유를 두어 8 |
| `maxIterations` | `null` | `BudgetConfig.maxAgentTurns: 4`가 이미 턴을 묶는다. 같은 것을 두 군데서 조이면 어느 쪽이 잘랐는지 모른다 |
| `defaultTimeout` | `null` | `BudgetConfig.taskTimeoutSecs: 120`이 이미 있다 |
| `contextCompressionThreshold` | `null` | **위험해서 비운 것이 아니라, 값을 몰라서 비웠다.** 컨텍스트 압축은 문맥을 다시 쓰는 동작이고, **다시 쓰인 앵커는 적용되지 않는 패치다.** 단위도 기본값도 확인되지 않았다. 압축이 실제로 걸리는지가 `03-검증과-배포.md` 점검표에 있다 |
| `allowedPaths` | `null` | 파일 도구가 하나도 안 켜져 있어 적용될 경로가 없다 |

### 6-3. 먹는지 확인하는 법

`settingsOverrides`가 실제로 LLM 호출에 반영되는지는 **한 번 돌려 보면 끝난다.**

| 확인 | 방법 | 결과 해석 |
|---|---|---|
| `maxTokens`가 먹나 | `maxTokens`를 **64** 같은 극단값으로 넣고 math 문항 1건 실행 | 응답이 잘리면 **먹는다.** 멀쩡하면 안 먹거나 다른 값이 이긴다 |
| `maxToolCalls`가 먹나 | Router의 값을 **1**로 낮추고 coding 문항 실행 | 태스크가 1개만 생기면 먹는다 |

**먹지 않는다면 남는 손잡이는 `BudgetConfig`뿐이다** — 그쪽은 스쿼드 예산 경로라 확실히 작동한다.

| | 무엇을 조이나 | 단위 |
|---|---|---|
| `maxTokensPerAgent` **50,000** | 한 에이전트가 **누적으로** 쓸 수 있는 총량 | 에이전트별 |
| `maxTokensPerTask` **40,000** | 태스크 하나의 총량 | 태스크별 |
| `maxAgentTurns` **4** | 턴 수 | 에이전트별 |

**단, 이 셋은 누적 예산이지 호출당 출력 상한이 아니다.** 잘림(`extraction_failed`)을 막는 것은 호출당 `max_tokens`이고, 그것을 못 정하면 전역 `inference.defaultMaxTokens`(현재 **131072**)가 걸린다. 상한이 너무 커서 잘릴 일은 없고, 대신 **모델이 길게 쓰는 것을 막지 못한다** — 토큰 효율 30점 쪽 손해다.

### 6-4. 여전히 JSON으로 못 하는 것 하나

| 항목 | 어디서 | 왜 |
|---|---|---|
| 전역 `inference.defaultReasoningEffort` | 앱 설정 화면 | **[디스크]** 현재 값 `none`. 스쿼드도 에이전트도 아닌 **앱 전역 설정**이라 어느 JSON에도 자리가 없다 (`02-모델-배정-분석.md` §1-2) |

---

## 7. 이 표에서 확인이 남은 것

정직하게 남긴다. 전부 `03-검증과-배포.md`의 점검표에 항목이 있다.

| # | 미확인 | 확인 방법 |
|---|---|---|
| 1 | `disabledTools`(22개)·`toolPermissionOverrides`(22개)를 채운 템플릿이 임포트를 통과하는가 | `aigo squad template import` 후 오류 여부. 개수 한도는 각 100이므로 **[바이너리]** 통과해야 정상이고, 값 `never_allow`는 공개 프로필 46개에서 전례가 0이다 |
| 2 | 임포트·생성 후 `preferredModelId`가 우리 값으로 남는가 | **[디스크]** 이 PC의 기존 스쿼드 8개는 템플릿에 모델이 없었는데도 전부 `unsloth/gpt-oss-20b`로 채워져 있었다. 앱이 생성 시점에 값을 **만들어 넣는다** |
| 3 | `enabledTools: []`가 워커 프롬프트의 `## Important: File Tool Paths` 블록을 없애는가 | 실행 후 세션 파일 `messages[0].content` 확인 |
| 4 | `role: "Reviewer"`의 설명 줄이 Planner 프롬프트에 실제로 들어가는가 | math 문항 1건 실행 후 플랜 확인 |
| 5 | 템플릿 `id` 길이 상한 | `name` ≤200은 `0x101da5828`에서 상수 `0xc8`로 확인했지만, `id` 검사는 다른 함수에 있고 상수를 못 짚었다. 현재 값 `user-monstrous-ledger-squad-v1`은 30자라 어느 상한이든 안전하다 |

**닫힌 질문 둘도 적어 둔다.** ① `minContextWindow`가 배선돼 있는가 — **아니다.** `resolve_agent_readiness` 디스어셈블리로 확정(§2-0). ② 포털이 hidden 실행의 per-item 응답 본문을 돌려주는가 — **아니다.** `BreakdownRow`가 스키마 주석에 *"Aggregated across items on purpose"*라고 적어 두었다.
