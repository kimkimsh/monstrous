# Claim–Evidence Matrix

## 등급

| 등급 | 의미 | 사용 원칙 |
|---|---|---|
| A | 공식 contest artifact, live portal, local deterministic verification | 실행 계약과 채점 사실의 기준 |
| B | peer-reviewed controlled study 또는 공식 model/provider 문서 | 강한 일반 근거. 환경 차이는 별도 기록 |
| C | 공개 preprint와 재현 가능한 정량 실험 | 설계 가설과 A/B 우선순위 |
| D | vendor engineering report 또는 project 문서 | 실제 운영 신호. 내부 eval과 제품 편향 고려 |
| E | 최근 30일 community signal | 탐색용. 정량 결론의 단독 근거로 사용 금지 |

## 대회·workload claims

| ID | Claim | 핵심 evidence | 등급 | 판정과 한계 |
|---|---|---|---|---|
| C01 | 총점은 benchmark 40, visualization 30, token efficiency 30이다. | local `3 LABL.pdf` p.24; [트랙 정리](../../../example_task/00-트랙-정리.md) 31~72행 | A | 확정 |
| C02 | benchmark는 coding 0.5, generic 0.25, math 0.25다. | manifest; [평가 규칙](../../../track_resource/lableup/02-평가-채점-규칙.md) 59~74행 | A | 확정 |
| C03 | grader는 deterministic이며 LLM judge가 아니다. | portal/manifest; [트랙 정리](../../../example_task/00-트랙-정리.md) 76~100행 | A | 확정 |
| C04 | 최신 public set은 121개다. | live portal 재조회; `bash tools/verify.sh`; [README](../../../example_task/README.md) 14~23행 | A | 2026-08-22 기준 |
| C05 | coding request가 비용 지배항이다. | 20개 총 872,683 bytes, median 63,812; math 32,253, generic 45,220 | A | token은 tokenizer/model에 따라 달라지므로 bytes는 proxy |
| C06 | coding 한 item이 generic보다 항상 10배 이상 중요하다. | hidden range와 weight로 계산한 3.73~9.97배 | A | **기각**. 중간값 약 6.03배 |
| C07 | one-shot prompt에 `{{TASK}}`를 두 번 넣으면 item이 두 번 삽입된다. | [합성 규칙](../../../example_task/01-요청-합성-규칙.md) 9~50행 | A | 확정. coding에서는 매우 큰 비용 risk |
| C08 | 정확히 한 Planner가 필요하고 평가 중 tool이 없다. | [AI:GO 가이드](../../../track_resource/lableup/03-AIGO-Squad-완전가이드.md) 124~133, 532~541행 | A | 현재 local track 자료 기준 |
| C09 | release server에서 squad end-to-end가 검증됐다. | [CLI 운영](../../../example_task/04-CLI-운영.md) 367~383행 | A | **미확인**. sidecar spawn까지만 확인 |

## Architecture claims

| ID | Claim | 핵심 evidence | 등급 | 판정과 한계 |
|---|---|---|---|---|
| A01 | Multi-agent는 agent 수만 늘리면 좋아진다. | [Scaling Agent Systems](https://www.nature.com/articles/s42256-026-01268-y): architecture/task에 따라 sign 변화 | B | **기각** |
| A02 | 고난도 task는 무조건 multi-agent가 낫다. | Nature study의 centralized/decentralized/hybrid 결과와 threshold | B | **기각**. threshold는 해당 조건의 predictor이지 보편 법칙이 아님 |
| A03 | Fixed total reasoning token에서 MAS가 SAS보다 낫다. | [Equal Token Budgets](https://arxiv.org/html/2604.02460v1) | C | 비교 benchmark에서는 대체로 **기각**; degraded context가 예외 |
| A04 | 범용 benchmark agent를 추가하면 평균 성능이 오른다. | [BenchAgent](https://arxiv.org/html/2606.05670): 7개 중 5개 하락, 최고 +1.44pp | C | **기각**. 비용도 증가 |
| A05 | Coordination failure는 드물다. | [MAST](https://arxiv.org/html/2503.13657v3): 1,642 traces, 41~86.7% failure | B/C | **기각**. framework/task 전이 한계 있음 |
| A06 | Agent 수가 성능의 핵심 독립 변수다. | Nature matched prompt/tool/compute study | B | **기각**. architecture와 task structure가 중요 |
| A07 | Broad parallel research는 MAS에 적합할 수 있다. | [Anthropic engineering report](https://www.anthropic.com/engineering/multi-agent-research-system) | D | 지지. 내부 breadth eval +90.2%; coding에는 poor fit이라고 명시 |
| A08 | 동일 compute에서도 복잡한 reasoning/MAD가 단순 baseline보다 안정적으로 낫다. | [Reasoning in Token Economies](https://aclanthology.org/2024.emnlp-main.1112/), [Should We Be Going MAD?](https://proceedings.mlr.press/v235/smit24a.html) | B | **기각**. 일부 tuned MAD 예외, hyperparameter 민감 |
| A09 | `expert` persona를 system prompt에 넣으면 객관적 정확도가 오른다. | [Helpful Assistant persona study](https://aclanthology.org/2024.findings-emnlp.888/) | B | 일반적으로 **기각**. task/output contract에 token 사용 |

## Routing·budget·verification claims

| ID | Claim | 핵심 evidence | 등급 | 판정과 한계 |
|---|---|---|---|---|
| R01 | Learned routing은 cost를 줄일 수 있다. | [RouteLLM](https://arxiv.org/html/2406.18665) | C | 지지. OOD calibration 필요, headline은 >2× 절감 |
| R02 | FrugalGPT가 일반적으로 98%를 절감한다. | [FrugalGPT](https://arxiv.org/html/2305.05176) | C | **과장**. 최대 98%; dataset별 50~98%, provider/price/labeled data 의존 |
| R03 | Concise reasoning은 항상 accuracy를 유지한다. | [Chain of Draft](https://arxiv.org/html/2502.18600) | C | **기각**. Qwen2.5-3B GSM8K는 59.1→43.1 |
| R04 | Prompt에 `Wait`를 쓰면 s1 budget forcing이 구현된다. | [s1](https://arxiv.org/html/2501.19393) | C | **기각**. decoder stop-token control이 필요 |
| R05 | Same-model self-review는 안전하게 개선한다. | [Intrinsic self-correction](https://arxiv.org/html/2310.01798) | C | **기각**. external feedback 없으면 흔히 저하 |
| R06 | Self-consistency는 정확도를 높일 수 있다. | [Self-Consistency](https://arxiv.org/abs/2203.11171) | C | 지지. 여러 sample 비용과 task/model 전이 검증 필요 |
| R07 | 이 대회에서 deterministic preflight를 evaluation loop에 넣을 수 있다. | organizer 문서에서 허용 여부 없음 | — | **미확인**. local harness에는 사용 가능 |

## Track-specific claims

| ID | Claim | 핵심 evidence | 등급 | 판정과 한계 |
|---|---|---|---|---|
| T01 | Localization과 repair를 분리하면 coding에 도움이 될 수 있다. | [Agentless](https://arxiv.org/html/2407.01489v2), [Loc2Repair](https://arxiv.org/html/2606.30963) | C | 유망한 가설. 이 대회는 repo/tool 없이 judge excerpt만 제공 |
| T02 | Structured editing은 code repair 비용과 정확도를 개선할 수 있다. | [SWE-Edit](https://arxiv.org/html/2604.26102v2) | C | 유망. tool-based viewer 조건과 AI:GO 조건이 다름 |
| T03 | Generic은 reasoning을 끄는 것이 안전하다. | [MMLU-Pro](https://arxiv.org/html/2406.01574v3): GPT-4o 53.5→72.6 CoT | C | **기각**. concise private reasoning A/B가 필요 |
| T04 | Qwen LCB 43.2 대 Aider 35.6 차이는 formatting 때문임을 증명한다. | [Qwen model card](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507) | B | **기각**. 서로 다른 benchmark |
| T05 | Qwen context 262K이므로 60KB coding input에는 문제가 없다. | Qwen model card; [Lost in the Middle](https://arxiv.org/html/2307.03172) | B/C | **미확인**. capacity와 task accuracy는 다름 |
| T06 | 엄격한 output format은 reasoning accuracy와 무관하다. | [Let Me Speak Freely?](https://arxiv.org/abs/2408.02442) | B/C | **기각 신호**. exact final boundary만 구조화하고 직접 A/B |
| T07 | 16~20k input은 context window 안이므로 안전하다. | [Chroma Context Rot](https://www.trychroma.com/research/context-rot) | D | **기각**. capacity와 reliable utilization은 다름; code repair 전이는 미확인 |

## Cache·observability claims

| ID | Claim | 핵심 evidence | 등급 | 판정과 한계 |
|---|---|---|---|---|
| O01 | Shared prefix는 반드시 billing cost를 크게 줄인다. | contest exact 할인율·TTL·worker request order 미공개 | — | **미확인**. actual cache-read usage와 billed rate를 측정해야 함 |
| O02 | OTel core의 GenAI 문서가 현재 authoritative source다. | [이전 문서의 이동 안내](https://opentelemetry.io/docs/specs/semconv/gen-ai/) | B | **기각** |
| O03 | 현재 OTel GenAI schema를 그대로 stable production contract로 써도 된다. | [semantic-conventions-genai](https://github.com/open-telemetry/semantic-conventions-genai) status Development | B | **기각**. version pin과 compatibility layer 필요 |
| O04 | Prompt/output content는 기본 수집해야 한다. | current OTel GenAI spans의 content field Opt-In | B | **기각**. hidden data는 기본 비수집 |
| O05 | 관측된 reviewer span을 제거한 UI replay는 true ablation이다. | causal execution semantics | — | **기각**. 재실행 없이는 prefix simulation일 뿐 |
| O06 | Portal은 cached input을 별도 계량하고 fresh input보다 싸게 처리한다. | [트랙 개요](../../../track_resource/lableup/01-트랙-개요.md) 138~148행 | A | 확정. exact multiplier·TTL·worker hit는 미확인 |

## 최종 evidence-weighted 결론

가장 강하게 지지되는 조합은 deterministic routing, track specialist, single-worker critical path, exact output check, hard budget, measured escalation이다. Architect/Editor split, reviewer, self-consistency, cache saving은 모두 **가능한 최적화**이지 확인된 contest 이득이 아니다. 따라서 이들은 실험 registry의 candidate로 남기고 baseline contract에 포함하지 않는다.
