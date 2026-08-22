# 05. NPU KV-Cache & Prefix Caching (NPU 환경 KV 캐시 및 접두사 캐싱 최적화)

> **핵심 테제:** FuriosaAI RNGD NPU 및 Backend.AI 인프라에서 작동하는 Automatic Prefix Caching (APC)의 하드웨어 특성을 이해하고, 문항 내(In-item) 멀티에이전트 60KB 컨텍스트 공유를 극대화하는 3층 프롬프트 아키텍처를 설계한다.

---

## 1. FuriosaAI NPU & Backend.AI 추론 가속 구조

### 1.1 FuriosaAI RNGD의 Automatic Prefix Caching (APC)
- **Radix Tree 기반 캐싱:** Furiosa SDK(Furiosa-LLM)는 프롬프트의 토큰 시퀀스를 Radix Tree 구조로 관리하여, 공통 접두사(Prefix)에 대한 Key-Value (KV) 텐서를 NPU HBM 메모리에 유지하고 중복 연산을 완전히 생략(Zero-Compute Prefill)한다.
- **Hybrid Memory Management:** Global Attention과 Sliding-Window Attention 레이어의 KV 캐시를 분할 관리하여 긴 컨텍스트(60KB+)에서도 OOM 없이 고속 서빙을 유지.
- **Backend.AI 연동:** Backend.AI 서빙 클러스터는 Prefix Cache Affinity 라우팅을 지원하여 동일한 프리픽스를 가진 요청을 동일한 NPU 노드로 자동 집중시킨다.

---

## 2. 저장소 간 캐시의 환상과 인-문항(In-Item) 캐시 실측

### 2.1 저장소별 캐시 기대의 무효성
- 사전 조사 결과, 서로 다른 SWE-bench 문항 간의 코드베이스 재사용률은 Django가 2.7%, 나머지 9개 프로젝트는 **0.0%**였다. 문항마다 커밋 해시와 주입되는 발췌 번들이 완전히 다르기 때문.
- 따라서 "저장소 단위 캐시"를 기대하는 것은 무의미하다.

### 2.2 인-문항(In-Item) 멀티에이전트 캐시 적중률 극대화
진짜 캐시 이득은 **단일 문항을 처리하는 과정에서 스쿼드 내 여러 에이전트(Architect, Editor, Auditor)가 동일한 60KB 컨텍스트를 공유할 때** 발생한다.

$$	ext{Input Token Cost} = T_{	ext{prefix}} + \sum_{i=1}^{M} T_{	ext{agent\_instruction}}^{(i)} \quad (	ext{단, APC 활성화 시 } T_{	ext{prefix}}	ext{는 1회만 계산})$$

```
[비교: 프롬프트 배치에 따른 NPU KV 캐시 적중률]

[나쁜 배치: 에이전트 역할이 맨 앞에 오는 경우]
Agent 1: [Role: Architect] + [대회 지시문] + [60KB 컨텍스트] ──> Cache MISS (신규 20K Prefill)
Agent 2: [Role: Editor]    + [대회 지시문] + [60KB 컨텍스트] ──> Cache MISS (신규 20K Prefill)
=> 총 40,000 토큰 전체 NPU 연산 발생!

[최적 배치: 프롬프트 3층 구조 (Cache-First)]
Agent 1: [Layer 1: 대회 지시] + [Layer 2: 60KB 컨텍스트] | [Layer 3: Architect 역할] ──> Layer 1,2 Cache HIT
Agent 2: [Layer 1: 대회 지시] + [Layer 2: 60KB 컨텍스트] | [Layer 3: Editor 역할]    ──> Layer 1,2 Cache HIT
=> Layer 1, 2 (19,800 토큰) 100% 캐시 적중! 새로 계산하는 것은 Layer 3 (200 토큰)뿐!
```

---

## 3. 프롬프트 3층 구조 (3-Layer Architecture) 표준 설계

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 1: 대회 시스템 컨텍스트 + 출력 계약 + Few-shot (고정 프리픽스)      │
│ - 전 트랙 전 문항 100% 동일 바이트 (Radix Tree Root Cache Hit)          │
├─────────────────────────────────────────────────────────────────────────┤
│ Layer 2: 문항 Payload + 60,000자 발췌 컨텍스트 (문항 공유 프리픽스)        │
│ - 해당 문항 내의 모든 에이전트가 100% 동일하게 공유 (In-Item Cache Hit)   │
╞═════════════════════════════════════════════════════════════════════════╡
│ ─────────────────────────── [KV CACHE 경계] ─────────────────────────── │
╞═════════════════════════════════════════════════════════════════════════╡
│ Layer 3: 개별 에이전트 전용 동적 지시 (Dynamic Agent Instruction)        │
│ - 각 에이전트별 짧은 역할 정의 (Architect: 앵커 추출 / Editor: 패치 작성)│
└─────────────────────────────────────────────────────────────────────────┘
```

- **포털 API 계측 검증:** 포털이 노출하는 `cached_input_share` 메트릭을 통해 실제 NPU 상에서 70% 이상의 캐시 적중률이 달성됨을 실시간으로 확인 가능.
