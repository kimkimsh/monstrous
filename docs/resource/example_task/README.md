# example_task — 연습 세트 실전 하네스

JunctionX Korea 2026 · Lablup + FuriosaAI 트랙 **Build the Ultimate Agent Squad** 용.

제출 서버가 공개하는 연습 문항 121개를, **AI:GO 스쿼드에 그대로 붙여넣어 돌릴 수 있는 형태**로 정리했다.
채점기와 배치 러너까지 같이 들어 있어서, 프롬프트를 고치고 → 돌리고 → 점수를 보는 순환을 로컬에서 반복할 수 있다.

수집 시각: 2026-08-22 08:46 UTC · 출처 `https://submission.jxc.events.lablup.ai:8444`

---

## 30초 요약

| 항목 | 값 |
|---|---|
| 문항 수 | **121** (coding 20 / math 59 / generic 42) |
| 점수 공식 | `0.5 × coding + 0.25 × generic + 0.25 × math` |
| 채점자 | 항상 결정론적 프로그램. LLM 심판 없음 |
| 동점 처리 | ① 총 토큰 적은 쪽 ② wall-clock 짧은 쪽 |
| 요청 무결성 | 121개 전부 서버 공개 SHA-256과 **바이트 일치 확인 완료** |
| coding 출력 | `*** PATCH START ***` … SEARCH/REPLACE … `*** PATCH END ***` |
| math 출력 | `FINAL ANSWER: \boxed{<answer>}` |
| generic 출력 | `ANSWER: <letter>` |

---

## 이 폴더가 있는 이유

포털의 `/practice-sets/requests` 페이지가 **judge가 보내는 요청의 절반**을 문항별로 공개한다.
문항 본문 + 트랙별 REQUIRED OUTPUT 블록이 렌더링된 상태이고, 빈칸은 우리 one-shot 프롬프트 하나뿐이다.

그래서 여기 있는 `requests/<item_id>.txt`는 **"프롬프트가 `{{TASK}}` 한 줄일 때 judge가 실제로 보내는 바이트"** 그 자체다.
서버가 문항마다 SHA-256을 같이 공개하므로, 우리가 붙여넣는 것이 채점 때 가는 것과 같은지 기계적으로 확인된다 —
`tools/compose.py --verify`가 그 대조를 한다.

---

## 폴더 구조

```
example_task/
├── README.md                     ← 지금 이 파일
├── 00-트랙-정리.md                해커톤·트랙 전체 분석. 먼저 읽을 것
├── 01-요청-합성-규칙.md            judge가 요청을 만드는 규칙, 답을 읽어가는 규칙
├── 02-실험-운영.md                프롬프트를 깎는 절차와 측정 항목
│
├── coding/                       가중치 0.5 · 20문항 (swebench 13 + livecodebench 7)
│   ├── README.md
│   ├── required_output.txt       트랙 REQUIRED OUTPUT 블록 (819바이트, 바이트 그대로)
│   ├── index.json                문항 메타 — kind, repo, 바이트 수, SHA-256
│   ├── requests/<id>.<kind>.txt  ★ 붙여넣기용 완성 요청 20개
│   │                             kind = swebench 13 / livecodebench 7
│   ├── tasks/<id>.<kind>.txt     {{TASK}} 자리에 들어가는 본문만
│   └── gold/
│       ├── answers.jsonl         채점용 정답. 프롬프트에 절대 넣지 말 것
│       └── context.jsonl         judge가 검색해 넣어준 저장소 컨텍스트 원본
│
├── math/                         가중치 0.25 · 59문항 (MATH-500 L5 48 + AIME 2024 11)
│   └── (같은 구조)
├── generic/                      가중치 0.25 · 42문항 (MMLU-Pro 14과목 × 3)
│   └── (같은 구조)
│
├── prompts/                      트랙별 one-shot 프롬프트. 여기를 고쳐가며 실험한다
│   ├── coding.txt  math.txt  generic.txt
│   └── variants/                 실험 변종 보관
│
├── tools/
│   ├── compose.py                프롬프트 + 문항 → judge와 바이트 동일한 요청
│   ├── run_batch.py              AI:GO 스쿼드에 배치 실행하고 답을 수집
│   ├── extract.py                AI:GO 실행 기록에서 judge와 같은 규칙으로 답을 뽑음
│   ├── grade.py                  3트랙 로컬 채점기 + 가중 점수
│   └── verify.sh                 원본 파일과 요청 121개 무결성 재확인
│
└── raw/                          원본 그대로. 손대지 말 것
    ├── set.manifest.json  SHA256SUMS
    ├── {coding,math,generic}.items.jsonl / .manifest.json
    ├── coding.context.manifest.json
    └── request-digests.json      문항별 공개 SHA-256과 로컬 실측값
```

---

## 바로 쓰는 법

### 1. 손으로 한 문항 (AI:GO 데스크톱)

```bash
pbcopy < math/requests/math-visible-0001.txt
```

AI:GO → Squad → 스쿼드 선택 → 요청 입력창에 붙여넣고 실행.
**답은 Execution Progress 패널의 각 태스크 아래 본문에서 읽는다.**
상단의 `**Execution complete** — N task(s) processed in M wave(s).` 줄은 런타임이 만든 상태 요약이고,
judge는 그걸 답으로 인정하지 않는다. 자세한 건 `01-요청-합성-규칙.md` 3절.

### 2. 프롬프트를 바꿔서 합성

```bash
# prompts/math.txt 를 고친 뒤
python3 tools/compose.py math-visible-0001 | pbcopy
```

### 3. 배치로 돌리고 채점

```bash
# 스쿼드 ID 확인
"/Applications/Backend.AI GO.app/Contents/MacOS/aigo-cli" squad list

# math 앞 10문항
python3 tools/run_batch.py <SQUAD_ID> <WORKSPACE_DIR> --tracks math --limit 10 --out run01.jsonl

# 채점
python3 tools/grade.py run01.jsonl --report run01.report.jsonl
```

`grade.py`가 문항별 PASS/FAIL과 트랙별 정확도, 가중 점수를 찍는다.

### 4. 무결성 확인

```bash
bash tools/verify.sh
```

`raw/`의 원본 파일 다이제스트와 요청 121개의 SHA-256을 서버 공개값과 대조한다.

---

## 반드시 알고 시작할 것 네 가지

1. **`gold/`는 프롬프트에 넣지 않는다.** 실제 평가에서 스쿼드는 `payload`만 본다.
   정답이 섞여 들어가면 연습 점수가 아무 의미도 갖지 않는다.

2. **평가 중 스쿼드는 도구가 없다.** 명령 실행도, 파일 열기도, 저장소 탐색도 못 한다.
   SWE-bench 문항의 저장소 코드는 judge가 검색해서 요청에 넣어준다 — 그게 `requests/`에 이미 들어 있는 60KB다.
   검색·탐색 에이전트를 설계하는 건 헛수고다.

3. **연습 세트가 축소됐다.** 서버가 2026-08-22 시점에 visible 세트를 364 → 121문항으로 줄였다
   (`raw/set.manifest.json`의 `trim` 블록). **hidden 세트는 그대로**다.
   같은 폴더 계열의 `track_resource/lableup/practice-sets/`에 있는 364문항 사본은 이제 옛날 것이다.

4. **`extraction_failed`는 오답과 별도로 분류된다.** 답을 지정된 형식으로 못 뽑으면 0점인데,
   포털은 그걸 "틀린 답"이 아니라 "추출 실패"로 기록한다. 형식을 맞추는 일이 정답률만큼 값어치가 있다.

---

## 데이터 고지

연습 문항은 아래 프로젝트에서 파생됐고, 사본에는 이 고지가 따라다녀야 한다.
전문은 `raw/coding.context.manifest.json` 안에 있다.

- SWE-bench (Jimenez et al., ICLR 2024) — 인스턴스는 업스트림 저장소에서 파생
- LiveCodeBench (Jain et al., 2024) — 문제 지문은 LeetCode / AtCoder / CodeForces에서 수집
- MATH-500 — Hendrycks et al. (MIT), level-5 부분집합, `HuggingFaceH4/MATH-500` 경유
- AIME 2024 — Mathematical Association of America 자료, `HuggingFaceH4/aime_2024` 경유, 라이선스 미선언
- MMLU-Pro (TIGER-Lab), MIT

컨텍스트 번들의 저장소 발췌는 업스트림 프로젝트의 무수정 소스이며 각 프로젝트 라이선스로 재배포된다.
