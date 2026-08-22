# test sample 규격 (schema_version 1)

`auto_test/test_sample/` 아래의 JSON 파일 하나가 test sample 하나다.
sample 하나는 **squad에 그대로 붙여넣을 요청 텍스트(`prompt`)** 와 **채점에 필요한 정답 데이터(`expected`)** 를 한 파일에 담는다.

121개는 `tools/build_samples.py`가 `docs/resource/example_task/`에서 생성한다.
이 문서는 그 생성기를 읽지 않고도 **sample을 손으로 하나 추가**할 수 있게 쓴 것이다.

---

## 1. 폴더 구조와 파일 이름

```
auto_test/
├── SAMPLE_SPEC.md              ← 이 문서
├── tools/
│   └── build_samples.py        생성기 (생성 + --check)
└── test_sample/
    ├── coding/                 20개 (swebench 13 + livecodebench 7)
    │   ├── coding-visible-0001.json
    │   └── ...
    ├── math/                   59개
    │   ├── math-visible-0001.json
    │   └── ...
    └── generic/                42개
        ├── generic-visible-mmlu-pro-10088.json
        └── ...
```

이름 규칙은 두 줄이다.

1. **폴더 이름 = `track` 필드값.** `coding` / `math` / `generic` 셋뿐이다.
2. **파일 이름 = `<id>.json`.** 확장자를 뗀 이름이 `id` 필드와 글자 그대로 같아야 한다.

`id`는 track 안에서 유일해야 한다. 손으로 추가하는 sample은 생성기가 쓰는 `*-visible-*` 이름과
겹치지 않게 짓는다. 생성기가 덮어쓰지는 않지만, 같은 이름이면 어느 쪽이 원본인지 알 수 없게 된다.
`math-local-0001`, `coding-regress-0003`처럼 출처가 드러나는 이름을 권한다.

**인코딩은 UTF-8, 들여쓰기는 space 2칸, 파일 끝에 newline 하나.**
생성기는 `json.dump(..., ensure_ascii=False, indent=2)` 결과에 `\n`을 붙여 쓴다.
`ensure_ascii=False`이므로 LaTeX·한글·`×` 같은 문자는 escape되지 않고 그대로 들어간다.

---

## 2. 필드 표

최상위 키는 아래 9개가 전부다. **키 순서도 아래 순서를 지킨다.**
생성된 121개는 이 순서가 강제된다 — `--check`가 파일을 byte 단위로 비교하므로 순서가 틀리면 실패한다.
손으로 쓴 sample은 순서까지 검사하지는 않지만, 나란히 놓고 읽을 일이 많으므로 맞춰 쓴다.

| 필드 | 타입 | 필수 | 의미 |
|---|---|---|---|
| `schema_version` | int | 필수 | 이 규격의 버전. 지금은 항상 `1` |
| `id` | string | 필수 | sample 식별자. 파일 이름(확장자 제외)과 같아야 한다 |
| `track` | string | 필수 | `coding` \| `math` \| `generic`. 상위 폴더 이름과 같아야 한다. 점수 가중치가 여기서 갈린다 (coding 0.5 / math 0.25 / generic 0.25) |
| `kind` | string | 필수 | 문항 종류. 실제로 쓰이는 값은 `math`, `swebench`, `livecodebench`, `letter_match` |
| `gradable` | bool | 필수 | 로컬에서 채점 가능한지. `swebench`만 `false` |
| `ungradable_reason` | string \| null | 필수 | `gradable`이 `true`면 `null`, `false`면 이유 문자열. 키 자체는 항상 있어야 한다 |
| `prompt` | string | 필수 | squad에 보내는 요청 전문. REQUIRED OUTPUT 블록까지 포함한 완성본 |
| `expected` | object | 필수 | 채점 데이터. 내용은 track마다 다르다 (4절) |
| `meta` | object | 필수 | 출처와 무결성 정보 (아래 표) |

`meta` 하위 키 5개, 역시 순서 고정.

| 필드 | 타입 | 필수 | 의미 |
|---|---|---|---|
| `meta.dataset` | string | 필수 | 원 데이터셋 이름. 실제 값: `swebench-lite`, `livecodebench-v6`, `math-500-level5`, `aime-2024`, `mmlu-pro` |
| `meta.native_id` | string | 필수 | 원 데이터셋 안에서의 식별자. 예: `astropy__astropy-14182`, `leetcode/3708`, `test/algebra/1031.json`, `10088` |
| `meta.prompt_bytes` | int | 필수 | `prompt`를 UTF-8로 encode 했을 때의 byte 수. 문자 수가 아니다 |
| `meta.prompt_sha256` | string | 필수 | 같은 byte열의 SHA-256 hex 소문자 64자 |
| `meta.source` | string | 필수 | 어디서 왔는지. 생성된 sample은 `docs/resource/example_task/<track>/requests/<파일명>` |

### `kind` 값을 정하는 규칙

| track | `kind`에 넣을 값 | 어디서 오나 |
|---|---|---|
| `math` | `math` | `math/index.json`의 `kind` |
| `coding` | `swebench` 또는 `livecodebench` | `coding/index.json`의 `kind` |
| `generic` | `letter_match` | `generic/gold/answers.jsonl`의 `kind`. 없으면 `mmlu_pro`로 떨어진다 |

generic만 규칙이 다른 이유는 `generic/index.json`의 `kind`가 `multiple_choice`인데,
채점기가 dispatch에 쓰는 값은 gold 쪽의 `letter_match`이기 때문이다. **gold 쪽을 따른다.**

### `gradable` / `ungradable_reason`

`gradable`이 `false`인 것은 **`kind == "swebench"` 뿐이다.** 121개 중 13개.
swebench의 grader는 `swebench_docker`이고, 채점하려면 문항마다 준비된 Docker image 안에서
`test_patch`를 적용하고 `fail_to_pass` / `pass_to_pass` test를 돌려야 한다. 그 image가 로컬에 없다.

이유 문자열은 아래 한 줄로 고정한다.

```
swebench_docker grading requires Docker images that are not available locally; the run still records the patch and token usage
```

`gradable: false`는 "돌리지 말라"가 아니다. **실행은 하되 정답/오답 판정만 하지 않는다.**
patch 본문과 token 사용량은 그대로 기록된다.

`gradable`이 `true`인 sample은 `ungradable_reason`이 반드시 `null`이다.
문자열을 넣어 두면 `--check`가 잡는다.

---

## 3. `prompt`가 반드시 끝내야 하는 블록

`prompt`는 **문항 본문 + 빈 줄 + track의 REQUIRED OUTPUT 블록**으로 끝난다.
생성기가 읽는 원본 요청 파일도 정확히 이 구조다. 실측으로 확인한 조립 규칙은 이렇다.

```
prompt = 문항본문.rstrip() + "\n\n" + required_output.txt 전문
```

`required_output.txt`는 이미 끝에 newline이 있어서, `prompt`도 newline으로 끝난다.
블록은 **track당 정확히 하나**이고 문항마다 달라지지 않는다.

### 왜 지워지면 안 되나

judge는 응답 본문을 자연어로 이해하지 않는다. **정해진 형태의 마지막 한 덩어리만 정규식으로 뽑아간다.**
블록이 없으면 squad가 그 형태를 낼 이유가 없고, 답을 맞혔더라도 뽑히지 않는다.
이때 결과는 "오답"이 아니라 **`extraction_failed`** — 점수는 똑같이 0이고, 별도 항목으로 기록된다.

세 track 모두 블록 끝에 같은 두 문장이 붙는다.

```
If more than one appears, the last one is used.
Anything before it is ignored, not penalised.
```

**마지막 것만 채점되고 그 앞은 읽지 않는다.** 그래서 답 블록 앞의 서술은 정확도를 깎지 않는다.
다만 token은 그대로 든다 — token 효율 점수와 동점 처리 기준에 전부 들어간다.

### math (258 byte, 끝 newline 포함)

```
=== REQUIRED OUTPUT ===
End your answer with a line of exactly this form:

FINAL ANSWER: \boxed{<answer>}

Put the final answer, and nothing else, inside \boxed{}.
If more than one appears, the last one is used.
Anything before it is ignored, not penalised.
```

`FINAL ANSWER: \boxed{...}` 줄이 없으면 `gold`와 대조할 문자열 자체가 없다.

### generic (290 byte, 끝 newline 포함)

```
=== REQUIRED OUTPUT ===
End your answer with a line of exactly this form:

ANSWER: <letter>

Replace <letter> with the single letter of the option you choose, and write nothing else
on that line.
If more than one appears, the last one is used.
Anything before it is ignored, not penalised.
```

`ANSWER: B` 형태의 letter 한 글자를 뽑아 `expected.answer`와 비교한다.
"정답은 B입니다" 같은 문장은 이 형식이 아니므로 뽑히지 않는다.

### coding (820 byte, 끝 newline 포함)

```
=== REQUIRED OUTPUT ===
Your answer must contain a patch, written as SEARCH/REPLACE edit blocks between the two
patch markers:

*** PATCH START ***
path/to/file.py
<<<<<<< SEARCH
<the exact lines currently in the file>
=======
<the lines that replace them>
>>>>>>> REPLACE
*** PATCH END ***

Rules: one path line before every <<<<<<< SEARCH; repeat the three-marker block once per
edit; paths are relative to the repository root; SEARCH must be whole lines copied from
the file; an empty SEARCH section creates a new file.

Only what lies between *** PATCH START *** and *** PATCH END *** is graded.
If more than one appears, the last one is used.
Anything before it is ignored, not penalised.
The full format specification, with worked examples and every failure code, is published
as `docs/contracts/patch-format.md`.
```

**coding은 unified diff가 아니라 SEARCH/REPLACE 블록이다.** 여기가 제일 자주 깨진다.
`git diff` 형태를 내놓는 squad는 정답 코드를 짜고도 전 문항 `extraction_failed`가 된다.
`*** PATCH START ***` / `*** PATCH END ***` 사이만 채점되고, SEARCH 섹션이 비어 있으면 새 파일을 만든다는
규칙도 이 블록에만 적혀 있다. 블록을 지우면 이 정보가 squad에 전달될 경로가 없다.

---

## 4. track별 `expected` — 채점기가 여기를 보고 갈라진다

`expected`는 원본 `gold/answers.jsonl`의 객체를 **손대지 않고 그대로** 옮긴 것이다.
키를 빼거나 이름을 바꾸면 채점기가 dispatch에 실패한다. `item_id` 키가 안에 한 번 더 들어 있는 것도
원본 그대로이므로 남겨 둔다.

### math — `grader: "math_answer"`

| 키 | 타입 | 의미 |
|---|---|---|
| `grader` | string | 항상 `"math_answer"` |
| `answer_format` | string | `"expression"` 또는 `"integer"`. 59개 중 integer 35 / expression 24 |
| `gold` | string | 정답. LaTeX 본문만, `\boxed{}` 없이 |
| `gold_latex` | string | `$\boxed{...}$`로 감싼 표시용 형태 |
| `checks` | array of string | 적용할 비교 방법. `["math_verify"]` 또는 `["integer_exact", "math_verify"]` |
| `item_id` | string | 원본 그대로 |

`checks`가 dispatch의 실체다. `integer_exact`는 정수 문자열 완전 일치,
`math_verify`는 `math-verify` 패키지로 수식 동치를 판정한다.
`answer_format`이 `integer`인 문항은 두 방법을 다 통과해야 한다.

### generic — `kind: "letter_match"`

| 키 | 타입 | 의미 |
|---|---|---|
| `kind` | string | 항상 `"letter_match"`. **generic만 `grader` 대신 `kind`로 dispatch한다** |
| `answer` | string | 정답 letter 한 글자. 예: `"B"` |
| `answer_index` | int | 0-based 보기 index. `"B"`면 `1` |
| `answer_text` | string | 그 보기의 본문 |
| `num_options` | int | 보기 개수. 42개 중 10개짜리가 36개, 나머지는 3/4/7/8/9개 |
| `case_sensitive` | bool | 42개 전부 `false` — 소문자 `b`도 정답으로 인정 |
| `item_id` | string | 원본 그대로 |

### coding / livecodebench — `grader: "livecodebench_tests"`

| 키 | 타입 | 의미 |
|---|---|---|
| `grader` | string | 항상 `"livecodebench_tests"` |
| `question_id` | string | 원 문제 id. atcoder는 `"abc387_b"`, leetcode는 `"3708"` |
| `contest_id` | string | `"abc387"`, `"weekly-contest-432"` |
| `contest_date` | string | ISO 8601 |
| `platform` | string | `"atcoder"` 또는 `"leetcode"` |
| `difficulty` | string | `"easy"` / `"medium"` |
| `evaluation_mode` | string | `"stdin"` 또는 `"functional"`. **실행 방식이 여기서 갈린다** |
| `public_test_cases` | array of object | 각 원소가 `{"input": ..., "output": ..., "testtype": ...}` |
| `metadata` | string | **JSON을 담은 문자열이지 object가 아니다.** functional이면 `"{\"func_name\": \"zigzagTraversal\"}"`, stdin이면 `"{}"` |
| `item_id` | string | 원본 그대로 |

`evaluation_mode`가 `"stdin"`이면 제출 파일을 프로세스로 실행해 stdin을 먹이고 stdout을 비교한다
(atcoder 4문항). `"functional"`이면 파일을 import 해서 `metadata`의 `func_name` 함수를 호출한다
(leetcode 3문항). `public_test_cases[*].testtype`도 같은 값을 따라간다.

`metadata`가 문자열인 점을 조심한다. 쓸 때 `json.loads`를 한 번 더 해야 한다.

### coding / swebench — `grader: "swebench_docker"`, `gradable: false`

| 키 | 타입 | 의미 |
|---|---|---|
| `grader` | string | 항상 `"swebench_docker"` |
| `instance_id` | string | SWE-bench instance id. 예: `"astropy__astropy-14182"` |
| `repo` | string | `"astropy/astropy"` |
| `version` | string | `"5.1"` |
| `base_commit` | string | patch를 적용할 기준 commit hash |
| `environment_setup_commit` | string | 환경 구성용 commit hash |
| `test_patch` | string | 채점용 test를 추가하는 diff 전문 |
| `fail_to_pass` | array of string | patch 후 통과해야 하는 test id 목록 |
| `pass_to_pass` | array of string | patch 전후 모두 통과해야 하는 test id 목록 |
| `item_id` | string | 원본 그대로 |

이 13개는 `gradable: false`로 두고 `ungradable_reason`을 2절의 고정 문자열로 채운다.
`expected`를 비우지는 않는다 — Docker image가 생기면 그대로 채점에 쓸 수 있어야 하고,
지금도 patch 형식이 맞는지 보는 데는 쓰인다.

---

## 5. 완성 예시

세 track 각각 실제 파일이다. **`prompt`는 지면 관계로 잘랐다** — 실제 파일에는 요청 전문이
REQUIRED OUTPUT 블록까지 통째로 들어 있다. 잘랐으므로 아래 예시의 `prompt_bytes` / `prompt_sha256`은
붙어 있는 `prompt` 문자열과 맞지 않는다. 손으로 쓸 때는 자르지 말고, 6절 방법으로 두 값을 다시 계산한다.

### math — `test_sample/math/math-visible-0001.json`

이 문항은 짧아서 `prompt`가 전문 그대로다.

```json
{
  "schema_version": 1,
  "id": "math-visible-0001",
  "track": "math",
  "kind": "math",
  "gradable": true,
  "ungradable_reason": null,
  "prompt": "What is the smallest real number $x$ in the domain of the function $$g(x) = \\sqrt{(x-3)^2-(x-8)^2}~?$$\n\n=== REQUIRED OUTPUT ===\nEnd your answer with a line of exactly this form:\n\nFINAL ANSWER: \\boxed{<answer>}\n\nPut the final answer, and nothing else, inside \\boxed{}.\nIf more than one appears, the last one is used.\nAnything before it is ignored, not penalised.\n",
  "expected": {
    "grader": "math_answer",
    "answer_format": "expression",
    "gold": "\\frac{11}{2}",
    "gold_latex": "$\\boxed{\\frac{11}{2}}$",
    "checks": [
      "math_verify"
    ],
    "item_id": "math-visible-0001"
  },
  "meta": {
    "dataset": "math-500-level5",
    "native_id": "test/algebra/1031.json",
    "prompt_bytes": 362,
    "prompt_sha256": "102920d5af35fcfe5771d2e234bef5882b84fd583219c31810b8d008dfac06cf",
    "source": "docs/resource/example_task/math/requests/math-visible-0001.txt"
  }
}
```

`answer_format`이 `integer`인 문항은 `expected`가 이렇게 생겼다.

```json
{
  "grader": "math_answer",
  "answer_format": "integer",
  "gold": "17",
  "gold_latex": "$\\boxed{17}$",
  "checks": [
    "integer_exact",
    "math_verify"
  ],
  "item_id": "math-visible-0003"
}
```

### generic — `test_sample/generic/generic-visible-mmlu-pro-10088.json`

`prompt`를 앞 200자만 남기고 잘랐다.

```json
{
  "schema_version": 1,
  "id": "generic-visible-mmlu-pro-10088",
  "track": "generic",
  "kind": "letter_match",
  "gradable": true,
  "ungradable_reason": null,
  "prompt": "A rotating mirror experiment, to measure the speed of light, is set up on Mt. Wilson with the return mirror on Mt. San Antonia 35377 meters away. ... (중략) ...\n\nOptions:\nA. 2.00 ×10^8 m/sec\nB. 3.00 ×10^8 m/sec\n... (중략) ...\n\n=== REQUIRED OUTPUT ===\n... (generic REQUIRED OUTPUT 블록 전문) ...\n",
  "expected": {
    "kind": "letter_match",
    "answer": "B",
    "answer_index": 1,
    "answer_text": "3.00 ×10^8 m/sec",
    "num_options": 10,
    "case_sensitive": false,
    "item_id": "generic-visible-mmlu-pro-10088"
  },
  "meta": {
    "dataset": "mmlu-pro",
    "native_id": "10088",
    "prompt_bytes": 789,
    "prompt_sha256": "760a8add3cad502fb92593955a0ce1320c9b0d6239ff93684fdc29fb21f6ea64",
    "source": "docs/resource/example_task/generic/requests/generic-visible-mmlu-pro-10088.txt"
  }
}
```

보기 목록은 `prompt` 안에 `A.` `B.` … 로 들어 있다. `expected`에 따로 담지 않는다.
채점기가 보는 것은 letter 하나뿐이다.

### coding / livecodebench — `test_sample/coding/coding-visible-0053.json`

`prompt`를 잘랐다. 실제 파일은 2403 byte다.

```json
{
  "schema_version": 1,
  "id": "coding-visible-0053",
  "track": "coding",
  "kind": "livecodebench",
  "gradable": true,
  "ungradable_reason": null,
  "prompt": "## Problem: zigzag-grid-traversal-with-skip\n\nYou are given an m x n 2D array grid of positive integers.\n... (중략) ...\n\n## Starter code\n\n```python\nclass Solution:\n    def zigzagTraversal(self, grid: List[List[int]]) -> List[int]:\n```\n\n=== REQUIRED OUTPUT ===\n... (coding REQUIRED OUTPUT 블록 전문) ...\n",
  "expected": {
    "grader": "livecodebench_tests",
    "question_id": "3708",
    "contest_id": "weekly-contest-432",
    "contest_date": "2025-01-11T18:30:00",
    "platform": "leetcode",
    "difficulty": "easy",
    "evaluation_mode": "functional",
    "public_test_cases": [
      {
        "input": "[[1, 2], [3, 4]]",
        "output": "[1, 4]",
        "testtype": "functional"
      },
      {
        "input": "[[2, 1], [2, 1], [2, 1]]",
        "output": "[2, 1, 2]",
        "testtype": "functional"
      }
    ],
    "metadata": "{\"func_name\": \"zigzagTraversal\"}",
    "item_id": "coding-visible-0053"
  },
  "meta": {
    "dataset": "livecodebench-v6",
    "native_id": "leetcode/3708",
    "prompt_bytes": 2403,
    "prompt_sha256": "4717b4a64091419eb43daf63242ac2b3e83d05fd9b40f2e80d7f756c8a389552",
    "source": "docs/resource/example_task/coding/requests/coding-visible-0053.livecodebench.txt"
  }
}
```

`evaluation_mode`가 `"stdin"`인 atcoder 문항은 `public_test_cases`가 이렇게 생긴다.

```json
{
  "public_test_cases": [
    {
      "input": "1",
      "output": "2024",
      "testtype": "stdin"
    }
  ],
  "metadata": "{}"
}
```

### coding / swebench — `test_sample/coding/coding-visible-0001.json`

`prompt`(65736 byte)와 `test_patch`, `pass_to_pass`를 잘랐다.
`prompt`에는 judge가 검색해서 넣어 준 저장소 발췌가 통째로 들어 있어서 이 track의 요청이 제일 크다.

```json
{
  "schema_version": 1,
  "id": "coding-visible-0001",
  "track": "coding",
  "kind": "swebench",
  "gradable": false,
  "ungradable_reason": "swebench_docker grading requires Docker images that are not available locally; the run still records the patch and token usage",
  "prompt": "You are resolving an issue in an existing repository. The issue report comes\nfirst, then the parts of the repository the judge retrieved for it.\n\n## Issue\n\nPlease support header rows in RestructuredText output\n... (중략, 저장소 발췌 약 60KB) ...\n\n=== REQUIRED OUTPUT ===\n... (coding REQUIRED OUTPUT 블록 전문) ...\n",
  "expected": {
    "grader": "swebench_docker",
    "instance_id": "astropy__astropy-14182",
    "repo": "astropy/astropy",
    "version": "5.1",
    "base_commit": "a5917978be39d13cd90b517e1de4e7a539ffaa48",
    "environment_setup_commit": "5f74eacbcc7fff707a44d8eb58adaa514cb7dcb5",
    "test_patch": "diff --git a/astropy/io/ascii/tests/test_rst.py b/astropy/io/ascii/tests/test_rst.py\n--- a/astropy/io/ascii/tests/test_rst.py\n... (중략) ...",
    "fail_to_pass": [
      "astropy/io/ascii/tests/test_rst.py::test_rst_with_header_rows"
    ],
    "pass_to_pass": [
      "astropy/io/ascii/tests/test_rst.py::test_read_normal",
      "astropy/io/ascii/tests/test_rst.py::test_read_normal_names"
    ],
    "item_id": "coding-visible-0001"
  },
  "meta": {
    "dataset": "swebench-lite",
    "native_id": "astropy__astropy-14182",
    "prompt_bytes": 65736,
    "prompt_sha256": "3e3214612d8f844ee3cddd5b71756b5d323b753b14577711bfbccc0b92c5c325",
    "source": "docs/resource/example_task/coding/requests/coding-visible-0001.swebench.txt"
  }
}
```

---

## 6. 손으로 쓴 sample 검증하기

### 순서

1. **`prompt`부터 확정한다.** 문항 본문을 쓰고, 빈 줄 하나, 그 track의 REQUIRED OUTPUT 블록 전문,
   마지막에 newline. 블록은 `docs/resource/example_task/<track>/required_output.txt`에서 복사한다.
2. **`prompt_bytes` / `prompt_sha256`을 계산해 넣는다.** 손으로 세지 말고 아래 명령을 쓴다.
3. **`expected`를 4절 표대로 채운다.** 새로 만드는 문항이면 `item_id`는 넣어도 되고 빼도 된다 —
   원본에서 옮겨 온 것만 원본 그대로 유지한다.
4. **`meta.source`에 출처를 적는다.** `docs/resource/example_task/`로 **시작하지 않는** 값이어야 한다
   (`"hand-written"`, `"regression/issue-231"` 등). 이 접두사로 시작하면 `--check`가
   "생성된 sample인데 index.json에 원본이 없다"는 drift로 보고 실패한다.
5. **`--check`를 돌린다.**

### 두 값 계산하기

`prompt` 문자열을 먼저 파일에 넣어 두고, 그 파일에서 다시 읽어 계산하는 쪽이 안전하다.

```bash
python3 -c '
import hashlib, json, sys
sample = json.load(open(sys.argv[1]))
raw = sample["prompt"].encode("utf-8")
print("prompt_bytes ", len(raw))
print("prompt_sha256", hashlib.sha256(raw).hexdigest())
' test_sample/math/math-local-0001.json
```

찍힌 두 값을 `meta`에 그대로 옮긴다.

원본 요청 파일에서 그대로 가져오는 경우라면 파일 자체로 계산해도 같은 값이 나온다.

```bash
wc -c   < docs/resource/example_task/math/requests/math-visible-0001.txt   #  362
shasum -a 256 docs/resource/example_task/math/requests/math-visible-0001.txt
```

### `--check`가 하는 일

```bash
python3 tools/build_samples.py --check
```

- 생성된 121개는 원본에서 다시 만들어 **byte 단위로 비교**한다. 한 글자라도 다르면 실패.
- 그 밖의 `*.json`은 **손으로 쓴 sample로 보고 구조만 검사**한다.
  키 9개가 다 있는지, 표에 없는 키가 섞였는지, `id`가 파일 이름과 같은지, `track`이 폴더와 같은지,
  `gradable`과 `ungradable_reason`이 짝이 맞는지, `prompt_bytes` / `prompt_sha256`이 `prompt`와 맞는지.
- 문제가 하나라도 있으면 목록을 stderr에 찍고 **exit code 1**로 끝난다.

정상일 때 출력은 이렇다. 마지막 줄이 손으로 쓴 sample 개수다.

```
coding   checked 20 sample(s)
math     checked 59 sample(s)
generic  checked 42 sample(s)
total    checked 121 sample(s) (13 ungradable) -> /Users/mark-mac/workspace/monstrous/auto_test/test_sample
         plus 1 hand-written sample(s), shape-checked only
```

`prompt`를 고쳐 놓고 hash를 안 고치면 이렇게 잡힌다.

```
check failed: 2 problem(s)
  .../test_sample/math/math-local-0001.json: meta.prompt_bytes is 3, prompt is 8 bytes
  .../test_sample/math/math-local-0001.json: meta.prompt_sha256 is 98ea6e4f...be4, prompt hashes to 7f8b1dfc...38f1
```

### `--check`가 못 잡는 것

구조 검사는 **`expected`의 내용까지는 보지 않는다.** 4절 표에 맞는지, `gold` 값이 실제 정답인지,
`grader` 이름이 맞는지는 사람이 확인해야 한다. `expected`가 비어 있지 않은 object인지만 본다.

REQUIRED OUTPUT 블록이 `prompt` 끝에 붙어 있는지도 검사하지 않는다.
블록을 빠뜨린 sample은 형식상 통과하지만 채점 때 전부 `extraction_failed`가 된다. 3절을 지킨다.

### 121개를 다시 만들기

```bash
python3 tools/build_samples.py
```

원본에서 다시 생성한다. 같은 원본이면 결과 파일도 byte 단위로 같다 (idempotent).
손으로 쓴 sample은 건드리지 않는다. 원본 요청 파일의 SHA-256이 `index.json`의 `request_sha256`과
하나라도 다르면 **아무것도 쓰지 않고** 해당 `item_id`를 찍으며 exit code 1로 끝난다.
