# spec — Monstrous Squad 제출 스펙

JUNCTIONX Korea 2026 · Lablup + FuriosaAI 트랙 "Build the Ultimate Agent Squad"

> **[2026-08-23] 먼저 읽을 것 — 리더보드 API가 인증 없이 열려 있다.**
> `https://submission.jxc.events.lablup.ai:8444/api/leaderboard`가 hidden 세트를 **147문항**(coding 38 / math 13 / generic 96, 반복 없음)으로,
> 토큰·시간 캡을 **둘 다 `null`**로, 평가 모델을 `providers.json`의 셋으로 확정해 준다. math는 **HMMT Feb 2026 + AIME 2026**, generic에는 **GPQA가 섞여 있다.**
> 그 결과 비용 모델이 40.0M → 약 **7.1M**이고, 1위 팀은 **gpt-oss-120b 하나로 2.53M**을 써서 0.4261을 냈다.
> 자세히는 `spec/00-스쿼드-스펙.md` §1-2와 부록 A-15.

| 파일 | 내용 |
|---|---|
| **`00-스쿼드-스펙.md`** | 본문. 명단·계약·모델 배정·예산·프롬프트 배치·검증·배포·측정·근거 |
| **`01-플랫폼-사실.md`** | 부록 A. Backend.AI GO 1.12.1을 이 PC에서 직접 뜯어 확인한 사실. 본문의 모든 스키마·필드명·측정값 출처 |
| ~~`squad-template.json`~~ | **2026-08-23 삭제.** 같은 프롬프트가 두 파일에 살면 어느 쪽이 제출물인지가 매번 다시 물음이 된다. 템플릿은 이제 `squad/squad_template/monstrous_squad/squad-template.json` 하나뿐이고, 다섯 `systemPrompt`도 거기에만 있다 |

Architect와 Reviewer의 판단 기준은 `docs/resource/background_research/engineering_doctrine/`의 레포 세 곳 분석에서 나왔다. 인용 줄 번호와 **버린 규칙의 이유**가 거기 있다.

제출물은 이 폴더 밖에도 있다. 포털에 내는 것은 **Squad Template JSON 1개 + 트랙별 one-shot 프롬프트 3개**(`docs/resource/example_task/prompts/`)이고, 트랙이 요구하는 산출물은 그것과 **인터랙티브 시각화**(`viz/trace-visualizer.html`) 둘이다. 시각화가 100점 중 30점이고, 스쿼드가 그것을 위해 무엇을 내야 하는지는 본문 **§11**에 있다.

## 세 줄 요약

에이전트 **5명**. 하나가 읽고 나누고(Router), 하나가 **어디를 고칠지 정하고**(Architect), 하나가 고치고(Editor), 하나가 풀고(Solver), 하나가 **내용과 형식을 둘 다 검토한 뒤 채점되는 블록을 낸다**(Reviewer).

문항당 LLM 호출은 **SWE-bench 4회 / 나머지 3회**다. Planner 호출도 LLM 호출이다.

Router는 문항을 **coding · math · generic · other 넷으로** 분류한다. 앞의 셋은 채점 벤치마크의 트랙이고, **`other`는 그 밖의 것이 왔을 때 셋 중 하나의 형식을 억지로 씌우지 않기 위한 자리**다. 경로는 셋뿐이고(A/B/C), 트랙 이름이 아니라 **코드를 읽어야 하는가·써야 하는가**가 경로를 정한다.

모델은 둘이다. **gpt-oss-120b(×2)**가 네 자리 — 2만 토큰짜리 coding 요청이 배치 64에서도 들어가는 유일한 모델이고, 같은 모델을 쓰면 문항 안에서 캐시가 걸린다. **K-EXAONE(×3)**이 Solver 한 자리 — MMLU-Pro 83.8이 가장 높고 AIME는 약 88.6이다(공개 92.8은 BF16, 우리가 부르는 것은 NVFP4 배포본). math·generic은 문항당 입력이 330~2,930바이트로 짧아 배율 3을 감당할 수 있는 유일한 자리다.

검증은 **파서 위에 얹은 판정**이다 — 형식은 정규식이 정하고, 내용은 Reviewer가 네 가지 판정 중 하나로 말한다. 포기는 **세 자리에 나뉜 판정 + 그 아래 예산 산수**다. 그리고 다섯 에이전트 모두 응답 첫 줄에 **ledger 한 줄**을 쓴다 — 답 블록 앞은 감점이 없고, hidden 제출 실행에서는 그 한 줄이 우리에게 남는 유일한 트레이스다.

## 먼저 확인할 것 두 가지

1. **`GET /v1/models`** — `max_prompt_len`, `max_context_len`. 컨텍스트는 빌드 때 굳어서 서빙 시점에 못 바꾼다. 본문 §4-1의 배치별 표를 이 실제 값으로 갱신한다. 같은 자리에서 **모델 배율 ×1/×2/×3과 컨텍스트 40K/128K/48K의 출처**도 확인한다 — 지금은 온보딩 구두 전달이고 기록된 근거가 없다.
2. **워커가 원 요청 전문을 보는가** — 연습 coding 문항 1건을 데스크톱 앱에서 돌리고 `history.json`의 `tasks[].description`을 본다. 본문 §3 전체의 전제다.

## 배포

```bash
aigo squad template import squad/squad_template/monstrous_squad/squad-template.json
```

예산은 템플릿에 안 들어간다. 본문 §9-1의 `aigo squad budget set` 명령을 따로 실행한다.

**헤드리스에서는 Planner가 돌지 않는다.** 검증은 데스크톱 앱을 띄운 상태에서 한다.

**실행마다 워크스페이스를 스냅샷한다** (`viz/tools/snapshot-logs.sh`). 로그는 덮어써지고, 안 남긴 실행은 되살릴 수 없다. 시각화 30점의 입력이 그것뿐이다.
