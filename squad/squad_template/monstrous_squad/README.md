# monstrous_squad — LEDGER Squad 제출 템플릿

JUNCTIONX Korea 2026 · Lablup + FuriosaAI 트랙 "Build the Ultimate Agent Squad"
대상: Backend.AI GO 데스크톱 앱 1.12.1

| 파일 | 내용 |
|---|---|
| **`squad-template.json`** | 제출용 템플릿. 에이전트 5명, 도구 0개, 메모리 off |
| **`squad-template.min.json`** | 대비책. `toolConfig`의 검증되지 않은 세 필드를 비운 판. 나머지는 바이트 단위로 동일 |
| **`budget.json`** | `aigo squad budget set`에 그대로 넣는 본문. 예산은 템플릿에 안 들어간다 |
| `tools/build_template.py` | 스펙 템플릿에서 위 두 JSON을 생성. 프롬프트가 바뀌지 않았음을 매번 확인한다 |
| `tools/validate_template.py` | 임포트 한도 + 실제 채점기(`grade.py`)로 검사. LLM 호출 0회 |
| `tools/make_update_body.py` | 템플릿이 못 싣는 `maxTokens`·`maxToolCalls`를 넣는 `aigo squad update` 본문 생성 |

기획·근거는 `docs/ideation/final_final_ideation/plan/`에 있다.
설계 원본은 `docs/ideation/final_final_ideation/spec/`이고, 다섯 `systemPrompt`는 거기서 **한 글자도 바꾸지 않고** 가져왔다.

## 세 줄 요약

에이전트 **5명**. 하나가 읽고 나누고(Router), 하나가 어디를 고칠지 정하고(Architect), 하나가 고치고(Editor), 하나가 풀고(Solver), 하나가 내용과 형식을 둘 다 검토한 뒤 채점되는 블록을 낸다(Reviewer).

모델은 둘이다. **gpt-oss-120b**가 네 자리 — 배치 64에서도 coding 요청이 들어가는 유일한 모델이고, 같은 모델을 쓰면 문항 안에서 프리픽스 캐시가 걸린다. **K-EXAONE-236B**가 Solver 한 자리 — MMLU-Pro 83.8이 최고이고, 좋은 수치가 **우리가 못 만지는 설정에 걸려 있지 않은 유일한 모델**이다. math·generic은 벤치마크 가중치의 절반인데 토큰 지출은 전체의 15% 미만이라 배율 ×3을 감당할 수 있는 유일한 자리이기도 하다.

**도구는 다섯 자리 전부 0개다.** 평가 중에는 어차피 도구가 없고, 도구가 있으면 모델이 답을 워크스페이스 파일에 쓰고 응답에는 요약만 낸다 — 이 PC의 실행 로그에 그 사고가 두 건 남아 있다.

## 바로 쓰기

```bash
# 검사 (LLM 호출 0회)
python3 tools/build_template.py
python3 tools/validate_template.py squad-template.json

# 배포 — JSON 셋이 서로 다른 명령으로 들어간다
aigo squad template import squad-template.json
aigo squad create '{"name":"LEDGER Squad","workspacePath":"<절대경로>","templateId":"user-monstrous-ledger-squad-v1"}'

aigo squad show <SQUAD_ID> > /tmp/squad.json                       # 출력 상한·도구 라운드
python3 tools/make_update_body.py /tmp/squad.json > /tmp/update.json
aigo squad update <SQUAD_ID> "$(cat /tmp/update.json)"

aigo squad budget set <SQUAD_ID> "$(cat budget.json)"              # 예산
```

**설정이 들어갔는지는 UI가 아니라 파일로 확인한다.** 도구가 0개면 화면에 고를 것이 없는 것이 정상이라 UI로는 판별이 안 된다.

```bash
python3 -m json.tool ~/Library/Application\ Support/ai.backend.go/squads/<SQUAD_ID>.json \
  | grep -E 'preferredModelId|enabledTools|memoryEnabled|maxTokens|maxToolCalls'
```

**헤드리스에서는 Planner가 돌지 않는다.** 검증은 데스크톱 앱을 띄운 상태에서 한다.
**실행마다 워크스페이스를 스냅샷한다** (`viz/tools/snapshot-logs.sh`). 로그는 덮어써진다.

## 준비된 실험 하나 — 기본값으로는 꺼져 있다

`tools/build_template.py`의 `REASONING_LINE`을 `{"Editor": "Reasoning: high"}`로 바꾸면, Editor의 **Layer 3 첫 줄**에 그 문장이 붙는다. Layer 1은 바이트 단위로 그대로 유지된다.

gpt-oss는 강도를 harmony 시스템 메시지의 한 줄로 읽고 기본값은 `medium`이다. 이 앱의 `systemPrompt`가 그 자리에 닿는지는 **미확인**이고, 닿는다면 Editor SWE-bench 기대값이 **52.6 → 62.4**로 오른다(coding 가중치 0.5 → 총점 +4.9%p). 판정은 싸다 — 강도가 실제로 바뀌면 응답 토큰이 8~24배로 는다.

**먼저 `PublishedCaps`를 읽는다.** `high`는 호출당 약 19,300토큰이라, 캡이 낮으면 실험 성공이 곧 `capped` 0점이다. 자세히는 `plan/02-모델-배정-분석.md` §1-2.

## 템플릿 스키마에 자리가 없는 값들

`AgentTemplate`은 9개 키뿐이고 `settingsOverrides`가 없다. **넣는 경로는 따로 있다** — `UpdateSquadRequest.agents`가 `Vec<AgentConfig>`이고(심볼 확인) `AgentConfig`에 `settingsOverrides`가 있다.

> ⚠️ **넣는 것과 먹는 것은 다르다.** `AgentSettingsOverrides`는 `squad::`가 아니라 `agent_profile::types`에 있고, `squad::` 안에서 설정을 해석하는 함수는 `effective_enabled_tools` 하나뿐이다. `disabledTools`·`toolPermissionOverrides`가 무효였던 것과 같은 모양이라 **스쿼드 실행이 이 값을 읽는다는 증거가 없다.** `maxTokens`를 64 같은 극단값으로 넣고 한 문항 돌리면 30초에 판별된다 — `plan/01` §6-3.

| 값 | 어디로 | 넣는 값 |
|---|---|---|
| `maxTokens` (출력 상한) | `aigo squad update` | **8192** 전원. 잘림 0%가 관측된 최소 상한 (2,048에서는 수학 응답 450건 중 49건이 최종 답 없이 끝났다) |
| `maxToolCalls` (도구 라운드) | 같음 | Router **8**, 나머지 **0**. `create_task`는 Planner 전용 경로로 들어오고 플랜 A가 3개를 만든다 |
| `maxIterations` · `defaultTimeout` | 같음 | `null` — `BudgetConfig`의 `maxAgentTurns`·`taskTimeoutSecs`가 이미 조인다 |
| `contextCompressionThreshold` | 같음 | `null` — 압축은 문맥을 다시 쓰고, **다시 쓰인 앵커는 적용되지 않는 패치다.** 단위도 기본값도 미확인 |
| 전역 `inference.defaultReasoningEffort` | **앱 설정 화면** | 어느 JSON에도 자리가 없는 유일한 항목. 이 PC의 현재 값은 `none` |

## 채우지 않은 필드와 그 이유

| 필드 | 값 | 이유 (자세히는 `plan/01-JSON-필드-결정표.md`) |
|---|---|---|
| `enabledTools` | `[]` | **이것 하나가 실제로 작동하는 손잡이다.** `build_tools_for_agent`는 이 목록이 비면 도구 0개로 모델을 부른다(디스어셈블리 확인). 평가 중에는 어차피 도구가 없고, 도구가 있으면 답이 워크스페이스 파일로 새어 `extraction_failed`가 된다 |
| `disabledTools` | 22개 전부 | 스쿼드 실행 경로가 **이 필드를 읽지 않는다.** 기록이지 방어선이 아니다 — 데스크톱 채팅 경로에서만 유효하다 |
| `toolPermissionOverrides` | 22개 `never_allow` | 같음. 권한 판정은 사람에게 승인을 묻는 채팅 경로에만 있다 |
| `customToolConfigs` | `{}` | 스키마가 *"arbitrary JSON"*이고 실사용 예시가 카탈로그 46개 + 빌트인 5개 전부에서 `{}`다. 모르는 형태에 값을 넣으면 임포트 실패 위험만 산다 |
| `minContextWindow` | `null` | **지금은 무효다** — 모델 배정 경로에 컨텍스트를 읽는 명령이 없다. 그러나 배선되면 앱 카탈로그가 gpt-oss-120b를 **2048**로 적어 두었으므로 우리 모델이 탈락하고, Planner가 모델을 잃으면 요청 전문이 전 에이전트에 뿌려진다 |
| `requiresToolCalling` | `false` | 같음. 배선되면 카탈로그가 gpt-oss-120b의 capabilities를 `["chat","code"]`로 적으므로 세 모델 중 둘이 탈락한다. 스키마 기본값이 `true`라 반드시 명시한다 |
| `requiresVision` | `false` | 세 트랙 전부 텍스트 |
| `preferredProviderId` | 없음 | provider id는 설치할 때 생기는 로컬 UUID다. 심사자 기기에는 없다 |
| `memoryEnabled` | `false` **(Planner 포함)** | 메모리 블록은 **시스템 프롬프트 안으로 들어가고**(`assemble_agent_chat_system_prompt`) 문항마다 달라진다 — 켜는 순간 그 에이전트의 프리픽스 캐시가 그 자리에서 끝난다. Router는 889회 전부 도는 자리라 비용도 가장 크다(약 3.56M, 총액의 9%). 그리고 실측에서 저장된 것은 도움이 아니라 환각이었다 — 문항 ID를 프로젝트 이름으로 착각한 기록이 다음 실행에 다시 실린다 |
| `i18nKey` | 없음 | 빌트인 전용 번역 키. 사용자 템플릿이 없는 키를 가리키면 UI 이름이 빈다 |
