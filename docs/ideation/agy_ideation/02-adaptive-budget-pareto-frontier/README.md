# 주제 2: Adaptive-Budget Squad & Pareto Frontier Visualizer

> **[갱신됨 2026-08-23 · 이 문서는 역사 기록이다]** 2026-08-22 발상 단계의 기록이고 최종 설계가 아니다. 현행은 `../../final_final_ideation/spec/`이다. **이 문서가 전제한 Unified Diff 출력은 틀렸다** — coding 출력은 SEARCH/REPLACE 블록이고, `git diff`를 내면 전 문항 `extraction_failed`다.
> **"불확실성 기반 3단계 조기 포기 및 토큰 한계효용 파레토 최적화 시스템"**

---

## 1. 한 줄 요약
**트랙 가중치(코딩 0.5 / 수학·일반 0.25)와 모델 불확실성을 평가하여 가망 없는 문제를 조기에 차단(Give-Up)하고 사고 예산(Thinking Budget)을 국소 제어하는 스쿼드**와, **토큰 비용 대비 정답률의 파레토 최적 경계(Pareto Frontier)를 증명하는 인터랙티브 시각화 시스템**.

---

## 2. 기획 배경 및 문제의식 (Why)

1. **Reasoning 모델의 토큰 폭주(97% 사고 토큰) 방어**:
   - 주최 측 평가 모델 3개 중 2개가 Reasoning 모델이며, 출력 예산의 97%를 `<think>` 블록에 소모합니다.
   - 무분별한 사고 활성화는 실행당 토큰 상한(Token Cap)에 즉시 도달하여 `capped_tokens`로 인한 대량 감점(0점)을 유발합니다.
2. **트랙 챌린지 핵심 질문 정면 대응**:
   - 문제 지문 원문: *"deciding which ones determine when it is time to give up."*
   - 풀 수 없는 문제에 끝까지 토큰을 쏟는 스쿼드는 자멸합니다. 조기에 손절하고 가중치가 높은 코딩 문제에 예산을 집중해야 합니다.
3. **토큰 효율 점수(30점) 및 동점 처리 1순위 장악**:
   - 벤치마크 동점 발생 시 1순위 기준이 "총 토큰 수가 적은 쪽"이므로, 낭비 토큰을 0으로 만드는 팀이 무조건 우승합니다.

---

## 3. 스쿼드 아키텍처 (How - Squad Architecture)

### 📌 3단계 조기 포기(Early-Exit) 및 동적 예산 배분

```
[ 문항 진입 ]
     │
     ▼
┌─────────────────────────┐
│ [Level 1] Fast-Reject   │ ──(불완전 문맥/추출 불능)──▶ [ 즉시 포기: 토큰 소모 < 100 ]
└────────────┬────────────┘
             │ (정상 통과)
             ▼
┌─────────────────────────┐
│ [Level 2] Track-Budget  │ ──▶ Coding: Instruct 모델 + 4단계 정밀 파이프라인
│           Controller    │ ──▶ Generic: Instruct 모델 + 1단계 단답 직행
└────────────┬────────────┘ ──▶ Math(AIME): 국소적 `--thinking-budget 64` 한정 투입
             │
             ▼
┌─────────────────────────┐
│ [Level 3] GiveUpJudge   │ ──(형식 불일치/2회 재시도 실패)──▶ [ 1단어 'give_up' 종료 ]
└─────────────────────────┘
```

### 👥 에이전트 역할 구성
- **Adaptive-Planner**: 문항 유형별 가중치에 따라 실행 웨이브 깊이(1~4단계)를 동적으로 결정
- **Specialist-Solver**: `--no-think`를 기본으로 하되, 고난도 AIME 수학 문항에만 정밀 상한선(`--thinking-budget 64`)을 주입하여 사고 토큰 캡 통제
- **Confidence-Verifier**: 1차 생성물의 신뢰도 및 형식 일치성을 채점기 기준(`integer_exact`, `letter_match`, `unified_diff`)으로 즉각 판정
- **GiveUpJudge**: 검증 실패 시 재시도 비용과 포기 이득을 계산하여 `continue` 또는 `give_up` 단 1단어(토큰 비용 0에 수렴)로 판단

---

## 4. 인터랙티브 트레이스 시각화 (Trace Visualization)

### 🖥️ `Pareto Frontier Visualizer` 핵심 대시보드 화면
1. **토큰-정확도 파레토 프론티어(Pareto Curve)**:
   - 364개 문항에 걸쳐 토큰 소비량 대비 누적 획득 점수의 한계 효용 곡선을 시각화.
2. **조기 포기(Give-Up) 의사결정 트리맵**:
   - Level 1(Fast-Reject), Level 2(Budget Gate), Level 3(GiveUpJudge)에서 차단된 문항들의 위치와, 이를 통해 절약한 누적 토큰 총량($\Delta \text{Tokens}$) 실시간 표시.
3. **Reasoning Token 절제율 게이지**:
   - Non-thinking vs Capped-thinking 대비 원본 Reasoning 모델 대비 절감된 97%의 사고 토큰 마진을 시각적으로 증명.

---

## 5. 1등 당선 전략 (Winning Edge)

| 평가 항목 | 전략적 우위 (Why it wins) |
|---|---|
| **토큰 효율 (30점)** | 고난도 가망 없는 문항의 조기 손절로 **불필요한 토큰 낭비 0건 달성**, 토큰 효율 30점 만점 독점. |
| **벤치마크 (40점)** | 절약한 토큰 예산을 가중치 0.5인 코딩(SWE-bench)에 집중 재투자하여 종합 가중 정확도 극대화. |
| **시각화 (30점)** | '왜 이 시점에 포기했는가(Explainability)'와 '포기함으로써 얻은 한계 이익(Insightfulness)'을 완벽하게 시각화. |
