# 주제 5: Speculative-Specialist Squad & Counterfactual Decision Matrix
> **"사변적(Speculative) 하이브리드 전문가 스쿼드 및 반사실적(What-If) 의사결정 분석 시스템"**

---

## 1. 한 줄 요약
**1개의 통합 템플릿 안에서 가벼운 Instruct 초안 생성(Fast Path)과 심층 검증(Deep Path)을 동적으로 전환하는 사변적 스쿼드**와, **"만약 다른 경로를 택했다면 어땠을까?"를 시뮬레이션하여 의사결정의 타당성을 입증하는 반사실적(Counterfactual) 시각화 시스템**.

---

## 2. 기획 배경 및 문제의식 (Why)

1. **단 1개의 Squad Template JSON 제약**:
   - 주최 측 규칙에 따라 트랙별로 별도 스쿼드를 제출할 수 없으며, **단 1개의 통합 템플릿 JSON**으로 Coding(가중치 0.5), Math(0.25), Generic(0.25)을 모두 최적화해야 합니다.
   - 단일 파이프라인으로 통일하면 Generic(쉬운 객관식)에서 과도한 토큰 낭비가 발생하고, 반대로 너무 단순화하면 Coding과 Math를 풀지 못합니다.
2. **사변적 추론(Speculative Routing)의 도입**:
   - 대부분의 문항은 가벼운 Instruct 모델의 초안(Fast Draft)으로 즉시 해결하고, 검증 실패 또는 고난도 AIME/SWE-bench 케이스에만 심층 전문가(Deep Specialist)를 점진 개입시키는 것이 최적의 비용 대비 성능을 보장합니다.
3. **시각화 최고 난도 축인 `Insightfulness(통찰력)`의 정복**:
   - 단순 사후 로그 재생은 누구나 만듭니다. 심사위원의 감탄을 자아내는 시각화는 **"우리 스쿼드의 판단이 왜 최선이었는지(반사실적 시나리오 대조)"**를 스스로 증명하는 인터랙티브 분석 도구입니다.

---

## 3. 스쿼드 아키텍처 (How - Squad Architecture)

### 📌 사변적 경로 전환 (Speculative Routing)

```
                       ┌─────────────────────────┐
                       │ Speculative Router      │
                       │ (문항 종류 및 난이도 판별)│
                       └───────────┬─────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼ (Fast Path)             ▼ (Balanced Path)         ▼ (Deep Path)
   [Generic MCQ]             [Math Track]              [Coding Track]
   Solver 1단답 직행          Solver (선별적 Thinking)   CodeReader (인덱싱)
   (소모 토큰 < 150)          + Verifier (포맷 검증)    + PatchWriter (Diff)
                             (소모 토큰 ~1,000)         + Verifier (사전문법)
                                                       (소모 토큰 ~5,000)
```

### 👥 에이전트 역할 구성
- **Speculative Router**: 문항 페이로드(MMLU-Pro / MATH-500 / SWE-bench)를 분석해 최적의 웨이브 깊이(1~4단계) 결정
- **Fast Solver**: Generic 및 직관적 수학 문항을 `--no-think` 초경량 모델로 1턴 내 즉시 해결
- **Deep Patch Specialist**: 코딩 문항 전용으로, 인덱싱된 컨텍스트를 분석해 Unified Diff 정밀 생성
- **Escalation Verifier**: Fast Path의 결과물이 불확실할 경우에만 고비용 추론 단계를 선별적으로 트리거

---

## 4. 인터랙티브 트레이스 시각화 (Trace Visualization)

### 🖥️ `Counterfactual Decision Matrix` 핵심 화면
1. **"What-If" 반사실적 시나리오 비교기**:
   - **실제 실행 경로**: Fast Path로 150토큰 소모하여 정답 획득.
   - **가상 비교 경로**: Reasoning 모델을 풀 가동했을 경우 소모되었을 예상 토큰(4,500토큰) 및 지연 시간 대조 $\rightarrow$ **스쿼드 설계의 정당성 입증**.
2. **Decision Branching Graph**:
   - Planner가 어떤 근거(프롬프트 지시, 문항 메타데이터)로 경로를 분기했는지 각 노드별 상태 전이와 토큰 누적량을 다이내믹 인터랙션으로 표시.
3. **트랙별 한계 가치 분석 맵**:
   - Coding(가중치 0.5)에 투자된 1토큰의 가치와 Generic(가중치 0.25)에 투자된 1토큰의 획득 점수 기여도 실시간 비교.

---

## 5. 1등 당선 전략 (Winning Edge)

| 평가 항목 | 전략적 우위 (Why it wins) |
|---|---|
| **시각화 (30점)** | 기존 대시보드가 보여주지 못하는 **"반사실적 분석(Counterfactual Reasoning)"**을 제시하여 `Insightfulness` 6대 축 최고점 달성. |
| **토큰 효율 (30점)** | Generic/쉬운 문항의 1-Step 직행 처리로 베이스라인 대비 **전체 토큰의 50% 이상 절감**. |
| **벤치마크 (40점)** | 난이도별 적응형 파이프라인으로 1개 템플릿 제약 하에서 3개 트랙 모두 최고 성능 발휘. |
