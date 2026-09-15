# P0 검토서 — 기술 검증 (TechSpike)

- 검증일: 2026-09-14 / 작성 LLM: Fable 5.1 / 브랜치: `impl-phase0`
- 규칙: `CLAUDE.md` 1절 1단계(요구사항 도출) 안에서, **작업 프롬프트 작성 전에** 수행. 내부 자료(9절 경계 — 제출물 아님)
- 대응 산출물: `docs/prompts/phase0/scope-and-common-modules-v1.md` (이 검증의 사실이 완료 기준·설계 제약에 들어간다)
- 결론: 핵심 경로(탭 목록 → 원어 자막 json3 → 자막 없으면 m4a 오디오 → CPU Whisper)는 **이 VM에서 전부 실제로 동작했다.** 단 (1) 숏폼 flat 목록에 `duration`이 없고 두 탭 모두 `upload_date`가 없어 **영상별 메타 보충 단계가 필수**, (2) 원어가 아닌 언어 자막은 번역 엔드포인트로 가서 **HTTP 429**를 맞으므로 **원어 트랙(`<lang>-orig`)만 받는 설계**가 필요, (3) PO 토큰 제공자(bgutil)는 pip 설치만으로는 안 되고 **Node 서버 디렉토리를 빌드**해야 동작, (4) 이 VM은 물리 코어 1개·디스크 여유 각 5GB 미만이라 **모델 크기·캐시 위치가 설계 제약**이다.

## 1. 검증 질문

| # | 질문 | 왜 지금 확인해야 하나 |
|---|---|---|
| Q1 | yt-dlp가 `/videos`·`/shorts` 탭을 분리해 목록화하는가. flat 결과에 어떤 필드가 오는가 | P1 완료 기준(전량 목록화)과 데이터 모델(어느 필드를 flat에서, 어느 필드를 영상별 조회에서 얻나) |
| Q2 | 자막을 영상 다운로드 없이 json3로 받을 수 있는가. 수동/자동/원어/번역을 구분할 수 있는가 | P2 Provider 체인의 1순위 설계 |
| Q3 | PO 토큰 요구(yt-dlp #14307)가 이 환경에서 자막·오디오에 실제로 영향을 주는가. bgutil 제공자는 어떻게 동작하는가 | 배포 시 동봉해야 할 구성요소 결정 |
| Q4 | ffmpeg 없이 오디오만 받을 수 있는가 | 설치파일에 ffmpeg 바이너리를 넣을지 결정 |
| Q5 | faster-whisper가 CPU 전용·물리 코어 1개 VM에서 얼마나 빠른가 | STT 전략(자막 우선 정책의 강도)과 기본 모델(보류 결정 2) |
| Q6 | youtube-transcript-api가 이 네트워크(사내 IP)에서 동작하는가 | 2순위 폴백 채택 여부 |
| Q7 | 실행 환경(CPU·RAM·디스크·네트워크·도구)의 실측값 | scope-definition 8절 실행 환경, 설계 제약 |

## 2. 방법

| 항목 | 값 |
|---|---|
| 스크립트 | `scripts/spike/p0_techspike.py` (등급 C) + 아래 3절의 개별 명령 |
| 대상 | 공개 채널 `https://www.youtube.com/@sebasi15` (세바시 강연 Sebasi Talk, `UCgheNMc3gGHLsT-RISdCzDQ`). 롱폼·숏폼이 모두 많은 한국어 채널이라 선택 |
| 환경 | Windows Server 2022 (10.0.20348), Python 3.12.10 (`backend\.venv`), Node v24.14.0, yt-dlp 2026.08.19, yt-dlp-ejs 0.8.0, bgutil-ytdlp-pot-provider 2.0.0, faster-whisper 1.2.1, ctranslate2 4.8.2, av 18.1.0, onnxruntime 1.30.0, youtube-transcript-api 1.2.4 |
| 하드웨어 | Intel Xeon (Icelake) **물리 코어 1 / 논리 2**, RAM 16GB, GPU 없음(Microsoft Basic Display Adapter), 디스크 여유 **C: 4.6GB / D: 4.7GB** (검증 시작 시점) |
| 네트워크 | 사내 고정 IP(AS45985 SamsungSDS, Incheon), 프록시 환경변수 없음. `www.youtube.com` HTTP 200 (1.5s), `huggingface.co` 200, `pypi.org` 200 |
| 실행 명령 | 7절 |

## 3. 실측 결과 — 실제 출력 복사

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

## 4. 문서·예상과 달랐던 것

| # | 예상(문서·기획) | 실제 | 영향 | 기록 |
|---|---|---|---|---|
| 1 | flat 목록에 길이·업로드일이 온다 | 숏폼은 `duration` 없음, 두 탭 모두 `upload_date` 없음 | P1에 **메타 보충 단계** 필수. "목록만으로 정렬·필터"는 불가 | 설계 반영(5절) |
| 2 | 자막 언어 우선순위 `ko→en→any`로 요청하면 된다 | 원어 외 언어는 번역 요청이 되어 **429**. 한 언어 실패 시 yt-dlp 명령 전체 실패 | 원어 트랙만 요청, 언어별 분리 요청, 번역은 옵션 | 설계 반영(5절) |
| 3 | PO 토큰 제공자는 pip 설치로 동작 | Node 서버 디렉토리 빌드 필요. HTTP 모드 미기동 시 경고 반복 | 배포물에 `generate_once.js` 동봉 + 설정 명시 필요 | `검토서_트러블슈팅.md` T-001 |
| 4 | CPU Whisper는 실시간의 0.3~1배로 느릴 것 | small int8: **3.05배** | 자막 없는 영상도 배치 처리 현실적. 다만 모델 크기별 재측정(3.6절) | — |
| 5 | 기획 시 CPU 코어 수 미확인 | **물리 코어 1개** | `cpu_threads` 기본값 2, 동시 STT 작업 1개 고정 | 설계 반영 |
| 6 | 디스크 여유 충분 | C·D 각 5GB 미만 | 모델 캐시 위치 설정 필수(`HF_HOME`), 대형 모델 동시 보유 불가, P4 Rust 툴체인 설치 전 **증설/정리 필요** | 보류 결정 등재 후보 |
| 7 | 롱/숏 판정에 길이 기준 보조 필요할 수도 | 롱폼 탭에 42초 영상 존재 | **탭 소속만**이 기준. 길이 기준은 쓰지 않는다 | 보류 결정 3 종료 근거 |

## 5. 설계·프롬프트에 반영할 것

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

## 6. 미확인 사항

| 항목 | 왜 지금 못 확인했나 | 확인 시점 |
|---|---|---|
| 채널 **전량**(수천 건) 목록화 시 페이지네이션·속도·차단 여부 | 60건 제한으로 실행. 전량은 P1 대상 | P1 TechSpike |
| 숏폼 탭 100건 초과 페이지네이션(yt-dlp #11130은 플레이리스트 문제, 탭은 정상이라는 보고) | 동일 | P1 TechSpike |
| 원어 자막 요청도 대량 반복 시 429가 나는가(간격·건수 한계) | 단발 요청만 실행 | P2 TechSpike(연속 30건) |
| `curl_cffi` 임퍼서네이션 설치 효과 | 경고만 관측, 실패는 없었음 | P1 (차단 발생 시 즉시) |
| PO 토큰 없이도 되는 상태가 언제까지 유지되나 | YouTube 실험 중 | 상시 — 제공자를 기본 구성으로 둔다 |
| medium 모델 속도·정확도 | 디스크 여유 부족으로 turbo만 추가 측정 | P2 벤치마크(보류 결정 2) |
| Whisper 한국어 품질 정량 비교(자막 있는 영상으로 WER) | 기준 자막 정규화 코드가 없음 | P2 |

## 7. 재실행 (요약)

```powershell
# 사전: backend\.venv 에 패키지 설치, tools\bgutil-ytdlp-pot-provider\server 빌드 (T-001·T-004 — 검증 당시엔 홈 디렉토리였다, 3.3절)
$env:PYTHONUTF8 = "1"
.\backend\.venv\Scripts\python.exe scripts\spike\p0_techspike.py --channel https://www.youtube.com/@sebasi15 --limit 60 --model small --threads 2 --out data\spike
```

기대값: 종료 코드 0, 소요 약 2분(모델 다운로드 제외), 산출 `data/spike/spike_result.json`·`data/spike/subs/*.json3`·`data/spike/audio/*.m4a`. 채널 업로드가 늘면 대상 영상 id와 건수는 바뀐다 — 바뀐 값은 3절 값과 나란히 기록한다.
