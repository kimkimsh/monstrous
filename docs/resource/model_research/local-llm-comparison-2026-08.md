# 로컬 LLM 모델 비교 분석 및 추천

**작성일**: 2026-08-22
**대상 하드웨어**: MacBook Pro (Mac17,2), Apple M5, 통합 메모리 24 GB
**비교 대상**: K-EXAONE-236B-A23B / gpt-oss-120b / Qwen3-32B

---

## 요약

| 항목 | 결론 |
|---|---|
| 세 모델 로컬 실행 가능 여부 | 셋 다 실용적으로 불가능. Qwen3-32B만 물리적으로 아슬아슬하게 적재되나 사용 가치 없음 |
| 추천 모델 | **Qwen3.6-35B-A3B** (Unsloth `UD-Q3_K_XL`, 약 17 GB) |
| 차순위 (속도 우선) | gpt-oss-20b (MXFP4, 약 12.1 GB) |
| 차순위 (한국어 우선) | EXAONE-4.5-33B (IQ4_XS, 약 18 GB, 비상업 라이선스) |

> **모델명 정정**: 요청에 있던 `K-EXAONE-236B-A22B`는 실제로 존재하지 않는다. 정식 명칭은 **K-EXAONE-236B-A23B** (active 파라미터 23B)이다.

---

## 1. 대상 하드웨어 사양

```
모델          MacBook Pro (Mac17,2)
칩            Apple M5
CPU           10코어 (Performance 4 + Efficiency 6)
GPU           10코어, Metal 4, 코어별 Neural Accelerator 내장
통합 메모리    24 GB (25,769,803,776 bytes)
메모리 대역폭  153 GB/s
디스크 여유    815 GB
```

### 메모리 제약 조건

macOS는 GPU가 점유할 수 있는 통합 메모리를 기본적으로 전체의 일부로 제한한다. 24 GB 기기에서 GPU가 안정적으로 쓸 수 있는 양은 약 16 GB이며, `iogpu.wired_limit_mb` 커널 파라미터로 약 20 GB까지 상향할 수 있다.

```bash
sudo sysctl iogpu.wired_limit_mb=20480   # 20 GB로 상향, 재부팅 시 초기화
sudo sysctl iogpu.wired_limit_mb=0       # 기본값 복원
```

24 GB 기기에서 20480(20 GB)을 초과해 설정하면 macOS 자체가 사용할 메모리가 부족해져 시스템 정지 또는 커널 패닉이 발생할 수 있다.

### 현재 설치 상태 (2026-08-22 확인)

| 도구 | 상태 |
|---|---|
| ollama | 미설치 |
| llama.cpp (llama-cli / llama-server) | 미설치 |
| LM Studio | 미설치 |
| MLX (mlx_lm) | 미설치 |
| Python 3 | `/opt/homebrew/bin/python3` |
| uv | `~/.local/bin/uv` |

로컬 LLM 추론 런타임이 하나도 설치되어 있지 않다. 모델 실행 전 런타임 설치가 선행되어야 한다.

---

## 2. 세 모델 비교

### 2.1 아키텍처 및 스펙

| 항목 | K-EXAONE-236B-A23B | gpt-oss-120b | Qwen3-32B |
|---|---|---|---|
| 개발 주체 | LG AI Research | OpenAI | Alibaba |
| 아키텍처 | MoE (Mixture-of-Experts) | MoE | Dense |
| 전체 파라미터 | 236B | 117B | 32.8B (non-embedding 31.2B) |
| Active 파라미터 | 23B | 5.1B | 32.8B (전량) |
| Expert 구성 | 128개 중 토큰당 8개 활성 | — | 해당 없음 |
| 레이어 | — | — | 64 |
| Attention | 3:1 hybrid, 128-token sliding window | — | GQA (Query 64 / KV 8) |
| Context 길이 | 262,144 (256K) | 131K | 32,768 native, YaRN factor 4.0 적용 시 131,072 |
| Vocabulary | 153,600 (SuperBPE) | — | — |
| 지원 언어 | 6개 (한국어, 영어, 스페인어, 독일어, 일본어, 베트남어) | 영어 중심 | 100개 이상 |
| 라이선스 | K-EXAONE AI Model License Agreement (상업 이용 제약) | Apache 2.0 | Apache 2.0 |
| 출시 | 2025-12 | 2025-08 | 2025-04-28 |
| Knowledge cutoff | 2024-12 | — | 2025-03-31 |

### 2.2 고유 기능

**K-EXAONE-236B-A23B**
- Multi-Token Prediction (MTP)으로 self-speculative decoding 지원, 추론 처리량 약 1.5배 향상
- 3:1 hybrid attention + 128-token sliding window로 장문 처리 시 메모리 사용량 절감
- 한국 정부 국가 AI 파운데이션 모델 프로젝트 1단계 평가에서 13개 벤치마크 중 10개 1위
- 지원 프레임워크: Transformers ≥5.1.0, vLLM ≥0.14.0, SGLang, llama.cpp ≥b7737, TensorRT-LLM (Ollama/LM Studio는 지원 예정)

**gpt-oss-120b**
- reasoning effort 3단계 조절 (low / medium / high)
- MXFP4 양자화가 MoE 가중치에 기본 적용됨 (FP32 대비 약 7.5배 메모리 절감, 정확도 손실 0.3% 이하)
- function calling, web browsing, Python 코드 실행 지원
- full chain-of-thought 접근 가능

**Qwen3-32B**
- thinking 모드 / non-thinking 모드 단일 아키텍처 내 전환
- 권장 샘플링 파라미터: thinking 모드 `temperature 0.6, top_p 0.95, top_k 20`, non-thinking 모드 `temperature 0.7, top_p 0.8, top_k 20`
- greedy decoding 사용 금지 (품질 저하)

### 2.3 벤치마크

아래는 LG AI Research가 공개한 K-EXAONE 기술 리포트의 비교표다.

> **중요**: 이 표의 Qwen 항목은 **Qwen3-32B가 아니라 Qwen3-235B-A22B-Thinking-2507**이다. Qwen3-32B는 이 비교군에 포함되어 있지 않다.

| Benchmark | K-EXAONE-236B-A23B | gpt-oss-120b | Qwen3-235B-A22B | DeepSeek-V3.2 |
|---|---|---|---|---|
| MMLU-Pro | 83.8 | 80.7 | 84.4 | **85.0** |
| GPQA-Diamond | 79.1 | 80.1 | 81.1 | **82.4** |
| AIME 2025 | 92.8 | 92.5 | 92.3 | **93.1** |
| LiveCodeBench v6 | 80.7 | **81.9** | 74.1 | 79.4 |
| SWE-Bench Verified | 49.4 | 62.4 | 25.0 | **73.1** |
| KMMLU-Pro (한국어) | 67.3 | 62.4 | 71.6 | **72.1** |
| KoBALT (한국어) | 61.8 | 54.3 | 56.1 | **62.7** |
| CLIcK (한국어) | 83.9 | 74.6 | 81.3 | **86.3** |
| Ko-LongBench (한국어) | 86.8 | 82.2 | 83.2 | **87.9** |

K-EXAONE 기술 리포트는 총 19개 벤치마크 카테고리에서 EXAONE 4.0 (32B Dense), GPT-OSS (117B MoE), Qwen3-Thinking-2507 (235B MoE), DeepSeek-V3.2 (671B MoE) 4개 모델과 비교 평가했다. 카테고리별 K-EXAONE 점수 범위는 다음과 같다.

| 카테고리 | 주요 벤치마크 | K-EXAONE 점수 범위 |
|---|---|---|
| World Knowledge | MMLU-Pro, GPQA-Diamond | 79.1 – 83.8 |
| Mathematics | AIME 2025, IMO-AnswerBench | 76.3 – 92.8 |
| Code / Agentic | LiveCodeBench, SWE-Bench | 25.9 – 80.7 |
| Tool Use | τ2-Bench, BrowseComp | 31.4 – 78.6 |
| Instruction Following | IFBench, IFEval | 67.3 – 89.7 |
| Long Context | AA-LCR, OpenAI-MRCR | 52.3 – 53.5 |
| Korean | KMMLU-Pro, KoBALT, CLIcK | 61.8 – 90.9 |
| Multilinguality | MMMLU, WMT24++ | 85.7 – 90.5 |
| Safety | Wild-Jailbreak, KGC-Safety | 89.9 – 96.1 |

**Qwen3-32B의 상대적 위치**: Artificial Analysis Intelligence Index 기준 gpt-oss-120b는 24점, Qwen3-32B는 8점(추정)으로 한 체급 아래에 위치한다. 생성 속도는 gpt-oss-120b 152.4 tok/s, Qwen3-32B 103.6 tok/s (서버 기준). 2025년 4월 출시 모델로 작성 시점(2026-08) 기준 약 16개월 경과했다.

### 2.4 모델별 성격 정리

**K-EXAONE-236B-A23B** — 한국어 특화가 실질적 차별점이다. KoBALT에서 61.8로 gpt-oss-120b(54.3)를 크게 앞서고, Ko-LongBench 86.8로 Qwen3-235B(83.2)도 상회한다. 반면 코딩·agentic 영역은 약하다 (SWE-Bench Verified 49.4 vs gpt-oss-120b 62.4). 라이선스가 독자 계약으로 상업 이용에 제약이 있다. 후속 모델인 K-EXAONE 2.0 (750B-A37B)은 Apache 2.0으로 전환되었다.

**gpt-oss-120b** — 코딩, agent, 수학에서 가장 강하다. active 파라미터가 5.1B에 불과해 서버 환경에서 매우 빠르다. 다만 CJK 언어 약점이 명확하다. 중국어 벤치마크에서 20%를 기록해 45% 기준선을 크게 밑돌았다. Apache 2.0으로 상업 이용 제약이 없다.

**Qwen3-32B** — 셋 중 유일한 Dense 모델이자 유일하게 소비자 하드웨어 용량대에 들어온다. 100개 이상 언어 지원과 thinking 모드 전환이 장점이다. 절대 성능은 나머지 둘보다 확실히 낮다.

---

## 3. 로컬 실행 가능 여부 판정

### 3.1 양자화별 용량

**K-EXAONE-236B-A23B GGUF**

| 양자화 | 용량 |
|---|---|
| IQ4_XS (4-bit) | 128 GB |
| Q4_K_M (4-bit) | 143 GB |
| Q5_K_M (5-bit) | 168 GB |
| Q6_K (6-bit) | 195 GB |
| Q8_0 (8-bit) | 252 GB |
| BF16 | 474 GB |

**gpt-oss-120b**

| 양자화 | 용량 |
|---|---|
| MXFP4 (기본) | 약 63 GB (실행 권장 80 GB GPU) |

**Qwen3-32B GGUF** (공식 저장소 실측 바이트)

| 양자화 | 용량 |
|---|---|
| Q4_K_M | 19,762,149,024 bytes (약 19.76 GB) |
| Q5_0 | 22,635,493,024 bytes (약 22.64 GB) |
| Q5_K_M | 23,214,831,232 bytes (약 23.21 GB) |
| Q6_K | 26,883,306,112 bytes (약 26.88 GB) |
| Q8_0 | 34,817,718,912 bytes (약 34.82 GB) |

### 3.2 판정 결과

| 모델 | 최소 실행 용량 | 24 GB 대비 | 판정 |
|---|---|---|---|
| K-EXAONE-236B-A23B | IQ4_XS 128 GB | 5.3배 초과 | 불가능 |
| gpt-oss-120b | MXFP4 63 GB | 2.6배 초과 | 불가능 |
| Qwen3-32B | Q4_K_M 19.76 GB | 적재는 되나 여유 없음 | 실용성 없음 |

### 3.3 Qwen3-32B를 권하지 않는 이유

**메모리** — Q4_K_M 가중치 19.76 GB에 KV cache 2~3 GB, macOS 자체 사용량 4~5 GB를 더하면 27 GB 이상이 필요하다. 24 GB를 초과하므로 swap이 발생한다. 기본 GPU wired limit 16 GB도 넘긴다. `iogpu.wired_limit_mb`를 20 GB로 상향해도 여유가 1 GB 미만이다.

**속도** — Dense 32B이므로 토큰 하나를 생성할 때마다 가중치 전체(19.76 GB)를 읽어야 한다. 메모리 대역폭 153 GB/s 기준 이론 최대 약 7.7 tok/s, 실제로는 대역폭 효율 60~70%를 감안해 5~6 tok/s 수준이다. 대화형 사용에 부적합하다.

Q3_K_M(약 16 GB)까지 낮추면 메모리는 맞지만 양자화로 인한 품질 저하가 발생하고 속도도 여전히 9 tok/s 내외에 머문다.

**gpt-oss-120b 디스크 offload 실행**은 llama.cpp로 기술적으로 가능하나, SSD에서 가중치를 읽으며 추론하므로 한 자리 tok/s 미만이 되어 실용성이 없다.

### 3.4 하드웨어 선택 원리

로컬 추론 속도는 **메모리 대역폭 ÷ 토큰당 읽는 바이트 수**로 결정된다. M5 기본형의 153 GB/s는 고정값이므로, 분모를 줄이는 것이 유일한 선택지다.

- **Dense 모델**은 매 토큰마다 전체 가중치를 읽는다. 24 GB 기기에서 20 GB짜리 Dense 모델은 구조적으로 느리다.
- **MoE 모델**은 active 파라미터만 읽는다. 35B 모델이라도 active가 3B라면 토큰당 읽는 양이 Dense 27B의 1/9 수준이다.

Apple 자체 MLX 벤치마크도 이를 뒷받침한다. M5는 Dense 14B에서 first token까지 10초 미만, 30B MoE에서는 3초 미만을 기록했다. M4 대비 19~27% 향상은 대역폭 증가(120 GB/s → 153 GB/s)에 기인한다.

---

## 4. 추천 모델

### 4.1 1순위 — Qwen3.6-35B-A3B

| 항목 | 값 |
|---|---|
| 개발 주체 | Alibaba Cloud |
| 출시 | 2026-04-27 |
| 아키텍처 | Hybrid sparse MoE (Gated DeltaNet linear attention + gated attention) |
| 전체 / Active 파라미터 | 35B / 3B |
| SWE-bench Verified | 73.4% |
| Context | 262K |
| 멀티모달 | 지원 |
| 라이선스 | Apache 2.0 |
| Apple Silicon 실측 속도 | 35~50 tok/s |

**권장 양자화**

| 양자화 | 용량 | 24 GB 적합성 |
|---|---|---|
| Unsloth UD-Q3_K_XL | 약 17 GB | 권장. KV cache와 macOS 여유 확보 |
| Unsloth Q4_K_S | 약 20.9 GB | 여유 1 GB 미만, swap 위험 |
| Unsloth UD-Q4_K_XL | 약 21 GB | 여유 1 GB 미만, swap 위험 |
| Q4_K_M | 약 21 GB | 여유 1 GB 미만, swap 위험 |
| Q8_0 | 약 37 GB | 불가 |

**UD-Q3_K_XL(17 GB)로 시작**하고, 메모리 압박이 없으면 Q4 계열로 올린다.

선정 근거: SWE-bench Verified 73.4%로 비교 대상 세 모델 중 최고인 gpt-oss-120b(62.4)를 상회한다. active 3B라 M5의 153 GB/s 대역폭 제약을 사실상 회피한다. Apache 2.0으로 라이선스 제약이 없고 262K context와 멀티모달을 함께 제공한다.

### 4.2 2순위 — gpt-oss-20b (속도·안정성 우선)

| 항목 | 값 |
|---|---|
| Active 파라미터 | 3.6B |
| 용량 | MXFP4 약 12.1 GB (Q4_K_M GGUF 13.3 GB) |
| 라이선스 | Apache 2.0 |
| 참고 속도 | M4 Pro 24 GB(273 GB/s) 기준 150~170 tok/s 보고. M5 기본형(153 GB/s)은 대역폭 비례로 절반 수준 예상 |

24 GB 기기에서 가장 여유롭다. 128K context를 확보하고도 메모리가 남는다. 단점은 한국어 성능이 약하다는 점이다.

### 4.3 3순위 — EXAONE-4.5-33B (한국어 우선)

| 항목 | 값 |
|---|---|
| 개발 주체 | LG AI Research |
| 출시 | 2026-04-09 |
| 파라미터 | 33B (vision encoder 1.2B 포함) |
| Context | 262,144 |
| 멀티모달 | 지원 (LG AI Research 최초 공개 VLM) |
| 라이선스 | EXAONE AI Model License Agreement 1.2 - **NC (비상업)** |

**GGUF 양자화별 용량**

| 양자화 | 용량 |
|---|---|
| IQ4_XS | 18 GB |
| Q4_K_M | 20 GB |
| Q5_K_M | 23.5 GB |
| Q6_K | 27.1 GB |
| Q8_0 | 35.1 GB |
| BF16 | 66.1 GB |

**한국어 벤치마크**: KMMMU 42.7 / K-Viscuit 80.1 / KRETA 91.9. CharXiv(차트·도표 이해)에서 Qwen3 VL 32B, GPT-5-mini, Claude Sonnet 4.5를 상회했다. K-EXAONE 236B의 약 1/7 규모로 텍스트 이해·추론에서 유사한 성능을 낸다.

단점 두 가지: Dense 33B라 M5 기본형 대역폭에서 약 7 tok/s로 느리다. 그리고 라이선스가 NC라 상업적 사용이 불가하다.

### 4.4 선택 기준 요약

| 우선순위 | 추천 모델 |
|---|---|
| 균형 (성능 + 속도 + 라이선스) | Qwen3.6-35B-A3B, UD-Q3_K_XL |
| 속도 및 안정성 | gpt-oss-20b, MXFP4 |
| 한국어 품질 | EXAONE-4.5-33B, IQ4_XS (비상업 한정) |

---

## 5. 설치 절차

현재 로컬 LLM 런타임이 설치되어 있지 않으므로 런타임 설치가 선행되어야 한다.

### 방법 1 — LM Studio (GUI, MLX와 GGUF 모두 지원)

```bash
brew install --cask lm-studio
```

설치 후 앱 내 검색에서 모델을 받아 실행한다. 초보자에게 가장 권장된다.

### 방법 2 — Ollama (CLI)

```bash
brew install ollama
ollama serve                                   # 별도 터미널에서 실행
ollama pull qwen3.6:35b-a3b-q3_K_XL
ollama run qwen3.6:35b-a3b-q3_K_XL
```

### 방법 3 — MLX (Apple Silicon 전용, 최고 속도)

```bash
uv tool install mlx-lm
mlx_lm.generate --model mlx-community/Qwen3.6-35B-A3B-4bit --prompt "안녕"
```

### GPU 메모리 한도 조정 (필요 시에만)

```bash
sudo sysctl iogpu.wired_limit_mb=20480
```

24 GB 기기에서 20480(20 GB)을 초과해 설정하면 시스템 정지 또는 커널 패닉 위험이 있다. 설정은 재부팅 시 초기화되며, `sudo sysctl iogpu.wired_limit_mb=0`으로 즉시 복원할 수 있다.

---

## 6. 참고 자료

### 모델 카드 및 저장소
- [K-EXAONE-236B-A23B (Hugging Face)](https://huggingface.co/LGAI-EXAONE/K-EXAONE-236B-A23B)
- [K-EXAONE-236B-A23B-GGUF (Hugging Face)](https://huggingface.co/LGAI-EXAONE/K-EXAONE-236B-A23B-GGUF)
- [K-EXAONE 공식 GitHub](https://github.com/LG-AI-EXAONE/K-EXAONE)
- [K-EXAONE 2.0 Technical Report (arXiv)](https://arxiv.org/html/2608.04505)
- [openai/gpt-oss-120b (Hugging Face)](https://huggingface.co/openai/gpt-oss-120b)
- [Qwen/Qwen3-32B (Hugging Face)](https://huggingface.co/Qwen/Qwen3-32B)
- [Qwen3-32B-GGUF 파일 목록](https://huggingface.co/Qwen/Qwen3-32B-GGUF)
- [Qwen3 Technical Report (arXiv 2505.09388)](https://arxiv.org/pdf/2505.09388)
- [LGAI-EXAONE/EXAONE-4.5-33B-GGUF](https://huggingface.co/LGAI-EXAONE/EXAONE-4.5-33B-GGUF)
- [unsloth/Qwen3.6-35B-A3B-GGUF](https://huggingface.co/unsloth/Qwen3.6-35B-A3B-GGUF)
- [bartowski/Qwen_Qwen3.6-27B-GGUF](https://huggingface.co/bartowski/Qwen_Qwen3.6-27B-GGUF)

### 하드웨어 및 성능
- [Apple ML Research — Exploring LLMs with MLX and the Neural Accelerators in the M5 GPU](https://machinelearning.apple.com/research/exploring-llms-mlx-m5)
- [Apple Newsroom — M5 발표](https://www.apple.com/newsroom/2025/10/apple-unleashes-m5-the-next-big-leap-in-ai-performance-for-apple-silicon/)
- [GPT-OSS 120B 메모리 요구량 분석](https://yingtu.ai/en/blog/gpt-oss-120b-memory-requirements)
- [Qwen3.6 VRAM 요구량 표 (27B / 35B-A3B)](https://knightli.com/en/2026/05/01/qwen3-6-local-vram-quantization-table/)
- [Qwen3.6-35B-A3B 로컬 실행 가이드](https://www.aimadetools.com/blog/qwen-3-6-35b-a3b-complete-guide/)
- [Unsloth — gpt-oss 실행 가이드](https://unsloth.ai/docs/models/gpt-oss-how-to-run-and-fine-tune)
- [Unsloth — Qwen3.6 실행 가이드](https://unsloth.ai/docs/models/qwen3.6)

### 벤치마크 비교
- [Artificial Analysis — gpt-oss-120b vs Qwen3 32B](https://artificialanalysis.ai/models/comparisons/gpt-oss-120b-vs-qwen3-32b-instruct)
- [OpenRouter — gpt-oss-120b vs Qwen3 32B](https://openrouter.ai/compare/openai/gpt-oss-120b/qwen/qwen3-32b)

### 뉴스 및 발표
- [LG — K-EXAONE 공개 (PR Newswire)](https://www.prnewswire.com/news-releases/lg-rolls-outs-k-exaone-south-korea-joins-the-global-frontier-ai-race-with-world-class-ai-model-302658264.html)
- [LG — EXAONE 4.5 공개 (PR Newswire)](https://www.prnewswire.com/news-releases/lg-reveals-next-gen-multimodal-ai-exaone-4-5-302736993.html)
- [Korea Times — K-EXAONE 2.0 (750B) 공개](https://www.koreatimes.co.kr/business/tech-science/20260731/lg-unveils-750-bil-parameter-frontier-ai-model-k-exaone-20)
- [LG AI Research Blog — EXAONE 4.5 VLM](https://www.lgresearch.ai/blog/view?seq=641)
- [OpenAI — Introducing gpt-oss](https://openai.com/index/introducing-gpt-oss/)
