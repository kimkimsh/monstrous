# Context, Prefix Cache, Observability

## 결론

Coding input은 비용의 지배항이다. Portal은 cached input이 존재하고 fresh input보다 싸다고 명시한다. 하지만 “모든 agent가 같은 60KB prefix를 보면 1/N 비용”이라는 가정은 exact discount, minimum prefix, TTL, prompt injection order와 actual hit가 확인되기 전까지 근거가 없다. 먼저 한 worker만 full context를 읽는 baseline을 만들고, cache 관련 값은 trace에서 measured field로 다룬다.

## 60KB context를 어떻게 볼 것인가

Local 공개 context는 거의 모두 60,000자 상한을 채우며 약 16~20k token이다. [Lost in the Middle](https://arxiv.org/html/2307.03172)은 relevant information이 긴 context의 처음이나 끝에 있을 때 높고 중간에서 낮아지는 U-shaped performance를 여러 model에서 관측했다. 다만 연구 model은 2023 세대이고 task도 multi-document QA/key-value retrieval이다.

[Chroma Context Rot](https://www.trychroma.com/research/context-rot)는 18개 model을 고정된 task의 여러 input length에서 평가해 context가 길어질수록 reliability가 불균일하게 떨어지는 현상을 보고했다. 이 technical report는 최신 Qwen3 계열도 포함하지만 code repair benchmark는 아니다. 따라서 “20k면 안전” 또는 “중간 위치만 옮기면 해결” 같은 단순 규칙의 근거로 쓰지 않고, fused/split 실험을 먼저 해야 한다는 위험 신호로 사용한다.

현재 Qwen model card의 RULER full-attention 성능은 4k 98.0, 16k 96.9, 32k 97.2, 64k 93.4다. 이 수치만 보면 16~20k가 명백한 failure zone은 아니다. RULER와 code repair는 다른 task이므로 다음 두 가설을 직접 비교한다.

- H1 fused: full 60KB를 한 CodePatchSolver가 읽는다.
- H2 split: Architect가 exact anchors를 만들고 Editor는 selected excerpts와 original lines만 본다.

H2가 이기려면 context reduction이 localization miss와 second-call overhead를 넘어서야 한다.

## Prompt 배치

Judge composition rule상 one-shot prompt의 `{{TASK}}`가 item으로 치환된다. Stable instruction을 앞에 두고 `{{TASK}}`를 끝에 한 번만 두는 것은 합리적이다.

```text
[stable track policy]
[short output reminders]
{{TASK}}
```

피해야 할 것:

- `{{TASK}}` 두 번.
- REQUIRED OUTPUT block 전문 중복.
- item-dependent text를 stable prefix 앞에 둠.
- agent별 role prompt가 거대한 shared prefix 앞에 들어가는 구조.

그러나 AI:GO가 Planner/worker message를 어떻게 조립하는지 확인되지 않았다. Portal의 development usage에는 `cached_input_tokens`와 `cached_input_share`가 존재하지만, 이 squad variant가 실제로 hit하는지는 별개다. 실제 run의 hit와 billed rate를 확인하기 전에는 예상 cache saving을 budget에 넣지 않는다.

## Cache accounting에 필요한 field

Model call마다 최소 다음을 기록한다.

```text
input_tokens
output_tokens
reasoning_output_tokens
cache_read_input_tokens
cache_write_input_tokens
model
agent
track
item_id
wave
latency_ms
finish_reason
```

Derived metrics:

```text
cached_input_share = cache_read_input_tokens / input_tokens
fresh_input_tokens = input_tokens - cache_read_input_tokens
cost = provider_pricing(model, token_type) × token_count
cost_per_correct = total_normalized_cost / correct_items
```

Provider가 billed token과 consumed token을 둘 다 주면 billed 값을 ranking cost에 사용하고 consumed 값을 engineering diagnostic으로 별도 저장한다.

## OpenTelemetry GenAI 사양의 현재 상태

기존 core 문서는 [별도 repository로 이동했으며 더 이상 유지되지 않는다](https://opentelemetry.io/docs/specs/semconv/gen-ai/). 현재 source는 [open-telemetry/semantic-conventions-genai](https://github.com/open-telemetry/semantic-conventions-genai)이고 status는 **Development**다. 따라서 version pin과 custom compatibility layer가 필요하다.

[현재 model spans 사양](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md)에서 쓸 field:

- `gen_ai.operation.name`
- `gen_ai.provider.name`
- `gen_ai.request.model`
- `gen_ai.response.model`
- `gen_ai.request.max_tokens`
- `gen_ai.request.reasoning.level`
- `gen_ai.response.finish_reasons`
- `gen_ai.usage.input_tokens`
- `gen_ai.usage.output_tokens`
- `gen_ai.usage.reasoning.output_tokens`
- `gen_ai.usage.cache_read.input_tokens`
- `gen_ai.usage.cache_write.input_tokens`

[현재 agent spans 사양](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md)은 `invoke_agent`, `invoke_workflow`, `plan`, `execute_tool` operation을 정의한다. `plan` span 아래 LLM call을 child로 두고, 실행 task는 같은 `invoke_agent` 아래 sibling으로 표현하는 model이 AI:GO wave trace와 잘 맞는다.

[현재 metrics 사양](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-metrics.md)은 `gen_ai.client.token.usage`, `gen_ai.client.operation.duration`, `gen_ai.invoke_agent.duration`, `gen_ai.invoke_agent.inference_calls`, `gen_ai.invoke_agent.tool_calls` 등을 정의한다.

## Custom field

OTel에 없는 competition field만 `jxc.*`로 추가한다.

```text
jxc.run.id
jxc.execution.id
jxc.item.id
jxc.track
jxc.wave.index
jxc.task.id
jxc.agent.role
jxc.answer.extracted_from
jxc.outcome
jxc.failure.kind
jxc.failure.owner
jxc.grader.name
jxc.patch.search_exact
jxc.budget.remaining_tokens
jxc.policy.variant
```

`gen_ai.*`를 custom 뜻으로 재정의하지 않는다. OTel Development schema version과 application schema version을 trace metadata에 함께 둔다.

## Privacy와 content capture

현재 OTel GenAI spec에서 `gen_ai.input.messages`, `gen_ai.output.messages`, `gen_ai.system_instructions`, prompt variable은 Opt-In이다. Default trace에는 full problem, model reasoning, repository code를 넣지 않는다.

권장 저장 계층:

1. 기본 telemetry: ID, timing, tokens, model, outcome, hashes.
2. local demo artifact: 공개 practice item과 team-owned prompt/output 원문.
3. secret/private run: access-controlled content, 명시적 retention.

Visualization이 실제 answer bytes를 보여줄 때는 공개 practice/demo run만 사용한다. Hidden evaluation content를 무조건 persist하거나 관객 browser로 보내지 않는다.

## Replay의 정직한 정의

이미 실행된 candidate sequence에서 “n번째에서 멈췄다면”을 계산하는 것은 **observed-prefix policy replay**다. 이전 실패 feedback을 보고 생성된 이후 candidate를 앞 단계가 없던 세계에도 그대로 적용하면 causal counterfactual이 아니다.

화면 label:

- `Observed replay`: 실제 실행된 event 재생.
- `Prefix stop simulation`: 관측된 prefix 중 어디서 멈출지 바꾼 계산.
- `Assumption-bound policy simulation`: 이후 output invariance를 가정한 계산.

“무료로 다른 agent를 제거했을 때 실제로 같은 결과”라고 표현하지 않는다. True ablation은 해당 configuration을 다시 실행해 측정해야 한다.
