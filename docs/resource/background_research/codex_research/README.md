# JUNCTIONX Korea 2026 Agent Squad 심층 리서치

조사 기준일: 2026-08-22 KST

이 디렉터리는 저장소 `docs/` 전체, JUNCTIONX Korea 2026 공식 페이지, Lablup + FuriosaAI 트랙 자료, 현재 공개 practice set, AI:GO 1.12.1 실측, multi-agent 및 test-time compute 연구를 하나의 의사결정 자료로 통합한다.

## 결론

이 트랙의 최적화 대상은 **agent 수가 아니라 문항당 유효 작업량**이다. 제출 baseline은 정확히 한 명의 `Planner`와 track별 전담 solver 세 명으로 구성하고, 각 문항은 `Planner → 해당 solver` 두 호출로 끝내는 것이 가장 근거가 강하다. coding의 `Architect → Editor` 분리는 유망한 실험 후보이지만, 60,000자 입력을 두 번 읽게 만들거나 원문 SEARCH anchor를 손실하면 오히려 악화한다. Reviewer, debate, self-consistency는 이름값으로 넣지 않고 동일 예산 A/B test에서 정확도-비용 Pareto frontier를 실제로 움직일 때만 승급시킨다.

권장 baseline:

1. `RouterPlanner`: AI:GO가 요구하는 유일한 Planner. `payload.kind`를 읽고 단일 task만 만든다.
2. `CodePatchSolver`: localization, repair, SEARCH/REPLACE formatting을 한 context 안에서 처리한다.
3. `MathSolver`: 짧지만 충분한 풀이 후 마지막 `FINAL ANSWER` 한 줄을 보장한다.
4. `GenericSolver`: 내부 reasoning은 허용하되 마지막 `ANSWER: <letter>`만 최소 출력한다.

선택적 다섯 번째 `CodingReviewer`는 baseline에 호출하지 않는다. coding split, reviewer, 추가 sample은 실험 결과가 있을 때만 켠다.

## 대회에서 바로 중요한 사실

| 항목 | 확인값 | 상태 |
|---|---:|---|
| 행사 | JUNCTIONX Korea 2026, 2026-08-21~23, 포항 | 공식 행사 페이지 확인 |
| 트랙 | Lablup + FuriosaAI, **Build the Ultimate Agent Squad** | 트랙 PDF 및 포털 확인 |
| 산출물 | AI:GO problem-solving squad + interactive trace visualization | 트랙 PDF 확인 |
| 제출 형태 | Squad Template JSON 1개 + coding/math/generic one-shot prompt 각 1개 | 포털 및 로컬 실측 문서 확인 |
| 총점 | benchmark 40 + visualization 30 + token efficiency 30 | 트랙 PDF p.24 |
| benchmark | `0.5×coding + 0.25×generic + 0.25×math` | manifest 및 포털 확인 |
| judge | 전부 deterministic program, LLM judge 없음 | 포털 확인 |
| 도구 | 평가 중 squad tool 및 repository browsing 없음 | 포털 확인 |
| coding context | judge가 최대 60,000자로 검색·구성 | manifest 및 20개 공개 문항 확인 |
| 공개 연습 세트 | 121개: coding 20, math 59, generic 42 | 2026-08-22 live server 재확인 |
| hidden 범위 | coding 140~240, math 60~66 × 2, generic 448~698 | manifest 확인 |
| 출력 | coding SEARCH/REPLACE, math boxed answer, generic letter | 121개 request digest 확인 |

## 기존 결론 중 바로잡아야 할 것

1. **“coding 한 문항은 generic보다 10배 넘게 무겁다”는 일반화는 틀리다.** 공개된 hidden 범위로 계산하면 문항당 benchmark 기여도 비율은 약 **3.73~9.97배**, 범위 중간값에서는 약 **6.03배**다. coding 우선순위라는 방향은 맞지만, 10배 초과는 보장되지 않는다.
2. **Qwen model card의 LiveCodeBench 43.2와 Aider-Polyglot 35.6 차이만으로 formatting이 유일한 원인이라고 결론낼 수 없다.** 서로 다른 benchmark다. 다만 strict edit-format risk를 별도로 측정해야 한다는 신호로는 충분하다.
3. **evaluation-time programmatic Preflight는 허용 여부가 확인되지 않았다.** 로컬 harness에서는 반드시 사용하되, 제출 squad의 critical path에 넣으려면 organizer 확인이 필요하다.
4. **generic에서 reasoning을 끄는 전략은 근거가 약하다.** MMLU-Pro 원 논문에서는 CoT가 direct answer보다 모든 비교 모델에서 높았고 GPT-4o는 +19.1pp였다. “생각하지 말라”가 아니라 “내부에서 생각하고 마지막 출력만 짧게”가 안전하다.
5. **OpenTelemetry GenAI 문서 위치가 바뀌었다.** core semantic-conventions의 기존 GenAI 문서는 더 이상 유지되지 않으며, 현재는 별도 `semantic-conventions-genai` repository의 Development 사양을 봐야 한다.

## 읽는 순서

### 01-context

- [로컬 docs 감사](01-context/01-local-docs-audit.md): 읽은 범위, 데이터셋 실측, 문서 간 상충.
- [해커톤·트랙 ground truth](01-context/02-hackathon-track-ground-truth.md): 일정, 제출물, 채점, 실행 계약.

### 02-evidence

- [single-agent 대 multi-agent](02-evidence/01-single-vs-multi-agent.md): fixed-budget 연구, 실패 taxonomy, 직접 적용 한계.
- [routing·budget·verification](02-evidence/02-routing-budget-verification.md): cascade, self-consistency, self-correction, hard cap.
- [track-specific evidence](02-evidence/03-track-specific-evidence.md): coding, MMLU-Pro, math에 각각 무엇이 전이되는가.
- [context·cache·observability](02-evidence/04-context-cache-observability.md): 60KB context, prefix cache, 현재 OTel schema.

### 03-recommendation

- [권장 AI squad](03-recommendation/01-recommended-squad.md): baseline 구조, packet, stop rule, 채택 기준.
- [track별 playbook](03-recommendation/02-track-playbooks.md): coding/math/generic prompt와 실패 방지.
- [실험·예산 계획](03-recommendation/03-experiment-plan.md): split, ablation, metric, 승급 기준.
- [사람 팀 운영](03-recommendation/04-human-team-operating-model.md): 최대 4인 hackathon team의 역할과 48시간 운영.
- [시각화·pitch](03-recommendation/05-visualization-pitch.md): judge가 검증 가능한 화면과 정직한 replay.

### 04-audit

- [claim-evidence matrix](04-audit/01-claim-evidence-matrix.md): claim별 source 등급과 적용 한계.
- [risk register](04-audit/02-risk-register-open-questions.md): 아직 organizer만 답할 수 있는 값과 fallback.
- [조사 방법·coverage](04-audit/03-research-method-and-coverage.md): 로컬 전수조사, Exa, Firecrawl, Scrapling, last30days의 실제 경계.

`99-raw/`는 최근 30일 signal 수집 결과와 query plan이다. 이 자료는 community signal이지 설계의 정량 근거가 아니다.

## 한 문장 전략

**한 template 안에 필요한 전문성은 준비하되, 한 문항에서 실제로 호출되는 agent는 최소화하고, 모든 추가 호출은 track별 holdout에서 얻은 정확도 증가가 normalized token cost를 이길 때만 허용한다.**
