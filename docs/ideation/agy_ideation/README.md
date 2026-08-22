# Lablup & FuriosaAI 트랙 1등 전략 주제 기획 (Top 5 Ideation)

> **트랙명**: Build the Ultimate Agent Squad (Lablup + FuriosaAI)  

> **[갱신됨 2026-08-23 · 이 문서는 역사 기록이다]** 2026-08-22 발상 단계의 기록이고 최종 설계가 아니다. 현행은 `../final_final_ideation/spec/`이다. **아래 다섯 주제가 전제한 Unified Diff 출력은 틀렸다** — 이 트랙의 coding 출력은 SEARCH/REPLACE 블록이고, `git diff`를 내면 전 문항 `extraction_failed`다.
> **핵심 질문**: *"How far can you go with a model you can actually hold in your hands?"*  
> **배점 구조**: 벤치마크 정확도 40% + 트레이스 시각화 30% + 토큰 효율 30% (동점 판정 1순위: 총 토큰 수)  
> **핵심 가중치**: Coding (0.5), Generic (0.25), Math (0.25)

---

## 🏆 1등 공략 5대 주제 개요 (Overview)

본 기획은 Lablup(Backend.AI, AI:GO)과 FuriosaAI(NPU 하드웨어)의 심사위원단 관점을 정밀 타격하여, **'정확도(40) + 시각화(30) + 토큰 효율(30)'의 완벽한 3각 균형**을 달성할 수 있는 5가지 차별화된 아키텍처 및 제품 주제를 제안합니다.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   5대 전략 주제 비교 매트릭스                                    │
├─────┬───────────────────────────┬────────────────────────────┬─────────────────────────────────┤
│ 번호│ 폴더명 및 주제명          │ 핵심 스쿼드 아키텍처       │ 인터랙티브 트레이스 시각화 컨셉  │
├─────┼───────────────────────────┼────────────────────────────┼─────────────────────────────────┤
│ 01  │ 01-cacheops-squad-        │ Prefix-Cache First 템플릿  │ NPU/서빙 레이어 레벨의          │
│     │ kv-profiler               │ (공통 컨텍스트 KV 캐시화)   │ KV Cache Hit/Miss 프로파일러    │
├─────┼───────────────────────────┼────────────────────────────┼─────────────────────────────────┤
│ 02  │ 02-adaptive-budget-       │ 3단계 조기 포기(GiveUp) 및 │ 토큰 투자 대비 정답 기대효용    │
│     │ pareto-frontier           │ Thinking Budget 정밀 제어  │ 파레토 최적 곡선 대시보드       │
├─────┼───────────────────────────┼────────────────────────────┼─────────────────────────────────┤
│ 03  │ 03-index-localized-       │ 무손실 위치 인덱스 기반    │ OTel GenAI v1.41 표준 준수      │
│     │ diff-flow                 │ CodeReader + PatchWriter   │ 4단계 Zoom 인과 그래프          │
├─────┼───────────────────────────┼────────────────────────────┼─────────────────────────────────┤
│ 04  │ 04-failure-attribution-   │ 상태머신 기반 오류 분류 및 │ 주최 인프라 vs 팀 책임 분리     │
│     │ root-cause                │ 자가 치유(Self-Healing)     │ Root-Cause 산키(Sankey) 다이어그램│
├─────┼───────────────────────────┼────────────────────────────┼─────────────────────────────────┤
│ 05  │ 05-speculative-specialist-│ 경량 Router 기반 경로 분기 │ "다른 판단을 했다면?"           │
│     │ counterfactual            │ (Coding/Math/MCQ 분리)     │ 반사실적(Counterfactual) 트리   │
└─────┴───────────────────────────┴────────────────────────────┴─────────────────────────────────┘
```

---

## 📂 폴더별 상세 문서 바로가기

1. [**01. CacheOps-Squad & KV-Trace Profiler**](./01-cacheops-squad-kv-profiler/README.md)
   - *NPU 친화적 Prefix Cache 공유 극대화 스쿼드 및 하드웨어 연계 KV 캐시 프로파일러*
2. [**02. Adaptive-Budget Squad & Pareto Frontier Visualizer**](./02-adaptive-budget-pareto-frontier/README.md)
   - *불확실성 기반 3단계 조기 포기 및 토큰 한계효용 파레토 최적화 시스템*
3. [**03. Index-Localized Squad & Diff-Flow Explainability Engine**](./03-index-localized-diff-flow/README.md)
   - *Coding 트랙(0.5 가중치) 저격 무손실 인덱싱 & OTel 4단계 줌 인과 추적 엔진*
4. [**04. Failure-Attribution Squad & Root-Cause Intelligence Dashboard**](./04-failure-attribution-root-cause/README.md)
   - *결정론적 채점기 규격 대응 자가 치유 스쿼드 및 책임 주체 분리형 옵저버빌리티*
5. [**05. Speculative-Specialist Squad & Counterfactual Decision Matrix**](./05-speculative-specialist-counterfactual/README.md)
   - *경로별 특화 하이브리드 파이프라인 & 반사실적 의사결정 시뮬레이션 뷰어*
