# 제출 폼 원고 — LEDGER Squad

바로 붙여넣는 평문은 `submission-copy-ko.txt`에 따로 있다.
폼이 국문이면 국문판, 영문이면 영문판을 쓴다.

이 원고는 `docs/ideation/final_final_ideation/spec/`의 5인 구성(Router · Architect · Editor · Solver · Reviewer)과
`squad-template.json`의 에이전트 이름에 맞춰져 있다. **셋 중 하나를 고치면 나머지 둘도 같이 고친다.**

---

## 국문판

### Punchline (111/200자)

```
세 종류의 벤치마크를 푸는 AI:GO 에이전트 스쿼드와 그 실행 기록을 보는 뷰어. 고칠 자리를 정하는 에이전트와 내용·형식을 검토하는 에이전트를 따로 두고, 실행 기록은 채점되는 답안 안에 남긴다.
```

### Description (795/1000자)

```
세 종류의 벤치마크(오픈소스 버그 수정, 경시 수학, 객관식)를 푸는 AI:GO 에이전트 스쿼드와, 그 실행 기록을 보는 웹 뷰어를 만든다.

에이전트는 다섯이다. Router가 문항을 coding·math·generic, 그리고 셋 어디에도 안 맞는 other 넷으로 분류한다. other는 실패가 아니라 분류다 — 요청이 말한 형식을 그대로 따르지, 아는 셋 중 하나를 억지로 씌우지 않는다. Router는 이어서 60,000자짜리 저장소 발췌에서 볼 곳만 잘라 넘긴다.

Architect는 그 안에서 값이 지나는 경로를 따라가 고칠 지점 하나를 고르고, 손대면 안 되는 것을 이름으로 적는다. 리포트가 말한 경로만 고치면 같은 함수를 쓰는 다른 호출자가 깨지기 때문이다. Editor가 그 자리에 SEARCH/REPLACE 블록을 쓴다. 수학과 객관식은 Solver가 한 번에 답한다.

Reviewer는 내용과 형식을 둘 다 본다. 바꾼 줄이 실제 실패에 대응하는지, 그리고 고른 보기가 그 문항의 보기 안인지·마커 짝이 맞는지를 확인하고, 통과·형식 수리·내용 수리·중단 넷 중 하나로 판정한 뒤 최종 답을 발행한다.

그만두는 시점은 세 자리에 나눠 있다. Router는 태스크를 몇 개 만들지, Architect는 고칠 자리를 찾았는지, Reviewer는 더 고칠 수 있는지를 판정한다. 그 아래에 예산 산수가 하드 스톱으로 깔린다.

세 트랙 모두 마지막 답 블록보다 앞은 채점하지 않는다. 그래서 에이전트들이 그 자리에 한 줄씩 실행 기록을 남긴다. 뷰어가 그리는 것이 채점기가 읽은 바로 그 텍스트다.
```

---

## 영문판

### Punchline (197/200 chars)

```
An AI:GO agent squad for three benchmark tracks, and a viewer for its runs. One agent decides where the fix goes, another judges the answer on content and form, and the run log lives in the answer.
```

### Description (994/1000 chars)

```
An AI:GO agent squad for three benchmark tracks — repository bug fixes, math, multiple choice — and a viewer for its runs.

Five agents. A router classifies the item and cuts the 60,000-character excerpt to the regions worth reading. A fourth class, other, catches items matching none of the three: the form is read from the request, not assumed. An architect names one place to change and what must not — fixing only the path the report names leaves a sibling caller broken. An editor writes the SEARCH/REPLACE block. Math and multiple choice go to a solver.

A reviewer judges both layers: does every changed line trace to the failure, and will the parser read the block? It returns pass, fix the form, fix the content, or stop.

Stopping splits three ways: the router's task count, the architect's confidence, the reviewer's verdict, over budget arithmetic.

Every track ignores anything before the answer block, so each agent writes its run log there; the viewer draws what the grader read.
```
