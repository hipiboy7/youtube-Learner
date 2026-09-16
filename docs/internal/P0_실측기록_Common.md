# P0 실측기록 — Common

- 상위 문서: `docs/P0_설계서_Common.md` (v2) 4절 FR-1~34, 22절 완료 기준
- 규칙: `CLAUDE.md` 4절 3단계 산출물. **이 Phase 에서 기계와 외부 서비스가 실제로 무엇을 했는지**를 한 곳에 모은다(단일 출처)
- 실행일: 2026-09-14 / 작성 LLM: Fable 5.1 / 브랜치: `impl-phase0` / 병합: `6480b0b`
- 결과: **전 항목 통과 (PASS)** — 백엔드 228건, 프론트 13건, 환경 검사 READY, 문서 검사 위반 0
- 상태: v2 — 방법론 개정(2026-09-16)으로 구 `P0_검토서_TechSpike`·`P0_테스트결과서_Common`·`P0_검토서_SelfReview` 를 통합

> **v2 개정 사유 (2026-09-16)**: 방법론 개정 — 실측값이 세 문서에 흩어져 서로 어긋났다(정합성 검사 31건의 주원인).
> 착수 전 실측(TechSpike) · 구현 후 실호출(테스트결과서) · 자체 점검(SelfReview) 을 이 문서로 합치고 원 문서는 지웠다.
> 기계가 이미 증명하는 것(테스트 수·커버리지 전량 표, FR 전건 대조표)은 **옮겨 적지 않는다** — 9절 명령으로 언제든 재현한다.
> 문장은 그대로이며 절 번호만 바뀌었다. 근거: `docs/internal/qa/질의응답_방법론개정.md`

## 1. 실행 환경

| 항목 | 값 |
|---|---|
| OS | Windows Server 2022 Standard (10.0.20348) |
| CPU / RAM / 디스크 여유 | Intel Xeon (Icelake) 물리 1 / 논리 2, 16GB, C: 4.78GB · D: 3.90GB (도구·모델 캐시·pip/npm 캐시를 D: 로 모으고 C: 캐시를 지운 뒤 — D: 우선 규칙) |
| Python | 3.12.10 (`backend\.venv\Scripts\python.exe`) |
| Node / npm | v24.14.0 / 11.9.0 |
| 테스트 도구 | pytest 8.4.2, pytest-cov 7.1.0, ruff 0.16.7 / vitest 3.2.7, @vitest/coverage-v8 |
| 주요 패키지 | pydantic 2.13.5, pydantic-settings 2.15.0, SQLAlchemy 2.0.52, yt-dlp 2026.8.19, faster-whisper 1.2.1, ctranslate2 4.8.2, av 18.1.0, youtube-transcript-api 1.2.4, bgutil-ytdlp-pot-provider 2.0.0 |
| 외부 상태 | `scripts\check_env.ps1` → `==> READY` (5.1절). 네트워크 호출 없음(P0 는 외부 서비스 코드를 만들지 않는다) |

## 2. 착수 전 실측 — 검증 질문

| # | 질문 | 왜 지금 확인해야 하나 |
|---|---|---|
| Q1 | yt-dlp가 `/videos`·`/shorts` 탭을 분리해 목록화하는가. flat 결과에 어떤 필드가 오는가 | P1 완료 기준(전량 목록화)과 데이터 모델(어느 필드를 flat에서, 어느 필드를 영상별 조회에서 얻나) |
| Q2 | 자막을 영상 다운로드 없이 json3로 받을 수 있는가. 수동/자동/원어/번역을 구분할 수 있는가 | P2 Provider 체인의 1순위 설계 |
| Q3 | PO 토큰 요구(yt-dlp #14307)가 이 환경에서 자막·오디오에 실제로 영향을 주는가. bgutil 제공자는 어떻게 동작하는가 | 배포 시 동봉해야 할 구성요소 결정 |
| Q4 | ffmpeg 없이 오디오만 받을 수 있는가 | 설치파일에 ffmpeg 바이너리를 넣을지 결정 |
| Q5 | faster-whisper가 CPU 전용·물리 코어 1개 VM에서 얼마나 빠른가 | STT 전략(자막 우선 정책의 강도)과 기본 모델(보류 결정 2) |
| Q6 | youtube-transcript-api가 이 네트워크(사내 IP)에서 동작하는가 | 2순위 폴백 채택 여부 |
| Q7 | 실행 환경(CPU·RAM·디스크·네트워크·도구)의 실측값 | scope-definition 8절 실행 환경, 설계 제약 |

## 3. 착수 전 실측 — 방법

| 항목 | 값 |
|---|---|
| 스크립트 | `scripts/spike/p0_techspike.py` (등급 C) + 아래 3절의 개별 명령 |
| 대상 | 공개 채널 `https://www.youtube.com/@sebasi15` (세바시 강연 Sebasi Talk, `UCgheNMc3gGHLsT-RISdCzDQ`). 롱폼·숏폼이 모두 많은 한국어 채널이라 선택 |
| 환경 | Windows Server 2022 (10.0.20348), Python 3.12.10 (`backend\.venv`), Node v24.14.0, yt-dlp 2026.08.19, yt-dlp-ejs 0.8.0, bgutil-ytdlp-pot-provider 2.0.0, faster-whisper 1.2.1, ctranslate2 4.8.2, av 18.1.0, onnxruntime 1.30.0, youtube-transcript-api 1.2.4 |
| 하드웨어 | Intel Xeon (Icelake) **물리 코어 1 / 논리 2**, RAM 16GB, GPU 없음(Microsoft Basic Display Adapter), 디스크 여유 **C: 4.6GB / D: 4.7GB** (검증 시작 시점) |
| 네트워크 | 사내 고정 IP(AS45985 SamsungSDS, Incheon), 프록시 환경변수 없음. `www.youtube.com` HTTP 200 (1.5s), `huggingface.co` 200, `pypi.org` 200 |
| 실행 명령 | 7절 |

## 4. 착수 전 실측 — 결과 (실제 출력 복사)

### 3.1 Q1 — 탭 분리 목록 (flat)

`extract_flat="in_playlist"`, `playlistend=60`, 탭당 1회 요청.

```
== tab_videos ==
  count = 60            elapsed_s = 2.4
  channel_id = UCgheNMc3gGHLsT-RISdCzDQ    channel_title = 세바시 강연 Sebasi Talk
  playlist_count_reported = None
  has_upload_date = False    has_timestamp = False
  duration_min_max = [42, 4079]
  keys = ['_type', 'duration', 'id', 'ie_key', 'thumbnails', 'title', 'url', 'view_count']
== tab_shorts ==
  count = 60            elapsed_s = 2.4
  duration_min_max = None
  keys = ['_type', 'id', 'ie_key', 'thumbnails', 'title', 'url', 'view_count']
overlap = []
```

판정:
- 탭 분리 **된다**. 60건씩 2.4초. 두 탭의 id 겹침 0건(상위 60건 기준).
- **롱폼 flat에는 `duration`이 있지만 숏폼 flat에는 없다.** 두 탭 모두 `upload_date`·`timestamp`가 없다.
  → 업로드일·(숏폼)길이는 **영상별 조회(메타 보충)** 로 얻어야 한다. `playlist_count`도 None이라 "전량"은 페이지 끝까지 돈 결과로 판정해야 한다.
- 롱폼 탭에 42초짜리도 있다 → **길이로 롱/숏을 판정하면 틀린다. 탭 소속이 기준**이다 (보류 결정 3 → 근거 확보, 본 검증으로 종료 가능).

### 3.2 Q2 — 자막 json3 (영상 다운로드 없이)

대상: 롱폼 1건 `L81RWsnY-vY` (996초, 업로드 2026-09-11).

```
[info] L81RWsnY-vY: Downloading subtitles: ko, en
[download] Destination: L81RWsnY-vY.ko.json3
ERROR: Unable to download video subtitles for 'en': HTTP Error 429: Too Many Requests
```
```
parsed: L81RWsnY-vY.ko.json3  events_with_text=745  chars=6814  first_start_ms=359  last_start_ms=986441
preview: "지난 명절에 한우 드렸나요? 혹시 그게 맛있었다라고 하면 그건 운이 좋아서 그랬을 겁니다. …"
```

트랙 구성(API `extract_info`):
```
language = ko | duration = 995 | upload_date = 20260911 | live_status = not_live
subtitles (manual) keys = []
automatic_captions count = 157 | ko-like keys = ['ko-orig', 'ko']
ko-orig name = Korean (Original) | ko name = Korean
```

판정:
- `--skip-download`로 json3를 **받는다**. 16분 영상의 자동자막 745이벤트·6,814자, 타임스탬프(ms) 포함.
- 이 영상은 **수동 자막이 없고 자동자막(ko)만** 있다. `automatic_captions` 157개 중 원어는 **`ko-orig`("Korean (Original)")** 하나이고 나머지 156개는 **번역**이다.
- `en`을 요청하면 번역 엔드포인트로 가며 **HTTP 429**를 즉시 맞았다(재시도 1회도 동일). 게다가 yt-dlp는 한 언어가 실패하면 **명령 전체를 종료 코드 1로 끝낸다**(ko 파일은 이미 저장됨).
  → 설계: **원어 트랙만**(`subtitles[<lang>]` → `automatic_captions[<lang>-orig]`) 받는다. 번역 자막은 기본 꺼짐. 언어별로 **따로 요청**하고 429는 백오프.
- 영상별 조회 1회에 `duration`·`upload_date`·`language`·`live_status`·자막 트랙 목록이 함께 온다 → 메타 보충과 자막 목록 확인은 **같은 요청**으로 처리 가능.

### 3.3 Q3 — PO 토큰과 bgutil 제공자

pip 설치 직후(서버 디렉토리 없음):
```
[debug] [youtube] [pot:bgutil:script-node] Script path doesn't exist: C:\Users\SYSADMIN\bgutil-ytdlp-pot-provider\server\build\generate_once.js
[debug] [youtube] [pot] PO Token Providers: bgutil:http-2.0.0 (external), bgutil:script-node-2.0.0 (external, unavailable), bgutil:script-deno-2.0.0 (external, unavailable)
[debug] [youtube] L81RWsnY-vY: Detected experiment to bind GVS PO Token to video ID for web client
WARNING: [youtube] [pot:bgutil:http] Error reaching GET http://127.0.0.1:4416/ping (caused by TransportError). Please make sure that the server is reachable at http://127.0.0.1:4416.
```
→ 제공자 없이도 이날은 ko 자막·오디오가 받아졌다. 그러나 "PO Token을 video ID에 묶는 실험 감지" 로그가 떴다.

`git clone https://github.com/Brainicism/bgutil-ytdlp-pot-provider` → `server/`에서 `npm ci && npx tsc` 후(기본 경로 `~/bgutil-ytdlp-pot-provider/server`):
```
[debug] [youtube] [pot] PO Token Providers: bgutil:http-2.0.0 (external), bgutil:script-node-2.0.0 (external), bgutil:script-deno-2.0.0 (external, unavailable)
[youtube] [pot:bgutil:script-node] Generating a gvs PO Token for web client via bgutil script
[debug] [youtube] [pot:bgutil:script-node] Executing command to get POT via script: "C:\Program Files\nodejs\node.EXE" C:\Users\SYSADMIN\bgutil-ytdlp-pot-provider\server\build\generate_once.js -c L81RWsnY-vY --innertube-context "{...}"
[debug] [youtube] L81RWsnY-vY: Retrieved a gvs PO Token for web client
[download] Destination: L81RWsnY-vY.ko.json3
```

판정:
- **bgutil 스크립트 모드(node)가 동작한다.** 요구 조건: Node ≥ 20 + 빌드된 `server/build/generate_once.js`. pip 패키지는 플러그인만 담고 있다.
- HTTP 모드는 `127.0.0.1:4416` 서버가 없으면 매 요청 WARNING을 낸다 → 설정에서 스크립트 경로를 명시하고 HTTP 제공자를 비활성화(또는 서버 동봉)해야 로그가 깨끗하다.
- JS 런타임: `--js-runtimes node`로 Node 24가 인식됐다(`[debug] JS runtimes: node-24.14.0`). Deno 불필요.
- 추가 경고: `The extractor specified to use impersonation ... no impersonate target is available` → `curl_cffi`(`yt-dlp[default,curl-cffi]`) 설치 여부는 **P1에서 판단**(6절).

### 3.4 Q4 — ffmpeg 없이 오디오

```
[info] QaZOH2zrUS8: Downloading 1 format(s): 140-2
[download] Destination: QaZOH2zrUS8.m4a
WARNING: QaZOH2zrUS8: writing DASH m4a. Only some players support this container. Install ffmpeg to fix this automatically
files: QaZOH2zrUS8.m4a  2,267,627 bytes   elapsed_s = 6.2
```

판정: `-f "bestaudio[ext=m4a]/bestaudio"`, 후처리 없음 → **ffmpeg 바이너리 없이 받는다.** DASH 컨테이너 경고가 나지만 PyAV(ffmpeg 라이브러리 내장)가 디코딩해 Whisper 입력으로 문제없이 쓰였다(3.5절). 140초 숏폼 오디오 2.3MB.

### 3.5 Q5 — faster-whisper CPU 속도 (small)

대상: 위 m4a(140.1초, 한국어 강연). `compute_type="int8"`, `cpu_threads=2`, `vad_filter=True`, `beam_size=1`.

```
whisper_small: load_s = 8.1   transcribe_s = 45.9   audio_duration_s = 140.1
               x_realtime = 3.05   language_probability = 1.0   segments = 43
preview: "누군가에게나 이제 끝인가 싶은 그 순간이 자주 오잖아요."
         "시험에 떨어졌을 때 원하던 일을 보기해야 할 때 나만 멈춰 있는 것처럼 느껴질 때요."
```

판정: **실시간의 3.05배**(140초 오디오 → 46초). 물리 코어 1개에서도 자막 없는 영상의 배치 처리가 현실적이다(1시간 영상 ≈ 20분). 품질은 대체로 맞지만 소형 모델 특유의 오인식이 있다("보기해야" → 실제는 "포기해야"). 모델 최초 다운로드는 HF 캐시(`C:\Users\SYSADMIN\.cache\huggingface`)로 약 480MB.

### 3.6 Q5 — faster-whisper CPU 속도 (large-v3-turbo)

같은 오디오·같은 옵션, 모델 `deepdml/faster-whisper-large-v3-turbo-ct2` (int8, 1.6GB).

```
load_s = 21.6   transcribe_s = 163.6   audio_s = 140.1   x_realtime = 0.86   segments = 43
preview: "누군가에게나 이제 끝인가 싶은 그 순간이 찾아오잖아요."
         "시험에 떨어졌을 때 원하던 일을 보기해야 할 때 나만 멈춰있는 것처럼 느껴질 때요."
```
```
Warning: `huggingface_hub` cache-system uses symlinks by default ... your machine does not support them ...
Caching files will still work but in a degraded version that might require more space on your disk.
```

| 모델 | 크기 | 로드 | 140초 처리 | x실시간 | 비고 |
|---|---|---|---|---|---|
| small | 464MB | 8.1s | 45.9s | **3.05** | 오인식 소수("보기해야") |
| large-v3-turbo | 1.6GB | 21.6s | 163.6s | **0.86** | 같은 자리 같은 오인식. 문장 일부만 더 자연스러움("찾아오잖아요") |

판정:
- 물리 코어 1개에서 turbo는 **실시간보다 느리다**(1시간 영상 ≈ 70분). small은 3배 빠르고 이 샘플에서 품질 차이는 작았다.
  → 이 급 CPU의 기본 모델은 **small**, turbo·medium은 사용자 선택 프리셋. **보류 결정 2는 열어 둔다** — medium 미측정, 긴 강연(발화 밀도 높음)·잡음 환경 미측정. P2에서 자막 있는 영상으로 정량 비교(WER) 후 확정.
- Windows에서 HF 캐시가 심볼릭 링크를 못 써 **디스크를 더 쓴다**. 측정 후 C: 여유가 4.6GB → **2.44GB**로 줄었다. turbo 캐시는 기록 후 삭제했다. 모델 캐시는 `.env` `HF_HOME`으로 **D:(또는 여유 드라이브)** 에 두고, `HF_HUB_DISABLE_SYMLINKS_WARNING=1`을 기본 환경으로 넣는다.

### 3.7 Q6 — youtube-transcript-api 폴백

```
tracks: [{"lang": "ko", "generated": true, "translatable": false}]
ko snippets: 373 chars: 6442 first: 지난 명절에 한우 드렸나요? 혹시 | start: 0.359 dur: 6.321
elapsed_s: 1.6
```

판정: 사내 IP에서 **동작한다**(1.6초). `is_generated`로 수동/자동을 구분해 준다. 동일 영상 자막이 yt-dlp json3(745이벤트·6,814자)와 문자 수가 비슷하다(6,442자 — 스니펫 병합 단위 차이). 2순위 폴백으로 적합. 단 비공식 엔드포인트라 차단 가능성은 상존.

### 3.8 Q7 — 실행 환경

| 항목 | 실측 |
|---|---|
| CPU | Intel Xeon Processor (Icelake) — NumberOfCores 1, NumberOfLogicalProcessors 2 |
| RAM | 16.0GB |
| GPU | 없음 (Microsoft Basic Display Adapter, Microsoft Remote Display Adapter) |
| 디스크 | C: 4.6GB 여유 / 35.4GB 사용, D: 4.7GB 여유 / 3.3GB 사용 (venv 331MB 포함) |
| Python | 3.14.3(기본 `py`), 3.12(`py -3.12`) → 프로젝트는 3.12 고정 |
| Node / npm | v24.14.0 / 11.9.0 |
| ffmpeg / Rust / gh | 모두 없음 |
| 네트워크 | 사내 고정 IP, 프록시 없음, YouTube·HF·PyPI 직접 접속 가능 |

## 5. 문서·예상과 달랐던 것

| # | 예상(문서·기획) | 실제 | 영향 | 기록 |
|---|---|---|---|---|
| 1 | flat 목록에 길이·업로드일이 온다 | 숏폼은 `duration` 없음, 두 탭 모두 `upload_date` 없음 | P1에 **메타 보충 단계** 필수. "목록만으로 정렬·필터"는 불가 | 설계 반영(5절) |
| 2 | 자막 언어 우선순위 `ko→en→any`로 요청하면 된다 | 원어 외 언어는 번역 요청이 되어 **429**. 한 언어 실패 시 yt-dlp 명령 전체 실패 | 원어 트랙만 요청, 언어별 분리 요청, 번역은 옵션 | 설계 반영(5절) |
| 3 | PO 토큰 제공자는 pip 설치로 동작 | Node 서버 디렉토리 빌드 필요. HTTP 모드 미기동 시 경고 반복 | 배포물에 `generate_once.js` 동봉 + 설정 명시 필요 | `검토서_트러블슈팅.md` T-001 |
| 4 | CPU Whisper는 실시간의 0.3~1배로 느릴 것 | small int8: **3.05배** | 자막 없는 영상도 배치 처리 현실적. 다만 모델 크기별 재측정(3.6절) | — |
| 5 | 기획 시 CPU 코어 수 미확인 | **물리 코어 1개** | `cpu_threads` 기본값 2, 동시 STT 작업 1개 고정 | 설계 반영 |
| 6 | 디스크 여유 충분 | C·D 각 5GB 미만 | 모델 캐시 위치 설정 필수(`HF_HOME`), 대형 모델 동시 보유 불가, P4 Rust 툴체인 설치 전 **증설/정리 필요** | 보류 결정 등재 후보 |
| 7 | 롱/숏 판정에 길이 기준 보조 필요할 수도 | 롱폼 탭에 42초 영상 존재 | **탭 소속만**이 기준. 길이 기준은 쓰지 않는다 | 보류 결정 3 종료 근거 |

## 6. 설계에 반영한 것

| 사실 | 반영 위치 |
|---|---|
| 목록은 flat(빠름, 60건/2.4초) + 영상별 메타 보충(길이·업로드일·언어·자막 트랙) 2단계 | scope 2절·4절, `설계서_Architecture` 4절 데이터 흐름, P1 완료 기준 |
| 자막은 `subtitles[<lang>]`(수동) → `automatic_captions[<lang>-orig]`(원어 자동) 순. 번역 트랙 기본 제외. 언어별 개별 요청 + 429 백오프 | scope 5절, P2 설계 판단, `constants.py`(`ORIGINAL_CAPTION_SUFFIX = "-orig"`) |
| Provider 체인 3단: yt-dlp json3 → youtube-transcript-api → Whisper | `설계서_Architecture` 2절 DIP 경계, `domain/interfaces.py` `TranscriptProvider` |
| bgutil 스크립트 모드 필수 구성: Node ≥ 20 + `server/build/generate_once.js`. 경로는 `.env`(`BGUTIL_SCRIPT_PATH`), HTTP 제공자 비활성화 옵션 | `.env.example`, `check_env` 검사 항목, P4 패키징 목록 |
| 오디오는 `bestaudio[ext=m4a]/bestaudio` 후처리 없음 → ffmpeg 미동봉 | scope 5절, `설계서_Architecture` 7절 "도입하지 않은 것" |
| Whisper 기본 모델 **small**(코어 1개 급에서 3.05x; turbo는 0.86x), `cpu_threads=2`(논리 코어 수), STT 워커 1개, `vad_filter=True`, `beam_size=1`. 기본값은 `backend/config/stt_default.json`, 프리셋 small/medium/turbo | `설계서_Architecture` 5절, 보류 결정 2(P2 정량 비교 후 확정) |
| 모델 캐시 위치를 `.env` `HF_HOME`으로 지정(기본 `DATA_DIR/models`), `HF_HUB_DISABLE_SYMLINKS_WARNING=1`. Windows HF 캐시는 심볼릭 링크 미지원으로 공간을 더 쓴다 | `config.py` Settings, `.env.example`, `check_env` 디스크 여유 경고 |
| 실행 환경 제약(코어 1·디스크 5GB·GPU 없음)을 scope 8절과 `CLAUDE.md` 0절에 명시. P4 전 디스크 확보를 보류 결정으로 등재 | scope 8절, `CLAUDE.md` 0절·1절 |
| 롱/숏 판정은 탭 소속(보류 결정 3 → 본 검증으로 종료) | `CLAUDE.md` 보류 결정 표 |

## 7. 미확인 사항

| 항목 | 왜 지금 못 확인했나 | 확인 시점 |
|---|---|---|
| 채널 **전량**(수천 건) 목록화 시 페이지네이션·속도·차단 여부 | 60건 제한으로 실행. 전량은 P1 대상 | P1 TechSpike |
| 숏폼 탭 100건 초과 페이지네이션(yt-dlp #11130은 플레이리스트 문제, 탭은 정상이라는 보고) | 동일 | P1 TechSpike |
| 원어 자막 요청도 대량 반복 시 429가 나는가(간격·건수 한계) | 단발 요청만 실행 | P2 TechSpike(연속 30건) |
| `curl_cffi` 임퍼서네이션 설치 효과 | 경고만 관측, 실패는 없었음 | P1 (차단 발생 시 즉시) |
| PO 토큰 없이도 되는 상태가 언제까지 유지되나 | YouTube 실험 중 | 상시 — 제공자를 기본 구성으로 둔다 |
| medium 모델 속도·정확도 | 디스크 여유 부족으로 turbo만 추가 측정 | P2 벤치마크(보류 결정 2) |
| Whisper 한국어 품질 정량 비교(자막 있는 영상으로 WER) | 기준 자막 정규화 코드가 없음 | P2 |

## 8. 테스트 결과 요약

| 구분 | 테스트 수 | 결과 |
|---|---|---|
| 등급 A (`backend/tests/unit/`) — constants 35 · exceptions 15 · domain_models 45 · interfaces 5 · run_context 15 · null_analyzer 6 | 121 | PASS |
| 등급 B (`backend/tests/integration/`) — config 28 · logging 9 · db 5 · analysis_registry 7 · check_env 25 · docs 33 | 107 | PASS |
| 프론트 (`frontend/`, vitest) — time 9 · api 3 · App 1 | 13 | PASS |
| E2E (`backend/tests/e2e/`, `-m e2e`) | 0 | 해당 없음 — P0 는 실호출 코드가 없다 |
| **합계 (기본 pytest)** | **228** | **PASS** |

## 9. 등급별 커버리지

`backend\.venv\Scripts\python.exe -m pytest --cov --cov-report=term` (branch 포함). 측정 대상 `youtube_learner` + `scripts/`(spike 제외).

### 3.1 등급 A — 목표 ≥ 90%

| 모듈 | Stmts | Miss | Branch | BrPart | Cover |
|---|---|---|---|---|---|
| `constants.py` | 47 | 0 | 8 | 0 | 100% |
| `domain/models.py` | 122 | 0 | 22 | 0 | 100% |
| `workflow/run_context.py` | 55 | 0 | 2 | 0 | 100% |
| `analysis/null_analyzer.py` | 14 | 0 | 0 | 0 | 100% |
| `scripts/verify_docs.py` (검사 함수 + main) | 275 | 6 | 138 | 7 | 97% |
| **소계** | **513** | **6** | | | **98.8%** (문 기준) → 목표 대비 +8.8%p |

`verify_docs.py` 미커버 6문: venv python 부재 분기(223-224), `--path` 로 없는 파일 이외의 드문 분기(250·269·302·424). 이 VM 에서는 재현할 수 없는 환경 분기다.

### 3.2 등급 B — 목표 ≥ 70%

| 모듈 | Stmts | Miss | Branch | BrPart | Cover |
|---|---|---|---|---|---|
| `cli/check_env.py` | 151 | 11 | 28 | 1 | 93% |
| `config.py` | 89 | 3 | 14 | 1 | 96% |
| `logging_config.py` | 49 | 1 | 8 | 2 | 95% |
| `analysis/registry.py` | 30 | 0 | 6 | 0 | 100% |
| `repository/db.py` | 25 | 0 | 0 | 0 | 100% |
| **소계** | **344** | **15** | | | **95.6%** (문 기준) → 목표 대비 +25.6%p |

`check_env.py` 미커버: 필수 모듈 import 실패 분기(82-83), 디렉토리 쓰기 실패(132-133), 디스크 OSError(150-151), `.env` ValidationError 진입(216-219), `__main__`(226). `config.py`: PyInstaller frozen 분기(36), `ensure_dirs` OSError(115-116) — P4 에서 실증.

### 3.3 A+B 가중 평균 — 목표 ≥ 80%

**97.5%** = (513 − 6 + 344 − 15) / (513 + 344). 도구가 보고한 TOTAL(`__init__` 포함, 879문)은 **97%**.

프론트(`frontend/src/lib/`): `time.ts`·`api.ts` Stmts/Branch/Funcs/Lines **100%** (vitest v8).

### 3.4 측정 제외

| 대상 | 이유 |
|---|---|
| `domain/interfaces.py` | Protocol 선언만 — 실행 로직 없음 (`pyproject.toml` omit). 구조적 서브타이핑은 `test_interfaces.py` 5건으로 검증 |
| `scripts/spike/p0_techspike.py` | 등급 C — 산출물은 `docs/internal/P0_실측기록_Common.md` |
| `frontend/src/App.tsx`·`main.tsx` | 자리 화면(P3 에서 교체). 렌더 테스트 1건으로 파이프라인만 확인 |

## 10. 구현 후 실연동 검증

### 5.1 환경 검사 — `scripts\check_env.ps1`

```powershell
.\scripts\check_env.ps1
```

```
[OK] python — 3.12.10 (venv D:\claude\youtubeLearner\backend\.venv)
[OK] import yt_dlp — yt-dlp 2026.8.19
[OK] import faster_whisper — faster-whisper 1.2.1
[OK] import ctranslate2 — ctranslate2 4.8.2
[OK] import av — av 18.1.0
[OK] import youtube_transcript_api — youtube-transcript-api 1.2.4
[OK] import sqlalchemy — SQLAlchemy 2.0.52
[OK] import pydantic_settings — pydantic-settings 2.15.0
[OK] node — v24.14.0 (C:\Program Files\nodejs\node.EXE)
[OK] bgutil script — D:\claude\youtubeLearner\tools\bgutil-ytdlp-pot-provider\server\build\generate_once.js
[OK] dirs — DATA_DIR=D:\claude\youtubeLearner\data STATUS_DIR=D:\claude\youtubeLearner\status HF_HOME=D:\claude\youtubeLearner\data\models
[WARN] disk — 3.90 GB 여유 (D:\) — 기준 10 GB 미달. 모델 캐시·P4 빌드 공간 확보 필요 (보류 결정 8)
[OK] config stt_default — 8 keys
[OK] config ytdlp_default — 9 keys
[OK] config sync_default — 5 keys
[OK] whisper model cache — Systran--faster-whisper-small
==> READY
exit=0
```

확인 일자 2026-09-14 — 위 출력은 Direct 리뷰 반영(bgutil 을 홈 C: → 저장소 `tools/` D: 로 이동, C: 캐시 정리) **후의 재실행**이다. 첫 실행에서는 bgutil 경로가 `C:\Users\…\bgutil-ytdlp-pot-provider\…` 였고 모델 캐시가 `[WARN]`(없음)이었다; 스파이크가 C: 기본 캐시에 내려받은 `small` 을 `data/models/hub/` 로 옮긴 뒤 `[OK]` 가 됐다(6.4절). 디스크 WARN 은 보류 결정 8(부족 시 D: 증설 — 사용자 결정).

거부 케이스(bgutil 스크립트 경로를 없는 곳으로): `test_check_env.py::TestThisMachine::test_bgutil_removed_makes_not_ready` — 마지막 줄 `==> NOT READY (1 failures)`, 종료 1.

### 5.2 문서 실검사 — `scripts\verify_docs.py`

```powershell
backend\.venv\Scripts\python.exe scripts\verify_docs.py
```

최종 실행 출력(산출물 전부 작성 후, 2026-09-14):

```
  OK  README.md
  OK  CLAUDE.md
  OK  docs\P0_설계서_Common.md
  OK  docs\P0_요구사항정의서_Common.md
  OK  docs\P0_테스트결과서_Common.md
  OK  docs\scope-definition.md
  OK  docs\설계서_Architecture.md
  OK  docs\internal\P0_검토서_SelfReview.md
  OK  docs\internal\P0_검토서_TechSpike.md
  OK  docs\internal\P0_학습가이드_Common.md
  OK  docs\internal\README.md
  OK  docs\internal\검토서_트러블슈팅.md
  OK  docs\internal\설계서_Agents.md
  OK  docs\internal\용어집.md
  OK  docs\internal\templates\README.md
  OK  docs\internal\templates\템플릿_검토서_SelfReview.md
  OK  docs\internal\templates\템플릿_검토서_TechSpike.md
  OK  docs\internal\templates\템플릿_설계서.md
  OK  docs\internal\templates\템플릿_요구사항정의서.md
  OK  docs\internal\templates\템플릿_테스트결과서.md
  OK  docs\internal\templates\템플릿_학습가이드.md

문서 21개 — 위반 없음
exit=0
```

작성 도중의 중간 실행은 **의도대로 위반을 잡았다**: 아직 없던 `docs/internal/P0_실측기록_Common.md`·SelfReview·`history/` 참조 9건과, 설계서 8.1절이 P3 예정 파일 `dev.ps1` 을 실재 경로처럼 적은 1건(6.6절).

### 5.3 프론트 — `npm test` · `npm run build`

```
 ✓ src/lib/time.test.ts (9 tests) 7ms
 ✓ src/lib/api.test.ts (3 tests) 6ms
 ✓ src/App.test.tsx (1 test) 132ms
 Test Files  3 passed (3)
      Tests  13 passed (13)
```
```
> tsc --noEmit -p tsconfig.json && vite build
vite v7.3.6 building client environment for production...
✓ 29 modules transformed.
dist/index.html                  0.33 kB │ gzip:  0.24 kB
dist/assets/index-Bm__X34J.js  223.12 kB │ gzip: 69.80 kB │ map: 1,055.11 kB
✓ built in 1.50s
```
커버리지(`npm run test:coverage`): `api.ts` 100/100/100/100, `time.ts` 100/100/100/100. `node_modules` 155 패키지 102MB.

### 5.4 패키지 설치 — `pip install -e "backend[youtube,stt,dev]"`

```
pydantic                  2.13.5
pydantic-settings         2.15.0
pytest                    8.4.2
pytest-cov                7.1.0
ruff                      0.16.7
SQLAlchemy                2.0.52
youtube-learner           0.1.0     D:\claude\youtubeLearner\backend
```
ruff: `All checks passed!` (line-length 140 — 6.3절).

## 11. 재작업·특이사항

### 6.1 등급 A 는 Red 를 확인한 뒤 Green (구현 순서 기록)

테스트 5파일을 먼저 쓰고 실행: `ModuleNotFoundError: No module named 'youtube_learner.constants'` — `ERROR tests/unit/test_constants.py … test_run_context.py`, `Interrupted: 5 errors during collection`, 종료 2. 구현 후 115 passed. (interfaces 5건은 SelfReview 3절 누락 보강으로 추가.)

### 6.2 `pyproject.toml` `readme = "../README.md"` 로 설치 실패 (구현 중 발견) ⚠️

- 증상: `distutils.errors.DistutilsOptionError: Cannot access 'D:\\claude\\youtubeLearner\\backend\\../README.md' (or anything outside 'D:\\claude\\youtubeLearner\\backend')`
- 조치: `readme` 줄 제거.

### 6.3 ruff 위반 24건 → 줄 길이 기준 140 으로 (구현 중 결정)

E501 23건(한국어 메시지·docstring)·E741 1건. 120 은 의미 없는 줄바꿈을 강요해 **140** 으로 정하고 근거를 `backend/pyproject.toml` 주석에 남겼다. 140 초과 1줄 분할, `l` → `content`.

### 6.4 Whisper `small` 캐시 위치 (조용한 디스크 낭비) ⚠️

TechSpike 는 `HF_HOME` 미설정으로 실행돼 464MB 가 `C:\Users\…\.cache\huggingface` 에 있었고 `check_env` 는 `data/models` 를 보므로 WARN. 캐시를 이동해 재다운로드를 막았다. 기록: `docs/internal/검토서_트러블슈팅.md` T-002, SelfReview 1.4.

### 6.5 `verify_docs` 가 전체 경로 명령을 놓쳤다 — 역테스트가 잡음 ⚠️

`test_detects_missing_project_module` 실패(`assert 'module' in set()`). 원인·조치는 SelfReview 1.2. 커버리지 85% → 인프로세스 테스트 5건 추가 → 97%.

### 6.6 설계서와 구현의 차이 2건 정정

`run_context(run_id=)` 인자, `make_engine` 의 `data_dir` 생성 — 구현이 맞고 문서가 뒤처짐. 설계서 7.1·8.1·8.2절 정정(SelfReview 1.1). 설계서 8.1절 `dev.ps1` 표기도 `verify_docs` 지적으로 수정.

### 6.7 최종 검증 실행 (산출물 전부 작성 후)

아래 9절 명령을 순서대로 실행한 결과(2026-09-14, `backend` 디렉토리에서):

```
== pytest --cov ==
D:\claude\youtubeLearner\scripts\verify_docs.py     275      6    138      7    97%   223-224, 250, 269, 293->301, 302, 406->400, 424
TOTAL                                               879     21    226     11    97%
228 passed in 6.14s

== ruff check src tests ..\scripts\verify_docs.py ==
All checks passed!

== scripts\verify_docs.py ==
문서 21개 — 위반 없음   (exit 0 — 전체 목록은 5.2절)

== scripts\check_env.ps1 ==
==> READY   (WARN 1: disk 3.90 GB — 보류 결정 8)

== frontend ==
Tests 13 passed (13) / ✓ built in 1.50s
```

주의 — 저장소 루트에서 `pytest --rootdir backend backend\tests --cov` 로 돌리면 테스트 결과는 같지만 coverage `source` 의 `../scripts` 가 CWD 기준으로 어긋나 TOTAL 이 1835문(98%)으로 부풀어 보인다. 커버리지는 `backend` 에서 측정한 값만 인정한다.

### 6.8 Direct 리뷰 반영 후 재검증 (2026-09-14)

사용자 지시 3건(디스크 D: 우선·증설, 수동 요약 흐름) 반영 — `docs/internal/P0_실측기록_Common.md` 9절. 코드 변경: `constants.MANUAL_ANALYZER_NAME/VERSION` + 테스트 1건, `Settings.bgutil_script_path` 기본값 `project_root()/tools/…` + 테스트 1건 → **228 passed**, TOTAL 879문 97%, ruff 통과, `check_env` READY(5.1절 재실행 출력), `verify_docs` 문서 21개 위반 0. 이 절의 수치가 최종이다.

## 12. 자체 점검에서 찾은 결함 — 8건 (전부 수정)

### 1.1 🟡 설계서 시그니처와 구현이 어긋났다 (2곳)

- 증상: `P0_설계서_Common` 7.1절 `run_context(stage, settings, logger=None, *, extra=None)` 인데 구현은 `run_id=None` 키워드 인자가 있다(덮어쓰기 거부 테스트에 결정적 run_id 가 필요해 추가). 8.1절은 "`init_db`가 `DATA_DIR`을 만든다"인데 구현은 `make_engine`이 만든다(SQLite 는 부모 디렉토리 없이는 파일을 못 만들고, 엔진 생성이 경로를 처음 아는 지점).
- 원인: 설계서를 쓴 뒤 **테스트를 쓰다가** 필요가 드러났고 그 자리에서 설계서로 돌아가지 않았다. "문서 → 코드" 방향만 챙기고 "코드 → 문서" 역방향을 놓친 전형.
- 조치: 설계서 7.1·8.1·8.2절 정정(정정 사유 표기). 구현이 맞고 문서가 뒤처진 경우라 코드는 그대로.
- 재발 방지: 테스트 작성 중 시그니처를 바꾸면 **같은 커밋에서** 설계서를 고친다 — SelfReview 체크 항목으로 남긴다(2절 표에 "설계서 시그니처 == 구현" 행).

### 1.2 🟡 `verify_docs` 가 전체 경로 명령(`…\python.exe -m …`)을 명령으로 인식하지 못했다

- 증상: 역테스트 `test_detects_missing_project_module` 실패 — `backend\.venv\Scripts\python.exe -m youtube_learner.cli.nope_module` 줄에서 `module` 위반이 나오지 않았다.
- 원인: `command_lines` 가 명령 머리를 `COMMAND_HEADS` 와 비교할 때 `python.exe` 의 `.exe` 접미를 떼지 않았다. 참조 구현은 Linux(`.venv/bin/python`)라 이 분기가 없었다. **이 프로젝트 문서의 표준 표기 자체**가 검사에서 빠지는 심각한 누락이었고, 저장소 전체 검사에서는 "위반 0"으로 보여 조용했다.
- 조치: `head_name.removesuffix(".exe")`. 역테스트 `test_full_path_python_exe_is_a_command` 추가.
- 재발 방지: 역테스트. **"통과만 확인하면 아무것도 검사하지 않는 검사기도 통과한다"** — 요구사항 FR-30(b) 가 이 사고를 위해 있었고 실제로 잡았다.

### 1.3 🟡 `verify_docs.py` 커버리지 85% — 등급 A 기준(90%) 미달

- 증상: `main()` 이 subprocess 로만 실행되어 커버리지에 잡히지 않았고, `strip_comment` 의 따옴표 분기·`Finding.__str__` 의 저장소 밖 경로 분기가 테스트되지 않았다.
- 조치: 인프로세스 테스트 5건(`TestHelpersAndMain` 4 + `TestCommandLines` 1) 추가 → **97%**. `pyproject.toml` coverage `source` 에 `../scripts` 추가(측정 대상에 넣지 않으면 등급 A 선언이 공허하다), `*/spike/*` 는 omit(등급 C).
- 재발 방지: 커버리지 측정 대상 목록 == 요구사항 5절 등급 표. 테스트결과서 3.4절 "측정 제외"에 이유를 적는다.

### 1.4 🟡 Whisper `small` 모델 캐시가 C: 기본 HF 경로에 남아 P2 에서 재다운로드될 상태였다

- 증상: `check_env` → `[WARN] whisper model cache — …\data\models\hub 에 모델 없음`. TechSpike 는 `HF_HOME` 미설정 상태로 실행돼 464MB 가 `C:\Users\…\.cache\huggingface` 에 있었다.
- 원인: 설계(`HF_HOME` = `DATA_DIR/models`)가 TechSpike **이후**에 정해졌다. 조용한 디스크 낭비 유형(T-002 와 같은 뿌리).
- 조치: 캐시 디렉토리를 `data/models/hub/` 로 이동 → `[OK] whisper model cache — Systran--faster-whisper-small`. C: HF 캐시 디렉토리 비움.
- 재발 방지: `check_env` 모델 캐시 항목이 이제 `HF_HOME` 기준으로 본다. P2 진입점은 `apply_process_env()` 를 import 전에 호출(설계서 15절 인계).

### 1.5 🟢 `pyproject.toml` 의 `readme = "../README.md"` 가 설치를 깨뜨렸다

- 증상: `pip install -e` → `DistutilsOptionError: Cannot access '…\\backend\\../README.md' (or anything outside 'backend')`.
- 조치: `readme` 줄 제거. 패키지 설명은 `description` 으로 충분.

### 1.6 🟢 ruff 줄 길이 120 위반 23건 + 모호한 변수명 1건

- 원인: 한국어 메시지·docstring 이 많아 120 이 의미 없는 줄바꿈을 강요했다.
- 조치: `line-length = 140` (근거를 `pyproject.toml` 주석에), 140 초과 1줄 분할, `l` → `content`. 결과 `All checks passed`.

### 1.7 🟢 설계서 8.1절이 P3 예정 스크립트를 실재 경로처럼 백틱으로 적었다

- 증상: `verify_docs` → `[bare-path] docs\설계서_Architecture.md:276 scripts/dev.ps1`.
- 조치: 문구를 "P3 에서 `scripts/` 아래에 추가한다"로. **검사기가 설계 의도(미래 파일)와 오류(오타)를 구분할 수 없으므로 표기 규칙으로 해결** — 미래 파일은 백틱 대신 코드펜스 트리나 평문.

### 1.8 🟢 요구사항정의서 초안 오기 2건

- FR 범위 "FR-1~35" → 실제 34건. FR-32 의존성 목록에 `python-json-logger` 가 있었으나 설계 판단(6.2절)으로 제거 → 요구사항을 정정(초안 단계라 정정 이력 없이 본문 수정, 변경 사유는 설계서 6.2절에).

## 13. 요구사항 누락 점검

| FR | 검증 존재 | 거부 케이스 | 판정 |
|---|---|---|---|
| FR-1~5 (config) | ✅ `test_config.py` 27건 | ✅ 잘못된 값 6종, `_comment` 없음, 비객체 | OK |
| FR-6~8 (constants) | ✅ 34건 | ✅ 빈 키·접미사만·미지 값 | OK |
| FR-9~15 (models) | ✅ 45건 | ✅ 패턴·빈 제목·음수·시간 역행·idx 불연속·frozen·extra | OK |
| FR-16 (Protocol 4종) | ❌→✅ | — | **누락 발견**: `NullAnalyzer` 로 `Analyzer` 만 검증했고 나머지 3종은 테스트가 없었다. `test_interfaces.py` 5건 추가(fake 만족 + 멤버 누락 객체 거부) |
| FR-17 (exceptions) | ✅ 15건 | — (거부 대상 없음) | OK |
| FR-18~19 (logging) | ✅ 9건 | ✅ 예약 키 충돌 | OK |
| FR-20~21 (run_context) | ✅ 15건 | ✅ 덮어쓰기·stage 패턴 | OK |
| FR-22~23 (db) | ✅ 5건 | — | OK (거부 대상 없음) |
| FR-24~25 (analysis) | ✅ 6+7건 | ✅ 중복·비Analyzer·미구현 이름 | OK |
| FR-26~27 (check_env) | ✅ 25건 + 실행 출력 | ✅ 버전·venv·Node 없음/구버전·스크립트 없음·설정 없음 | OK |
| FR-28~30 (verify_docs) | ✅ 33건 | ✅ 7종 역테스트 + 오탐 방지 6종 | OK |
| FR-31 (frontend) | ✅ 13건 | ✅ 음수·NaN·Infinity | OK |
| FR-32~34 (패키징·설정) | ✅ 간접(설치 성공·`_comment`·키 대조) | ✅ | OK — pytest 마커 `-m 'not e2e'` 는 수동 확인(e2e 0건이라 판별 불가, P2 에서 실증) |

## 14. 완료 기준 대조 (설계서 22절)

- [x] FR-1~34 전건에 대응하는 테스트가 존재하고 통과한다 — 4절
- [x] 등급 A ≥ 90% (98.8%), B ≥ 70% (95.6%), A+B ≥ 80% (97.5%) — 3절
- [x] `.\scripts\check_env.ps1` 마지막 줄 `==> READY`, 종료 0 — 5.1절
- [x] bgutil 스크립트를 없는 경로로 바꾸면 `[FAIL]`·`NOT READY` — `test_bgutil_removed_makes_not_ready`
- [x] `scripts\verify_docs.py` 종료 0, pytest 포함 — 5.2절·6.7절, `test_all_docs_pass_verification`
- [x] 검사 7종 역테스트 통과 — `test_docs.py` 33건
- [x] `frontend`: `npm test` 13 passed, `npm run build` 성공 — 5.3절
- [x] `build_registry` `available()` 빈 목록, `get("summary")` → `AnalyzerNotConfiguredError` — `TestBuildRegistry`
- [x] 상태 파일 덮어쓰기 `OutputExistsError`; 예외 시 `failed` 기록 후 재전파 — `TestRunContext`
- [x] `.env.example` 키 집합 == `Settings` 필드 집합 — `TestEnvExample`
- [x] `backend/config/*.json` 3종 `_comment` 보유, 로더 통과 — `TestJsonConfig`, 5.1절
- [x] 모듈·테스트 docstring 첫 줄 규약 전 파일 — 수동 대조(SelfReview 2절 12항; 기계 검사는 P1 보류 후보)
- [x] `scripts/verify_docs.py` 종료 0 — 6.7절

## 15. 남은 위험

| # | 위험 | 왜 지금 못 닫나 | 드러나는 시점 | 감지 방법 |
|---|---|---|---|---|
| 1 | `verify_docs` 휴리스틱(`COMMAND_HEADS` 목록, `-0` 예외, 자리표시자 문자) — 새 명령 형태에서 오탐·누락 | 문서가 늘어야 사례가 나온다 | 매 Phase | 위반이 나오면 역테스트 추가 후 규칙 수정 |
| 2 | `check_env` 가 YouTube 차단 상태를 못 본다 | 의도된 범위(READY 가 외부 상태에 흔들리지 않게) | P2 | 작업 실패 카운트(P2 설계) |
| 3 | `Settings` 가 `.env` 를 **현재 디렉토리**에서 읽는다 — 데스크톱 앱(P4)은 실행 디렉토리가 다르다 | 사이드카 실행 방식이 P4 에서 정해진다 | P4 | P4 TechSpike: 사이드카 CWD 확인, 필요 시 `env_file` 을 `resource_root()` 기준으로 |
| 4 | pydantic frozen 모델 ↔ SQLAlchemy ORM 변환 비용·중복 정의 | 첫 테이블이 P1 | P1 | P1 설계서에 변환 함수 위치 명시 |
| 5 | 디스크 여유 C 4.78 / D 3.90GB — P1·P2 오디오 캐시·모델 프리셋이 들어갈 자리가 없다 | **사용자 결정(2026-09-14): 부족하면 D: 증설** — 시점은 P4 전, 조기 트리거는 P2 모델 2개 보유 | P2 벤치마크 | `check_env` disk WARN, 보류 결정 8 |
| 6 | docstring 첫 줄 규약(대응 절·FR·등급)을 사람이 대조했다 | 기계 검사 규칙(정규식)이 아직 없다 | P1 부터 파일이 늘 때 | P1 보류 후보: `verify_docs` 에 docstring 검사 추가 |

## 16. Direct 리뷰 반영 (2026-09-14~15)

| # | 사용자 지시·결정 | 반영 |
|---|---|---|
| 1 | "로컬 디스크를 사용할 때는 항상 D 드라이브를 우선" | `CLAUDE.md` 7절 규칙. bgutil 을 홈(C:)→저장소 `tools/`(D:, git 미추적), `Settings.bgutil_script_path` 기본 `project_root()/tools/…`(+테스트), `.env.example`·README·Architecture 3.2·요구사항 FR-1·설계서 3.1/3.2 정정, pip/npm 캐시 `D:\claude\.cache\`, C: 캐시(pip 116MB·npm 321MB·HF) 삭제 → C 4.78GB |
| 2 | "디스크가 필요하면 D 드라이브를 증설" | 보류 결정 8 판정 재료로 기록(scope 8.1, `CLAUDE.md` 1절). 정리 대상은 `data/audio` 캐시만 남음 |
| 3 | "스크립트 원클릭 복사 + 외부 AI 요약을 붙여 넣는 '요약 및 정리' 메뉴와 저장" | scope **v2**(1·2.3·2.4·2.5·6·7·9절), `CLAUDE.md` 0절, Architecture 4절 흐름·5.2절, `constants.MANUAL_ANALYZER_NAME/VERSION`(+테스트), 요구사항 FR-7·설계서 1.1/9.2, 용어집·학습가이드. 구현은 P3(화면·API), 스키마는 P1 |

원문·문답은 `docs/internal/qa/P0_질의응답_초기요구.md`, `docs/internal/qa/P0_질의응답_디스크와수동요약.md`. 반영 후 `doc-consistency` 2회차(opus)를 돌린다 — `설계서_Agents` 5절.

## 17. 다음 Phase 인계 사항

| 항목 | 내용 | 받는 Phase |
|---|---|---|
| `Settings.apply_process_env()` 호출 계약 | faster-whisper import **전에** 진입점이 호출 | P2 |
| `Base` 빈 스키마 | 첫 테이블(`channels`·`videos`·`analyses`)·Alembic 초기 리비전. `analyses` 는 P3 수동 저장(`manual`)이 바로 쓴다. `VideoStub`/`Video` ↔ ORM 변환은 저장소 계층 | P1 |
| `build_registry` 미구현 이름 예외 | 이름→팩토리 표로 대체 | P5 |
| `resource_root()` frozen 분기·`.env` 탐색 위치(CWD) | 사이드카 실행 디렉토리 확인 후 `env_file` 기준 결정 | P4 |
| `check_env` 디스크 기준 10GB(임시)·모델 캐시 위치 | P4 빌드 실측 후 갱신 (보류 결정 8) | P4 |
| `verify_docs` docstring 규약 기계 검사 | 파일이 늘기 전에 규칙 추가 (P1 보류 후보) | P1 |
| P1 TechSpike 질문 | 채널 전량 페이지네이션·숏폼 100+·메타 보충 속도·`curl_cffi` 효과 (`P0_검토서_TechSpike` 6절) | P1 |

## 18. 착수 전 실측 재실행

```powershell
# 사전: backend\.venv 에 패키지 설치, tools\bgutil-ytdlp-pot-provider\server 빌드 (T-001·T-004 — 검증 당시엔 홈 디렉토리였다, 3.3절)
$env:PYTHONUTF8 = "1"
.\backend\.venv\Scripts\python.exe scripts\spike\p0_techspike.py --channel https://www.youtube.com/@sebasi15 --limit 60 --model small --threads 2 --out data\spike
```

기대값: 종료 코드 0, 소요 약 2분(모델 다운로드 제외), 산출 `data/spike/spike_result.json`·`data/spike/subs/*.json3`·`data/spike/audio/*.m4a`. 채널 업로드가 늘면 대상 영상 id와 건수는 바뀐다 — 바뀐 값은 3절 값과 나란히 기록한다.

## 19. 검증 재현 명령

```powershell
.\scripts\check_env.ps1
Push-Location backend
.\.venv\Scripts\python.exe -m pytest --cov --cov-report=term
.\.venv\Scripts\python.exe -m ruff check src tests ..\scripts\verify_docs.py
Pop-Location
backend\.venv\Scripts\python.exe scripts\verify_docs.py
Push-Location frontend; npm test; npm run build; Pop-Location
```

기대값: READY(종료 0) / 228 passed, TOTAL 97% / All checks passed / 문서 21개 — 위반 없음(종료 0) / 13 passed, built. 소요 약 2분(프론트 빌드 포함).
pytest 는 **`backend` 디렉토리에서** 실행한다 — coverage `source` 의 `../scripts` 가 그 디렉토리 기준이다(6.7절).
