# Single-Agent와 Multi-Agent: 언제 squad가 이득인가

## 결론

이 대회에서는 **minimal routed single-worker path**를 baseline으로 삼아야 한다. Multi-agent는 다음 세 조건이 동시에 성립할 때만 실험할 가치가 있다.

1. subtask가 실제로 분리 가능하다.
2. agent 사이 handoff가 중요한 정보를 잃지 않는다.
3. 추가 input/output/coordination token을 포함한 동일 budget 비교에서 정확도가 오른다.

coding, math, generic 세 track은 open-ended web research처럼 독립적인 breadth search가 아니다. 한 문항은 이미 fully observed이고, 도구가 없고, 답은 하나이며, coding은 같은 60KB context에 강하게 결합된다. 이 조건은 많은 multi-agent 성공 사례보다 controlled negative results에 더 가깝다.

## 가장 강한 최신 controlled evidence

### Nature Machine Intelligence 2026

[Capable language models can outgrow the benefits of collaboration](https://www.nature.com/articles/s42256-026-01268-y)은 prompt, tools, per-system compute ceiling을 맞추고 260개 configuration, 6개 benchmark, 5개 architecture, 3개 LLM family를 비교했다.

핵심 결과:

- single-agent baseline performance가 coordination 효과의 가장 robust한 predictor였다.
- 약 45% capability-saturation threshold는 SWE-bench Verified와 Terminal-Bench validation 16개 configuration에서 multi-agent gain의 부호를 94% 맞혔다.
- 이 threshold는 universal law가 아니라 within-domain selection rule이다. underlying interaction coefficient 자체는 cluster-robust correction을 통과하지 못했다.
- SWE-bench Verified 평균 single-agent 0.488 대비 hybrid 0.481, centralized 0.475, decentralized 0.456, independent 0.425였다.
- fixed budget에서 Hybrid는 single-agent보다 turn 6.2배, centralized 3.8배, decentralized 3.6배를 썼다.
- agent가 3~4명을 넘으면 per-agent reasoning budget이 얇아지고 communication cost가 지배하는 resource ceiling을 관측했다.
- centralized verification은 error amplification을 줄였지만, 모든 domain에서 성능을 올리지는 않았다.

대회 적용:

- coding benchmark가 SWE-bench 계열이라는 점은 직접 관련 있다.
- 그러나 이 track은 tool-free, judge-prepared context이고 논문의 SWE-bench setup은 tool-enabled agentic environment다.
- 따라서 “45% 이상이면 절대 multi-agent 금지”가 아니라 “strong baseline을 먼저 재고, split은 실험으로 증명”이 올바른 전이다.

### Equal-thinking-token preprint 2026

[Single-Agent LLMs Outperform Multi-Agent Systems on Multi-Hop Reasoning Under Equal Thinking Token Budgets](https://arxiv.org/html/2604.02460v1)는 FRAMES와 MuSiQue, Qwen3·DeepSeek·Gemini, Sequential·Debate·Ensemble·Parallel Roles·Subtask Parallel을 fixed thinking-token budget으로 비교했다.

핵심 결과:

- 정상 context에서 single-agent가 모든 비교에서 best이거나 통계적으로 indistinguishable했다.
- multi-agent가 경쟁력을 얻은 경우는 single-agent의 effective context utilization을 deletion, masking, substitution 등으로 충분히 훼손했을 때였다.
- 저자들은 여러 agent의 이점으로 보이는 결과가 실제로는 extra compute 또는 context effect일 수 있다고 경고한다.
- API가 요청한 reasoning budget과 실제 사용 token을 정확히 맞추지 않는 artifact도 관측했다.

대회 적용:

- math/generic의 fully observed single-shot reasoning에는 강하게 적용된다.
- coding 60KB에는 context filtering 가설이 남는다. 다만 Qwen model card상 16k~32k long-context 성능이 높고, 60KB는 대략 16~20k token이므로 context가 길다는 이유만으로 split이 자동 정당화되지는 않는다.
- AI:GO model별 실제 token accounting을 측정해야 한다.

### BenchAgent preprint 2026

[Do More Agents Help?](https://arxiv.org/html/2606.05670)은 benchmark loader, tool access, answer contract, usage accounting, trajectory logging을 정렬한 뒤 GPT-4.1 기반 single-agent와 6개 MAS를 10개 reasoning/coding/tool benchmark에서 비교했다.

- single-agent benchmark-balanced average는 74.12%.
- 유일하게 수치상 앞선 EvoAgent는 75.56%, +1.44pp였지만 one-run uncertainty보다 작았다.
- 나머지 5개 MAS는 2.56~11.29pp 뒤졌고 더 비싼 accuracy-cost 영역에 있었다.
- 개별 protocol은 error mode와 맞을 때만 이득이었다. HumanEval/MATH처럼 결과를 확인하기 쉬운 task에서 debate가 이득인 경우가 있었고, AIME에서는 한 MAS가 붕괴했다.

이 연구도 preprint이며 evaluation backend가 대회 model과 다르다. 그러나 “agent count가 아니라 protocol-task fit을 재라”는 원칙은 직접 적용된다.

### 동일 예산 peer-reviewed 비교

[Reasoning in Token Economies](https://aclanthology.org/2024.emnlp-main.1112/)는 EMNLP 2024에서 compute budget을 맞춰 reasoning strategy를 비교했다. 단순 CoT + self-consistency baseline은 comparable compute를 받으면 복잡한 strategy를 자주 앞섰고, multi-agent debate와 Reflexion은 compute를 늘렸을 때 오히려 나빠지는 경우도 있었다.

[Should We Be Going MAD?](https://proceedings.mlr.press/v235/smit24a.html)는 ICML 2024에서 multi-agent debate가 self-consistency와 여러 reasoning-path ensemble을 안정적으로 이기지 못했다고 보고했다. 잘 튜닝한 일부 MAD variant는 앞섰지만 protocol이 hyperparameter에 민감하고 최적화하기 어려웠다.

두 결과는 debate를 절대 금지하라는 뜻이 아니다. 이 contest에서 debate가 baseline이 되려면 **같은 total compute에서** 이기고, tuning 비용까지 run ledger에 포함해야 한다는 뜻이다.

## Multi-agent 실패가 생기는 이유

[MAST: Why Do Multi-Agent LLM Systems Fail?](https://arxiv.org/html/2503.13657v3)은 7개 framework의 1,642개 trace를 분석해 14개 failure mode를 세 category로 묶었다.

1. system design issue.
2. inter-agent misalignment.
3. task verification failure.

연구는 7개 system에서 41.0~86.7% failure rate를 관측했다. taxonomy는 150개 trace를 6명의 expert가 분석해 만들었고, 최종 human inter-annotator kappa는 0.88이었다. ChatDev에서 CEO에게 final say를 명확히 주는 workflow 수정은 같은 prompt/model 조건에서 +9.4% success였다.

이 결과가 주는 설계 규칙:

- final answer owner를 하나로 고정한다.
- role boundary와 deliverable schema를 짧고 명시적으로 둔다.
- stop condition을 LLM의 막연한 판단에 맡기지 않는다.
- verifier가 있더라도 무엇을 검증할 수 있는지 한정한다.
- handoff packet은 재서술보다 exact evidence reference를 전달한다.

MAST는 framework failure trace를 분류하는 연구이지 이 track에서 +9.4%가 재현된다는 보장은 없다. 수치는 context-specific다.

## 역할 이름보다 output contract

[When “A Helpful Assistant” Is Not Really Helpful](https://aclanthology.org/2024.findings-emnlp.888/)는 162개 persona, 4개 LLM family, 2,410개 factual question을 비교했다. System prompt의 persona는 control보다 전반적으로 성능을 높이지 않았고, question별 best persona를 자동 선택하는 방법도 random selection보다 나은 결과가 일관되지 않았다.

따라서 `CodePatchSolver` 같은 이름은 책임을 사람이 읽기 쉽게 만드는 label일 뿐이다. Prompt token은 “expert developer처럼 행동하라”보다 supplied input, exact task, output contract, stop condition에 쓴다. Persona 연구는 factual QA 중심이므로 coding에서 persona가 절대 무효라는 증거는 아니지만, 검증되지 않은 역할 서사를 긴 system prompt로 만드는 근거도 아니다.

## 성공 사례는 왜 그대로 전이되지 않는가

[Anthropic의 multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)은 Opus 4 lead + Sonnet 4 subagents가 internal breadth-first research eval에서 single Opus 4보다 90.2% 높았다고 보고한다. 동시에 다음도 공개한다.

- agent는 chat보다 약 4배 token.
- multi-agent system은 chat보다 약 15배 token.
- BrowseComp 성능 분산의 80%를 token usage 하나가 설명했고, model/tool call을 합치면 95%였다.
- coding은 parallelizable subtask가 적고 shared context와 dependency가 많아 흔히 좋지 않은 fit이다.

이 사례의 task는 web/tool search가 가능한 open-ended breadth research다. 이 track은 no-tool, one-answer, deterministic judge다. Anthropic의 성능 증가는 “coordination 자체”보다 더 많은 token과 병렬 search capacity가 만든 결과일 수 있으며, 30점 token efficiency와 직접 충돌한다.

## 이 track에 대한 architecture 판정

| 후보 | 장점 | 핵심 비용/위험 | baseline 여부 |
|---|---|---|---|
| Planner → track solver | 정보 손실 최소, 두 호출, answer owner 명확 | Planner overhead | **예** |
| Planner → Architect → Editor | context filtering, reasoning/format 분리 | full context 중복, anchor 손실, wave 증가 | coding A/B만 |
| 2~3 independent solvers + vote | 오류 다양성 | token 2~3배, correlated error | math/generic 제한 실험 |
| solver → critic → reviser | 오류 검토 | intrinsic critique가 정답 신호 아님 | 기본 off |
| 다수 역할 debate | 관점 다양성 | fully observed one-answer task에서 overhead | 제외 |
| tool-based verifier | 강한 external feedback | 평가 중 tool 없음 | local harness만 |

## 실무 판단 규칙

Multi-agent variant를 채택하려면 다음 조건을 모두 만족해야 한다.

```text
1. 동일한 practice split과 model에서 비교한다.
2. Planner를 포함한 total input/output/reasoning/cache token을 센다.
3. extraction failure를 accuracy와 분리한다.
4. accuracy gain이 repeated run의 noise보다 크다.
5. normalized cost 대비 gain이 baseline Pareto frontier를 지배한다.
6. 마지막 wave answer owner가 하나다.
```

조건 4와 5가 없으면 agent를 추가하지 않는다. “역할이 있어 보인다”는 architecture evidence가 아니다.
