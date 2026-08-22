# 07. Squad Template & Prompt Engineering Playbook (스쿼드 템플릿 및 프롬프트 완제품 가이드)

> **핵심 테제:** 본 대회의 유일한 제출물은 단 1개의 Squad Template JSON과 트랙별 One-shot 프롬프트 3개이다. 요청 합성 규칙, REQUIRED OUTPUT 후처리 정렬, 웨이브 역순 추출 규칙을 완벽하게 만족하는 엔드투엔드 템플릿을 제공한다.

---

## 1. 제출물 규격 및 런타임 주입 규칙

### 1.1 요청 합성 공식
$$	ext{Request} = 	ext{rstrip}(	ext{normalize}(	ext{prompt}).	ext{replace}("{{\text{TASK}}}", 	ext{normalize}(	ext{item\_content}))) + "\n\n" + 	ext{REQUIRED\_OUTPUT} + "\n"$$

- `{{TASK}}`는 프롬프트 맨 뒤에 정확히 **단 한 번** 위치해야 함.
- `REQUIRED_OUTPUT` 블록은 서버가 자동으로 맨 뒤에 덧붙이므로 프롬프트 내에 중복 기재하지 않음.

### 1.2 답안 추출 역순 탐색 규칙 (`answer-extraction.md`)
- AI:GO 런타임이 생성하는 `**Execution complete** — N task(s)...` 요약문은 채점기가 **답안으로 인정하지 않고 거부**함.
- 채점기는 **마지막 웨이브(Last Wave)의 태스크 출력부터 거꾸로 역순 탐색**함.
- 따라서 **스쿼드의 마지막 에이전트 출력 맨 마지막 줄이 반드시 유효한 답안 블록으로 끝나야 함**.

---

## 2. 단일 통합 Squad Template JSON 스키마 (`squad_template.json`)

```json
{
  "$schema": "https://json-schema.lablup.ai/aigo/squad-template-v1.json",
  "name": "LEDGER-Ultimate-Squad",
  "version": "1.0.0",
  "description": "Deterministic Preflight Guarded Token-Efficient Squad",
  "budget": {
    "max_agent_turns": 6,
    "max_plan_iterations": 1,
    "max_tokens_per_task": 4096
  },
  "agents": [
    {
      "id": "router",
      "name": "Router",
      "role": "Planner",
      "model": "Qwen3-30B-A3B-Instruct-2507-FP8",
      "system_prompt": "You are the Task Router. Analyze the prompt payload.kind. If coding, route to Architect then Editor. If math or generic, route to Solver. Output a single-line JSON plan.",
      "temperature": 0.0,
      "max_tokens": 256
    },
    {
      "id": "architect",
      "name": "Architect",
      "role": "Custom",
      "model": "Qwen3-30B-A3B-Instruct-2507-FP8",
      "system_prompt": "You are the Code Architect. Read the 60KB context. DO NOT summarize code. Output ONLY exact file paths and anchor line ranges with bug explanation.",
      "temperature": 0.1,
      "max_tokens": 1024
    },
    {
      "id": "editor",
      "name": "Editor",
      "role": "Developer",
      "model": "Qwen3-30B-A3B-Instruct-2507-FP8",
      "system_prompt": "You are the Code Editor. Generate exact SEARCH/REPLACE blocks. SEARCH must be verbatim lines from the excerpt. The last thing you output MUST be the patch between *** PATCH START *** and *** PATCH END ***.",
      "temperature": 0.2,
      "max_tokens": 3072
    },
    {
      "id": "solver",
      "name": "Solver",
      "role": "Custom",
      "model": "Qwen3-30B-A3B-Instruct-2507-FP8",
      "system_prompt": "You are the Fast Solver. For Math, output FINAL ANSWER: \\boxed{<ans>}. For Generic MCQ, output ANSWER: <letter>. Be extremely concise. Output answer in 1 turn.",
      "temperature": 0.0,
      "max_tokens": 512
    },
    {
      "id": "auditor",
      "name": "Auditor",
      "role": "Reviewer",
      "model": "Qwen3-30B-A3B-Instruct-2507-FP8",
      "system_prompt": "You are the Escalation Auditor. You are only invoked when format verification fails. Fix the formatting error and output the required final block.",
      "temperature": 0.0,
      "max_tokens": 1024
    }
  ]
}
```

---

## 3. 트랙별 One-Shot 프롬프트 완제품

### 3.1 `prompts/coding.txt`
```text
You are an expert software engineer operating in an isolated evaluation environment.
Your squad's goal is to resolve the given repository issue by producing a surgical SEARCH/REPLACE patch.

Rules:
1. First, identify the exact target file and line numbers.
2. The SEARCH block must contain exact, verbatim lines copied directly from the provided excerpt. Do not paraphrase or alter whitespace.
3. Keep changes minimal and focused solely on resolving the failure.
4. The final output of this squad must end with the valid patch markers.

{{TASK}}
```

### 3.2 `prompts/math.txt`
```text
You are an expert mathematician. Solve the problem with rigorous, concise steps.

Rules:
1. Verify the required answer format (integer or simplified expression).
2. For integer answers, ensure the final boxed content contains only digits (or negative sign).
3. The very last line emitted by this squad must strictly adhere to the REQUIRED OUTPUT format.

{{TASK}}
```

### 3.3 `prompts/generic.txt`
```text
You are an expert reasoning system. Select the single best option for the multiple-choice question.

Rules:
1. Look ONLY at the provided Options list in the prompt.
2. Output strictly the single letter corresponding to the correct answer.
3. Do not output lengthy reasoning. The final line must be ANSWER: <letter>.

{{TASK}}
```
