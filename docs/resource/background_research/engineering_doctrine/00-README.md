# engineering_doctrine — 소프트웨어 작성 규율 세 갈래 분석

LEDGER Squad의 **Architect**와 **Reviewer** 두 에이전트의 시스템 프롬프트가 여기서 나온다.

배경: 초안의 Architect는 "60,000자 발췌를 읽고 앵커를 뽑는" 에이전트였다. 방향을 바꿔서, **소프트웨어를 어떻게 고치는가 — 어디가 이음매고 무엇이 최소 변경이고 무엇을 건드리면 안 되는가 — 를 판단하는** 에이전트로 만든다. 그 판단 기준을 아래 세 레포에서 뽑았다.

| 파일 | 레포 | 성격 |
|---|---|---|
| `01-ponytail.md` | [dietrichgebert/ponytail](https://github.com/dietrichgebert/ponytail) | **덜 짓는 규율.** 7칸 사다리 + 근본 원인 지시 + 안전 바닥. 유일하게 자기 효과를 벤치마크로 측정하고 일부를 철회했다 |
| `02-mark-pattern.md` | [kimkimsh/mark_pattern](https://github.com/kimkimsh/mark_pattern) | **설계 판단 규율.** 3개 Move + 실패 경로 카탈로그 10종 + 리뷰 패스 7개. 조언이 아니라 **채워야 하는 칸**으로 만든 것이 특징 |
| `03-karpathy-guidelines.md` | [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills) | **최소 변경 규율.** 4개 섹션 65줄. Surgical Changes 섹션이 SEARCH/REPLACE 과제에 거의 그대로 맞는다 |
| `04-종합.md` | — | 셋을 합쳐 Architect·Reviewer 계약으로 만든 것. **충돌 지점과 승자를 명시** |

## 읽는 순서

`04-종합.md`만 읽어도 스펙 작업은 된다. 개별 레포 문서는 인용 출처와 반대 증거를 확인할 때 본다.

## 세 레포에 공통으로 적용한 이식 기준

우리 에이전트가 놓인 조건은 셋이다.

1. **물어볼 상대가 없다.** 원샷이고 후속 턴이 없다. "물어라 / 멈춰라 / 사용자에게 제시하라"로 끝나는 규칙은 전부 **패치 대신 질문을 내게** 만든다.
2. **실행해서 확인할 방법이 없다.** 평가 중 도구가 0개다. "테스트를 돌려라 / 검증할 때까지 반복하라"는 실행 불가이고, 더 나쁘게는 **돌리지도 않고 돌렸다고 쓰게** 만든다.
3. **SEARCH 텍스트는 원문과 바이트 단위로 같아야 한다.** 그래서 "기존 스타일을 유지하라" 같은 규칙이 예절이 아니라 **적용 실패를 막는 기계적 규칙**이 된다.

세 조건이 각 레포의 절반쯤을 살리고 절반쯤을 죽인다. 각 문서의 마지막 절이 그 판정표다.
