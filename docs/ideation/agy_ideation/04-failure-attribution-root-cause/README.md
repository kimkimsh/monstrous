# 주제 4: Failure-Attribution Squad & Root-Cause Intelligence Dashboard

> **[갱신됨 2026-08-23 · 이 문서는 역사 기록이다]** 2026-08-22 발상 단계의 기록이고 최종 설계가 아니다. 현행은 `../../final_final_ideation/spec/`이다. **이 문서가 전제한 Unified Diff 출력은 틀렸다** — coding 출력은 SEARCH/REPLACE 블록이고, `git diff`를 내면 전 문항 `extraction_failed`다.
> **"결정론적 채점기 규격 대응 자가 치유 스쿼드 및 책임 주체 분리형 옵저버빌리티"**

---

## 1. 한 줄 요약
**주최 측 채점 체계의 5대 Outcome 규격을 스쿼드 상태 머신에 내재화하여 형식 추출 실패(`extraction_failed`)를 0%로 만들고 자가 치유(Self-Healing)하는 스쿼드**와, **인프라 장애(주최측)와 모델 오류(팀)를 명확히 분리 입증하는 Root-Cause 진단 대시보드**.

---

## 2. 기획 배경 및 문제의식 (Why)

1. **치명적인 '침묵의 0점(`extraction_failed`)' 방지**:
   - 주최 측 채점기는 100% 결정론적 프로그램(Docker pytest, integer_exact, letter_match 등)입니다.
   - 아무리 훌륭한 추론을 하더라도 사소한 마크다운 펜스 오류나 서두 미사여구 때문에 답안 추출에 실패하면 `extraction_failed`로 즉시 0점 처리됩니다.
2. **AI:GO 인프라 장애의 억울한 감점 리스크 차단**:
   - 리더보드 문서 확인 결과: 주최 측 엔드포인트는 간헐적 다운타임이 발생하며, AI:GO는 이를 *"모든 태스크 실패(팀의 0점)"*로 오인식할 위험이 있습니다.
   - `infrastructure_failed`와 `grader_error`는 주최측 책임으로 공식 순위 분모에서 제외되므로, 이를 트레이스 상에서 명확히 분리 태깅(`FailureOwner = organizer`)해야 점수를 온전히 지킬 수 있습니다.
3. **심사위원(Lablup)의 채점 아키텍처와 100% 동기화**:
   - 제출 서버의 OpenAPI 스펙 어휘(`Outcome`, `ItemStatus`, `FailureKind`, `FailureOwner`)를 시각화에 그대로 채택함으로써 전문성과 완성도를 극대화합니다.

---

## 3. 스쿼드 아키텍처 (How - Squad Architecture)

### 📌 자가 치유 및 결함 분리 상태 머신

```
[ 문제 입력 ]
     │
     ▼
┌──────────────────────────────┐
│ Contract-Enforcing Planner   │ ──(트랙별 엄격 포맷 템플릿 강제)
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ Model Worker (Solver/Coder)  │
└──────────────┬───────────────┘
               │ (답안 생성)
               ▼
┌──────────────────────────────┐
│ Deterministic Pre-Grader     │ ──(형식 검증 통과)──▶ [ 정상 제출 완료 ]
│ (정규식 기반 로컬 검증기)    │
└──────────────┬───────────────┘
               │ (형식 위반 발견 시: extraction_failed 위험)
               ▼
┌──────────────────────────────┐
│ Self-Healing Sanitizer       │ ──(마크다운 제거 / \boxed{} 정규화)──▶ [ 자가 치유 후 제출 ]
└──────────────────────────────┘
```

### 👥 에이전트 역할 구성
- **Contract-Enforcing Planner**: 각 트랙별 엄격한 출력 계약(SWE-bench diff, Math \boxed{}, MCQ 단일 알파벳)을 모든 에이전트에 주입
- **Deterministic Pre-Grader**: 주최 측 채점기 로직(`math_verify`, `letter_match` 정규식)을 스쿼드 내부에서 사전 시뮬레이션
- **Self-Healing Sanitizer**: 서두/설명 텍스트가 섞인 경우 핵심 답안만 정제 추출하여 `extraction_failed`를 완벽 방지
- **Fault-Isolator**: 네트워크 타임아웃 발생 시 즉시 `organizer` 결함으로 플래깅하여 불필요한 재시도 토큰 낭비 차단

---

## 4. 인터랙티브 트레이스 시각화 (Trace Visualization)

### 🖥️ `Root-Cause Intelligence Dashboard` 핵심 화면
1. **5대 Outcome 분류 매트릭스**:
   - `graded`(정상 채점), `extraction_failed`(추출 실패), `capped`(상한 초과), `grader_error`(채점기 오류), `infrastructure_failed`(인프라 오류) 실시간 분포 차트.
2. **Failure Ownership Sankey 다이어그램**:
   - 전체 실패 케이스가 `Team`(프롬프트/지능), `Policy`(토큰 상한), `Organizer`(서버 타임아웃)로 어떻게 분기되는지 인과 흐름 시각화.
3. **Self-Healing Success Tracker**:
   - Pre-Grader 단계에서 형식 오류가 감지되었으나 Sanitizer를 통해 자가 치유되어 정답 처리된 복구 성공 사례 타임라인.

---

## 5. 1등 당선 전략 (Winning Edge)

| 평가 항목 | 전략적 우위 (Why it wins) |
|---|---|
| **벤치마크 (40점)** | 포맷 불일치로 인한 `extraction_failed`를 **0건으로 완벽 방어**하여 허성 감점 제로화. |
| **시각화 (30점)** | 주최 측의 공식 OpenAPI 및 채점 스키마 어휘를 100% 흡수한 **가장 정확하고 직관적인 Interpretability & Clarity** 제공. |
| **토큰 효율 (30점)** | 인프라 장애 시 헛도는 재시도 루프를 즉각 격리하여 불필요한 토큰 누수 완벽 차단. |
