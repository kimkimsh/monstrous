# coding 트랙 — 가중치 0.5

20문항. **점수의 절반을 여기서 가져간다.** 문항 수는 셋 중 가장 적은데 무게는 가장 크다.

| 항목 | 값 |
|---|---|
| 구성 | swebench-lite **13** + livecodebench-v6 **7** |
| 가중치 | **0.5** |
| grader | `swebench_docker` / `livecodebench_tests` |
| 요청 크기 | 최소 1,999 / 중앙값 63,812 / 최대 70,310 바이트 |
| 요청 합계 | 872,683 바이트 |
| 출력 형식 | `*** PATCH START ***` … SEARCH/REPLACE … `*** PATCH END ***` |

**파일명에 종류가 박혀 있다.** 둘은 완전히 다른 과제라서 섞어 보면 안 된다.

```
coding/requests/coding-visible-0001.swebench.txt        ← SWE-bench 13개
coding/requests/coding-visible-0041.livecodebench.txt   ← LiveCodeBench 7개
```

```bash
ls coding/tasks/*.swebench.txt        # 13개
ls coding/tasks/*.livecodebench.txt   #  7개
```

도구는 `item_id`만 넘기면 알아서 찾는다 — `python3 tools/compose.py coding-visible-0001`.

---

## 이 트랙에서 제일 먼저 알아야 할 것

**출력이 unified diff가 아니라 SEARCH/REPLACE 블록이다.**

```
*** PATCH START ***
path/to/file.py
<<<<<<< SEARCH
<the exact lines currently in the file>
=======
<the lines that replace them>
>>>>>>> REPLACE
*** PATCH END ***
```

`git diff` 형식을 내놓으면 전 문항 `extraction_failed`다. 정답을 알아도 0점이다.
규칙 원문은 `required_output.txt` 819바이트에 그대로 들어 있다.

- `<<<<<<< SEARCH` 앞에는 반드시 경로 한 줄
- 편집마다 세 마커 블록을 반복
- 경로는 저장소 루트 기준 상대 경로
- SEARCH는 파일에서 **줄 통째로 복사**한 것
- **SEARCH가 비어 있으면 새 파일 생성** — LiveCodeBench에서 쓰는 게 이것이다

---

## SWE-bench 13문항 — 컨텍스트가 이미 요청 안에 있다

**평가 실행 중 스쿼드는 도구가 없다.** 명령 실행도, 파일 열기도, 저장소 탐색도 못 한다.
저장소 코드는 judge가 검색해서 요청 본문에 넣어준다. 그게 `requests/*.txt`의 60KB다.

context.manifest.json이 기록한 검색 예산:

| 상한 | 값 |
|---|---|
| `max_candidate_chars` | 400,000 (후보로 고려하는 소스 총량) |
| **`max_context_chars`** | **60,000** (한 문항에 실제로 들어가는 총량) |
| `max_file_chars` | 12,000 |
| `max_files` | 10 |
| `max_query_terms` | 120 |

레시피 버전 `R1`, fingerprint `f2bcf89a…95ec1851`. 레시피가 바뀌면 fingerprint가 바뀌므로
우리가 연습한 조건이 평가 조건과 같은지 확인할 수 있다.

**13문항 전부 60,000자 상한을 거의 꽉 채운다** (중앙값 59,966자).
발췌 항목 수가 `max_files: 10`보다 많은 문항이 있는데, 한 파일에서 여러 구간을 뽑으면 항목이 늘기 때문이다.

| item_id | repo | version | 발췌 | 컨텍스트 문자 | 요청 바이트 |
|---|---|---|---|---|---|
| `coding-visible-0001` | astropy/astropy | 5.1 | 11 | 59,994 | 65,736 |
| `coding-visible-0002` | django/django | 3.0 | 8 | 59,994 | 63,481 |
| `coding-visible-0003` | django/django | 3.0 | 19 | 59,988 | 65,673 |
| `coding-visible-0017` | matplotlib/matplotlib | 3.5 | 13 | 59,966 | 70,310 |
| `coding-visible-0018` | matplotlib/matplotlib | 3.6 | 10 | 59,777 | 68,533 |
| `coding-visible-0020` | mwaskom/seaborn | 0.12 | 7 | 59,998 | 66,558 |
| `coding-visible-0021` | psf/requests | 0.14 | 11 | 59,634 | 63,100 |
| `coding-visible-0022` | pydata/xarray | 0.12 | 10 | 59,992 | 66,777 |
| `coding-visible-0023` | pylint-dev/pylint | 2.13 | 6 | 59,923 | 62,938 |
| `coding-visible-0024` | pytest-dev/pytest | 5.4 | 7 | 59,988 | 66,261 |
| `coding-visible-0026` | scikit-learn/scikit-learn | 0.20 | 13 | 59,852 | 67,736 |
| `coding-visible-0029` | sphinx-doc/sphinx | 3.1 | 9 | 59,959 | 64,922 |
| `coding-visible-0031` | sympy/sympy | 1.0 | 8 | 59,858 | 64,143 |

`gold/context.jsonl`에 judge가 넣어준 발췌 원본이 문항별로 들어 있다.
경로·시작줄·끝줄·전체 줄 수·생략량이 구조화돼 있어서, 요청 본문에서 무엇이 잘려 나갔는지 볼 수 있다.
**이 파일은 참고용이다. 프롬프트에 넣으면 안 된다** — 요청 본문에 이미 같은 내용이 들어 있다.

### 여기서 나오는 설계 결론

1. **검색·탐색 에이전트는 헛수고다.** 뒤질 저장소가 없다.
   필요한 건 읽기 → 가설 → 패치 작성 → 형식 자가검증이다.
2. **컨텍스트 중복 전달이 토큰 1번 문제다.** 60KB를 에이전트 3명이 각자 읽으면 그대로 3배다.
3. **SEARCH 구간을 발췌에서 그대로 복사해야 한다.** 기억으로 재타이핑하면 적용이 실패한다.
   발췌에 없는 파일을 고치려 드는 것도 같은 결과다.
4. **패치 형식 검증을 스쿼드 안에 두는 것이 정확도에 직접 기여한다.**
   맞는 수정을 0점으로 만드는 실패 모드가 정확히 형식이기 때문이다.

---

## LiveCodeBench 7문항 — 완전히 다른 과제다

컨텍스트가 없고 지문만 짧게 온다. 저장소가 아니라 **빈 저장소에서 `solution.py` 한 파일을 새로 만든다.**
요청 본문이 그렇게 지시한다.

> Your answer is a single new file, `solution.py`. The judge starts from an empty repository,
> so create it with an edit block whose SEARCH section is empty, and make it complete and self-contained.

| item_id | 출처 | 난이도 | 실행 모드 | starter_code | 요청 바이트 |
|---|---|---|---|---|---|
| `coding-visible-0041` | atcoder/abc387_b | easy | `stdin` | 없음 | 2,274 |
| `coding-visible-0042` | atcoder/abc387_c | medium | `stdin` | 없음 | 1,999 |
| `coding-visible-0043` | atcoder/abc388_a | easy | `stdin` | 없음 | 2,002 |
| `coding-visible-0044` | atcoder/abc388_b | easy | `stdin` | 없음 | 2,354 |
| `coding-visible-0053` | leetcode/3708 | easy | `functional` | 있음 | 2,403 |
| `coding-visible-0054` | leetcode/3714 | medium | `functional` | 있음 | 2,417 |
| `coding-visible-0055` | leetcode/3720 | medium | `functional` | 있음 | 3,066 |

실행 모드가 둘이고 **출력 형식이 완전히 다르다.**

| 모드 | 요구하는 것 | 출처 |
|---|---|---|
| `stdin` | 표준 입력을 읽어 표준 출력에 쓰는 완전한 프로그램 | AtCoder 계열 |
| `functional` | `starter_code`의 시그니처를 채우는 함수 | LeetCode 계열 |

**같은 에이전트 구성으로 SWE-bench와 LiveCodeBench를 둘 다 처리하려 하지 말 것.**
planner가 요청 본문에서 분기하도록 설계한다.
지문이 `## Problem:` 으로 시작하면 LiveCodeBench, `You are resolving an issue in an existing
repository.` 로 시작하면 SWE-bench다.

`gold/answers.jsonl`에 `public_test_cases`가 들어 있어서 **`grade.py`가 실제로 실행하고 정답을 판정한다.**
SWE-bench는 Docker가 필요해 로컬 판정이 안 되므로, 코딩 능력의 대리 지표로는 이 7문항을 쓴다.

---

## 로컬 채점의 한계

| 데이터셋 | `grade.py`가 하는 것 |
|---|---|
| livecodebench | 패치에서 새 파일을 꺼내 `public_test_cases`로 실제 실행. **PASS/FAIL 판정** |
| swebench | 패치 파싱과 SEARCH 구간 형식만 확인. **`format_ok`만 찍고 정답 판정 안 함** |

진짜 SWE-bench 채점은 `swebench_docker` — 저장소와 test_patch와 컨테이너가 있어야 한다.
여기서 확인되는 건 "패치가 파싱되고 경로가 그럴듯한가"뿐이다.

---

## 파일

```
coding/
├── required_output.txt        819바이트, 바이트 그대로
├── index.json                 20문항 메타 — kind, repo, 컨텍스트 크기, SHA-256
├── requests/<id>.<kind>.txt   붙여넣기용 완성 요청 20개
├── tasks/<id>.<kind>.txt      {{TASK}} 자리에 들어가는 본문
│                              kind는 파일명에 박혀 있다 — `.swebench.txt` 13개,
│                              `.livecodebench.txt` 7개. 둘은 완전히 다른 과제다
└── gold/
    ├── answers.jsonl          instance_id, fail_to_pass, pass_to_pass, test_patch,
    │                          public_test_cases — 채점기만 읽는다
    └── context.jsonl          judge가 검색해 넣어준 발췌 원본 (참고용)
```
