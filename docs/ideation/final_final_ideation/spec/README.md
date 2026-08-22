# spec — LEDGER Squad 제출 스펙

JUNCTIONX Korea 2026 · Lablup + FuriosaAI 트랙 "Build the Ultimate Agent Squad"

| 파일 | 내용 |
|---|---|
| **`00-스쿼드-스펙.md`** | 본문. 명단·계약·모델 배정·예산·프롬프트 배치·검증·배포·측정·근거 |
| **`01-플랫폼-사실.md`** | 부록 A. Backend.AI GO 1.12.1을 이 PC에서 직접 뜯어 확인한 사실. 본문의 모든 스키마·필드명·측정값 출처 |
| **`squad-template.json`** | 제출용 Squad Template JSON. 앱에 바로 가져올 수 있다 |

## 세 줄 요약

에이전트 **4명**, 문항당 LLM 호출 **2회**. 하나가 읽고 나누고, 하나가 고치고, 하나가 풀고, 하나가 채점되는 블록을 낸다.

모델은 셋 다 쓰되 자리마다 이유가 있다. **gpt-oss-120b(×2)**는 20,089토큰짜리 coding 요청이 배치 64에서도 들어가는 유일한 모델이라서, **K-EXAONE(×3)**은 MMLU-Pro 83.8·AIME 92.8이 가장 높은데 math·generic 토큰 지출은 전체의 15% 미만이라서, **Qwen3-32B(×1)**는 마지막 형식 변환에 추론이 필요 없어서.

검증은 판사가 아니라 **파서**다. 포기는 판단이 아니라 **산수**다.

## 먼저 확인할 것 두 가지

1. **`GET /v1/models`** — `max_prompt_len`, `max_context_len`. 컨텍스트는 빌드 때 굳어서 서빙 시점에 못 바꾼다. 본문 §4-1의 배치별 표를 이 실제 값으로 갱신한다.
2. **워커가 원 요청 전문을 보는가** — 연습 coding 문항 1건을 데스크톱 앱에서 돌리고 `history.json`의 `tasks[].description`을 본다. 본문 §3 전체의 전제다.

## 배포

```bash
aigo squad template import squad-template.json
```

예산은 템플릿에 안 들어간다. 본문 §9-1의 `aigo squad budget set` 명령을 따로 실행한다.

**헤드리스에서는 Planner가 돌지 않는다.** 검증은 데스크톱 앱을 띄운 상태에서 한다.
