# Scope Definition — youtubeLearner

- 작성일: 2026-09-14 / 작성 LLM: Fable 5.1
- 사용 프롬프트: `docs/prompts/phase0/project-plan-v1.md` (승인된 기획서), `docs/prompts/phase0/scope-and-common-modules-v1.md`
- 선행 검증: `docs/internal/P0_검토서_TechSpike.md` (2026-09-14 실측)
- 규칙: 이 문서는 **무엇을/왜**만 답한다. **어떻게**는 `docs/설계서_Architecture.md`, **어떤 규칙으로**는 `CLAUDE.md` (경계 규약은 설계서 0절)
- 상태: v1 — Phase 0 진행 중 (`impl-phase0`)

## 1. 프로젝트 개요

**youtubeLearner**는 사용자가 고른 유튜브 채널의 **롱폼·숏폼 영상 목록**과 각 영상의 **전체 스크립트**를 확보해 학습 자료로 쓰게 하는 프로그램이다.
스크립트는 유튜브가 제공하는 자막을 우선 쓰고, 자막이 없으면 **오디오를 받아 로컬 음성 인식(faster-whisper)** 으로 만든다.

- **왜 만드나**: 채널 단위로 "무엇을 말했나"를 텍스트로 쌓아 두면 검색·복습·요약이 가능하다. 유튜브 UI는 채널 전체를 텍스트로 보는 수단이 없다.
- **누가 쓰나**: 개발자 본인(단일 사용자). 이후 가족·동료용 배포를 배제하지 않지만 v1의 설계 기준은 아니다.
- **어떤 형태로**: 로컬 웹앱(P3) → Windows 데스크톱 앱(P4) → 스마트폰 앱(P6). 무거운 작업(STT)은 항상 PC/서버 쪽 API 서버가 하고, 클라이언트는 화면만 맡는다.
- **무엇을 미루나**: **요약·핵심 도출은 v1에서 만들지 않는다.** 대신 붙일 자리(분석 슬롯 — 2.4절)만 만든다. 스크립트 추출을 완성해 배포한 뒤(P4) 붙인다(P5).

## 2. 기능 정의

### 2.1 채널 선택

| 입력 형태 | 예 | 처리 |
|---|---|---|
| 핸들 URL | `https://www.youtube.com/@sebasi15` | 그대로 사용 |
| 핸들 | `@sebasi15` | URL로 정규화 |
| 채널 ID / 채널 URL | `UCgheNMc3gGHLsT-RISdCzDQ`, `/channel/UC…` | 그대로 사용 |
| 영상 URL | `https://www.youtube.com/watch?v=…` | 영상의 채널로 해석 (P1에서 지원 여부 확정) |

채널의 **정체성은 `yt_channel_id`(UC…)** 다. 핸들은 바뀔 수 있으므로 표시용으로만 저장한다 (TechSpike 3.1절: flat 목록 응답에 `channel_id`가 온다).

### 2.2 영상 목록 — 롱폼과 숏폼을 분리

| 구분 | 출처 | 판정 기준 |
|---|---|---|
| 롱폼 (`long`) | 채널 **Videos 탭** (`/@handle/videos`) | 탭 소속 |
| 숏폼 (`short`) | 채널 **Shorts 탭** (`/@handle/shorts`) | 탭 소속 |
| 라이브 (`live`) | Streams 탭 (`/streams`) | v1 목록 대상 아님 — 값만 예약 (9절) |

**길이로 판정하지 않는다.** 롱폼 탭에 42초 영상이 실재하고(TechSpike 3.1절) 숏폼은 최대 3분까지 올라온다. 두 탭에 같은 영상이 나오는 사례는 상위 60건 기준 0건이었다 — 전량에서 겹침이 나오면 P1에서 규칙을 정한다.

목록은 두 단계로 얻는다 (TechSpike 3.1·3.2절):

1. **flat 목록** — 탭당 한 번의 페이지 순회. `id`·`title`·`thumbnails`·`view_count`·(롱폼만)`duration`. 60건에 2.4초.
2. **영상별 메타 보충** — flat에 없는 `duration`(숏폼)·`upload_date`·`language`·`live_status`·자막 트랙 목록. 영상당 1회 요청. **증분**으로 한다(이미 보충된 영상은 건너뜀).

동기화는 **증분**이다: 최신순 순회 중 이미 알고 있는 id에 닿으면 멈춘다. 전체 재스캔은 명시적 옵션. 채널당 수천 건까지 같은 방식으로 늘어나야 한다 (완료 판정은 6절).

### 2.3 스크립트 (전체 텍스트 + 타임스탬프)

스크립트는 **세그먼트 목록**(시작 ms, 끝 ms, 텍스트)이다. 전체 텍스트는 세그먼트를 이어 붙여 만든다(저장도 하지만 파생물이다).

확보 순서 (5절 상세):

| 순위 | 소스(`source`) | 조건 |
|---|---|---|
| 1 | `manual` | 업로더가 올린 자막 (yt-dlp `subtitles[<lang>]`) |
| 2 | `auto` | 유튜브 자동 생성 **원어** 자막 (`automatic_captions[<lang>-orig]`) |
| 3 | `whisper` | 1·2가 없거나 실패 → 오디오(m4a) 다운로드 → faster-whisper (CPU) |

모든 스크립트 레코드는 **어디서 어떤 버전으로 만들었는지**(`source`, `language`, `engine`, `model_name`, `pipeline_version`)를 함께 저장한다. 규칙이 바뀌면 "다시 만들어야 할 것"을 기계로 고를 수 있어야 한다.

### 2.4 분석 슬롯 (v1은 자리만)

요약·핵심 도출·챕터 나누기 같은 **분석(analysis)** 은 P5에서 붙인다. v1이 미리 만들어 두는 것:

| 요소 | v1 상태 |
|---|---|
| `Analyzer` 인터페이스(Protocol) | 정의 (P0) |
| 분석기 레지스트리 | `NullAnalyzer`만 등록 (P0) |
| `analyses` 테이블 | 스키마 예약 (P1에서 생성) |
| API `GET /analyzers`, `POST /videos/{id}/analyses` | 목록은 빈 값, 생성은 `501 Not Implemented` + 사용 가능 분석기 목록 (P1~P3) |
| 화면 "분석" 탭 | "설정된 분석기가 없습니다" 안내 (P3) |

분석기 후보는 추출식(TextRank류) / 로컬 LLM(Ollama) / Claude API이며 **선택은 P5 착수 시**(보류 결정 1). 어느 것을 골라도 `analysis/` 패키지 밖 코드를 고치지 않아야 한다 — 이것이 슬롯의 완료 기준이다.

### 2.5 사용자 화면

| 단계 | 형태 | 핵심 화면 |
|---|---|---|
| P3 | 로컬 웹앱 (브라우저) | 채널 추가·동기화 / 롱폼·숏폼 탭 그리드 / 스크립트 뷰어(타임스탬프 클릭 → 영상 위치) / 작업 모니터 / 설정 / 분석 탭(자리) |
| P4 | Windows 데스크톱 앱 | 같은 화면. 백엔드를 사이드카로 동봉해 설치파일 하나로 |
| P6 | 스마트폰 앱 | 같은 화면. PC/서버의 API에 접속 (STT는 폰에서 하지 않는다) |

## 3. 외부 서비스

### 3.1 YouTube — yt-dlp로 접근

공식 API를 쓰지 않는다(3.6절). yt-dlp(2026.08.19)가 목록·메타·자막·오디오를 모두 처리한다. **문서가 아니라 실측으로 확인한 사실**(2026-09-14, TechSpike 3절):

| 기능 | 확인한 사실 | 절 |
|---|---|---|
| 탭 목록 | `/videos`·`/shorts` 분리. flat 60건/2.4초. 숏폼 flat에 `duration` 없음, 두 탭 `upload_date` 없음, `playlist_count` 없음 | 3.1 |
| 영상 메타 | 영상별 1회 요청에 `duration`·`upload_date`·`language`·`live_status`·자막 트랙 목록이 함께 옴 | 3.2 |
| 자막 | `--skip-download`로 json3 수신. 원어 자동자막은 `<lang>-orig`. **다른 언어는 번역 요청이 되어 HTTP 429**. 한 언어 실패 시 yt-dlp 명령 전체가 종료 코드 1 | 3.2 |
| 오디오 | `bestaudio[ext=m4a]/bestaudio` 후처리 없음 → **ffmpeg 바이너리 불필요**. 140초에 2.3MB, 6.2초 | 3.4 |
| JS 런타임 | Node 24가 `--js-runtimes node`로 인식됨. Deno 불필요 | 3.3 |
| 임퍼서네이션 | `curl_cffi` 미설치 경고. 실패는 없었음 — 차단 발생 시 P1에서 도입 판단 | 3.3 |

### 3.2 PO 토큰 제공자 — bgutil-ytdlp-pot-provider

YouTube가 웹 클라이언트 요청에 PO 토큰을 요구하기 시작했다(yt-dlp #14307). 제공자 플러그인 2.0.0은 **pip 패키지 + Node ≥ 20 + 빌드된 `server/build/generate_once.js`(스크립트 모드)** 로 동작함을 확인했다(TechSpike 3.3절). 제공자 없이도 이날은 자막·오디오가 받아졌지만 "PO Token을 video ID에 묶는 실험 감지" 로그가 떴다 → **기본 구성으로 둔다.** HTTP 모드(`127.0.0.1:4416`)는 서버 미기동 시 경고를 반복하므로 스크립트 경로를 명시하고 HTTP 제공자를 끈다.

### 3.3 youtube-transcript-api (폴백)

비공식 엔드포인트를 쓰는 라이브러리(1.2.4). 사내 IP에서 동작(1.6초, TechSpike 3.7절). 수동/자동 구분(`is_generated`)을 준다. yt-dlp 자막 경로가 막힐 때의 **2순위**. 클라우드 IP 차단 사례가 많아 1순위로는 두지 않는다.

### 3.4 Hugging Face Hub (모델 다운로드)

faster-whisper 모델(CTranslate2 변환본)을 최초 사용 시 내려받는다. small 464MB, large-v3-turbo 1.6GB. Windows에서 HF 캐시가 심볼릭 링크를 못 써 **공간을 더 쓴다** → 캐시 위치는 우리가 정한다(`HF_HOME`, 8절).

### 3.5 실측으로만 알 수 있었던 것

- 번역 자막 429, 숏폼 flat `duration` 부재, `playlist_count` 부재, 롱폼 탭의 42초 영상, bgutil 빌드 필요, DASH m4a 경고와 PyAV 디코딩 성공, Whisper small 3.05x / turbo 0.86x.
  전부 문서에 없거나 문서와 다른 것이다. **외부 서비스 동작은 Phase마다 프롬프트 작성 전에 다시 실측한다** (`CLAUDE.md` 1절 1단계).

### 3.6 쓰지 않는 것 (v1)

| 대상 | 이유 | 재검토 트리거 |
|---|---|---|
| YouTube Data API v3 | API 키·할당량 관리가 필요하고 자막·오디오는 어차피 못 준다 | yt-dlp 목록 경로 차단 시 (보류 결정 7) |
| 클라우드 STT / LLM API | 사용자 결정: 로컬·무료·데이터 외부 유출 없음 | P5 분석기 선택 시 Claude API는 후보 |
| ffmpeg 바이너리 동봉 | 오디오 다운로드·디코딩에 불필요함을 확인 | MP3/WAV 변환 기능이 필요해질 때 |

## 4. 데이터 모델과 보존 원칙

### 4.1 엔터티

| 엔터티 | 자연키 | 핵심 필드 | 생성 Phase |
|---|---|---|---|
| `channels` | `yt_channel_id` | handle, title, thumbnail_url, last_synced_videos_at, last_synced_shorts_at | P1 |
| `videos` | `yt_video_id` | channel_id, **kind**(long/short/live), title, duration_s, upload_date, language, view_count, thumbnail_url, live_status, metadata_fetched_at, transcript_status | P1 |
| `transcripts` | (video_id, source, language, model_name, pipeline_version) | engine, is_primary, full_text, created_at | P2 |
| `transcript_segments` | (transcript_id, idx) | start_ms, end_ms, text | P2 |
| `jobs` | id | type, payload, status, priority, attempts, error, progress, timestamps | P2 |
| `analyses` | (video_id, analyzer_name, analyzer_version, kind) | content(JSON), model_info, created_at | 예약 — P1에 스키마, P5에 데이터 |

기록 원본(system of record)은 **SQLite** 한 파일이다. 파일 산출물(4.3절)은 원본 보존·재생성용이다.

### 4.2 자연키와 멱등성

`yt_video_id`·`yt_channel_id`가 자연키다. 같은 동기화를 두 번 돌려도 행이 늘지 않아야 하고, 같은 영상의 같은 (source, language, model, pipeline_version) 스크립트는 한 번만 만든다. 이미 있고 버전이 같으면 **건너뛴다** (`CLAUDE.md` 6절).

### 4.3 파일 산출물 (`DATA_DIR` 아래)

```
data/
├── youtube_learner.db                      # 기록 원본 (SQLite, WAL)
├── channels/<yt_channel_id>/
│   ├── captions/<yt_video_id>.<lang>.json3 # 유튜브 자막 원본 — 보존
│   ├── audio/<yt_video_id>.m4a             # STT 입력 캐시 — 삭제 가능(재다운로드)
│   └── whisper/<yt_video_id>.<model>.json  # Whisper 원출력(세그먼트·확률) — 보존
├── models/                                 # HF_HOME (Whisper 모델 캐시)
└── spike/                                  # 기술 검증 산출물 (git 미추적)
status/<stage>_<run_id>.json                # 실행 기록 (CLAUDE.md 6절)
```

### 4.4 보존 원칙

- **원본은 변형하지 않는다.** 자막 json3와 Whisper 원출력은 그대로 두고, 정규화(공백·특수문자·병합)는 DB의 세그먼트/전체 텍스트에만 적용한다. 정규화 규칙이 바뀌면 원본에서 다시 만든다.
- **하류를 직접 고치지 않는다.** 방향은 `원본 파일 → DB 세그먼트 → 전체 텍스트 → [분석]` 한쪽이다. 수정은 항상 상류에서.
- **버전 동반 저장.** 스크립트 레코드는 `pipeline_version`·`model_name`을 들고 다닌다. 재생성 대상 판정은 이 값으로 한다.
- 오디오 캐시는 **유일하게 삭제 가능한 산출물**이다(디스크 제약, 8절). 삭제 후에도 DB·원출력만으로 화면은 완전해야 한다.

### 4.5 인코딩·키 규칙

UTF-8(BOM 없음), LF. JSON·DB **키는 영문 ASCII**, 값은 원문(한국어) 그대로.

## 5. 스크립트 확보 전략

### 5.1 우선순위 체인

`manual(<lang>) → auto(<lang>-orig) → [폴백 라이브러리 → manual/auto] → whisper`

- 1·2순위는 yt-dlp json3. 2순위의 원어 판정은 트랙 키 접미사 **`-orig`** 다(TechSpike 3.2절).
- yt-dlp 자막 경로가 실패(429·차단·형식 변경)하면 youtube-transcript-api로 같은 것을 다시 시도한다.
- 모두 없으면 Whisper. Whisper 결과는 자막이 나중에 생겨도 지우지 않는다(레코드가 별개).

### 5.2 언어 정책

- **기본은 원어 하나.** 영상의 `language`(yt-dlp 메타)를 원어로 보고, 그 언어의 수동 → 원어 자동 트랙만 받는다. 사용자 선호 언어 목록(기본 `["ko"]`)은 **원어가 여러 후보일 때의 우선순위**다 — 없는 언어를 만들어 달라는 뜻이 아니다.
- **번역 트랙은 기본 꺼짐.** 켜면 언어별로 **따로** 요청하고 429는 지수 백오프한다. 한 언어의 실패가 다른 언어·다른 영상 작업을 실패시키지 않는다.
- Whisper는 `language`가 있으면 고정, 없으면 자동 감지. 다국어 채널 확장은 이 규칙 안에서 된다(`LANG_PRIORITY`에 언어 추가).

### 5.3 STT 전략 (CPU 전용)

| 항목 | 결정 | 근거 |
|---|---|---|
| 엔진 | faster-whisper (CTranslate2, int8) — `SttEngine` 뒤에 둬 whisper.cpp 등으로 교체 가능 | TechSpike 3.5·3.6절 |
| 기본 모델 | **small** (물리 코어 1개에서 3.05x 실시간). medium·large-v3-turbo(0.86x)는 프리셋 | 보류 결정 2 — P2에서 정량 비교 후 확정 |
| 스레드 | 논리 코어 수(개발 VM 2) | |
| 동시성 | STT 작업 **1개**. 네트워크 작업과 큐 분리 | CPU 1개, 차단 위험 |
| VAD | 켬(Silero 내장) — 무음 구간 제거 | |
| 운영 방식 | 자막 있는 영상은 Whisper를 돌리지 않는다(**자막 우선**). Whisper는 큐에 쌓아 배치로 | |

### 5.4 차단·레이트리밋 대응 원칙

- 네트워크 작업은 **워커 1개**, 요청 간 1~3초 지터.
- 429·차단은 실패가 아니라 **대기 후 재시도**. 재시도 상한 후 작업을 `failed`로 두고 사용자에게 보인다.
- yt-dlp 버전은 고정하되 설정에서 갱신할 수 있게 한다(YouTube 변경이 잦다).
- 실패 유형별 카운트를 남겨 "차단이 시작됐다"를 기계가 알아채게 한다(P2).

## 6. 성공 기준

### 6.1 제품 v1 (P4 완료 시점)

Python·ffmpeg·Node가 없는 **깨끗한 Windows PC**에서 설치파일 하나로 설치 → 채널 1개 추가 → 롱폼·숏폼 목록 전량 → 자막 있는 영상은 즉시, 없는 영상은 Whisper로 스크립트 열람 → 분석 탭에 "설정된 분석기 없음" 안내가 보인다.

### 6.2 Phase별 기계 판정

| Phase | 판정 |
|---|---|
| 0 | `scripts/check_env.ps1` → `==> READY`; `pytest` 통과(A ≥ 90%, B ≥ 70%); `scripts/verify_docs.py` 종료 0; `npm run build` 성공 |
| 1 | 300개+ 채널과 숏츠 100개+ 채널이 **전량** 목록화(마지막 페이지까지); 재동기화 시 신규만 추가(행 수 불변) |
| 2 | 수동자막 영상 → `manual`, 자동만 → `auto`, 없음 → `whisper`; 워커 강제 종료 후 재개; 모델별 벤치표 |
| 3 | Vitest 통과; 수동 시나리오 체크리스트 전건 |
| 4 | 6.1절 시나리오가 깨끗한 VM에서 통과 |
| 5 | 분석기 교체가 `analysis/` 밖 코드 수정 없이 됨; `analyses`에 결과 |
| 6 | 폰에서 PC 서버에 접속해 스크립트 열람 |

## 7. Phase 로드맵

| Phase | 명칭 | 핵심 산출물 | 브랜치 | 상태 |
|---|---|---|---|---|
| 0 | 범위 정의 + 공통 모듈 | 상위 문서 3종, 템플릿, 에이전트/스킬, 공통 모듈(config·constants·domain·exceptions·logging·run_context·db·analysis 슬롯)+테스트, 프론트 스캐폴드, check_env·verify_docs | `impl-phase0` | 🔄 진행 중 |
| 1 | 채널·영상 목록 | 채널 해석, 탭 리스팅, 증분 동기화, 메타 보충, DB 스키마(channels·videos·analyses 예약), API·CLI | `impl-phase1` | 예정 |
| 2 | 스크립트 파이프라인 | Provider 체인, json3 파싱, 오디오→Whisper, Huey 큐·재시도·재개, 벤치마크 | `impl-phase2` | 예정 |
| 3 | 웹 UI | React 화면 일체, 분석 탭 자리 | `impl-phase3` | 예정 |
| 4 | 빌드·배포 | PyInstaller 사이드카, Tauri 데스크톱, 설치파일, 모델 최초 다운로드 | `impl-phase4` | 예정 |
| 5 | 분석 플러그인 | 분석기 구현·UI 렌더 | `impl-phase5` | 예정 (P6과 순서 — 보류 결정 5) |
| 6 | 모바일 | Capacitor Android, 서버 URL 설정 | `impl-phase6` | 예정 |

## 8. 실행 환경

### 8.1 개발 VM (실측 2026-09-14, TechSpike 3.8절)

| 항목 | 값 | 설계에 미치는 것 |
|---|---|---|
| OS | Windows Server 2022 (10.0.20348) | PowerShell 스크립트, `.venv\Scripts\` 경로 |
| CPU | Intel Xeon (Icelake) **물리 1 / 논리 2** | STT 워커 1개, `cpu_threads=2`, 기본 모델 small |
| RAM | 16GB | Whisper small/turbo 모두 여유 |
| GPU | 없음 | CPU 전용 int8 |
| 디스크 | **C: 4.17GB / D: 4.09GB 여유** (2026-09-14 — turbo 캐시 삭제, small 캐시 464MB 를 D: `data/models` 로 이동 후) | 모델 캐시 `HF_HOME`을 지정, 대형 모델 동시 보유 불가, **P4 전 디스크 확보 필수**(보류 결정 8) |
| Python | 3.14.3(기본) / **3.12.10(프로젝트)** | `py -3.12 -m venv backend\.venv` |
| Node | v24.14.0 | yt-dlp JS 런타임, bgutil 스크립트, 프론트 빌드 |
| 없음 | ffmpeg, Rust/cargo, gh CLI | ffmpeg 불필요 확인; Rust는 P4에서 설치(≈2GB) |
| 네트워크 | 사내 고정 IP(SamsungSDS), 프록시 없음 | YouTube·HF·PyPI 직접 접속. 차단 시 가정용 회선에서 재확인 |

### 8.2 목표 사용자 환경

- **데스크톱(P4)**: 일반 Windows 10/11 PC. Python·Node·ffmpeg 없음 → 설치파일이 백엔드(PyInstaller)·Node 스크립트(bgutil)를 동봉. 모델은 최초 사용 시 다운로드.
- **모바일(P6)**: 안드로이드 폰. 같은 네트워크(또는 터널)의 PC 서버에 접속. 폰에서 STT를 돌리지 않는다.
- 데이터 위치: 개발은 `./data`, 배포는 `%LOCALAPPDATA%\youtubeLearner` (`DATA_DIR`로 이동 가능).

## 9. Scope

### In-Scope (v1 = P0~P4)

| # | 항목 | Phase |
|---|---|---|
| 1 | 채널 입력(URL·핸들·ID) → 채널 식별 | P1 |
| 2 | 롱폼·숏폼 탭 분리 목록, 증분 동기화, 메타 보충 | P1 |
| 3 | 원어 자막(수동→자동) json3 확보, 세그먼트 저장, 원본 보존 | P2 |
| 4 | 자막 없는 영상의 오디오 다운로드 + CPU Whisper | P2 |
| 5 | 작업 큐·재시도·재개·진행률 | P2 |
| 6 | 웹 화면(목록·뷰어·작업·설정·분석 자리) | P3 |
| 7 | Windows 설치파일(백엔드 사이드카 동봉) | P4 |
| 8 | 분석 슬롯(인터페이스·레지스트리·테이블·API 501·화면 자리) | P0~P3 |
| 9 | 방법론 도구(템플릿·에이전트·스킬·verify_docs·check_env) | P0 |

### Out-of-Scope (v1)

| 항목 | 이유 | 재검토 |
|---|---|---|
| 요약·핵심 도출·챕터 등 분석 **구현** | 사용자 결정 — 추출 완성·배포 후 | P5 |
| 모바일 앱 | 배포(P4) 이후 | P6 |
| 라이브(Streams 탭) 목록 | 학습 대상이 아님. kind 값만 예약 | 요청 시 |
| 번역 자막 기본 수집 | 429·품질·용량 | 옵션으로만 |
| 댓글·재생목록·멤버십 콘텐츠 | 범위 밖 | — |
| YouTube Data API, 클라우드 STT/LLM | 3.6절 | 보류 결정 1·7 |
| 다중 사용자·인증 | 단일 사용자 | 배포 대상이 늘 때 |
| Docker 서버 배포 | 데스크톱 우선 | 보류 결정 6 |

## 10. 작업 원칙

- 방법론은 `CLAUDE.md`가 규정한다: Phase당 브랜치, 요구사항정의서→설계서→코드+테스트→테스트결과서, 자체 점검, 학습가이드, Direct 리뷰, `merge --no-ff`, 브랜치 보존, 커밋 즉시 push.
- **프롬프트 작성 전에 실측한다**(TechSpike). 외부 서비스가 문서와 다르게 동작하는 것이 이 프로젝트의 가장 큰 위험이다.
- **근거는 우리 것으로.** 참조 방법론·외부 사례를 봤더라도 산출물에는 우리 판단의 이유만 남긴다.
- **결정을 미룰 때는 등재한다.** 트리거·기계 판정법·이정표 문서 3요소 없이 "나중에"라고 쓰지 않는다.
- **판단이 바뀌면 지우지 않는다.** 제자리 개정 + 머리에 개정 사유.

## 11. 개정 이력

| 판 | 일자 | 사유 |
|---|---|---|
| v1 | 2026-09-14 | 초판 — 기획서(승인)와 TechSpike 실측 반영 |
