# 03. AI:GO (Backend.AI GO) Squad 완전 가이드

> 출처: 공식 매뉴얼 `https://go.backend.ai/en/manual/` 전 섹션을 크롤링해 정리했다.
> 릴리스 저장소: `https://github.com/lablup/backend.ai-go-releases` (2026-08 기준 최신 v1.12.x 계열)
> 이 트랙의 **필수 제약**이 "문제 해결 과정의 결정적 부분은 AI:GO의 agent squad 기능 위에 구현할 것"이므로, 이 문서가 사실상 구현 매뉴얼이다.

---

## 1. AI:GO가 무엇인가

Backend.AI GO는 Lablup이 만든 **크로스 플랫폼 데스크톱 애플리케이션**이다. 로컬 머신에서 LLM을 돌리고, 이미지 생성·음성 인식을 하고, 멀티 에이전트 스쿼드를 오케스트레이션한다.

- **런타임**: Rust로 작성된 코어 + Tauri 데스크톱 셸. 데스크톱은 Tauri IPC, 헤드리스는 REST/SSE로 같은 런타임을 쓴다.
- **추론 엔진**: `llama.cpp`(CUDA/ROCm/oneAPI/CPU), Apple `MLX`(Metal), 컨테이너형 `vLLM`·`SGLang`, `stable-diffusion.cpp`.
- **모델 소스**: Hugging Face에서 앱 안에서 직접 검색·다운로드. 클라우드 provider(OpenAI/Anthropic/Gemini/OpenAI 호환) 연동도 가능.
- **API**: OpenAI 호환. Continuum Router가 기본 포트 `39080`에서 `/v1/*`를 서빙한다. Management API는 기본 `8001`.
- **CLI**: `aigo` (Rust). 헤드리스 서버 바이너리는 `aigo-server`.

### 네 가지 작동 모드 (런처 홈)

| 모드 | 성격 | 이번 트랙에서의 위치 |
|---|---|---|
| **Chat** | 모델 하나와 1:1 대화 | 프롬프트 실험용 |
| **Cowork** | 주 에이전트가 하위 에이전트에 위임. `@mention` 디스패치 | 즉흥적 탐색용 |
| **Squad** | **자율 멀티 에이전트 팀. 명시적 플랜 + 의존성 그래프 + 웨이브 실행** | **← 이번 트랙 필수** |
| **Draw** | 이미지 생성 | 해당 없음 |

### Cowork vs Squad 차이 (공식 비교표)

| 항목 | Cowork | Squad |
|---|---|---|
| 에이전트 | 단일 (하위 에이전트 선택적) | 여러 명, 각자 역할이 다른 명명된 에이전트 |
| 계획 | 암묵적 (에이전트가 알아서 단계 결정) | **명시적 플랜 + 태스크 그래프 + 의존성** |
| 워크스페이스 | 기존 디렉터리에 폴더 권한 | 스쿼드마다 전용 워크스페이스 |
| 메모리 | 공유 메모리 | 에이전트별 메모리 + 교차 검색 |
| 예산 | 세션당 토큰 추적 | **에이전트별·태스크별·전체 세분화 한도** |
| 적합 | 임시 작업, 탐색 | 대규모·다단계·협업 작업 |

---

## 2. Squad의 실행 모델

### 전체 흐름

```
사용자 요청
   ↓
[1] Planner 에이전트가 플랜 생성
   ↓
[2] 사용자 승인 (auto-approve로 건너뛸 수 있음)
   ↓
[3] Wave 실행 — 의존성이 충족된 태스크 묶음을 병렬로
   ↓
[4] Aggregation — 결과 수집·합성
   ↓
최종 산출물
```

### 실행 생명주기 (`Execution Lifecycle`)

| 단계 | 설명 |
|---|---|
| `Planning` | Planner가 태스크 플랜 생성 |
| `Awaiting Approval` | 사용자 검토 대기 (auto-approve 시 생략) |
| `Executing` | 웨이브 단위로 태스크 실행 중 |
| `Aggregating` | 모든 태스크 결과 수집·합성 |
| `Completed` | 완료, 최종 결과 확보 |
| `Failed` | 오류로 중단 |
| `Cancelled` | 사용자가 수동 취소 |

### 플랜의 구조

Planner가 만드는 플랜에 들어가는 것:
- **Title** — 계획된 작업의 짧은 요약
- **Tasks** — 개별 작업 단위. 각 태스크는 다음을 가진다:
  - 제목과 설명
  - **담당 에이전트**
  - **다른 태스크에 대한 의존성**
  - 우선순위 (`low` / `medium` / `high` / `critical`)

### Wave 실행 규칙

- 같은 웨이브 안의 태스크는 **병렬 실행**된다.
- 이전 웨이브의 모든 태스크가 끝나야 다음 웨이브가 시작된다.
- **태스크가 실패하면 뒤 웨이브의 의존 태스크는 자동으로 skip된다.**

예시 (공식 문서의 예):
```
Wave 1: Design API schema
Wave 2: Implement endpoints | Write validation   (병렬)
Wave 3: Write unit tests
Wave 4: Code review
```

> **이번 트랙 관점의 함의** — 벤치마크 문항 하나가 스쿼드 실행 하나에 대응한다면, 웨이브 구조가 곧 "읽기 → 수정 → 검증 → 포기 판단"의 파이프라인이 된다. 문제 지문이 요구한 네 가지 역할이 그대로 웨이브에 매핑된다.

---

## 3. Squad 생성 — 4단계 위저드

**Squad 페이지 → New Squad**

### Step 1: Basic Info
이름(필수)과 설명(선택). 목적이 드러나는 이름을 쓸 것.

### Step 2: Workspace
스쿼드가 파일을 저장할 **워크스페이스 디렉터리**를 고른다. 위저드가 검사하는 것:
- 경로가 존재하고 쓰기 가능한가
- 다른 스쿼드가 같은 디렉터리를 쓰고 있지 않은가

### Step 3: Agents

에이전트를 구성한다. 세 가지 출발점:
- 템플릿에서 시작 (사전 채워짐)
- **Add Agent**로 직접 추가
- Cowork 에이전트 프로필 마켓플레이스에서 임포트

에이전트마다 설정하는 것:

| 설정 | 내용 |
|---|---|
| **Name** | 표시 이름 |
| **Role** | Planner / Developer / Reviewer / Writer / Custom |
| **System Prompt** | 이 에이전트의 행동과 전문성을 정의하는 지시문 |
| **Tools** | 이 에이전트가 쓸 수 있는 도구 (파일 읽기/쓰기, 메모리, 검색 등) |
| **Memory** | 영속 메모리 파일을 줄 것인가 |

#### 역할별 성격

- **Planner** — 팀을 조율. 요청 분석, 플랜 생성, 태스크 배정, 진행 추적. **스쿼드당 정확히 한 명을 지정한다.**
- **Developer** — 코드 작성·수정. 프로젝트 파일 읽기/쓰기를 위한 파일시스템 도구 접근.
- **Reviewer** — 품질·보안·정확성 검토. 보통 읽기 전용 권한.
- **Writer** — 문서·기사 등 글 작성.
- **Custom** — 위 범주에 안 맞는 역할. 이름을 직접 짓고 시스템 프롬프트를 맞춘다.

### Step 4: Review
전체 구성 확인 후 **Create**. 워크스페이스 디렉터리가 자동 생성·초기화된다.

### 스쿼드 전체 모델 일괄 변경

스쿼드 상세 페이지 헤더 또는 스쿼드 카드의 **Set model** 액션에서 **Set model for all agents**를 쓴다.
- 모델을 한 번만 고르면 된다.
- 에이전트별 목록에서 기본은 전원 선택. 특정 에이전트를 토글 해제하면 그 에이전트의 모델은 그대로 둔다.
- **해당 스쿼드에만** 원자적으로 적용된다. 다른 스쿼드에는 영향 없음.

---

## 4. Squad Template JSON 스키마 ★ 제출물의 실체

**제출 포털이 요구하는 "Squad Template JSON"이 바로 이 형식이다.** 정확히 익혀야 한다.

템플릿은 `camelCase` 필드로 직렬화된다. Rust 백엔드(`src-tauri/src/squad/templates.rs`)와 TypeScript 프론트엔드(`src/types/squad/templates.ts`)가 같은 형태를 공유한다.

```json
{
  "schemaVersion": 1,
  "id": "user-…",
  "name": "Full-Stack Dev Team",
  "description": "A complete development team…",
  "icon": "🛠️",
  "category": "development",
  "isBuiltin": false,
  "suggestedModels": [],
  "i18nKey": {
    "name": "squad.templates.builtin.fullstackDevTeam.name",
    "description": "squad.templates.builtin.fullstackDevTeam.description"
  },
  "agents": [
    {
      "name": "Planner",
      "role": "Planner",
      "systemPrompt": "You are a technical project planner…",
      "tools": ["read_file", "write_file"],
      "toolConfig": {
        "enabledTools": ["read_file", "write_file"],
        "disabledTools": [],
        "toolPermissionOverrides": {},
        "customToolConfigs": {}
      },
      "modelPreferences": {
        "requiresToolCalling": true,
        "requiresVision": false
      },
      "memoryEnabled": true,
      "icon": "📋",
      "i18nKey": {
        "name": "…",
        "role": "…",
        "systemPrompt": "…"
      }
    }
  ]
}
```

### 최상위 필드

| 필드 | 타입 | 설명 |
|---|---|---|
| `schemaVersion` | number | 스키마 버전. 없으면 `1`로 간주 |
| `id` | string | 고유 식별자. 내장은 `builtin-…`, 사용자는 `user-…` |
| `name` | string | 표시 이름 |
| `description` | string | 짧은 설명 |
| `icon` | string | 이모지 또는 아이콘 식별자 |
| `category` | string | `development` / `content` / `research` / `review` / `custom` 중 하나 |
| `isBuiltin` | boolean | 내장 템플릿 여부. **임포트 시 항상 `false`로 강제됨** |
| `suggestedModels` | string[] | 정보성 필드일 뿐, 동작에 영향 없음 |
| `i18nKey` | object? | 필드별 번역 키 (선택) |
| `agents` | array | 에이전트 정의 배열 |

### 에이전트 필드

| 필드 | 타입 | 설명 |
|---|---|---|
| `name` | string | 에이전트 표시 이름 |
| `role` | string | 역할 라벨. `Planner`/`Developer`/`Reviewer`/`Writer`는 알려진 역할 타입으로 매핑되고, **그 외 문자열은 커스텀 역할이 된다** |
| `systemPrompt` | string | 시스템 프롬프트 |
| `tools` | string[] | 활성 도구 이름의 레거시 편의 목록. `toolConfig`가 있으면 그것을 미러링 |
| `toolConfig` | object? | 전체 도구 설정. **있으면 `tools`보다 우선한다** |
| `modelPreferences` | object? | 모델 선호 (선호 모델, 최소 컨텍스트 윈도우, 도구 호출/비전 요구 여부) |
| `memoryEnabled` | boolean | 이 에이전트의 메모리 활성화 여부 |
| `icon` | string | 이모지 또는 아이콘 식별자 |
| `i18nKey` | object? | 필드별 번역 키 (선택) |

`tools`만 있고 `toolConfig`/`modelPreferences`/`schemaVersion`/`i18nKey`가 없는 구버전 템플릿도 로드된다. 누락 필드는 안전한 기본값으로 채워진다.

### 템플릿 저장·내보내기·가져오기

- **저장**: 스쿼드 목록의 카드 액션 또는 스쿼드 상세 헤더의 **Save as template**. 저장 시 **전체 충실도**로 보존된다 — 도구 설정 일체(활성/비활성, 도구별 권한 오버라이드, 커스텀 도구 설정)와 모델 선호 일체(선호 모델, 최소 컨텍스트 윈도우, 도구 호출/비전 요구).
- **내보내기**: 템플릿 카드의 **Export** → JSON 파일 다운로드. ← **제출용 JSON을 뽑는 경로가 이것이다.**
- **가져오기**: 카테고리 탭 옆 **Import template**. 드래그앤드롭 또는 파일 선택. 전송 전에 로컬에서 검증하며, 잘못된 파일은 인라인 오류를 띄운다. 임포트된 템플릿은 항상 사용자 템플릿으로 저장되고, 내장 템플릿과 ID가 충돌하면 자동 재생성된다.

---

## 5. 내장 템플릿 (Built-in Templates)

| 템플릿 | 카테고리 | 에이전트 | 용도 |
|---|---|---|---|
| **Full-Stack Dev Team** | development | Planner, Frontend Dev, Backend Dev, Code Reviewer | 계획과 리뷰가 있는 소프트웨어 개발 |
| **Content Team** | content | Planner, Writer, Editor, Translator | 기사 작성·편집·번역 |
| **Research Team** | research | Planner, Researcher, Analyst, Summarizer | 분석·합성이 있는 심층 조사 |
| **Code Review Team** | review | Planner, Security Reviewer, Performance Reviewer, Style Reviewer | 보안·성능·스타일 코드 리뷰 |
| **Documentation Team** | content | Planner, API Doc Writer, Tutorial Writer, Diagram Creator | 다중 포맷 기술 문서 |

내장 템플릿은 **코드가 아니라 데이터**다. `resources/squad-templates/builtin/*.json`에 JSON 시드 파일로 존재하며 컴파일 시 바이너리에 임베드된다.

> **출발점 추천** — 이번 트랙의 coding 트랙은 **Full-Stack Dev Team**보다 **Code Review Team**의 구조(하나의 대상, 여러 관점의 검증자)가 SWE-bench 채점 방식(fail-to-pass + pass-to-pass)에 더 가깝다. 다만 어느 쪽이든 그대로 쓰지 말고 트랙에 맞춰 재설계할 것.

---

## 6. 워크스페이스와 메모리

### 워크스페이스 레이아웃

스쿼드 생성 시 다음 구조가 만들어진다.

```
my-squad-workspace/
├── .squad-config.json    # 스쿼드 매니페스트 (복원용)
├── plans/                # 생성된 플랜
├── tasks/                # 태스크 출력과 아티팩트
├── agents/               # 에이전트별 파일
│   ├── planner/
│   │   └── memory.md     # Planner의 메모리 파일
│   ├── developer/
│   │   └── memory.md
│   └── reviewer/
│       └── memory.md
└── logs/                 # 실행 로그          ← ★ 시각화 원천 데이터
```

**`logs/`가 시각화 산출물의 1차 데이터 소스가 될 가능성이 높다.** 채점 기준이 "Trace, represented as log (text) data"라고 못박았기 때문이다.

### 메모리 2계층 구조

`memory_enabled`가 켜진 에이전트는 `trigger_interval` 턴마다 LLM 추출 패스가 돈다. 추출된 각 사실은 같은 LLM 호출 안에서 두 계층 중 하나로 분류되어 각각의 저장소로 이중 라우팅된다. 이건 **fire-and-forget 백그라운드 작업**이라 채팅 응답을 막지 않는다.

| 계층 | 이름 | 저장 위치 | 성격 |
|---|---|---|---|
| **Layer B** | project-scoped | `{workspace}/memory/{agent}.md`의 Insights 섹션 | 현재 프로젝트 안에서만 의미 있는 사실 — 파일 배치, 진행 중 결정, 프로젝트 로컬 관례. **다른 스쿼드/프로젝트로 따라가지 않는다.** |
| **Layer A** | experiential | 에이전트 전용 전역 `MemoryNamespace` (`Agent Experience: <이름>`) | 내구성 있는 교차 프로젝트 학습 — 사용자 선호, 재사용 가능한 스킬, 사용자와 엮인 명명 개체. **미래의 스쿼드로 따라간다.** |

- Layer A 네임스페이스의 정체성은 **에이전트의 source profile**로 결정된다. 같은 프로필을 인스턴스화한 두 스쿼드는 하나의 Layer A 네임스페이스를 공유하므로, 에이전트가 프로젝트를 넘나들며 경험을 누적한다.
- Layer A 네임스페이스는 **기본 비활성**이다. 전역 메모리 주입 파이프라인은 활성 네임스페이스만 노출하므로, Memory 페이지에서 수동으로 켜기 전에는 다른 에이전트의 채팅이나 메인 채팅에 자동 주입되지 않는다. 단 **에이전트별 채팅 경로는 이 플래그를 무시하고** 자기 Layer A를 매 전송마다 읽는다.
- 주입 예산: Settings → Memory → Per-agent memory read-back. `memory.maxTokens`의 배수(기본 ×1.0, 범위 0.1~4.0) 또는 절대 토큰 수(1~100000). Layer A 비중 기본 60%(범위 5~95%), 나머지가 Layer B. 합이 2 이상이면 Layer B는 최소 1토큰을 받는다.

### 메모리를 켜야 하는 경우 (공식 권고)

| 상황 | 권고 |
|---|---|
| Planner 에이전트 | **항상 켤 것** — 결정과 프로젝트 맥락을 추적해야 함 |
| 장기 프로젝트 | 지식이 누적되는 핵심 에이전트에 켤 것 |
| 일회성 작업 | 선택 — 메모리는 시작 오버헤드를 더한다 |
| Reviewer 에이전트 | 리뷰 패턴과 반복 이슈 추적에 유용 |

> **이번 트랙에서의 판단** — 벤치마크는 문항마다 독립적인 일회성 작업에 가깝다. 메모리를 켜면 **매 태스크 시작마다 메모리 파일이 컨텍스트에 로드되고**, 추출 패스가 추가 LLM 호출을 발생시킨다. 즉 **토큰 효율 30점을 갉아먹는다.** 그런데 prefix cache 관점에서는 고정된 메모리 블록이 앞에 오면 캐시 히트를 만들 수도 있다. **양쪽을 실측으로 비교할 것.**

### 교차 에이전트 메모리 검색

Memory Search로 모든 에이전트의 메모리 파일을 동시에 검색한다. 특정 에이전트/섹션 필터, 대소문자 구분 토글, 매치 주변 컨텍스트 라인 표시.

---

## 7. 예산과 안전장치 (Budget & Safety) ★ 토큰 효율의 핵심 레버

스쿼드 모니터링 대시보드의 **Budget Config** 패널에서 설정한다.

### 토큰 한도

| 설정 | 기본값 | 설명 |
|---|---|---|
| **Max total tokens** | 100,000 | 실행 전체 최대 토큰 |
| **Max tokens per agent** | 30,000 | 단일 에이전트가 쓸 수 있는 최대 |
| **Max tokens per task** | 10,000 | 단일 태스크 실행의 최대 |

### 실행 한도

| 설정 | 기본값 | 설명 |
|---|---|---|
| **Max concurrent agents** | 3 | 동시 실행 에이전트 수 |
| **Max tasks per plan** | 20 | Planner가 만들 수 있는 최대 태스크 수 |
| **Max plan iterations** | 3 | 플랜이 거부됐을 때 재계획 최대 횟수 |
| **Max agent turns** | 20 | 태스크당 에이전트의 최대 추론 턴 수 |

### 시간 한도

| 설정 | 기본값 | 설명 |
|---|---|---|
| **Execution timeout** | 1,800초 (30분) | 전체 실행 최대 시간 |
| **Task timeout** | 300초 (5분) | 단일 태스크 최대 시간 |
| **Agent idle timeout** | 60초 | 에이전트가 중지되기까지의 최대 유휴 시간 |

### 경고 임계값

기본 80%. 토큰 사용량이 총 예산의 이 비율에 도달하면 알림을 띄운다.

### 안전 이벤트 (시각화에 그대로 쓸 수 있는 이벤트 이름)

| 이벤트 | 발생 조건 | 동작 |
|---|---|---|
| `squad:budget-warning` | 사용량이 경고 임계값 도달 | 대시보드 예산 미터가 호박색으로 강조 |
| `squad:budget-exceeded` | 어떤 한도든 도달 | 실행 자동 일시정지. 실행 중 태스크는 현재 턴까지만 완료, 새 태스크 시작 안 함 |
| `squad:emergency-stopped` | 급격한 토큰 소비 등 위급 상황 | 전 에이전트 즉시 중지, 대기 태스크 취소, 실행 상태 **failed** |

> **주의** — 공식 문서 명시: "Token counting is approximate and may slightly exceed configured limits before the system detects the overage." 토큰 카운팅은 근사치이며 시스템이 초과를 감지하기 전에 한도를 약간 넘길 수 있다. **여유를 두고 한도를 설정할 것.**

> **이번 트랙에서의 활용** — 문제 지문이 "which ones determine when it is time to give up"을 물었다. 그 답의 절반은 **에이전트 설계**(포기 판단 전용 에이전트/프롬프트)이고, 나머지 절반은 **여기 있는 예산 한도**다. `Max agent turns`와 `Max tokens per task`를 낮게 잡는 것이 가장 직접적인 "포기 장치"다.

---

## 8. 모니터링 대시보드 — 6개 탭

| 탭 | 내용 |
|---|---|
| **Overview** | Hero stats, 에이전트 활동(리스트/그리드), 실행 타임라인, 예산 미터, 활동 피드, 메모리 검색 |
| **Chat** | 스쿼드 단위 실행 채팅 |
| **Tasks** | 현재 실행의 칸반 태스크 보드 |
| **Workspace** | 스쿼드 워크스페이스 파일 브라우저 |
| **Discussion** | 멀티 에이전트 Discussion Room |
| **Analytics** | 분석 대시보드 + 실행 이력 |

### Hero Stats
- **Active / Total agents** — 실행 중 / 전체 에이전트 수
- **Session tokens** — 현재 세션의 전 에이전트 누적 토큰
- **Execution phase** — 현재 단계 (idle, planning, executing, aggregating 등)

### Execution Timeline ★ 시각화 참고 대상
에이전트별 상태 전이를 **가로 스윔레인(swimlane)** 으로 보여준다. 색칠된 블록 하나가 전이 하나이며, 그 상태에 머문 시간에 비례해 크기가 정해진다.

색상 규약: 초록 = running, 빨강 = error, 노랑/호박 = created, 파랑 = completed, 회색 = idle.
블록에 hover하면 상태 라벨, 지속 시간, 타임스탬프, (해당 시) 오류 원인이 툴팁으로 뜬다.
스윔레인 아래 시간축은 최초 기록 이벤트부터 현재까지의 상대 타임스탬프를 보여준다.

> **우리 시각화는 이것보다 나아야 한다.** 심사위원은 이 화면을 매일 본다. 같은 것을 다시 만들면 30점 중 상위권을 못 받는다. `06-시각화-설계-가이드.md` 참고.

### Activity Feed
스쿼드 이벤트의 시간순 로그. 최근 **200개** 항목 유지. 실시간 갱신.
포함 이벤트: 에이전트 세션 시작/중지, 태스크 배정·시작·완료·실패, 메모리 갱신, 워크스페이스 파일 변경, 예산 경고와 초과.

### Task Board 컬럼
`Pending`(의존성 대기) / `In Progress` / `Review` / `Done` / `Failed`
태스크 카드에 표시되는 것: 제목과 담당 에이전트, 우선순위(색상 코딩), 다른 태스크 의존성, 결과 요약 또는 오류 메시지.
카드를 클릭하면 **Task Detail** 패널에 전체 설명, 출력, 로그, 토큰 사용량이 뜬다.

### 승인 대기 섹션
어떤 스쿼드의 어떤 에이전트든 도구 실행 승인을 기다리면 Overview 탭 최상단에 **Waiting for Approval** 섹션이 고정된다. 각 행에 에이전트 ID, 승인을 요청한 도구 이름, 위험도 배지(safe/low/medium/high/critical)가 표시된다.

---

## 9. Discussion Room — 구조화된 턴 기반 토론

스쿼드 에이전트들이 공유 주제에 대해 순번대로 응답하는 공간. 오케스트레이터가 턴 순서와 예산을 강제한다.

### 모드

| 모드 | 동작 |
|---|---|
| **Moderated** | 지정된 moderator 에이전트가 턴 순서를 조종하고, 진행을 요약하고, 목표 도달 시점을 판단 |
| **Brainstorm** | moderator 없이 각자 이전 응답에 얹어서 응답. 기본 전략은 아래 Brainstorm(legacy) |

### 전략 (Strategy Selector로 명시적 오버라이드 가능)

| 전략 | 동작 | LLM 호출 비용 |
|---|---|---|
| **Moderated** | 모드와 무관하게 moderator 전략 강제 | 있음 |
| **Brainstorm (legacy)** | 지금까지 가장 적게 말한 참가자를 고름. 동점은 참가자 순서로. **결정론적** | **화자 선택에 LLM 호출 없음** |
| **Round Robin** | 고정 순환: `participants[turns_taken % count]` | **화자 선택에 LLM 호출 없음** |
| **Autonomous** | 각 에이전트가 짧은 "말할래?" LLM 호출로 스스로 판단. 참가자 순서상 처음 yes한 에이전트가 턴을 가짐. 아무도 yes 안 하면 `awaiting user`로 정지. **첫 턴은 게이트를 우회**해 첫 참가자가 결정론적으로 연다 | **참가자 수 × 턴마다 LLM 호출 1회 추가** |

> **토큰 효율 관점** — Autonomous 전략은 매 턴 참가자 수만큼 추가 LLM 호출을 발생시킨다. **이번 트랙에서는 피할 것.** Round Robin이나 Brainstorm(legacy)가 비용이 0이다.

### 종료 조건

- 턴 예산 소진 → `awaiting user`. 사용자가 메시지를 주입하면 예산 사이클 재장전.
- 사용자 **Stop** → `cancelled`, 사유 `UserStopped`.
- **합의 게이트**: Moderated 모드에서 facilitator 에이전트에게 **3턴마다** 수렴 여부를 묻는다. 신뢰도 ≥0.8로 보고하면 `completed`, 사유 `ConsensusReached`.
- **유휴 워치독**: 새 메시지도 큐 입력도 5분간 없으면 자동 완료, 사유 `IdleTimeout`.
- `awaiting user`에서 큐 메시지 없이 10분 → 자동 완료, 사유 `BudgetExhausted`.

### 결론 합성과 실행 인계
- **Synthesize Conclusion** — facilitator가 전체 대화록(매우 길면 head+tail 발췌)을 읽고 구조화된 결론을 반환한다: 짧은 요약, 핵심 논점, 결정 사항, (담당자 제안이 붙은) 액션 아이템.
- **Start Execution** — 결론을 스쿼드 실행 엔진으로 넘긴다. 백엔드가 주제·요약·결정·액션 아이템을 요청 문자열로 조립해 `submit_squad_request`에 넣는다. **요청 문자열은 8 kB 상한**이다.

### 대화록 내보내기
`Markdown` / `JSON` / `Plain text`. 파일명은 `discussion-{short-id}-{sanitized-topic}.{ext}`, 주제 조각은 영숫자 40자로 제한.
**JSON은 디스크 상의 룸 파일과 바이트 동일**하다 — 시각화 도구의 입력으로 쓰기 좋다.

### Discussion Analytics
총 메시지·에이전트 턴 수, 에이전트별 턴 수와 토큰(prompt + completion), 전체 대화록 토큰, **합성 토큰(대화록 총계와 분리)**, 지속 시간, 전략 변경 이력.

---

## 10. 도구(Tools) 31종 — 위험도와 승인 정책

AI:GO는 8개 범주에 걸쳐 **31개 내장 도구**를 제공한다. 채팅 도구 선택기와 에이전트 런타임이 같은 레지스트리에서 파생되므로 두 표면의 도구 정의와 동작이 동일하다.

레거시 이름 별칭: `execute_python`→`run_python`, `list_files`→`list_directory`, `run_shell`→`run_command`.

### 위험 기반 권한 체계

| 등급 | 성격 | 동작 |
|---|---|---|
| 🟢 **Safe** | 공개 데이터 읽기, 계산 | **자동 실행**, 사용자 개입 없음 |
| 🟡 **Moderate** | 개인 파일 읽기, 외부 사이트 접근 | **세션당 1회 승인**. 승인 후 그 대화 내내 자유 사용 |
| 🔴 **Critical** | 데이터 수정, 코드 실행 | **매 호출마다 명시적 승인** |

### 1. 파일시스템 도구

| 도구 | 설명 | 위험도 |
|---|---|---|
| `read_file` | 지정 경로 파일 내용 읽기 | 🟢 Low |
| `write_file` | 지정 경로에 내용 쓰기 | 🟡 Medium |
| `list_directory` | 지정 경로의 파일·디렉터리 나열 | 🟢 Low |
| `create_directory` | 새 디렉터리 생성 | 🟡 Medium |
| `delete_file` | 파일 삭제. **매 호출 승인 필요** | 🔴 High |
| `move_file` | 파일 이동·이름 변경. **매 호출 승인 필요** | 🔴 High |
| `search_files` | glob 패턴 파일 검색 (`*.pdf`, `**/*.ts`) | 🟢 Low |
| `search_content` | 정규식으로 파일 내용 재귀 검색. 바이너리·10MB 초과 파일 자동 skip | 🟢 Low |
| `diff_files` | 두 텍스트 파일 비교, unified diff 반환. 바이너리 거부 | 🟡 Medium |

### 2. 웹 도구

| 도구 | 설명 | 위험도 |
|---|---|---|
| `web_search` | Brave Search 또는 Google(Serper) 웹 검색. **Settings에 API 키 필요** | 🟢 Low |
| `fetch_url` | URL 내용 가져오기. HTML은 Markdown 변환, Readability 기반 보일러플레이트 제거가 기본 (`extract_main_content: false`로 끔) | 🟡 Medium |
| `http_request` | 전체 메서드 지원 HTTP 요청 (GET/POST/PUT/PATCH/DELETE/HEAD/OPTIONS), 커스텀 헤더, 바디, 타임아웃, SSRF 보호 | 🟡 Medium |

### 3. 유틸리티·시스템 도구

| 도구 | 설명 | 위험도 |
|---|---|---|
| `calculator` | 수식 계산. `+ - * / ^ %`, 괄호, `sqrt sin cos log exp` 등 | 🟢 Safe |
| `get_current_time` | 현재 날짜·시각. ISO 8601, Unix timestamp, 사람이 읽는 형식, 커스텀 strftime | 🟢 Safe |
| `get_system_info` | CPU, 메모리, 디스크, OS 정보. 카테고리 필터 가능 | 🟢 Safe |
| `pdf_reader` | PDF 텍스트 추출. 페이지 범위 선택 (`5`, `1-10`, `1,3,5-10`). 호출당 최대 500페이지 | 🟡 Medium |
| `diff_text` | 두 문자열 비교, unified diff 반환 | 🟢 Safe |
| `image_to_base64` | 이미지를 base64 data URI로 변환. PNG/JPEG/WebP/GIF, 리사이즈·포맷 변환 가능 | 🟡 Medium |
| `image_info` | 이미지 메타데이터 (크기, 포맷, 색공간, 파일 크기) | 🟡 Medium |

### 4. 데이터 질의 도구

| 도구 | 설명 | 위험도 |
|---|---|---|
| `json_query` | JSONPath 문법으로 JSON 질의. 문자열 또는 파일에서 읽기 | 🟢 Low |
| `csv_reader` | CSV 읽기·분석. 컬럼 선택, 커스텀 구분자, 행 제한(최대 10,000행) | 🟢 Low |

### 5. 코드 실행 도구 ★ coding 트랙 관련

| 도구 | 설명 | 위험도 |
|---|---|---|
| `run_python` | 샌드박스에서 Python 실행. **매 호출 새 프로세스**라 이전 변수·import는 유지되지 않음. 네트워크 모듈(`socket`, `urllib`, `http`), 프로세스 생성 모듈(`subprocess`, `multiprocessing`), 시스템 모듈(`ctypes`, `signal`) 차단 | 🔴 Critical |
| `run_command` | 셸 명령 실행. 내장 셸 보안 검증기가 위험 명령 차단. **매 호출 명시적 승인 필요** | 🔴 Critical |

**파일시스템 샌드박스**: `run_python`과 `run_command`가 하는 모든 파일 접근은 하나의 **샌드박스 폴더**로 제한된다.
- `run_python`은 샌드박스 폴더를 작업 디렉터리로 삼고, 인터프리터의 파일 프리미티브(`open`, `io.open`, `os.open`, 경로를 받는 `os.*`)를 래핑해 `..` 축약과 심볼릭 링크 추적 후 샌드박스 밖으로 나가는 경로는 `PermissionError`를 던진다.
- `run_command`도 샌드박스 폴더를 작업 디렉터리로 삼고 밖을 가리키는 경로 인자를 거부한다(예: `cat /etc/passwd` 거부).
- Python `tempfile`이 만드는 임시 파일은 샌드박스 폴더로 리다이렉트된다.
- 설정: **Settings > Tools & extensions > Python sandbox → Code execution sandbox folder** (절대 경로). 비워두면 앱 데이터 디렉터리 아래 `code-exec-sandbox`.
- Python 인터프리터를 못 찾으면 같은 화면의 **Python interpreter path**에 실행 파일 경로를 직접 지정한다.

> **공식 경고**: 이건 OS 격리가 아니라 애플리케이션 수준 제한이다. 도구 호출은 신뢰할 수 없는 모델 출력(가져온 콘텐츠에서 오는 간접 프롬프트 인젝션 포함)이 유발할 수 있으므로, `run_python`과 `run_command`는 승인 필요 상태(기본값)로 두라고 권고한다.

### 6. 오디오 도구

`audio_transcribe` — Whisper로 오디오를 텍스트 변환. MP3/WAV/M4A/FLAC/OGG/WebM/MP4/MPEG/MPGA/OGA/Opus. 언어 자동 감지 또는 명시(`en`, `ko`, `ja`). 🟡 Medium. **헤드리스에서는 사용 불가** (`available_in_headless: false`) — `/api/v1/audio/transcriptions` 엔드포인트를 대신 쓴다.

### 7. 이미지 생성 도구

`generate_image` — Settings → Models → Default Image Model로 설정된 기본 이미지 모델로 생성. 로컬 diffusion(sd-server 풀)과 클라우드 provider 이미지 모델(continuum-router 경유) 모두 지원. 🟡 Medium. **헤드리스에서는 사용 불가** — `/api/v1/diffusion/generate`를 대신 쓴다.

### 8. 데스크톱 통합 도구 (헤드리스 불가)

| 도구 | 설명 | 위험도 |
|---|---|---|
| `clipboard_read` | 시스템 클립보드 텍스트 읽기 | 🟢 Low |
| `clipboard_write` | 시스템 클립보드에 쓰기 | 🟡 Medium |
| `notification` | 네이티브 데스크톱 알림 전송 | 🟢 Safe |
| `read_memory` | 에이전트 자신의 메모리 뱅크 읽기. 섹션 지정 가능 | 🟢 Low |
| `write_memory` | 메모리 뱅크의 명명된 섹션에 쓰기. 없으면 생성 | 🟢 Low |
| `search_memory` | **스쿼드 내 모든 에이전트의 메모리 뱅크를 검색.** 매칭 라인과 주변 컨텍스트 반환 | 🟢 Low |

### 9. 인터랙티브 도구 (에이전트 런타임 전용)

`select_option` — 에이전트를 멈추고 사용자에게 클릭 가능한 선택지를 제시한다. 사용자의 선택이 도구 결과로 모델에 반환되어, 에이전트가 추론이 아니라 **명시적 사용자 입력**에 따라 분기할 수 있다. 단일/다중 선택 지원.
파라미터: `prompt`(필수), `options`(필수 — 각 항목은 `id`, `label`, 선택적 `description`/`recommended`/`priority`/`risk`), `mode`(`"single"` 기본 / `"multiple"`).
**일회성 채팅 도구 선택기에는 의도적으로 노출되지 않는다** — 에이전트 루프의 대화형 승인 채널이 있어야 결과를 해소할 수 있기 때문.

### ★ Squad 에이전트의 도구 제한 (중요)

공식 문서 명시:

> File tools (`read_file`, `write_file`, `list_files`) are **workspace-scoped**: paths are resolved relative to the squad workspace root and cannot escape it. Tools that operate on arbitrary host paths (`list_directory`, `search_files`, `execute_python`, etc.) are **blocked for all squad agents regardless of the tool configuration.**

- 파일 도구 3종은 **워크스페이스 루트 기준 상대 경로**로만 동작하며 밖으로 나갈 수 없다.
- 임의의 호스트 경로를 다루는 도구(`list_directory`, `search_files`, `execute_python` 등)는 **도구 설정과 무관하게 모든 스쿼드 에이전트에게 차단된다.**

> 이 제한은 벤치마크 실행 조건과 정합한다. 제출 서버의 practice-sets 페이지도 "your squad has no tools during a run and never browses a repository"라고 명시한다. **평가 실행 중 스쿼드는 도구를 쓰지 않는다.** 저장소 코드는 judge가 직접 검색해서 요청에 넣어준다. `04-벤치마크-데이터셋-분석.md`의 컨텍스트 번들 절 참고.

---

## 11. 템플릿 카탈로그 (레지스트리 배포)

GitHub 기반 카탈로그에서 사전 제작 스쿼드 템플릿을 발견·설치하는 기능이다. 에이전트 프로필과 **같은 다중 소스 레지스트리**를 쓴다.

- **Catalog 페이지 → Squad Templates 탭**. 카드에 아이콘, 이름, 카테고리, 설명, 태그, 저자, 버전, 출처 표시.
- 소스 목록은 에이전트 프로필과 **공유**된다. **Settings > Agent Registry**에서 소스를 추가/제거/활성화하면 Community 탭과 Squad Templates 탭에 동시에 반영된다.
- 설치하면 로컬 `squad-templates` 디렉터리에 기록되고, 이후로는 일반 사용자 템플릿과 동일하게 동작한다.
- 설치된 템플릿이 로컬에 없는 모델을 참조하면, 해당 에이전트는 **Settings → Models의 기본 모델로 자동 폴백**한다.

### 카탈로그 저장소 구조

```
your-catalog/
├── index.json
├── code-assistants/
│   └── python-expert.json        # 에이전트 프로필
└── squad-templates/
    └── code-review-crew.json     # 스쿼드 템플릿
```

`index.json` 항목에 `"kind": "squad_template"`을 붙인다(없으면 `agent_profile`로 간주). 항목은 요약 필드만 담고, 실제 에이전트 구성·프롬프트·도구·모델 선호는 `path`의 템플릿 JSON에 들어간다.

### 콘텐츠 검증

- **체크섬(무결성)**: 항목의 `checksum` 필드에 `sha256:<hex>`. 파일 바이트 그대로에 대해 계산.
  ```bash
  printf 'sha256:%s\n' "$(sha256sum squad-templates/code-review-crew.json | cut -d' ' -f1)"
  ```
- **서명(진정성, 선택)**: 같은 바이트에 대한 detached **Ed25519** 서명을 base64로 `signature` 필드에. 소스의 신뢰 앵커로 공개 키를 **Settings > Agent Registry → Verification settings → Signing public key**에 설정.
- **소스별 "Require content verification" 토글**: 끄면 미서명 리소스도 설치되지만 **Unverified**로 표시된다. 체크섬/서명 **불일치는 토글과 무관하게 항상 설치를 차단**한다.
- 배지: `Verified` / `Unverified` / `Unverified — trusted source`.
- REST 엔드포인트: `POST /api/v1/squad-registry/install`

---

## 12. 컨테이너 실행 모드

Squad와 Cowork는 컨테이너 안에서 실행할 수 있다 (`container/squad-container-mode`). Docker Desktop 또는 Apple Container(macOS arm64)가 필요하다. 에이전트 러너 이미지를 빌드하고 마운트 허용 목록을 설정한다.

Autonomous Agents 플랫폼은 별개 기능이며 provider로 **Hermes**(컨테이너 기반 에이전트 런타임, 권장)와 **Claw(legacy, OpenClaw 어댑터)** 를 가진다. 단 `/autonomous-agents` 사이드바 경로는 **개발 빌드에만 등록**되어 있고 프로덕션 데스크톱 빌드에는 아직 노출되지 않는다.

---

## 13. CLI (`aigo`) — 자동화의 핵심

이 트랙에서 **반복 실험을 자동화하려면 CLI를 써야 한다.** GUI로 364문항을 돌릴 수는 없다.

### 엔드포인트 자동 발견

`--endpoint`를 안 주면 Management API 서버가 시작 시 기록한 discovery 파일을 읽어 로컬 인스턴스를 자동으로 찾는다.

해석 순서:
1. `--endpoint` 플래그 또는 `BACKEND_AI_GO_ENDPOINT` 환경 변수
2. 설정 파일의 endpoint (`aigo config set endpoint ...`로 바꾼 경우)
3. 자동 발견 파일 (로컬 인스턴스가 살아 있고 정상일 때)
4. 기본 폴백: `http://127.0.0.1:8001`

discovery 파일 위치:
- **macOS**: `~/Library/Application Support/ai.backend.go/mgmt-api.json`
- **Linux**: `$XDG_RUNTIME_DIR/ai.backend.go/mgmt-api.json` (폴백: `~/.config/ai.backend.go/mgmt-api.json`)
- **Windows**: `%APPDATA%\ai.backend.go\mgmt-api.json`

연결 전에 PID로 서버 프로세스 생존 확인 + health check를 한다. 죽은 인스턴스의 낡은 파일은 조용히 무시된다.

### 전역 옵션

| 옵션 | 축약 | 환경 변수 | 설명 |
|---|---|---|---|
| `--endpoint` | `-e` | `BACKEND_AI_GO_ENDPOINT` | Management API 엔드포인트 |
| `--token` | `-t` | `BACKEND_AI_GO_TOKEN` | API 인증 토큰 |
| `--output` | `-o` | `BACKEND_AI_GO_OUTPUT` | 출력 형식: `console`, `json`, `yaml` |
| `--quiet` | `-q` | | 비필수 출력 억제 |
| `--verbose` | `-v` | | 상세 출력 |
| `--no-verify-ssl` | | | SSL 인증서 검증 생략 |

### 명령 그룹 (전체 목록)

`bench` `config` `model` `loaded` `pool` `router` `system` `hf` `engine` `provider` `settings` `storage` `monitor` `search-key` `stats` `log` `conversation` `folder` `memory` `plugin` `mcp` `schedule` `lifecycle` `key` `diffusion` `image` `audio` `translate` `glossary` `agent-profile` `agent-registry` `agent` `node` `mesh` **`squad`** `supervisor` `cowork` `extension` `session` `chat` `complete`

정확한 플래그와 하위 명령은 `aigo <command> --help`로 확인할 것.

### `chat` — 일회성 채팅 완성 ★ 벤치마크 실험에 직결

```
aigo chat [OPTIONS] [MESSAGE]
```
`MESSAGE`를 생략하면 stdin에서 읽는다 (최대 1 MiB).

| 옵션 | 축약 | 설명 |
|---|---|---|
| `--model <MODEL>` | `-m` | 사용할 모델 |
| `--max-tokens <INT>` | | 생성 최대 토큰 (기본 1024) |
| `--temperature <FLOAT>` | | 샘플링 온도 0.0~2.0 (기본 0.7). `--reasoning-effort` 설정 시 무시됨 |
| `--system <PROMPT>` | `-s` | 앞에 붙일 시스템 프롬프트 |
| `--reasoning-effort <LEVEL>` | | 하이브리드 사고 모델의 추론 강도: `none`, `low`, `medium`, `high`, `xhigh` |
| `--no-think` | | 사고 모드 비활성화 (`chat_template_kwargs.enable_thinking=false`). `--reasoning-effort`보다 우선 |
| `--thinking-budget <N>` | | `<think>` 블록 안에서 낼 수 있는 토큰의 요청별 상한. `-1`=무제한, `0`=즉시 종료(사고 비활성화), `N>0`=N토큰 하드 캡 |
| `--preserve-thinking` | | 이전 assistant 턴의 `<think>` 블록을 제거하지 않고 유지 (Qwen3.6+ 기능). **에이전트의 KV 캐시 재사용을 개선** |

**동작 상세** — `--reasoning-effort`를 `none` 외의 값으로 주면 `reasoning_effort`와 `chat_template_kwargs: {"enable_thinking": true}`를 함께 보낸다. `none`이거나 `--no-think`를 주면 `chat_template_kwargs: {"enable_thinking": false}`만 보낸다. 이것이 Qwen3/3.5 하이브리드 사고 모델에서 `<think>` 블록을 억제하는 올바른 방법이다.

`--thinking-budget`과 `--preserve-thinking`은 `--reasoning-effort`와 독립적이며 요청별 HTTP 바디로 전달되어 llama-server와 mlxcel-server에 그대로 포워드된다(continuum-router 패스스루 경로 포함).

```bash
# 사고 모드를 끄고 요약
aigo chat --no-think "Summarize this document" < report.txt

# 사고를 64토큰으로 제한 (간결한 추론 강제)
aigo chat --thinking-budget 64 --reasoning-effort high "Quick: 2+2=?"

# 사고 비활성화
aigo chat --thinking-budget 0 "Just answer directly."

# 시스템 프롬프트와 함께 파이프 입력
echo "SELECT * FROM users" | aigo chat --system "You are a SQL expert."
```

> **이 트랙에서의 의미가 크다.** 8절에서 본 대로 평가 모델 3개 중 2개가 reasoning 모델이고, 그중 하나는 **출력 예산의 97%를 추론 토큰에 쓴다**고 측정됐다. `--no-think`, `--thinking-budget`, `--reasoning-effort none`은 **토큰 효율 30점을 직접 좌우하는 레버**다.

### `squad` 관련 명령

```bash
aigo squad discussion create --json '{"squadId":"sq-1","topic":"Release plan"}'
aigo squad discussion list <SQUAD_ID>
aigo squad discussion show <ID> | delete <ID> [-y]
aigo squad discussion start|pause|resume|stop <ID>
aigo squad discussion post <ID> --message <TEXT>
aigo squad discussion cancel-message <ID> <MESSAGE_ID>
aigo squad discussion mode <ID> <moderated|brainstorm>
aigo squad discussion strategy <ID> [moderated|brainstorm|roundRobin|autonomous|none]
aigo squad discussion turn-budget <ID> <N>
aigo squad discussion conclude <ID> [--force]
aigo squad discussion handoff <ID>
aigo squad discussion export <ID> [--format markdown|json|plainText]   # ← 시각화 입력
aigo squad discussion analytics <ID>
aigo squad template install --path <PATH> [--source-id <ID>]
```

`aigo squad --help`로 나머지 하위 명령(스쿼드 생성·실행·상태 조회 등)을 확인할 것.

### 기타 유용한 명령

```bash
aigo model list -o json               # 로컬 모델 목록을 JSON으로
aigo loaded list                      # 메모리에 로드된 모델
aigo loaded load <MODEL_ID> --gpu-layers 33 --tool-calling
aigo loaded unload <ID>
aigo system gpu                       # GPU 상태
aigo router status|start|stop|restart # Continuum Router 제어
aigo stats                            # API 사용 통계
aigo log                              # 로그 파일 관리     ← 시각화 원천
aigo session list|show|diagnostics    # 세션 진단
```

---

## 14. REST API / 헤드리스 모드

### 헤드리스 서버

```bash
aigo-server                       # 로컬
aigo-server --external --port 8001  # 외부 바인딩
```

- `tauri` 크레이트가 의존성 그래프에 없다.
- Management API가 주 컨트롤 플레인이 된다.
- WebUI가 Tauri IPC 대신 HTTP/SSE로 붙는다.
- 모델 풀, 라우터 관리, 스케줄링, 에이전트, 메모리, provider/runtime 조정이 데스크톱과 같은 공유 런타임 매니저를 재사용한다.
- 첫 실행 시 `http://<host>:8001`에서 Initial Setup 화면. 비로컬 인터페이스에 바인딩된 경우 setup token 필요 (`AIGO_SETUP_TOKEN`, 또는 시작 로그에 찍히는 일회성 토큰).
- SDK 클라이언트는 `X-API-Key` 또는 `Authorization: Bearer` 헤더를 쓴다. 키는 로그인 후 **API > Access keys**에서 만든다.
- 헤드리스에서는 OS 키체인 대신 암호화 파일(`encrypted_keys.json`)에 API 키를 저장한다.

### OpenAI 호환 API (Continuum Router)

기본 포트 `39080`. 활성화: **API 페이지 → General → TCP Server 토글**. 외부 접근이 필요하면 **External access**도 켠다(경고 수락 필요).

```bash
curl http://localhost:39080/v1/models

curl http://localhost:39080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"llama-3-8b","messages":[{"role":"user","content":"..."}]}'
```

OpenAI 공식 SDK나 OpenAI를 지원하는 어떤 라이브러리든 `base_url`만 바꾸면 그대로 쓸 수 있다.

### 알아둘 REST 엔드포인트

| 엔드포인트 | 용도 |
|---|---|
| `GET /api/v1/tools` | 도구 목록. 각 도구에 `available_in_headless` 플래그 |
| `POST /api/v1/tools/execute` | 도구 직접 실행 (데스크톱 전용 도구는 거부) |
| `POST /api/v1/audio/transcriptions` | 오디오 전사 (헤드리스에서 `audio_transcribe` 대체) |
| `POST /api/v1/diffusion/generate` | 이미지 생성 (헤드리스에서 `generate_image` 대체) |
| `POST /api/v1/squad-registry/install` | 카탈로그에서 스쿼드 템플릿 설치 |
| `GET /api/v1/autonomous/availability` | Autonomous Agents provider 가용성 |
| `GET /api/v1/sessions/events` | 세션 이벤트 SSE 스트림 (CLI 명령 없음, 직접 구독) |

---

## 15. 이 트랙을 위한 실전 체크리스트

1. **설치**: `go.backend.ai`에서 AI:GO 데스크톱 앱 설치. 최신 릴리스는 `github.com/lablup/backend.ai-go-releases`.
2. **모델 연결**: 제출 포털의 **Development keys** 탭에서 개발용 API 키를 발급받고, AI:GO의 **Cloud Integration → OpenAI-compatible** 또는 Provider 설정에 등록한다. 이렇게 하면 로컬 하드웨어 없이 주최 측 공유 서빙 스택의 모델을 쓸 수 있다.
3. **스쿼드 만들기**: Squad → New Squad. 내장 템플릿에서 시작하되 트랙에 맞춰 재설계.
4. **예산 설정**: Budget Config에서 `Max agent turns`, `Max tokens per task`를 공격적으로 낮춰서 "포기 장치"를 만든다.
5. **연습 세트로 검증**: `practice-sets/` 아래 364문항으로 반복 측정. 이때 쓰는 토큰이 test run(1/5 과금) 대상이다.
6. **템플릿 내보내기**: Save as template → Export → JSON 파일. 이 JSON이 제출물.
7. **Check → Submit**: 포털에서 Check를 무제한 돌려 검증하고, 확신이 설 때만 Submit to the queue.
8. **Trace 수집**: 워크스페이스의 `logs/`, Discussion export(JSON), 포털의 `/runs/{run_id}/details`를 모아 시각화 데이터 파이프라인을 만든다.
