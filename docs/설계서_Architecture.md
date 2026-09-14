# 설계서 — Architecture

- 상위 문서: `docs/scope-definition.md` (v1) 2절·4절·5절·7절·8절
- 사용 프롬프트: `docs/prompts/phase0/project-plan-v1.md`, `docs/prompts/phase0/scope-and-common-modules-v1.md`
- 선행 검증: `docs/internal/P0_검토서_TechSpike.md`
- 규칙: 이 문서는 **어떻게**에 답한다. Phase별 상세는 `P{N}_설계서_*`가 맡고, 이 문서는 전체 골격·경계·규약만 둔다
- 작성일: 2026-09-14 / 작성 LLM: Fable 5.1
- 상태: v1 — Phase 0 진행 중

## 0. 범위 문서와의 경계 (중복 방지 규약)

같은 내용을 두 문서에 쓰면 한쪽만 고쳐지는 사고가 난다. 위치를 고정한다.

| 내용 | 위치 |
|---|---|
| 기능 정의, 롱/숏 판정 기준, 스크립트 소스 우선순위, 언어 정책, 성공 기준, Phase 로드맵, 실행 환경 실측, In/Out of Scope | `docs/scope-definition.md` |
| 모듈 구조, Protocol 경계, 외부 연동 옵션 계약, 데이터 흐름·파일 명명, STT·분석 슬롯 구현 설계, CLI 계약, 기술 스택, 배포 구성, 테스트 전략, 디렉토리 | **이 문서** |
| 작업 규칙(Phase 절차·TDD 등급·하드코딩 금지·Git·문서 규칙·보류 결정 표) | `CLAUDE.md` |
| Phase별 FR·모듈 시그니처·설계 판단 상세 | `docs/P{N}_요구사항정의서_*.md`, `docs/P{N}_설계서_*.md` |

## 1. 아키텍처 개요

```
┌──────────────── 클라이언트 (화면만) ─────────────────┐      ┌──────────── 백엔드 (모든 무거운 일) ────────────┐
│ frontend/  React SPA  ──(P4) Tauri 데스크톱 셸        │ HTTP │ FastAPI (api/)                                  │
│                        ──(P6) Capacitor 모바일 셸      │ ───▶ │   ├─ 서비스: youtube/ transcripts/ stt/ analysis/│
│  API base URL은 설정값 (localhost | PC 서버 주소)      │      │   ├─ 작업 큐: jobs/ (Huey + SQLite)              │
└──────────────────────────────────────────────────────┘      │   └─ 저장: repository/ (SQLite WAL, 파일 산출물)  │
                                                              │ CLI (cli/) — 같은 서비스 코드를 단계별로 실행      │
                                                              └─────────────────────────────────────────────────┘
                                                                      │ yt-dlp(+bgutil, Node)   │ faster-whisper (CPU)
                                                                      ▼                         ▼
                                                                  YouTube                  HF Hub(모델 1회)
```

- **백엔드는 항상 별도 프로세스인 API 서버**다. 데스크톱 앱은 그것을 사이드카로 띄우고, 폰은 네트워크로 붙는다. 화면 코드는 세 형태에서 같다.
- **CLI와 API는 같은 서비스 계층을 부른다.** CLI는 단계별 실행·재현·자동화용, API는 화면용이다. 로직을 두 벌 두지 않는다.
- 모든 오래 걸리는 일(동기화·자막·STT)은 **작업(job)** 으로 큐에 들어가고, 화면은 진행률만 본다.

### 1.1 왜 단계를 파일·DB 경계로 나누나

목록 → 메타 → 자막 → 오디오 → STT → 정규화는 각각 실패 원인이 다르다(네트워크 차단 / 429 / CPU 시간). 각 단계가 자기 산출물을 DB·파일에 남기고 다음 단계는 그것만 읽으면, **끊긴 곳부터 다시** 돌릴 수 있다. 워크플로 도구로의 이식(Airflow류)도 이 경계를 그대로 쓴다.

### 1.2 입출력 보존 원칙

`scope-definition.md` 4.4절이 규정한다. 구현 규약은 6절.

## 2. 모듈 구조 (SOLID — SRP/DIP 중심)

### 2.1 패키지와 책임 (SRP)

```
backend/src/youtube_learner/
├── config.py            # [P0] Settings(.env) — 환경별 값                         등급 B
├── constants.py         # [P0] 설계 고정값 (kind/source 값, -orig 접미사, 버전)       등급 A
├── exceptions.py        # [P0] 예외 계층                                          등급 A
├── logging_config.py    # [P0] JSON 한 줄 로깅                                     등급 B
├── domain/
│   ├── models.py        # [P0] pydantic 모델 — 경계에서 거부                        등급 A
│   └── interfaces.py    # [P0] Protocol 4종 (+저장소 Protocol은 P1)                 측정 제외
├── workflow/
│   └── run_context.py   # [P0] status/<stage>_<run_id>.json, 실행 기록              등급 A
├── repository/
│   ├── db.py            # [P0] SQLite 엔진·세션 (WAL, busy_timeout, FK)              등급 B
│   ├── schema.py        # [P1] 테이블 정의 (channels·videos·analyses 예약 …)        등급 B
│   └── files.py         # [P2] 파일 산출물 경계 (captions/ audio/ whisper/)          등급 B
├── analysis/
│   ├── registry.py      # [P0] 이름 → Analyzer 레지스트리                            등급 B
│   └── null_analyzer.py # [P0] 미설정 상태를 표현하는 구현                            등급 A
├── youtube/
│   ├── channel_resolver.py  # [P1] URL/핸들/ID → ChannelRef                          등급 A
│   ├── tab_lister.py        # [P1] yt-dlp flat 탭 목록 (VideoListSource 구현)         등급 B
│   └── metadata_fetcher.py  # [P1] 영상별 메타·자막 트랙 목록 보충                     등급 B
├── transcripts/
│   ├── json3_parser.py      # [P2] json3 → 세그먼트                                  등급 A
│   ├── normalizer.py        # [P2] 세그먼트 병합·공백 정규화 (버전 상수 동반)          등급 A
│   ├── providers.py         # [P2] YtDlpCaption / YoutubeTranscriptApi / Whisper      등급 B
│   └── chain.py             # [P2] 우선순위 체인·폴백                                 등급 B
├── stt/
│   ├── audio_fetcher.py     # [P2] bestaudio m4a 다운로드                             등급 B
│   └── faster_whisper_engine.py  # [P2] SttEngine 구현                               등급 B
├── jobs/
│   ├── state.py             # [P2] 작업 상태기계 (허용 전이)                          등급 A
│   └── tasks.py             # [P2] Huey 태스크 (sync_channel, fetch_transcript, transcribe)  등급 B
├── api/
│   ├── app.py               # [P1] FastAPI 앱 조립 (의존성 주입 지점)                  등급 B
│   └── routers/             # [P1~P3] health channels videos transcripts jobs analyzers  등급 B
└── cli/
    ├── check_env.py         # [P0] 환경 검사 → ==> READY                              등급 B
    ├── run_sync.py          # [P1] 채널 동기화 단계                                    등급 B
    ├── run_transcripts.py   # [P2] 스크립트 단계                                      등급 B
    └── serve.py             # [P1] API 서버 기동                                       등급 B
```

- 한 패키지는 한 종류의 책임만 진다: "유튜브에서 가져오기"(`youtube/`), "스크립트 만들기"(`transcripts/`, `stt/`), "저장"(`repository/`), "일 시키기"(`jobs/`), "보여주기"(`api/`).
- `domain/`은 **아무것도 import하지 않는다**(pydantic·표준 라이브러리만). 나머지는 `domain/`을 향한다.

### 2.2 DIP — 변경 가능성이 가장 높은 네 축을 Protocol 뒤에 둔다

```python
# domain/interfaces.py  (P0에서 확정. 시그니처 상세는 P0_설계서_Common)
class VideoListSource(Protocol):      # yt-dlp 탭 ↔ (보류 결정 7) YouTube Data API
    def list_tab(self, channel: ChannelRef, kind: VideoKind) -> Iterator[VideoStub]: ...

class TranscriptProvider(Protocol):   # 체인: YtDlpCaption → YoutubeTranscriptApi → Whisper
    name: str
    def fetch(self, video: Video, languages: Sequence[str]) -> TranscriptResult | None: ...

class SttEngine(Protocol):            # FasterWhisperEngine ↔ (후보) WhisperCppEngine
    def transcribe(self, audio_path: Path, language: str | None, on_progress: ProgressCallback | None) -> TranscriptResult: ...

class Analyzer(Protocol):             # NullAnalyzer(v1) ↔ Extractive / Ollama / Claude (P5)
    name: str
    version: str
    def analyze(self, transcript: TranscriptResult, kind: AnalysisKind, options: Mapping[str, object]) -> AnalysisResult: ...
```

| 축 | 왜 바뀔 가능성이 높은가 | 경계가 없으면 |
|---|---|---|
| 영상 목록 소스 | YouTube 차단·yt-dlp 변경, Data API 전환 가능성 | 동기화·API·화면까지 전부 수정 |
| 스크립트 소스 | 자막 엔드포인트 정책(PO 토큰·429)이 수시로 바뀜 | 체인 순서 하나 바꾸는 데 파이프라인 전체 수정 |
| STT 엔진 | CPU 성능·모델 발전(whisper.cpp, 신규 모델) | 오디오 처리·저장 코드가 엔진에 묶임 |
| 분석기 | **v1에 없고 P5에서 붙는다** — 슬롯 그 자체 | 요약을 붙일 때 화면·API·DB를 다시 설계 |

구현체 선택(조립)은 **한 곳**(`api/app.py`, 각 CLI의 `_run`)에서만 한다. 서비스 코드는 Protocol 타입만 본다. 테스트는 Protocol을 만족하는 fake로 대체한다(9절).

### 2.3 원본 보호를 코드로 강제

`repository/files.py`는 `captions/`·`whisper/` 아래 기존 파일이 있으면 **덮어쓰기를 거부**한다(예외). 재생성은 명시적 삭제 후에만. `audio/`만 삭제 가능 캐시로 다룬다(`scope-definition.md` 4.4절).

## 3. 외부 연동

### 3.1 yt-dlp 옵션 계약 (TechSpike 실측 기반, 2026-09-14)

| 용도 | 옵션 | 근거 |
|---|---|---|
| 탭 flat 목록 | `extract_flat="in_playlist"`, URL `…/videos` 또는 `…/shorts`, `sleep_interval_requests` 1~3s | 60건/2.4초. 플레이리스트가 아닌 **탭** URL(숏츠 플레이리스트 100개 상한 이슈 회피) |
| 영상 메타 | `extract_info(url, download=False)`, `skip_download=True` | `duration`·`upload_date`·`language`·`live_status`·`subtitles`·`automatic_captions` 동시 획득 |
| 자막 | `writesubtitles`/`writeautomaticsub`, `subtitlesformat="json3"`, `subtitleslangs=[<lang>]` **한 언어씩**, 원어 자동은 `<lang>-orig` | 번역 요청 429, 한 언어 실패 시 명령 전체 실패 |
| 오디오 | `format="bestaudio[ext=m4a]/bestaudio"`, 후처리 없음 | ffmpeg 불필요, PyAV 디코딩 확인 |
| JS 런타임 | `js_runtimes={"node": {}}` (CLI `--js-runtimes node`) | Node 24 인식 확인 |
| PO 토큰 | bgutil 스크립트 모드: `extractor_args`로 `youtubepot-bgutilscript:script_path=<generate_once.js>`; HTTP 제공자 비활성화 | 3.3절 실측 |
| 차단 대응 | 네트워크 워커 1개, 지터, 429 지수 백오프, 실패 유형 카운트 | scope 5.4절 |

옵션 값은 `backend/config/ytdlp_default.json`에 두고 코드는 읽기만 한다(7.1절). yt-dlp API 호출은 `youtube/`·`transcripts/providers.py`·`stt/audio_fetcher.py` **세 곳으로 한정**한다 — 옵션 변경이 그 밖으로 새지 않게.

### 3.2 bgutil PO 토큰 제공자 구성

| 구성요소 | 개발 VM | 배포(P4) |
|---|---|---|
| 플러그인 | pip `bgutil-ytdlp-pot-provider` (venv) | PyInstaller에 포함 |
| 스크립트 | 저장소 안 `tools/bgutil-ytdlp-pot-provider/server/build/generate_once.js` (git clone + `npm ci` + `npx tsc`; git 미추적, D: 우선 규칙) | 빌드 산출물 `generate_once.js`(+node_modules)를 앱 리소스로 동봉 |
| Node | 시스템 Node 24 | 시스템 Node 감지 → 없으면 동봉 Node 바이너리(P4 판단) |
| 설정 | `.env` `BGUTIL_SCRIPT_PATH` | 앱 리소스 경로로 자동 설정 |

`check_env`가 스크립트 실재와 `node --version ≥ 20`을 검사한다.

### 3.3 youtube-transcript-api

`transcripts/providers.py`의 두 번째 구현체. `list(video_id)` → `is_generated`로 manual/auto 판정 → `fetch()`. 네트워크·429 예외는 `YouTubeAccessError`로 감싼다(예외 계층은 P0_설계서_Common).

### 3.4 Hugging Face Hub

`HF_HOME`(기본 `DATA_DIR/models`)을 프로세스 시작 시 환경변수로 설정한다. `HF_HUB_DISABLE_SYMLINKS_WARNING=1`. 모델 다운로드는 STT 작업의 첫 단계로 취급해 진행률을 낸다(P2).

## 4. 데이터 흐름 상세

```
[채널 입력] ──resolve──▶ ChannelRef ──list_tab(long)──▶ VideoStub* ─┐
                                    └──list_tab(short)─▶ VideoStub* ─┴─upsert(yt_video_id)──▶ videos (kind, flat 필드)
                                                                                                   │
        ┌──────────────────────────── metadata_fetch (증분: metadata_fetched_at IS NULL) ◀──────────┘
        ▼
  videos.duration_s/upload_date/language/live_status + 자막 트랙 목록(메모리)
        │
        ├─ 트랙 있음 ──▶ captions/<id>.<lang>.json3 (원본 보존) ──parse──▶ transcript_segments ──normalize──▶ transcripts.full_text
        │
        └─ 트랙 없음 ──▶ audio/<id>.m4a (캐시) ──transcribe──▶ whisper/<id>.<model>.json (원본 보존) ──▶ (같은 경로)
                                                                                                          │
                                                       [P3] analyses ◀── 사용자 붙여넣기(manual) · [P5] ◀── Analyzer.analyze ─┘
```

- 각 화살표는 **작업(job) 하나**의 단위다. 작업은 자연키 기준으로 멱등하다(6절).
- 화면은 `videos.transcript_status`(none/pending/done/failed)와 `jobs.progress`만 읽는다.

### 4.1 파일 명명 규약

`scope-definition.md` 4.3절의 트리를 따른다. 규칙: `<yt_video_id>` 그대로(대소문자·`-`·`_` 보존), 언어 코드는 yt-dlp 트랙 키 그대로(`ko`, `ko-orig`는 저장 시 `ko`로 정규화하고 DB `source=auto`로 구분), 모델명은 HF 리포 이름의 마지막 세그먼트(`faster-whisper-small`).

## 5. STT·분석 슬롯 설계

### 5.1 STT 설정 (`backend/config/stt_default.json`)

| 키 | 기본값 | 근거 |
|---|---|---|
| `model` | `small` | 코어 1개에서 3.05x. 보류 결정 2로 재확정 |
| `presets` | `small` / `medium` / `large-v3-turbo` | 사용자 선택 |
| `compute_type` | `int8` | CPU |
| `cpu_threads` | 논리 코어 수(`.env` `STT_CPU_THREADS` 우선) | 실측 2 |
| `vad_filter` | `true` | 무음 제거 |
| `beam_size` | `1` | 속도 우선. 정확도 비교는 P2 |
| `condition_on_previous_text` | `false` | 반복 환각 억제 |

### 5.2 분석 슬롯

```python
# analysis/registry.py
class AnalyzerRegistry:
    def register(self, analyzer: Analyzer) -> None: ...
    def get(self, name: str) -> Analyzer: ...        # 없으면 AnalyzerNotConfiguredError
    def available(self) -> list[AnalyzerInfo]: ...   # v1: [] (NullAnalyzer는 목록에 내지 않는다)
```

| 계층 | v1 동작 | P5 이후 |
|---|---|---|
| Protocol `Analyzer` | 정의만 | 구현체 추가 |
| 레지스트리 | `NullAnalyzer` 하나. `available()`은 빈 목록 | 설정(`.env` `ANALYZERS`)으로 켠 구현체 등록 |
| DB `analyses` | 스키마(P1). **수동 글**(`analyzer_name="manual"`, `analyzer_version="user"`) 저장(P3) | 자동 분석 결과도 같은 테이블, 출처로 구분 |
| API | `GET /analyzers` → `[]`; `POST /videos/{id}/analyses` — 수동(`manual`) 입력이면 **201 저장**, 분석기 요청이면 **501** + `{"available": []}` (P3) | 자동도 201 |
| 화면 | '요약 및 정리' 탭 — 스크립트 **원클릭 복사**, 붙여넣기 편집기 + 저장; 자동 분석 버튼은 "설정된 분석기가 없습니다" (P3) | 자동 결과도 같은 탭에 출처 표시 |

수동 입력은 `Analyzer`가 아니다 — 계산이 없으므로 레지스트리를 거치지 않고 저장소에 바로 기록한다(`constants.MANUAL_ANALYZER_NAME`, scope 2.4절 v2).

완료 기준: P5에서 분석기를 붙일 때 `analysis/` 밖은 **설정 한 줄**만 바뀐다.

## 6. Workflow 친화 규약 (모든 CLI·작업 공통)

| 규약 | 내용 |
|---|---|
| 진입점 | 단계마다 `cli/run_*.py`. docstring에 `Trigger / Input / Output / ⚠️ 사전 조건` |
| 입력 | 명시적 인자만(채널 id·범위·설정 파일 경로). 암묵적 상대경로 탐색 금지 |
| 실행 기록 | `with run_context(stage, settings) as (run_id, logger)` → `status/<stage>_<run_id>.json`에 started/succeeded/failed. 실패는 기록 후 **재전파**(종료 코드는 CLI가 결정) |
| 멱등성 | 자연키 upsert. 스크립트는 (video, source, language, model, pipeline_version) 존재 시 건너뜀. 파일은 덮어쓰기 거부 |
| 재시작 | 작업 단위(영상 1건)로 재시도. `jobs.attempts` 상한 후 `failed` |
| 로그 | JSON 한 줄, UTC, `run_id`·`stage`·`yt_video_id` 필드 고정 |
| 동시성 | 네트워크 큐 1워커 / STT 큐 1워커 (Huey 인스턴스 2개 또는 우선순위) |

## 7. 기술 스택

| 영역 | 선택 | 근거 (TechSpike·기획 검증 2026-09-14) |
|---|---|---|
| 언어/런타임 | Python **3.12** (venv `backend\.venv`) | ctranslate2·onnxruntime·av 휠 확인, PyInstaller 성숙도. 3.14는 보류 결정 4 |
| 웹 프레임워크 | FastAPI + uvicorn | OpenAPI 자동 문서 → 프론트 타입 생성, 비동기 |
| 설정/모델 | pydantic v2, pydantic-settings | 경계에서 거부, `.env` 로딩 |
| 저장 | SQLite(WAL) + SQLAlchemy 2.x + Alembic(P1~) | 단일 파일, 추가 인프라 0, 수천 건 규모 충분 |
| 작업 큐 | Huey + SqliteHuey, thread worker(P2) | Redis 불필요. Windows는 process worker 미지원 → thread |
| 유튜브 | yt-dlp[default] 2026.08.19 + yt-dlp-ejs + bgutil 2.0.0, youtube-transcript-api 1.2.4 | 3절 |
| STT | faster-whisper 1.2.1 / ctranslate2 4.8.2 / PyAV 18.1 | 실측 3.5·3.6절 |
| 프론트 | React + Vite + TypeScript, TanStack Query, Vitest + Testing Library | 3 플랫폼 공유 |
| 데스크톱(P4) | Tauri v2 + PyInstaller **onedir** 사이드카 + NSIS | 8절 |
| 모바일(P6) | Capacitor | React 재사용 |
| 로깅 | 표준 logging + JSON 포매터 직접 구현(외부 패키지 없음) | 한 줄 JSON — P0_설계서_Common 6.2절 |
| 품질 | pytest, pytest-cov, ruff / vitest | 9절 |

### 7.1 값을 어디에 두는가 (하드코딩 금지 — 3분류)

| 분류 | 위치 | 예 |
|---|---|---|
| 환경에 따라 다른 값 | `.env` → `config.Settings` | `DATA_DIR`, `HF_HOME`, `API_PORT`, `CORS_ORIGINS`, `BGUTIL_SCRIPT_PATH`, `STT_CPU_THREADS`, `LOG_LEVEL` |
| 설계상 고정된 값 | `constants.py` | `VideoKind`/`TranscriptSource` 값, `ORIGINAL_CAPTION_SUFFIX="-orig"`, `PIPELINE_VERSION`, DB 파일명, status 파일명 패턴 |
| 실행마다 조절하는 값 | `backend/config/*.json` (`"_comment"` 필수) | `stt_default.json`(모델·스레드·VAD), `ytdlp_default.json`(포맷·간격·재시도), `sync_default.json`(페이지 크기·증분 규칙) |

### 7.2 도입하지 않은 것

| 후보 | 이유 | 재검토 |
|---|---|---|
| ffmpeg 바이너리 | 다운로드·디코딩에 불필요 확인 | 변환 기능 필요 시 `imageio-ffmpeg` |
| Redis/Celery/RQ | 추가 인프라. 단일 PC | 다중 워커 서버 배포 시 |
| Docker 우선 배포 | 사용자 환경이 Windows 데스크톱 | 보류 결정 6 |
| ORM 대신 raw SQL | 마이그레이션·타입 안전성 | — |
| YouTube Data API | scope 3.6절 | 보류 결정 7 |
| whisper.cpp | faster-whisper int8이 x86에서 유리하다는 보고. 미측정 | `SttEngine` 뒤에 있어 언제든 |

## 8. 배포 구성

### 8.1 개발 (P0~P3)

`backend\.venv` + `uvicorn` (`cli/serve.py`) + `frontend` Vite dev server. 둘을 함께 띄우는 dev 스크립트는 P3 에서 `scripts/` 아래에 추가한다(10절 트리의 `dev.ps1`).

### 8.2 데스크톱 (P4) — Tauri v2 사이드카

| 항목 | 결정 | 근거 |
|---|---|---|
| 백엔드 패키징 | PyInstaller **onedir** (onefile 금지) | onefile은 부트로더 PID만 알아 자식 종료 불가, 기동 느림 |
| 사이드카 등록 | `bundle.externalBin`, `shell:allow-spawn`, 기동 시 빈 포트 전달 → `/health` 폴링 | Tauri 문서 |
| 종료 | 앱 종료 시 프로세스 트리 종료(`taskkill /T`) | 사이드카 잔존 방지 |
| 동봉 | bgutil `generate_once.js`(+deps), Node(시스템 감지 → 없으면 동봉) | 3.2절 |
| 모델 | 설치파일에 넣지 않음. 최초 사용 시 다운로드(진행률) | 크기·라이선스 |
| 설치 | NSIS. 사이드카 exe에 버전 리소스 | NSIS 교체 문제 회피 |
| 환경 | `PYTHONUTF8=1`, hidden imports(ctranslate2·onnxruntime·tokenizers·huggingface_hub·faster_whisper assets) | |

### 8.3 모바일 (P6) — Capacitor

`frontend/dist`를 감싸 Android 앱으로. API base URL은 설정 화면에서 입력. FastAPI CORS 허용목록, HTTPS 또는 개발용 cleartext. 서버는 PC(데스크톱 앱의 백엔드) 또는 Docker(보류 결정 6).

## 9. 테스트 전략

| 등급 | 대상 | 방법 | 위치 | 목표 |
|---|---|---|---|---|
| A | 순수·결정적 로직 (`constants` 검증, `domain/models`, `run_context` 상태 전이, `json3_parser`, `normalizer`, `channel_resolver`, `jobs/state`, 프론트 유틸) | **테스트 먼저** (Red→Green→Refactor) | `backend/tests/unit/`, `frontend/src/**/*.test.ts` | ≥ 90% |
| B | 설정·IO·외부 의존 오케스트레이션 (`config`, `logging_config`, `db`, `check_env`, `tab_lister`, `providers`, `chain`, `tasks`, `api/`, React 컴포넌트) | 구현 후 통합 테스트. 외부는 **Protocol fake** 또는 기록된 응답(fixture) | `backend/tests/integration/`, `frontend/src/**/*.test.tsx`(MSW) | ≥ 70% |
| C | 실호출·탐색 (`scripts/spike/*`, 벤치마크) | 자동 테스트 없음. 산출물 검증 + 문서 기록 | `scripts/spike/` | 측정 제외 |
| E2E | 실제 YouTube·Whisper | 기본 pytest에서 **제외**(`-m e2e`). 수동·선택 실행. 테스트결과서 5절에 실호출 출력·일자 | `backend/tests/e2e/` | — |

- 테스트 파일은 대상과 1:1. docstring에 등급·대응 문서·FR 번호.
- **거부 케이스 필수**: 부적합 입력을 거부하는 모듈은 거부 테스트가 없으면 미완.
- 문서 검증(`scripts/verify_docs.py`)은 pytest에 포함(`backend/tests/integration/test_docs.py`). 검사기가 실제로 위반을 잡는지 **역테스트**를 함께 둔다.

## 10. 디렉토리 구조 (목표 형태)

```
youtubeLearner/
├── CLAUDE.md  README.md  .env.example  .gitignore  .gitattributes
├── .claude/agents/doc-consistency.md   .claude/skills/troubleshoot/SKILL.md
├── backend/
│   ├── pyproject.toml            # extras: youtube stt api jobs dev
│   ├── config/*.json             # stt_default / ytdlp_default / sync_default
│   ├── src/youtube_learner/      # 2.1절
│   └── tests/{unit,integration,e2e}/  conftest.py
├── frontend/                     # Vite + React + TS  [P0 스캐폴드, P3 화면]
├── desktop/                      # Tauri v2            [P4]
├── mobile/                       # Capacitor           [P6]
├── scripts/
│   ├── check_env.ps1             # → python -m youtube_learner.cli.check_env
│   ├── verify_docs.py            # 문서 실검사 (pytest 포함)
│   ├── dev.ps1                   # [P3] 백엔드+프론트 동시 기동
│   ├── build_backend.ps1         # [P4] PyInstaller
│   └── spike/                    # 등급 C 실측 스크립트
├── data/  status/                # 런타임 (git 미추적) — scope 4.3절
├── docs/                         # 제출물: scope-definition, 설계서_Architecture, P{N}_요구사항정의서/설계서/테스트결과서
│   ├── internal/                 # SelfReview · TechSpike · 학습가이드 · 용어집 · 트러블슈팅 · 설계서_Agents · templates/ · qa/
│   └── prompts/phase{N}/         # 작업 프롬프트 -v{k}
└── history/                      # <날짜>_<작업자>_<주제>.md
```

`backend/config/`를 루트가 아닌 `backend/` 아래에 둔 이유: P4에서 백엔드 디렉토리를 **한 단위로** 패키징하기 위해서다. `data/`·`status/`는 코드가 아니라 런타임이므로 `DATA_DIR`·`STATUS_DIR`로 이동 가능하다.

## 11. 문서 간 추적성

```
docs/prompts/phase0/project-plan-v1.md (기획서, 승인)
   └─▶ docs/scope-definition.md (무엇을/왜)
          └─▶ docs/설계서_Architecture.md (어떻게 — 이 문서)
                 └─▶ docs/P{N}_요구사항정의서_*.md (FR-…)  ◀─ docs/internal/P{N}_검토서_TechSpike.md (실측)
                        └─▶ docs/P{N}_설계서_*.md (모듈·설계 판단)
                               └─▶ 코드 (docstring 첫 줄 = 설계서 절·FR) + 테스트 (docstring = FR)
                                      └─▶ docs/P{N}_테스트결과서_*.md (FR 전건 대조, 커버리지 실측)
                                             └─▶ docs/internal/P{N}_검토서_SelfReview.md → CLAUDE.md 보류 결정 표
CLAUDE.md (규칙) ── 모든 단계에 적용. 충돌 시 CLAUDE.md 우선
```

## 12. 개정 이력

| 판 | 일자 | 사유 |
|---|---|---|
| v1 | 2026-09-14 | 초판 — 기획서·TechSpike 반영. 모노레포·4 Protocol·분석 슬롯·CPU STT·Tauri 사이드카 |
