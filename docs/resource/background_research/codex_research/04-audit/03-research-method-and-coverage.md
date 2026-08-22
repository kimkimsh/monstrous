# 조사 방법, Coverage, 검증 경계

조사 기준일: 2026-08-22 KST

## 결론

로컬 `docs/` 351개 파일은 `codex_research/`를 제외하고 전수 inventory와 content decode를 수행했고, 최신 121개 request는 공식 digest와 재생성 결과가 일치했다. 조사 중 갱신된 `claude_research/`도 다시 읽었다. 외부 조사는 공식 event/model/spec 문서, peer-reviewed 논문, preprint, vendor engineering, 최근 30일 community signal 순으로 교차검증했다. Community signal과 검색 snippet은 claim의 최종 증거로 사용하지 않았다.

## 로컬 전수조사

처리 범위:

- 351 files, 23,095,045 bytes.
- UTF-8 text 346개 전체 decode.
- Markdown 61, TXT 251, JSON 15, JSONL 11, Python 4, Shell 1, extensionless 6.
- binary 5개: `.DS_Store` 3, PDF 1, ZIP 1.
- PDF 29 pages 전체 text extraction.
- ZIP 11 entries integrity check.

이 수치는 최종 검증 시점 snapshot이며, 이번에 새로 작성한 `codex_research/` 파일은 제외했다. 상세 분포와 상충 판정은 [로컬 docs 감사](../01-context/01-local-docs-audit.md)에 있다.

최종 pass에서 `claude_research/` 12개 Markdown, 2,687행, 194,354바이트를 전부 다시 읽었다. 결론이 충돌하는 경우 공식 contest artifact와 직접 확인한 paper 본문을 우선했고, contest와 다른 tool/model 조건의 연구는 candidate 가설로 낮췄다.

무결성 명령:

```bash
cd /Users/mark-mac/workspace/monstrous/docs/resource/example_task
bash tools/verify.sh
```

결과는 raw checksum 통과, coding 20/math 59/generic 42의 ID set과 digest 121/121 일치였다. PDF는 `uv run --with pypdf`로 text extraction했고 ZIP은 `unzip -t`로 검사했다.

## Live portal 재확인

Scrapling CLI의 기존 environment는 `click` dependency가 빠져 실행되지 않았다. 설치 artifact를 수정하지 않고 isolated `uvx` environment에서 fetcher extra를 사용했다.

```bash
uvx --from 'scrapling[fetchers]' scrapling extract get \
  --no-verify \
  --ai-targeted \
  'https://submission.jxc.events.lablup.ai:8444/practice-sets/requests' \
  /tmp/jxc-practice-requests-scrapling.html
```

2026-08-22 20:54:35 KST에 HTTP 200과 35,525-byte HTML을 받았고, 페이지의 최신 공개 목록과 20 coding/59 math/42 generic local set을 대조했다. `/practice-sets/SHA256SUMS`도 logical `(hash, path)` pair가 local manifest와 같았다. Server와 local 파일의 공백 배치는 달라 raw file byte hash 비교가 아니라 parsed pair 비교를 사용했다.

Scrapling Markdown output은 optional `markdownify`가 없어 실패했고 HTML extraction으로 대체했다. TLS `--no-verify`는 행사 서버의 certificate chain 환경 때문에 썼으며, 이는 content authenticity를 별도로 보증하지 않는다. 그래서 hash manifest와 local digest를 함께 대조했다.

## Exa

사용 가능한 Exa web search로 네 개의 독립 query군을 각 최대 8개 결과로 조사했다.

1. fixed-budget single-agent 대 multi-agent controlled evidence.
2. code localization/edit/verification architecture.
3. routing, token budget, self-consistency, self-correction.
4. JUNCTIONX Korea 2026와 Lablup/FuriosaAI official material.

`exa-agent` skill이 우선 요구하는 `agent_run` capability는 현재 session에 노출되지 않았다. 이를 숨기지 않고 `mcp__exa__web_search_exa` 결과에서 primary source로 직접 이동해 본문을 확인했다. Search snippet 자체를 숫자의 근거로 쓰지 않았다.

## Firecrawl

Firecrawl broad web search로 multi-agent architecture, efficient routing, coding repair, observability source 후보를 넓혔다. 심층 research endpoint는 `Unauthorized`였고, 후속 targeted search는 다음 오류로 중단됐다.

```text
The free daily limit for this network has been reached.
```

Quota를 우회하거나 사용자 API credential을 임의 설정하지 않았다. 확보한 후보는 Exa, browser fetch, 공식 페이지와 paper 본문으로 재검증했다. 따라서 Firecrawl coverage는 discovery 보조이며 completeness 보장이 아니다.

## 최근 30일 signal

`last30days`를 다음 주제로 실행했다.

```text
efficient LLM multi-agent squad architecture for benchmark accuracy and token cost
```

실행 시간은 216.3초, 결과는 49개였다.

| source | 수량 | 상태 |
|---|---:|---|
| GitHub | 40 | active |
| Hacker News | 4 | active |
| Reddit | 4 | partial, HTTP 429 영향 |
| YouTube | 1 | active |
| X | 0 | credential/source 없음 |
| TikTok/Instagram | 0 | connector 없음 |

원자료는 [최근 30일 raw signal](../99-raw/efficient-llm-multi-agent-squad-architecture-for-benchmark-accuracy-and-token-cost-raw-recent-signal.md)과 [query plan](../99-raw/last30days-query-plan.json)에 보존했다. 이 표본은 GitHub에 크게 편향되고 engagement가 research validity를 뜻하지 않으므로, architecture의 정량 결론에는 사용하지 않았다.

## Primary source set

### 공식·사양

- [JUNCTIONX Korea official](https://asia.hackjunction.com/)
- [Junction platform event](https://hackjunction.app/hackathons/junctionx-korea-2026)
- [Qwen3-30B-A3B-Instruct-2507 model card](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507)
- [OpenTelemetry GenAI migration notice](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
- [OpenTelemetry GenAI repository](https://github.com/open-telemetry/semantic-conventions-genai)

### Multi-agent architecture

- [Towards a science of scaling agent systems](https://www.nature.com/articles/s42256-026-01268-y)
- [The More the Merrier? Multi-Agent Systems Under Equal Token Budgets](https://arxiv.org/html/2604.02460v1)
- [BenchAgent](https://arxiv.org/html/2606.05670)
- [MAST](https://arxiv.org/html/2503.13657v3)
- [Anthropic multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [Reasoning in Token Economies](https://aclanthology.org/2024.emnlp-main.1112/)
- [Should We Be Going MAD?](https://proceedings.mlr.press/v235/smit24a.html)
- [Personas in System Prompts](https://aclanthology.org/2024.findings-emnlp.888/)

### Coding·reasoning·routing

- [Agentless](https://arxiv.org/html/2407.01489v2)
- [SWE-Edit](https://arxiv.org/html/2604.26102v2)
- [Loc2Repair](https://arxiv.org/html/2606.30963)
- [MMLU-Pro](https://arxiv.org/html/2406.01574v3)
- [s1](https://arxiv.org/html/2501.19393)
- [Self-Consistency](https://arxiv.org/abs/2203.11171)
- [Large Language Models Cannot Self-Correct Reasoning Yet](https://arxiv.org/html/2310.01798)
- [RouteLLM](https://arxiv.org/html/2406.18665)
- [FrugalGPT](https://arxiv.org/html/2305.05176)
- [Chain of Draft](https://arxiv.org/html/2502.18600)
- [Lost in the Middle](https://arxiv.org/html/2307.03172)
- [Let Me Speak Freely?](https://arxiv.org/abs/2408.02442)
- [Chroma Context Rot](https://www.trychroma.com/research/context-rot)

각 source의 숫자, 등급, contest 전이 한계는 [claim–evidence matrix](01-claim-evidence-matrix.md)에서 분리했다.

## 재현하지 못한 boundary

- AI:GO model inference accuracy와 token은 이번 조사에서 실행하지 않았다.
- 나머지 reasoning model 두 종, 가격, cap, cache 과금은 공개 근거를 찾지 못했다.
- Release `aigo-server`의 planner부터 final answer까지 headless E2E completion은 기존 문서에서도 미검증이다.
- Firecrawl deep research는 authorization/quota로 완주하지 못했다.
- Exa `agent_run`과 X/TikTok/Instagram source는 사용할 수 없었다.
- Hidden dataset과 evaluation environment는 접근하지 않았다.

따라서 “최적 squad가 입증됐다”가 아니라 “가장 방어 가능한 baseline, candidate set, 검증 순서가 만들어졌다”가 정확한 완료 범위다.

## 문서 품질 확인 기준

최종 검증은 다음을 확인한다.

1. README의 모든 relative link가 존재한다.
2. local path는 실제 file로 resolve된다.
3. Markdown code fence와 table 구조가 닫힌다.
4. 대회 수치가 local source와 일치한다.
5. proposal, confirmed fact, unresolved question이 섞이지 않는다.
6. `codex_research/` 밖의 사용자 파일은 수정하지 않는다.
