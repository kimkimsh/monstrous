# monstrous

JUNCTIONX Korea 2026 · Lablup + FuriosaAI 트랙 **Build the Ultimate Agent Squad**

AI:GO 벤치마크 문항을 **에이전트 셋**으로 풀고, **어느 실행이 실제로 점수가 되는지**를
말해 주는 **HTML 파일 하나짜리 뷰어**를 같이 낸다.

> Three agents, one model, two model calls per benchmark item, and a viewer that separates
> runs the app calls finished from runs the grader can actually score.

---

## 스쿼드

```
문항 ──► Router ──create_task──► Coder    패치 · 처음부터 짜는 프로그램
                            └─► Solver   수학 · 객관식 · 그 외 전부
                                           └─ 이 출력이 채점된다
```

에이전트 셋, 모델 하나(`furiosa-ai/gpt-oss-120b`), 웨이브 하나, **문항당 모델 호출 두 번.**

**왜 웨이브 하나인가.** 채점기는 하나만 읽는다 — **마지막 태스크의 출력**이다.
런타임의 `finalResult` 는 상태 요약이라 28번 중 28번 거부됐다. 그래서 답을 쓰는 태스크가
마지막이어야 하고, 그 뒤에 무엇을 놓든 답을 잃는 것이 실측됐다. 도구를 쥔 에이전트는
답을 워크스페이스 파일에 저장하고 "done" 이라고 답했는데 채점기는 워크스페이스를 열지 않는다.

**왜 하나가 아닌가.** 요청 본문을 보는 것은 플래너뿐이라 그 자리는 남는다.
Router 와 Solver 는 프롬프트 길이 때문에 갈린다 — 패치 형식 규칙만 7,698자다.

자세한 것은 [`docs/submit/description.md`](docs/submit/description.md) 에 있다.

---

## 뷰어

**설치도 서버도 인터넷도 필요 없다.** HTML 파일 하나를 열고 워크스페이스 폴더를 끌어다 놓는다.

```
viz_revise_program/trace-visualizer.html
```

상단 계기의 **AI:GO 성공 ⇄ 채점 적격**이 이 도구가 만들어진 이유다.
앱은 태스크가 끝나면 성공이라고 적고, 제출 서버는 응답 본문에 요구된 형식이 있어야 점수를 준다.
**그 사이가 점수가 새는 자리다.**

0점도 한 덩어리가 아니다. 네 갈래로 가르고 **고칠 사람을 색이 아니라 글자로** 적는다 —
호출 거부(설정) · 판정 보류(검사기) · 답 형식 없음(프롬프트) · 문항 아님(고칠 것 없음).

**로그에 없는 것은 그리지 않는다.** 캐시 적중률도 태스크별 토큰 차트도 없다 — 그 필드가 비어 있다.
추정한 값은 추정이라고 적고, 절단선 숫자는 손실의 상한이라고 화면에 적는다.

`#demo` 를 붙여 열면 90초짜리 자동 시연이 돈다 — [`사용설명서.md §15`](viz_revise_program/사용설명서.md)

---

## 저장소

| 경로 | 무엇 |
|---|---|
| [`squad/squad_template/monstrous_squad/`](squad/squad_template/monstrous_squad/) | **제출물.** `squad-template.json` 과 트랙별 one-shot 프롬프트 |
| [`viz_revise_program/`](viz_revise_program/) | **제출물.** 트레이스 뷰어 (현행) |
| `viz/` | 뷰어 이전 판. 개편 전 화면이고 판정 로직의 출처다 |
| [`auto_test/`](auto_test/) | 연습 문항을 스쿼드에 넣고 토큰·정확도를 보는 로컬 하네스 |
| `squad/` | AI:GO 워크스페이스 로그. 뷰어의 입력이자 모든 실측의 출처 |
| `docs/submit/` | 제출 문구 |
| `docs/presentation/deck/` | 발표 자료 |
| `docs/viz_revise/` | 뷰어 개편의 기획·조사·스펙 |
| `docs/ideation/` · `docs/resource/` | 설계 이전의 조사 기록 |

---

## 해보기

**뷰어** — `viz_revise_program/trace-visualizer.html` 을 열고 `squad/Demo` 를 끌어다 놓는다.
브라우저가 `file://` 에서 폴더 읽기를 막으면:

```bash
python3 -m http.server 8777
# http://127.0.0.1:8777/viz_revise_program/trace-visualizer.html
```

**자동 시연** — 주소 끝에 `#demo` 를 붙이면 90초 동안 스스로 돈다.

**auto_test**

```bash
cd auto_test
./start.sh
```

헤드리스 서버 → 로컬 모델 → GUI 순으로 올린다. 토큰은 필요 없다.

---

## v1 이 무엇을 알려줬나

v1 은 24팀 중 **23위**, 총점 **0.0925** 였다. 리더보드 API 가 부검 결과를 줬다 —
요청 **1,192회**(문항당 8.1회), 입력 토큰 **5,368,135개**로 전 팀 최다.
시스템 프롬프트 다섯 개가 평균 3,670토큰이었고 그것이 입력의 **81%** 였다.
디스크의 태스크 파일 76개 중 플래너가 실제로 쓴 63개는 **답 형식을 한 번도 언급하지 않았다.**

v2 는 그 줄들에 하나씩 답한다. 에이전트 셋, 모델 하나, 공용 서두 없음,
`enabledTools: []`, 메모리 끔. 연습 세트 기준 약 **294회 요청 · 2.12M 토큰**이다.
**이건 추정이고 결과가 아니다** — v2 의 점수는 아직 없다.

---

## 뷰어가 우리를 고친 적이 있다

「계약 미전송」이라는 0점 갈래가 하나 더 있었다. 요청 지문에 출력 계약 절이 없으면
러너가 안 보낸 것이라고 읽었고, 그렇게 8건을 러너 잘못으로 세고 있었다.

화면에 띄워 보니 그 요청들이 **83~499바이트**였다. 계약 절 하나가 250바이트다 —
애초에 들어갈 자리가 없었다. 그중 6건의 응답에는 `\boxed{}` 가 들어 있었다.
모델은 형식을 들었고, 로그가 그 부분을 안 남겼을 뿐이었다.

갈래를 지웠더니 채점 적격이 **6/15 에서 12/22** 가 됐다. 나아진 것이 아니라 **잘못 세고 있었다.**

---

## Team Monstrous

SEONGHYEON KIM · JUHYEONG LEE · ILKWON KIM
