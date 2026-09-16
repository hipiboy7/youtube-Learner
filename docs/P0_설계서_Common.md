# P0 설계서 — Common

- 상위 문서: `docs/scope-definition.md` 2.4절·4절·5.3절·7절·8절, `docs/설계서_Architecture.md` 2절·5절·6절·7절·9절
- 규칙: `CLAUDE.md` 4절 1단계 산출물(요구사항 + 설계). 다음 산출물은 코드+테스트 → `docs/internal/P0_실측기록_Common.md`
- 실측 근거: `docs/internal/P0_실측기록_Common.md`
- 작성일: 2026-09-14 / 작성 LLM: Fable 5.1
- 상태: v2 — 방법론 개정(2026-09-16)으로 구 `P0_요구사항정의서_Common.md` 를 1~4절로 흡수

> **v2 개정 사유 (2026-09-16)**: 방법론 개정 — Phase 당 문서를 3개(설계서·실측기록·학습가이드)로 줄였다.
> 요구사항정의서와 설계서가 모듈 목록을 두 번 쓰고 있었다. 요구사항(목적·범위·FR·완료 기준)을 이 문서 1~4절로 옮기고
> 원 문서는 지웠다. 문장은 그대로이며 절 번호만 바뀌었다. 근거: `docs/internal/qa/질의응답_방법론개정.md`

## 1. 목적 (Why)

Phase 1~6이 공통으로 딛는 바닥을 만든다: 설정을 어디서 읽고, 무엇이 고정값이고, 데이터가 어떤 모양이며, 어떤 인터페이스 뒤에서 구현을 바꾸고, 실행 기록·로그·예외를 어떻게 남기는지. 이것이 없으면 Phase마다 같은 결정을 다시 하고 서로 다르게 한다.
또한 방법론이 **기계로 강제**되게 한다 — 환경 검사(`check_env`), 문서 실검사(`verify_docs`), 테스트 등급·커버리지 측정. 규칙은 잊히지만 검사는 매번 돈다.
분석 슬롯(`Analyzer`·레지스트리)을 여기서 확정해 두어야 P1~P3가 API·화면 자리를 만들 수 있다.

## 2. 배경 및 제약

- 실행 환경(TechSpike 3.8절): 물리 코어 1 / 논리 2, RAM 16GB, GPU 없음, **디스크 C 4.78GB / D 3.90GB 여유**(2026-09-14, C: 캐시 정리·D: 이동 후), Python 3.12.10 venv, Node 24. → 자원 관련 값은 설정으로 빼고 기본값을 작게. 모델 캐시 위치는 우리가 정한다(T-002).
- PO 토큰 제공자는 Node 스크립트 빌드가 필요하다(T-001). 환경 검사가 이를 잡아야 한다.
- 원어 자막 트랙 키는 `<lang>-orig`(TechSpike 3.2절). 상수와 정규화 함수가 필요하다.
- 문서 규약: 문서의 명령은 PowerShell·`backend\.venv\Scripts\python.exe` 전체 경로(`CLAUDE.md` 4절). 검사기가 Windows 규칙을 알아야 한다.
- 이 Phase는 **외부 서비스를 호출하는 코드를 만들지 않는다**(P1·P2 책임). 따라서 실호출 검증 대상은 `check_env`가 Node·스크립트 실재를 확인하는 것으로 한정된다.

## 3. 범위

### In Scope

| # | 항목 | 근거 |
|---|---|---|
| 1 | 설정(`.env`)·상수·설정 JSON 로더 | `설계서_Architecture` 7.1절, `CLAUDE.md` 5절 |
| 2 | 도메인 모델(pydantic)과 4 Protocol | `설계서_Architecture` 2.2절, scope 4.1절 |
| 3 | 예외 계층, JSON 로깅, 실행 기록(`run_context`) | `설계서_Architecture` 6절 |
| 4 | SQLite 엔진 팩토리(WAL·busy_timeout·FK) | `CLAUDE.md` 12절 |
| 5 | 분석 슬롯: `NullAnalyzer` + 레지스트리 | scope 2.4절, `설계서_Architecture` 5.2절 |
| 6 | 환경 검사 `check_env` + PowerShell 래퍼 | `CLAUDE.md` 1절 0단계 |
| 7 | 문서 실검사 `verify_docs` + pytest 포함 + 역테스트 | `CLAUDE.md` 4절 |
| 8 | 프론트 스캐폴드(Vite+React+TS+Vitest) + A등급 유틸 1개 | `설계서_Architecture` 7절·9절 |
| 9 | `backend/pyproject.toml`, `.env.example`, `backend/config/*.json` 3종 | `CLAUDE.md` 5절·7절 |

### Out of Scope (다른 Phase 책임)

| 항목 | 담당 Phase | 근거 |
|---|---|---|
| 채널 해석·탭 리스팅·메타 보충·DB 테이블(`channels`·`videos`·`analyses`)·Alembic | Phase 1 | scope 7절 |
| 자막·오디오·Whisper·Provider 체인·Huey 작업·`jobs` 테이블 | Phase 2 | scope 7절 |
| FastAPI 앱·라우터(`api/`) — P0는 `api/` 패키지를 만들지 않는다 | Phase 1~3 | 프롬프트 "하지 않는 것" |
| React 화면(목록·뷰어·원클릭 복사·'요약 및 정리' 수동 입력·저장·설정) | Phase 3 | scope 2.5절 |
| PyInstaller·Tauri·NSIS | Phase 4 | scope 7절 |
| 분석기 구현(추출식·Ollama·Claude) | Phase 5 | 보류 결정 1 |
| Capacitor | Phase 6 | scope 7절 |

## 4. 기능 요구사항 (FR-1~34)

> 번호대: P0 = FR-1~99. 모듈 경로는 `backend/src/youtube_learner/` 기준.

### 4.1 `config.py` — 환경별 설정 (`Settings`)

**FR-1.** `.env`(작업 디렉토리) 및 환경변수에서 읽는 `Settings(BaseSettings)`를 제공해야 한다. 아래 키를 **한 번에 확정**한다(이후 Phase가 키를 추가하되 이름을 바꾸지 않는다).

| 키 | 기본값 | 용도 | 근거 |
|---|---|---|---|
| `DATA_DIR` | `./data` | DB·파일 산출물·모델 캐시의 루트 | scope 4.3절 |
| `STATUS_DIR` | `./status` | 실행 기록 | `설계서_Architecture` 6절 |
| `HF_HOME` | `{DATA_DIR}/models` | Whisper 모델 캐시 | T-002, scope 3.4절 |
| `CONFIG_DIR` | `backend/config` (저장소 기준) | 설정 JSON 위치 | `설계서_Architecture` 7.1절 |
| `LOG_LEVEL` | `INFO` | 로그 레벨 (DEBUG/INFO/WARNING/ERROR) | |
| `LOG_FORMAT` | `json` | `json` 한 줄 / `text` 개발용 | `설계서_Architecture` 6절 |
| `API_HOST` / `API_PORT` | `127.0.0.1` / `8765` | P1 API 서버 | 8000 충돌 회피 |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | P3 프론트 dev, P6 모바일 | `설계서_Architecture` 8.3절 |
| `YTDLP_JS_RUNTIME` | `node` | yt-dlp JS 런타임 | TechSpike 3.3절 |
| `BGUTIL_SCRIPT_PATH` | `<저장소>/tools/bgutil-ytdlp-pot-provider/server/build/generate_once.js` (D:, git 미추적; 초안의 `~/…` 는 디스크 D: 우선 규칙으로 정정) | PO 토큰 스크립트 | T-001, `CLAUDE.md` 7절 |
| `BGUTIL_HTTP_ENABLED` | `false` | HTTP 제공자 사용 여부 | TechSpike 3.3절 경고 반복 |
| `STT_CPU_THREADS` | 논리 코어 수 | faster-whisper `cpu_threads` | TechSpike 3.5절 |
| `ANALYZERS` | (빈 목록) | 켤 분석기 이름 목록 (P5) | scope 2.4절 |
| `DISK_FREE_WARN_GB` | `10` | 환경 검사 디스크 경고 기준 | 보류 결정 8 |

**FR-2.** 파생 경로를 속성으로 제공해야 한다: `db_path = DATA_DIR/youtube_learner.db`, `channels_dir = DATA_DIR/channels`, `models_dir = HF_HOME`. 경로는 `Path`로 절대경로화한다.

**FR-3.** `Settings.ensure_dirs()`는 `DATA_DIR`·`STATUS_DIR`·`HF_HOME`을 만들고(있으면 무시), `Settings.apply_process_env()`는 라이브러리가 읽는 환경변수(`HF_HOME`, `HF_HUB_DISABLE_SYMLINKS_WARNING=1`, `PYTHONUTF8=1`)를 프로세스에 설정해야 한다. faster-whisper import **전에** 호출되는 것이 계약이다.

**FR-4.** 잘못된 값은 **로딩 시점에 거부**해야 한다: `LOG_LEVEL` 허용 집합 외, `LOG_FORMAT` ∉ {json,text}, `API_PORT` ∉ 1~65535, `STT_CPU_THREADS` < 1, `DISK_FREE_WARN_GB` < 0. 알 수 없는 키는 무시한다(`extra="ignore"`).

**FR-5.** `load_json_config(name, settings) -> dict`는 `CONFIG_DIR/<name>.json`을 읽어 `"_comment"` 키가 있는지 확인하고 그 키를 **제거한** dict를 반환해야 한다. 파일 없음·JSON 오류·`_comment` 없음은 `ConfigError`.

### 4.2 `constants.py` — 설계 고정값

**FR-6.** 다음 열거형을 `StrEnum`으로 정의해야 한다: `VideoKind = long|short|live`, `TranscriptSource = manual|auto|translated|whisper`, `TranscriptStatus = none|pending|done|failed`, `AnalysisKind = summary|keypoints|chapters`.

| 값 | 근거 |
|---|---|
| `VideoKind` 3값 | scope 2.2절 (live는 예약) |
| `TranscriptSource` 4값 | scope 2.3절·5.2절 (translated는 옵션) |

**FR-7.** 상수: `ORIGINAL_CAPTION_SUFFIX = "-orig"`, `LANG_PRIORITY_DEFAULT = ("ko",)`, `PIPELINE_VERSION = "1"`, `DB_FILENAME = "youtube_learner.db"`, `STATUS_FILENAME_PATTERN = "{stage}_{run_id}.json"`, `YT_VIDEO_ID_PATTERN = r"^[A-Za-z0-9_-]{11}$"`, `YT_CHANNEL_ID_PATTERN = r"^UC[A-Za-z0-9_-]{22}$"`, `PACKAGE_NAME = "youtube_learner"`, `MANUAL_ANALYZER_NAME = "manual"`, `MANUAL_ANALYZER_VERSION = "user"`(v2 — 사용자가 붙여 넣은 요약·정리의 `analyses` 출처, scope 2.4절).

**FR-8.** 순수 함수 `split_caption_key(key) -> (language, is_original)`: `"ko-orig"` → `("ko", True)`, `"ko"` → `("ko", False)`, `"pt-BR"` → `("pt-BR", False)`; 빈 문자열은 `ValueError`. 역함수 `original_caption_key(lang) -> f"{lang}-orig"`.

### 4.3 `domain/models.py` — 도메인 모델 (pydantic v2, 경계에서 거부)

**FR-9.** 모든 모델은 `frozen=True`, `extra="forbid"`. 알 수 없는 필드·사후 변경을 거부한다.

**FR-10.** `ChannelRef(yt_channel_id: str | None, handle: str | None, url: str)`: `yt_channel_id`는 `YT_CHANNEL_ID_PATTERN`, `handle`은 `@`로 시작, 둘 다 없으면 거부.

**FR-11.** `VideoStub(yt_video_id, kind: VideoKind, title, url, duration_s: int | None, view_count: int | None, thumbnail_url: str | None)`: `yt_video_id`는 `YT_VIDEO_ID_PATTERN`, `duration_s`·`view_count`는 음수 거부, `title` 공백만이면 거부. flat 목록에서 `duration_s`가 `None`인 것은 **정상**(숏폼, TechSpike 3.1절).

**FR-12.** `Video(VideoStub)`에 `upload_date: date | None`, `language: str | None`, `live_status: str | None`, `metadata_fetched_at: datetime | None`, `transcript_status: TranscriptStatus = none`을 추가한다.

**FR-13.** `TranscriptSegment(idx: int ≥ 0, start_ms: int ≥ 0, end_ms: int ≥ start_ms, text: str)`: `text`는 strip 후 비어 있으면 거부.

**FR-14.** `TranscriptResult(yt_video_id, source: TranscriptSource, language, engine: str, model_name: str | None, pipeline_version: str = PIPELINE_VERSION, segments: list[TranscriptSegment])`: 세그먼트 1개 이상, `idx`가 0부터 연속, `start_ms` 비감소. 파생 속성 `full_text`(세그먼트 텍스트를 공백 하나로 결합), `duration_ms`(마지막 `end_ms`).

**FR-15.** `AnalyzerInfo(name, version, kinds: list[AnalysisKind], description)`, `AnalysisResult(yt_video_id, analyzer_name, analyzer_version, kind: AnalysisKind, language, content: dict, model_info: dict, created_at: datetime)`.

### 4.4 `domain/interfaces.py` — Protocol 4종

**FR-16.** `runtime_checkable` Protocol: `VideoListSource.list_tab(channel: ChannelRef, kind: VideoKind) -> Iterator[VideoStub]`, `TranscriptProvider.name` + `fetch(video: Video, languages: Sequence[str]) -> TranscriptResult | None`, `SttEngine.transcribe(audio_path: Path, language: str | None, on_progress: ProgressCallback | None) -> TranscriptResult`, `Analyzer.name`·`version`·`info() -> AnalyzerInfo`·`analyze(transcript, kind, options) -> AnalysisResult`. `ProgressCallback = Callable[[float, str], None]`(0~1 진행률, 메시지). 이 파일은 실행 로직을 갖지 않는다(커버리지 제외).

### 4.5 `exceptions.py` — 예외 계층

**FR-17.** 단일 베이스 `YoutubeLearnerError(Exception)` 아래: `ConfigError`, `YouTubeAccessError(status: int | None, retry_after_s: float | None)`, `TranscriptUnavailableError`, `SttError`, `AnalyzerNotConfiguredError(available: list[str])`, `StorageError`, `OutputExistsError(StorageError, path)`. 메시지는 사람이 읽을 한국어 한 줄 + 구조 필드.

### 4.6 `logging_config.py` — JSON 한 줄 로깅

**FR-18.** `setup_logging(settings)`: 루트 로거 핸들러를 **교체**(중복 출력 방지, 두 번 호출해도 핸들러 1개), stdout, `LOG_FORMAT=json`이면 한 줄 JSON(`timestamp` UTC ISO8601 `Z`, `level`, `logger`, `message`, extra 병합, `ensure_ascii=False`), `text`면 사람이 읽는 형식. 레벨은 `LOG_LEVEL`.

**FR-19.** `ContextLoggerAdapter(logger, context)`: 호출부 `extra`와 어댑터 `context`(`run_id`·`stage`·`yt_video_id` 등)를 **병합**한다(덮지 않음). `bind(**more) -> ContextLoggerAdapter`로 컨텍스트를 누적한다.

### 4.7 `workflow/run_context.py` — 실행 기록

**FR-20.** `new_run_id(now=None) -> str`은 `YYYYMMDD-HHMMSS-<8 hex>` 형식이어야 한다(UTC). `run_context(stage: str, settings, logger=None, *, run_id=None, extra=None)` 컨텍스트 매니저는(`run_id` 주입은 테스트·재실행용) 진입 시 `STATUS_DIR/<stage>_<run_id>.json`에 `status="started"`를 쓰고 `(run_id, ContextLoggerAdapter)`를 내준다. 정상 종료 시 `succeeded`·`finished_at`·`duration_s`, 예외 시 `failed`·`error{type,message}`를 기록하고 **예외를 재전파**한다(종료 코드는 CLI가 정한다).

**FR-21.** 상태 파일 스키마: `stage, run_id, status, started_at, finished_at, duration_s, error, pipeline_version, extra`. `read_status(path) -> dict`. 같은 `run_id` 파일이 이미 있으면 `OutputExistsError`(덮어쓰기 금지). `stage`는 `[a-z0-9_]+`만 허용.

### 4.8 `repository/db.py` — SQLite 엔진

**FR-22.** `make_engine(settings) -> Engine`: `DATA_DIR` 이 없으면 만들고(SQLite 는 부모 디렉토리 없이 파일을 못 만든다), `sqlite:///{db_path}`, 연결마다 `PRAGMA journal_mode=WAL`, `busy_timeout=5000`, `foreign_keys=ON`, `synchronous=NORMAL`. `make_session_factory(engine) -> sessionmaker`. `Base = DeclarativeBase`(테이블은 P1이 정의).

**FR-23.** `init_db(engine)`은 `Base.metadata.create_all`을 수행하고 PRAGMA가 적용됐는지 확인해 `dict(journal_mode=..., foreign_keys=...)`를 반환한다. 파일 DB에서 `journal_mode == "wal"`, `foreign_keys == 1`이어야 한다. (디렉토리 생성은 FR-22 `make_engine` — 초안은 여기에 적었으나 SelfReview 1.1 로 정정)

### 4.9 `analysis/` — 분석 슬롯

**FR-24.** `NullAnalyzer`: `name="null"`, `version="0"`, `info()`는 `kinds=[]`, `analyze()`는 항상 `AnalyzerNotConfiguredError(available=[])`.

**FR-25.** `AnalyzerRegistry`: `register(analyzer)`(같은 이름 재등록은 `ConfigError`), `get(name)`(없으면 `AnalyzerNotConfiguredError(available=<null 제외 이름들>)`), `available() -> list[AnalyzerInfo]`(**`null` 제외**), `names()`. `build_registry(settings) -> AnalyzerRegistry`: `settings.analyzers`가 비어 있으면 `NullAnalyzer`만 등록; 비어 있지 않은데 구현이 없으면(P0~P4) `ConfigError`("분석기 <이름>은 아직 구현되지 않았다 — Phase 5").

### 4.10 `cli/check_env.py` + `scripts/check_env.ps1` — 환경 검사

**FR-26.** `python -m youtube_learner.cli.check_env [--json] [--strict]`는 아래 항목을 검사해 각 줄 `[OK]|[WARN]|[FAIL] <항목> — <실측>`을 출력하고, FAIL이 없으면 마지막 줄 `==> READY`(종료 0), 있으면 `==> NOT READY (<n> failures)`(종료 1). `--strict`는 WARN도 실패로 본다. `--json`은 항목 배열을 JSON으로 출력한다.

| 항목 | 판정 | 근거 |
|---|---|---|
| Python | 3.12.x 이고 venv(`sys.prefix != sys.base_prefix`) → OK; 아니면 FAIL | `CLAUDE.md` 0절 |
| 패키지 import | `yt_dlp`, `faster_whisper`, `ctranslate2`, `av`, `youtube_transcript_api`, `sqlalchemy`, `pydantic_settings` → 각 OK/FAIL(버전 표기) | 3.8절 |
| Node | `node --version` ≥ 20 → OK; 없음/미만 FAIL | T-001 |
| bgutil 스크립트 | `BGUTIL_SCRIPT_PATH` 실재 → OK; 없으면 FAIL(빌드 절차 안내) | T-001 |
| 디렉토리 | `DATA_DIR`·`STATUS_DIR`·`HF_HOME` 생성·쓰기 가능 → OK; 불가 FAIL | FR-3 |
| 디스크 | `HF_HOME` 드라이브 여유 ≥ `DISK_FREE_WARN_GB` → OK; 미만 **WARN** | T-002, 보류 결정 8 |
| 설정 JSON | `stt_default`·`ytdlp_default`·`sync_default` 로드 성공 → OK; 실패 FAIL | FR-5 |
| Whisper 모델 캐시 | `HF_HOME/hub/models--*` 존재 → OK(목록); 없으면 **WARN**("최초 사용 시 다운로드") | 3.5절 |

**FR-27.** `scripts/check_env.ps1`은 `backend\.venv\Scripts\python.exe`를 찾아(없으면 생성 절차를 출력하고 종료 1) `-m youtube_learner.cli.check_env`를 인자 그대로 실행하고 종료 코드를 전달해야 한다.

### 4.11 `scripts/verify_docs.py` + `backend/tests/integration/test_docs.py` — 문서 실검사

**FR-28.** 검사 대상: `README.md`, `CLAUDE.md`, `docs/*.md`, `docs/internal/*.md`, `docs/internal/templates/*.md`, `docs/internal/qa/*.md`. `history/`(사후 수정 금지 기록)는 글롭에 넣지 않아 제외된다. `--path <상대경로>`로 단일 문서, `--quiet`로 위반만 출력. 종료 코드 0/1.

**FR-29.** 검사 7종(각각 `Finding(doc, line_no, kind, detail)`):

| kind | 내용 | Windows 규칙 |
|---|---|---|
| `venv` | `powershell`/`bash`/`sh` 펜스 안에서 bare `python`/`pytest`/`pip`을 쓰기 전에 활성화 안내가 없다 | 허용: `backend\.venv\Scripts\python.exe` 또는 `backend/.venv/Scripts/python.exe` 전체 경로, 앞선 줄에 `Activate.ps1`. `-m venv` 생성 명령은 예외 |
| `module` | `python -m <모듈>`의 모듈을 venv python으로 import할 수 없다 | `youtube_learner.*`만 검사. `venv`·`pip`·`pytest`·`yt_dlp`·`http.server`는 예외 |
| `path` | 명령 속 저장소 경로가 없다 | 접두사 `backend/ frontend/ scripts/ docs/ .claude/ history/ desktop/ mobile/`. 백슬래시를 슬래시로 정규화. `<>*?{}`가 있으면 자리표시자로 건너뜀. `data/`·`status/`는 런타임이라 건너뜀 |
| `ps1` | 명령 속 `scripts\*.ps1`이 실재하지 않는다 | 실행 권한 검사 대신 실재 검사 |
| `link` | 마크다운 상대 링크 대상이 없다 | 괄호 깊이를 세어 파일명 속 괄호를 견딤. URL 디코딩 |
| `table` | 표 행 → 빈 줄 → 표 행이고 뒤 표에 구분선이 없다(쪼개짐) | 코드펜스 안은 제외 |
| `bare-path` | 백틱 안 저장소 경로가 실재하지 않는다 | 접두사 규칙 동일. 자리표시자 문자(`* < > { } … $ = \| ·`) 포함 시 건너뜀. `data/`·`status/`·`*.db`·`*.m4a`·`*.json3` 제외. `경로:행`·`경로#절` 접미는 떼고 본다 |

**FR-30.** `backend/tests/integration/test_docs.py`는 (a) 스크립트를 subprocess로 실행해 종료 0을 요구하고, (b) 검사 7종 각각에 대해 **위반을 실제로 잡는지**(tmp 문서로) 역테스트하며, (c) 정당한 경우(활성화 안내 뒤 bare python, 별개의 두 표, 코드펜스 안 파이프, 자리표시자, 존재하는 경로)에 오탐하지 않는지 확인한다.

### 4.12 `frontend/` — 스캐폴드

**FR-31.** `frontend/`에 Vite + React + TypeScript 프로젝트. `npm run build` 성공. Vitest + Testing Library(jsdom). `src/lib/time.ts`의 `formatTimestamp(ms: number): string`은 `0 → "0:00"`, `65000 → "1:05"`, `3_600_000 → "1:00:00"`, 음수·NaN은 `RangeError`(등급 A, 테스트 먼저). `src/lib/api.ts`는 `VITE_API_BASE_URL`(기본 `http://127.0.0.1:8765`)을 내보낸다. `App`은 자리 문구만("화면은 Phase 3").

### 4.13 패키징·설정 파일

**FR-32.** `backend/pyproject.toml`: 이름 `youtube-learner`, `requires-python = ">=3.12,<3.13"`, 기본 의존성 `pydantic`·`pydantic-settings`·`sqlalchemy`(하한·상한; JSON 로깅은 표준 `logging` 포매터로 직접 구현해 의존성을 늘리지 않는다 — 설계서 6절), extras `youtube`(`yt-dlp[default]`, `bgutil-ytdlp-pot-provider`, `youtube-transcript-api`), `stt`(`faster-whisper`), `api`(`fastapi`, `uvicorn`), `jobs`(`huey`), `dev`(`pytest`, `pytest-cov`, `ruff`). pytest: `testpaths=["tests"]`, `pythonpath=["src"]`, `addopts="-q -m 'not e2e'"`, marker `e2e`. coverage: `source=["youtube_learner"]`, `branch=true`, `omit=["*/domain/interfaces.py"]`. setuptools `src` 레이아웃.

**FR-33.** `.env.example`(저장소 루트)에 FR-1의 **모든 키**를 기본값·근거 절 주석과 함께 나열한다. 빈 값 허용 키는 이유를 주석으로.

**FR-34.** `backend/config/` 3종, 각 `"_comment"` 필수:

| 파일 | 키 | 기본값 |
|---|---|---|
| `stt_default.json` | `model`, `presets`, `compute_type`, `cpu_threads`(null → `STT_CPU_THREADS`), `vad_filter`, `beam_size`, `condition_on_previous_text` | `small`, `["small","medium","large-v3-turbo"]`, `int8`, null, true, 1, false |
| `ytdlp_default.json` | `audio_format`, `subtitles_format`, `js_runtime`, `sleep_interval_requests_s` `[min,max]`, `max_retries`, `backoff_base_s`, `backoff_max_s`, `translated_captions` | `bestaudio[ext=m4a]/bestaudio`, `json3`, `node`, `[1,3]`, 3, 2, 60, false |
| `sync_default.json` | `tabs`, `stop_on_known_id`, `full_rescan`, `metadata_batch_size`, `lang_priority` | `["videos","shorts"]`, true, false, 20, `["ko"]` |

## 5. 모듈 구성 및 의존 방향

```
backend/src/youtube_learner/
├── constants.py          # [P0] StrEnum 4종·고정값·split_caption_key            등급 A   (FR-6~8)
├── exceptions.py         # [P0] YoutubeLearnerError 계층                        등급 A   (FR-17)
├── config.py             # [P0] Settings(.env)·파생 경로·process env·JSON 로더   등급 B   (FR-1~5)
├── logging_config.py     # [P0] JsonFormatter·setup_logging·ContextLoggerAdapter 등급 B   (FR-18~19)
├── domain/
│   ├── models.py         # [P0] pydantic 모델 (frozen, extra=forbid)             등급 A   (FR-9~15)
│   └── interfaces.py     # [P0] Protocol 4종 + ProgressCallback                  측정 제외 (FR-16)
├── workflow/
│   └── run_context.py    # [P0] new_run_id·run_context·read_status               등급 A   (FR-20~21)
├── repository/
│   └── db.py             # [P0] make_engine(PRAGMA)·session_factory·init_db      등급 B   (FR-22~23)
├── analysis/
│   ├── null_analyzer.py  # [P0] NullAnalyzer                                     등급 A   (FR-24)
│   └── registry.py       # [P0] AnalyzerRegistry·build_registry                  등급 B   (FR-25)
└── cli/
    └── check_env.py      # [P0] 환경 검사 → ==> READY                            등급 B   (FR-26)

scripts/check_env.ps1     # [P0] venv python 탐색 → -m youtube_learner.cli.check_env       (FR-27)
scripts/verify_docs.py    # [P0] 문서 실검사 7종 (검사 함수 등급 A, main 등급 B)             (FR-28~29)
backend/tests/integration/test_docs.py   # [P0] verify_docs 실행 + 역테스트                  (FR-30)
frontend/src/lib/{time.ts, api.ts}       # [P0] formatTimestamp(A) · API base URL(B)          (FR-31)

의존 방향 (화살표 = import):
  cli/check_env ─▶ config ─▶ constants, exceptions
  cli/check_env ─▶ repository/db ─▶ config
  analysis/registry ─▶ analysis/null_analyzer ─▶ domain/*, exceptions
  workflow/run_context ─▶ config, exceptions, logging_config, constants
  domain/models ─▶ constants            (domain/은 pydantic·표준 라이브러리 외 import 없음)
  domain/interfaces ─▶ domain/models
  logging_config ─▶ config
  scripts/verify_docs.py ─▶ (독립. 저장소 루트·venv python 경로만 안다)
```

원칙: `constants`·`exceptions`는 잎(leaf). `domain/`은 바깥을 모른다. `config`는 `domain`을 모른다(설정은 도메인이 아니다). 순환 없음.

## 6. `constants.py` — 설계 고정값

**대응**: FR-6, FR-7, FR-8

### 1.1 인터페이스

```python
class VideoKind(StrEnum): LONG = "long"; SHORT = "short"; LIVE = "live"
class TranscriptSource(StrEnum): MANUAL = "manual"; AUTO = "auto"; TRANSLATED = "translated"; WHISPER = "whisper"
class TranscriptStatus(StrEnum): NONE = "none"; PENDING = "pending"; DONE = "done"; FAILED = "failed"
class AnalysisKind(StrEnum): SUMMARY = "summary"; KEYPOINTS = "keypoints"; CHAPTERS = "chapters"

ORIGINAL_CAPTION_SUFFIX: Final = "-orig"
LANG_PRIORITY_DEFAULT: Final[tuple[str, ...]] = ("ko",)
PIPELINE_VERSION: Final = "1"
DB_FILENAME: Final = "youtube_learner.db"
STATUS_FILENAME_PATTERN: Final = "{stage}_{run_id}.json"
YT_VIDEO_ID_PATTERN: Final = r"^[A-Za-z0-9_-]{11}$"
YT_CHANNEL_ID_PATTERN: Final = r"^UC[A-Za-z0-9_-]{22}$"
STAGE_NAME_PATTERN: Final = r"^[a-z0-9_]+$"
PACKAGE_NAME: Final = "youtube_learner"
MANUAL_ANALYZER_NAME: Final = "manual"      # v2 — 사용자가 붙여 넣은 요약·정리의 analyses 출처 (scope 2.4절)
MANUAL_ANALYZER_VERSION: Final = "user"

def split_caption_key(key: str) -> tuple[str, bool]: ...   # "ko-orig" → ("ko", True); "" → ValueError
def original_caption_key(language: str) -> str: ...        # "ko" → "ko-orig"
```

### 1.2 설계 판단

- **왜 `StrEnum`인가** — 값이 그대로 DB·JSON·API에 문자열로 들어가고, `VideoKind.LONG == "long"`이 참이어야 P1의 SQLAlchemy 컬럼·P3의 TypeScript 타입과 마찰이 없다. → `Enum` + `.value` 접근은 호출부마다 `.value`를 잊는 사고가 난다. `Literal` 타입만 쓰는 대안은 순회·검증 코드가 흩어진다.
- **왜 `translated`를 지금 넣나** — scope 5.2절이 "옵션"으로 정의했고, 나중에 값을 추가하면 P1 스키마의 CHECK 제약·P3 타입을 다시 고쳐야 한다. 값 집합은 P0에서 닫는다.
- **왜 `split_caption_key`가 여기 있나** — yt-dlp 트랙 키 규칙(`-orig`)은 설계 고정값에 붙은 파생 규칙이다. `transcripts/`(P2)에 두면 P1의 메타 보충(트랙 목록 요약)이 P2를 import하게 된다. → 대안 "P2에서 정의"는 의존 방향을 거꾸로 만든다.
- 패턴 상수는 문자열로 두고 컴파일은 사용처(models)에서 한다 — 상수 모듈이 `re`에 의존하지 않게.

### 1.3 검증 방법

| 등급 | 테스트 파일 | 확인하는 것 |
|---|---|---|
| A | `backend/tests/unit/test_constants.py` | 값 집합이 문서와 일치(하드코딩 대조), `split_caption_key` 정상 3종 + 빈 문자열 거부, 역함수 왕복 |

## 7. `exceptions.py` — 예외 계층

**대응**: FR-17

### 2.1 인터페이스

```python
class YoutubeLearnerError(Exception): ...
class ConfigError(YoutubeLearnerError): ...
class YouTubeAccessError(YoutubeLearnerError):
    def __init__(self, message: str, *, status: int | None = None, retry_after_s: float | None = None) -> None
class TranscriptUnavailableError(YoutubeLearnerError): ...
class SttError(YoutubeLearnerError): ...
class AnalyzerNotConfiguredError(YoutubeLearnerError):
    def __init__(self, message: str, *, available: Sequence[str] = ()) -> None   # .available: tuple[str, ...]
class StorageError(YoutubeLearnerError): ...
class OutputExistsError(StorageError):
    def __init__(self, path: Path) -> None                                     # .path
```

### 2.2 설계 판단

- **왜 단일 베이스인가** — CLI·API 최상위에서 `except YoutubeLearnerError`로 "우리가 예상한 실패"와 "버그"를 나눈다. 예상한 실패는 사용자 메시지+종료 코드 1, 버그는 스택트레이스.
- **왜 `YouTubeAccessError`에 `status`·`retry_after_s`가 있나** — 429 백오프(`CLAUDE.md` 8절)는 예외에서 대기 시간을 읽어야 한다. 메시지 문자열 파싱은 취약하다.
- **왜 `OutputExistsError`가 `StorageError`의 하위인가** — 덮어쓰기 거부는 저장 계층의 규칙(`CLAUDE.md` 6절)이다. 호출부는 `StorageError`로 뭉쳐 잡거나 이것만 따로 잡아 "이미 있음 → 건너뜀"으로 처리한다.
- 메시지는 한국어 한 줄. 구조 필드는 속성. `str(exc)`는 메시지만.

### 2.3 검증 방법

| A | `backend/tests/unit/test_exceptions.py` | 계층(issubclass), 속성 보존, 기본값, `str()` |
|---|---|---|

## 8. `config.py` — 환경별 설정

**대응**: FR-1, FR-2, FR-3, FR-4, FR-5

### 3.1 인터페이스

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", protected_namespaces=())
    data_dir: Path = Path("./data")
    status_dir: Path = Path("./status")
    hf_home: Path | None = None                 # None → data_dir / "models"
    config_dir: Path | None = None              # None → resource_root() / "config"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["json", "text"] = "json"
    api_host: str = "127.0.0.1"
    api_port: int = Field(8765, ge=1, le=65535)
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]   # 콤마 구분 문자열 허용
    ytdlp_js_runtime: str = "node"
    bgutil_script_path: Path = Field(default_factory=_default_bgutil_script)   # project_root()/tools/… — D: 우선 규칙 (정정 2026-09-14)
    bgutil_http_enabled: bool = False
    stt_cpu_threads: int = Field(default_factory=lambda: os.cpu_count() or 1, ge=1)
    analyzers: list[str] = []
    disk_free_warn_gb: float = Field(10, ge=0)

    # 파생 (모두 절대경로, ~ 확장)
    @property def db_path(self) -> Path
    @property def channels_dir(self) -> Path
    @property def models_dir(self) -> Path        # == hf_home 해석값
    @property def resolved_config_dir(self) -> Path

    def ensure_dirs(self) -> None
    def apply_process_env(self) -> None           # HF_HOME, HF_HUB_DISABLE_SYMLINKS_WARNING=1, PYTHONUTF8=1

def resource_root() -> Path            # 개발: backend/ ; PyInstaller frozen: sys._MEIPASS (P4)
def project_root() -> Path             # 저장소 루트(backend/ 의 부모). tools/ 기준. frozen 에서는 resource_root()
def get_settings() -> Settings         # 캐시 없음 — 테스트가 env를 바꿔 여러 번 만든다
def load_json_config(name: str, settings: Settings) -> dict[str, Any]
```

| 입력 | 출력 | 예외 | 부작용 |
|---|---|---|---|
| `.env`·환경변수 | `Settings` | 검증 실패 → pydantic `ValidationError` (CLI가 `ConfigError`로 감싼다) | 없음 |
| `ensure_dirs()` | — | OSError → `ConfigError` | 디렉토리 생성 |
| `apply_process_env()` | — | — | `os.environ` 변경 |
| `load_json_config("stt_default", s)` | dict(`_comment` 제거) | 없음/JSON 오류/`_comment` 없음 → `ConfigError` | 없음 |

### 3.2 설계 판단

- **왜 `HF_HOME` 기본을 `DATA_DIR/models`로 우리가 정하나** — HF 기본(C: 사용자 프로필)은 이 VM에서 여유가 가장 적은 드라이브였고 심볼릭 링크 미지원으로 공간을 더 썼다(T-002). 데이터와 모델을 한 루트 아래 두면 "어디에 얼마나 쓰는가"가 한 곳에서 보인다. `.env`로 다른 드라이브를 지정할 수 있다.
- **왜 `apply_process_env`가 별도 호출인가** — `huggingface_hub`는 import 시점에 `HF_HOME`을 읽는다. Settings 생성 시 자동으로 `os.environ`을 바꾸면 "설정 객체를 만들었더니 환경이 바뀌었다"는 숨은 부작용이 생기고 테스트가 서로 오염된다. → 대안 "생성자에서 자동 적용"은 기각. CLI·API 진입점이 `settings.apply_process_env()`를 **faster_whisper import 전에** 명시 호출한다(P2 계약).
- **왜 `CONFIG_DIR`를 패키지 위치에서 유도하나** — 작업 디렉토리 기준 상대경로는 "어디서 실행했나"에 따라 깨진다(참조 프로젝트 Phase 1 사고와 같은 유형). `resource_root()`가 개발(`backend/`)과 P4 frozen 번들을 구분하는 단일 지점이다.
- **왜 bgutil 스크립트 기본 위치가 저장소 안 `tools/`인가** — 사용자 규칙 "로컬 디스크는 D: 우선"(2026-09-14, `CLAUDE.md` 7절). 플러그인의 기본 경로(`~`)는 홈 디렉토리(C:)다. 저장소 아래에 두면 프로젝트가 있는 드라이브를 자동으로 따르고 git 은 추적하지 않는다. yt-dlp 에는 P2 가 `extractor_args` 로 이 경로를 명시해 넘긴다(`설계서_Architecture` 3.1절). → 대안 "홈 디렉토리 기본값 + .env 덮어쓰기"는 새 PC 에서 규칙을 어기는 기본값이 된다.
- **왜 pydantic-settings인가** — 타입 변환·검증·`.env` 로딩을 한 번에. 콤마 구분 목록(`CORS_ORIGINS`)은 `field_validator(mode="before")`로 분할. → `os.environ` 직접 읽기는 검증이 흩어진다.
- **왜 `_comment`를 필수로 하나** — 설정 JSON은 "왜 이 값인가"를 잃기 쉽다. 파일이 스스로 근거를 들고 다니게 강제한다. 로더가 제거해 코드에 새지 않는다.
- **왜 `get_settings()`에 캐시가 없나** — 테스트가 환경변수를 바꿔 다른 Settings를 만든다. 캐시는 API 앱(P1)이 자기 수명 안에서 한다.

### 3.3 검증 방법

| B | `backend/tests/integration/test_config.py` | 기본값, `.env` 로딩(tmp_path + `monkeypatch.chdir`), 파생 경로 절대화·`~` 확장, 잘못된 값 5종 **거부**, `cors_origins` 콤마 분할, `ensure_dirs` 생성, `apply_process_env` 3키, `load_json_config` 정상 + 3종 거부, 실제 `backend/config/*.json` 3종 로드, `.env.example` 키 집합 == 필드 집합 |
|---|---|---|

## 9. `domain/models.py` — 도메인 모델

**대응**: FR-9 ~ FR-15

### 4.1 인터페이스

```python
class _Frozen(BaseModel): model_config = ConfigDict(frozen=True, extra="forbid")

class ChannelRef(_Frozen):     yt_channel_id: str | None; handle: str | None; url: str
    # validators: 채널ID 패턴 / handle '@' 시작 / 둘 중 하나 필수 (model_validator)
class VideoStub(_Frozen):      yt_video_id: str; kind: VideoKind; title: str; url: str
                               duration_s: int | None = None; view_count: int | None = None; thumbnail_url: str | None = None
    # validators: 영상ID 패턴 / title strip 비어 있음 거부 / 음수 거부
class Video(VideoStub):        upload_date: date | None = None; language: str | None = None; live_status: str | None = None
                               metadata_fetched_at: datetime | None = None; transcript_status: TranscriptStatus = TranscriptStatus.NONE
class TranscriptSegment(_Frozen): idx: int (ge=0); start_ms: int (ge=0); end_ms: int; text: str
    # validators: end_ms >= start_ms / text strip 비어 있음 거부 (text는 strip 저장)
class TranscriptResult(_Frozen): yt_video_id; source: TranscriptSource; language: str; engine: str
                               model_name: str | None = None; pipeline_version: str = PIPELINE_VERSION
                               segments: list[TranscriptSegment] (min_length=1)
    # validators: idx 0..n-1 연속 / start_ms 비감소
    @property full_text -> str   # " ".join(seg.text)
    @property duration_ms -> int # segments[-1].end_ms
class AnalyzerInfo(_Frozen):   name: str; version: str; kinds: list[AnalysisKind]; description: str = ""
class AnalysisResult(_Frozen): yt_video_id; analyzer_name; analyzer_version; kind: AnalysisKind; language: str
                               content: dict[str, Any]; model_info: dict[str, Any] = {}; created_at: datetime
```

### 4.2 설계 판단

- **왜 pydantic이고 dataclass가 아닌가** — 경계(yt-dlp 응답·자막 파일·API 입력)에서 부적합 데이터를 **거부**하는 것이 목적이다. dataclass는 검증이 없고, 직접 쓰면 모델마다 다른 방식이 된다. pydantic v2는 P1 FastAPI 응답 스키마·P3 타입 생성(OpenAPI)에도 그대로 쓰인다.
- **왜 `frozen`인가** — 모델이 계층 사이를 오가며 "누가 어디서 바꿨나"를 추적할 수 없게 되는 것을 막는다. 변경은 `model_copy(update=...)`로 새 객체를 만든다. ORM 행(P1)은 별개 클래스이고 변환 함수가 저장소 계층에 있다(요구사항 8절 리스크 5).
- **왜 `extra="forbid"`인가** — yt-dlp 응답을 `**dict`로 넘기면 조용히 필드가 늘어난다. 매핑은 명시적으로 한다(P1).
- **왜 `VideoStub`와 `Video`를 나누나** — flat 목록(1단계)과 메타 보충(2단계)이 서로 다른 시점에 다른 필드를 채운다(TechSpike 3.1절). 한 클래스에 전부 Optional로 두면 "보충됐는가"를 `metadata_fetched_at`으로만 알 수 있어 타입이 말해주지 않는다. `Video`는 `VideoStub`를 상속해 flat 필드 규칙을 공유한다.
- **왜 `full_text`가 저장 필드가 아니라 속성인가** — 파생물은 원본(세그먼트)에서 계산한다(`CLAUDE.md` 6절 하류 덮어쓰기 금지). DB에는 검색 편의를 위해 저장하되(P2), 도메인 모델에서는 항상 세그먼트가 진실이다.
- **왜 `idx` 연속·`start_ms` 비감소를 검증하나** — json3 파싱(P2)이 잘못되면 순서가 뒤섞인 채 저장되어 화면의 타임스탬프 클릭이 틀린 곳으로 간다. 조용한 오류라 모델이 잡는다.
- `text`는 strip해서 저장한다 — 공백만인 세그먼트는 거부. 정규화(병합·특수문자)는 P2 `normalizer`의 일이고 여기서는 최소 규칙만.

### 4.3 검증 방법

| A | `backend/tests/unit/test_domain_models.py` | 모델별 정상 생성 + **거부 케이스**(패턴 위반, 빈 제목, 음수, end<start, 빈 텍스트, idx 불연속, 시간 역행, 빈 세그먼트, extra 필드, frozen 변경), `full_text`·`duration_ms`, `Video`가 `VideoStub` 규칙 상속 |
|---|---|---|

## 10. `domain/interfaces.py` — Protocol 4종

**대응**: FR-16

### 5.1 인터페이스

```python
ProgressCallback = Callable[[float, str], None]     # (0.0~1.0, 메시지)

@runtime_checkable
class VideoListSource(Protocol):
    def list_tab(self, channel: ChannelRef, kind: VideoKind) -> Iterator[VideoStub]: ...
@runtime_checkable
class TranscriptProvider(Protocol):
    @property def name(self) -> str: ...
    def fetch(self, video: Video, languages: Sequence[str]) -> TranscriptResult | None: ...
@runtime_checkable
class SttEngine(Protocol):
    def transcribe(self, audio_path: Path, language: str | None, on_progress: ProgressCallback | None = None) -> TranscriptResult: ...
@runtime_checkable
class Analyzer(Protocol):
    @property def name(self) -> str: ...
    @property def version(self) -> str: ...
    def info(self) -> AnalyzerInfo: ...
    def analyze(self, transcript: TranscriptResult, kind: AnalysisKind, options: Mapping[str, Any]) -> AnalysisResult: ...
```

### 5.2 설계 판단

- **왜 Protocol이고 ABC가 아닌가** — 구조적 서브타이핑. 테스트 fake·P2 구현체가 이 모듈을 상속하지 않아도 되고, 의존 방향이 한쪽(구현 → domain)으로만 간다. ABC는 "등록"을 강제해 결합을 만든다.
- **왜 `runtime_checkable`인가** — 조립 지점(P1 `api/app.py`, CLI)이 `isinstance(obj, TranscriptProvider)`로 주입 실수를 기동 시 잡는다.
- **왜 `fetch`가 `None`을 반환할 수 있나** — "이 소스에 자막이 없다"는 정상 결과다(체인이 다음으로 넘어간다). 예외는 "시도했는데 실패했다"(429·차단)에만 쓴다. 두 상황을 구분해야 폴백 정책이 선다.
- **왜 `SttEngine.transcribe`가 `TranscriptResult`를 반환하나** — 엔진마다 다른 세그먼트 표현을 도메인 모델로 정규화하는 책임이 엔진 구현체에 있다. 호출부는 엔진 차이를 모른다.
- 실행 로직이 없으므로 커버리지 측정에서 제외한다(`pyproject.toml` omit).

## 11. `logging_config.py` — JSON 한 줄 로깅

**대응**: FR-18, FR-19

### 6.1 인터페이스

```python
class JsonFormatter(logging.Formatter):        # 한 줄 JSON: timestamp(UTC Z) level logger message + extra
class TextFormatter(logging.Formatter):        # "2026-09-14T04:00:00Z INFO  logger  message  {extra}"
def setup_logging(settings: Settings) -> logging.Logger    # 루트 핸들러 교체, stdout, 레벨 적용, 루트 반환
class ContextLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs): ...        # kwargs["extra"] = {**self.extra, **호출부 extra}
    def bind(self, **more) -> "ContextLoggerAdapter"
```

### 6.2 설계 판단

- **왜 python-json-logger를 쓰지 않고 직접 포매터를 쓰나** — 필요한 것은 필드 5개를 JSON 한 줄로 내는 30줄이다. 외부 패키지는 버전·API 변경 위험만 더한다. P4 PyInstaller 번들 크기도 준다. 요구사항 FR-32에서 의존성 목록을 이에 맞춰 정정했다.
- **왜 루트 핸들러를 교체하나** — uvicorn(P1)·huey(P2)가 자기 핸들러를 붙이면 같은 줄이 두 번 나온다. `setup_logging`은 멱등(두 번 호출해도 핸들러 1개)이다.
- **extra 병합 규칙**: 어댑터 컨텍스트(`run_id`·`stage`) 위에 호출부 `extra`(`yt_video_id`)를 얹는다. 표준 `LoggerAdapter`는 호출부 extra를 **덮어써** 버리므로 `process`를 재정의한다. `LogRecord` 예약 이름(`message`·`asctime` 등)과 충돌하는 키는 `ctx_` 접두를 붙인다.
- **왜 stdout인가** — 데스크톱 사이드카(P4)는 stdout을 캡처하고, 서버 배포는 컨테이너 로그가 stdout이다. 파일 로그는 보류(요구사항 9절).

### 6.3 검증 방법

| B | `backend/tests/integration/test_logging_config.py` | JSON 한 줄 파싱 가능·필드·UTC `Z`·`ensure_ascii=False`(한국어 그대로), text 포맷, 두 번 호출 시 핸들러 1개, 레벨 적용, 어댑터 병합(덮지 않음)·`bind` 누적·예약 키 충돌 회피 |
|---|---|---|

## 12. `workflow/run_context.py` — 실행 기록

**대응**: FR-20, FR-21

### 7.1 인터페이스

```python
def new_run_id(now: datetime | None = None) -> str            # "20260914-043000-1a2b3c4d" (UTC)
def status_path(settings: Settings, stage: str, run_id: str) -> Path
@contextmanager
def run_context(stage: str, settings: Settings, logger: logging.Logger | None = None,
                *, run_id: str | None = None, extra: Mapping[str, Any] | None = None
               ) -> Iterator[tuple[str, ContextLoggerAdapter]]     # run_id 주입은 테스트·재실행용 (SelfReview 1.1 정정)
def read_status(path: Path) -> dict[str, Any]
```

상태 파일(JSON, 키 정렬, `ensure_ascii=False`, LF):
```json
{"stage": "sync_channel", "run_id": "20260914-043000-1a2b3c4d", "status": "started|succeeded|failed",
 "started_at": "2026-09-14T04:30:00Z", "finished_at": null, "duration_s": null,
 "error": null | {"type": "YouTubeAccessError", "message": "…"}, "pipeline_version": "1", "extra": {}}
```

### 7.2 설계 판단

- **왜 진입 시점에 `started`를 먼저 쓰나** — 프로세스가 강제 종료되면 `finished_at`이 없는 `started` 파일이 남는다. 그것이 "중간에 죽었다"는 증거다. 끝날 때만 쓰면 죽은 실행은 흔적이 없다.
- **왜 같은 파일을 끝에서 갱신하나(덮어쓰기 금지와의 관계)** — 상태 파일은 한 실행의 기록이고 `started → succeeded|failed`는 같은 기록의 완결이다. 금지하는 것은 **다른 실행**이 같은 파일을 쓰는 것 → `run_id` 충돌 시 `OutputExistsError`(`open(path, "x")`).
- **왜 예외를 재전파하나** — 종료 코드·사용자 메시지는 CLI/API의 책임이다. 컨텍스트 매니저가 삼키면 호출부가 실패를 모른다.
- **왜 `stage` 패턴을 제한하나** — 파일명에 들어간다. 공백·한글·슬래시는 OS별로 다르게 깨진다.
- `now` 주입은 테스트용(결정적 run_id). 랜덤 8 hex는 같은 초에 두 실행이 겹칠 때를 위해서다.

### 7.3 검증 방법

| A | `backend/tests/unit/test_run_context.py` | run_id 형식·주입 시각, 정상 종료 `succeeded`·`duration_s`, 예외 시 `failed`·`error`·재전파, **덮어쓰기 거부**, stage 패턴 거부, 어댑터에 `run_id`·`stage` 포함, `read_status` 왕복 |
|---|---|---|

## 13. `repository/db.py` — SQLite 엔진

**대응**: FR-22, FR-23

### 8.1 인터페이스

```python
class Base(DeclarativeBase): ...
def make_engine(settings: Settings, *, echo: bool = False) -> Engine     # data_dir 생성 + sqlite:///<db_path>, connect 이벤트에서 PRAGMA
def make_session_factory(engine: Engine) -> sessionmaker[Session]
def init_db(engine: Engine) -> dict[str, Any]                            # create_all + {"journal_mode": "wal", "foreign_keys": 1, "busy_timeout": 5000}
```

### 8.2 설계 판단

- **왜 SQLite 단일 파일인가** — 단일 사용자·단일 PC·수천 행. 서버 프로세스가 없어 데스크톱 배포(P4)가 단순하다. → PostgreSQL은 설치·운영 부담이 목적을 넘는다.
- **왜 WAL인가** — API가 읽는 동안 워커가 쓴다(P2). 기본 rollback journal은 쓰기 중 읽기를 막아 화면이 멎는다. `busy_timeout=5000`으로 짧은 잠금 경합은 대기로 넘긴다.
- **왜 `foreign_keys=ON`을 연결마다 켜나** — SQLite는 기본이 OFF이고 연결 단위 설정이다. 연결 풀에서 새 연결이 나올 때마다 켜야 한다(`event.listens_for(engine, "connect")`).
- **왜 `init_db`가 PRAGMA 적용값을 반환하나** — "설정했다"와 "적용됐다"는 다르다(WAL은 파일 DB에서만 유효). 반환값을 테스트가 검증한다(`check_env`는 DB를 열지 않는다 — 검사가 DB 파일을 만들면 안 된다).
- **왜 `data_dir` 생성이 `make_engine`에 있나** — SQLite는 부모 디렉토리가 없으면 파일을 만들지 못한다. 엔진을 만드는 순간이 "이 경로에 DB가 있을 것"을 처음 아는 지점이다. (SelfReview 1.1 정정 — 초판은 `init_db`가 만든다고 적었다)
- Alembic은 P1(첫 테이블)부터. P0는 `Base`만 둔다 — 빈 스키마에 마이그레이션 도구를 얹는 것은 과설계.

### 8.3 검증 방법

| B | `backend/tests/integration/test_db.py` | tmp DB에서 `init_db` 반환값 `wal`·`1`·`5000`, 세션 열고 `SELECT 1`, 두 연결 모두 FK ON, 없는 디렉토리 → 생성 |
|---|---|---|

## 14. `analysis/` — 분석 슬롯

**대응**: FR-24, FR-25

### 9.1 인터페이스

```python
class NullAnalyzer:                        # Analyzer Protocol 만족 (상속 없음)
    name = "null"; version = "0"
    def info(self) -> AnalyzerInfo         # kinds=[]
    def analyze(...) -> NoReturn           # AnalyzerNotConfiguredError(available=())

class AnalyzerRegistry:
    def register(self, analyzer: Analyzer) -> None      # 중복 이름 → ConfigError
    def get(self, name: str) -> Analyzer                # 없음 → AnalyzerNotConfiguredError(available=names 제외 null)
    def names(self) -> list[str]                        # null 제외
    def available(self) -> list[AnalyzerInfo]           # null 제외
def build_registry(settings: Settings) -> AnalyzerRegistry
    # settings.analyzers == [] → NullAnalyzer만
    # 아니면 ConfigError("분석기 '<이름>'은 아직 구현되지 않았다 (Phase 5)")  ← P5가 이름→팩토리 표로 대체
```

### 9.2 설계 판단

- **왜 `NullAnalyzer`가 존재하나** — "분석기 없음"을 `None` 검사로 처리하면 API·화면·작업 코드 곳곳에 `if analyzer is None`이 생긴다. Null 객체는 같은 인터페이스로 "설정되지 않았다"를 **예외로** 말한다. API(P1)는 이 예외를 501로 매핑한다.
- **왜 `available()`에서 null을 빼나** — 화면의 분석기 목록에 "null"이 보이면 사용자는 선택 가능한 것으로 오해한다. null은 내부 표현이다.
- **수동 입력은 왜 `Analyzer`가 아닌가** (v2) — 계산이 없다. 사용자가 외부 AI 챗에서 받아 붙여 넣은 글은 저장소(P1 `analyses`)에 `MANUAL_ANALYZER_NAME` 출처로 바로 기록한다(P3). 레지스트리는 **자동** 분석기만 관리하고, `available()`이 비어 있어도 수동 저장은 된다.
- **왜 `build_registry`가 미구현 이름에 예외를 내나** — `.env`에 `ANALYZERS=ollama`를 적었는데 조용히 무시되면 사용자는 "왜 안 되지"를 몇 시간 찾는다. 기동 시점에 시끄럽게 실패한다.
- P5 완료 기준("`analysis/` 밖 수정 없음")을 지키는 구조: 구현체 추가 = `analysis/` 안에 파일 추가 + `build_registry`의 이름→팩토리 표 한 줄.

### 9.3 검증 방법

| A | `backend/tests/unit/test_null_analyzer.py` | Protocol 만족(`isinstance`), `info().kinds == []`, `analyze` 예외·`available=()` |
| B | `backend/tests/integration/test_analysis_registry.py` | 등록·조회, **중복 거부**, 없는 이름 예외의 `available`, `available()`·`names()`가 null 제외, `build_registry` 기본/미구현 이름 거부 |

## 15. `cli/check_env.py` + `scripts/check_env.ps1` — 환경 검사

**대응**: FR-26, FR-27

### 10.1 인터페이스

```python
class Level(StrEnum): OK = "OK"; WARN = "WARN"; FAIL = "FAIL"
@dataclass(frozen=True) class CheckResult: name: str; level: Level; detail: str

def check_python() -> CheckResult
def check_imports(modules: Sequence[str] = REQUIRED_MODULES) -> list[CheckResult]
def check_node(which=shutil.which, run=subprocess.run) -> CheckResult          # 주입 가능 → 테스트에서 fake
def check_bgutil_script(settings) -> CheckResult
def check_dirs(settings) -> CheckResult
def check_disk(settings, disk_usage=shutil.disk_usage) -> CheckResult          # WARN 기준 settings.disk_free_warn_gb
def check_config_files(settings) -> list[CheckResult]
def check_model_cache(settings) -> CheckResult                                 # WARN if none
def run_checks(settings, **injected) -> list[CheckResult]
def render(results, *, as_json: bool) -> str                                    # 줄 형식 + 마지막 줄 ==> READY | ==> NOT READY (n failures)
def main(argv: Sequence[str] | None = None) -> int                              # 0 / 1 ; --json --strict
```

```powershell
# scripts/check_env.ps1 — 얇은 래퍼
$py = Join-Path $PSScriptRoot "..\backend\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Host "backend\.venv 없음. 생성: py -3.12 -m venv backend\.venv; backend\.venv\Scripts\python.exe -m pip install -e backend[youtube,stt,dev]"; exit 1 }
& $py -m youtube_learner.cli.check_env @args
exit $LASTEXITCODE
```

### 10.2 설계 판단

- **왜 검사 로직을 Python에 두고 `.ps1`은 래퍼인가** — 검사는 테스트 대상(등급 B)이다. PowerShell 로직은 pytest로 검증하기 어렵다. `.ps1`의 유일한 일은 "venv python을 찾는다"이며, 그것이 없을 때의 안내가 곧 설치 절차다.
- **왜 `which`·`run`·`disk_usage`를 주입 가능하게 하나** — "Node가 없을 때 FAIL"을 테스트하려고 실제 Node를 지울 수 없다. 함수 인자 기본값 주입은 mock 라이브러리 없이 fake를 넣는 가장 단순한 방법이다.
- **왜 디스크는 WARN이고 bgutil은 FAIL인가** — 디스크 부족은 "지금 당장 안 되는" 것이 아니라 "곧 문제"다(P4 트리거, 보류 결정 8). bgutil 스크립트 부재는 자막 요청이 **조용히** 저품질로 가는 원인(T-001)이라 막아야 한다.
- **왜 네트워크를 호출하지 않나** — READY 판정이 YouTube 상태에 흔들리면 무관한 작업이 막힌다. 차단 감지는 P2 작업 실패 카운트의 일이다(요구사항 8절 리스크 4).
- 출력 형식은 `[LEVEL] 이름 — 실측`으로 고정 — 사람과 `verify_docs`가 문서에 복사된 출력을 대조하기 쉽게.

### 10.3 검증 방법

| B | `backend/tests/integration/test_check_env.py` | 각 검사 함수 OK/FAIL/WARN 경로(fake 주입), `render` 형식·마지막 줄, `--json` 파싱, `--strict`로 WARN→실패, 실제 환경에서 `main([])` == 0 (이 VM은 READY여야 함), bgutil 경로를 없는 곳으로 바꾸면 FAIL |
|---|---|---|

## 16. `scripts/verify_docs.py` + `backend/tests/integration/test_docs.py` — 문서 실검사

**대응**: FR-28, FR-29, FR-30

### 11.1 인터페이스

```python
ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = ROOT / "backend" / ".venv" / "Scripts" / "python.exe"
DOC_GLOBS = ("README.md", "CLAUDE.md", "docs/*.md", "docs/internal/*.md", "docs/internal/templates/*.md", "docs/internal/qa/*.md")
REPO_PREFIXES = ("backend/", "frontend/", "scripts/", "docs/", ".claude/", "history/", "desktop/", "mobile/")
RUNTIME_PREFIXES = ("data/", "status/")
FENCES = {"powershell", "pwsh", "bash", "sh", "shell", "console"}

class Finding: doc, line_no, kind, detail
def command_lines(text) -> list[tuple[int, str]]      # 펜스 안 명령 줄 (주석·프롬프트 기호 제거, 백슬래시 → 슬래시 정규화 사본 제공)
def check_venv(doc, text, commands) -> list[Finding]
def check_modules(doc, commands) -> list[Finding]
def check_paths(doc, commands) -> list[Finding]        # kind "path" | "ps1"
def check_links(doc, text) -> list[Finding]
def check_tables(doc, text) -> list[Finding]
def check_bare_paths(doc, text) -> list[Finding]
def verify(doc) -> list[Finding]
def main(argv=None) -> int                             # --path, --quiet
```

### 11.2 설계 판단

- **Windows 규칙의 핵심 세 가지** — (1) venv 힌트는 `backend\.venv\Scripts\python.exe`(슬래시 표기 포함) 전체 경로 또는 앞선 `Activate.ps1`; (2) 경로 토큰의 백슬래시를 슬래시로 바꿔 실재 검사(`scripts\verify_docs.py` → `scripts/verify_docs.py`); (3) 실행 권한 대신 `.ps1` 실재. `$env:NAME`·`$py` 같은 PowerShell 변수 토큰은 경로가 아니므로 `$`가 있으면 건너뛴다.
- **왜 `data/`·`status/`를 건너뛰나** — 런타임 산출물은 새 clone에 없다. 문서가 "만들어진다"고 안내하는 경로다.
- **왜 접두사가 없는 경로(`domain/models.py`)는 보지 않나** — 설계서 관행인 패키지 상대 표기는 의도가 여러 가지라 기계가 판정할 수 없다. 접두사가 있는 경로는 뜻이 하나다. 참조 프로젝트가 오탐 11건으로 확인한 규칙을 그대로 채택한다.
- **왜 `history/`를 검사하지 않나** — 사후에 고치지 않는 기록이다(`CLAUDE.md` 11절). 검사하면 "고칠 수 없는 위반"이 쌓여 관문이 무시된다. (구 docs/prompts/ 제외 규칙은 방법론 v2 로 그 디렉토리가 없어져 삭제했다 — 2026-09-16)
- **왜 템플릿은 검사하나** — 템플릿의 자리표시자는 `<>{}`로 건너뛰고, 그 밖의 경로(`docs/internal/templates/README.md` 등)는 실재해야 한다. 템플릿이 깨진 경로를 퍼뜨리는 것을 막는다.
- 구조(검사 함수 1개 = kind 1개, `Finding`)는 참조와 같다 — 역테스트를 함수 단위로 쓰기 위해서다.

### 11.3 검증 방법

| B | `backend/tests/integration/test_docs.py` | (a) 저장소 전체 `main(["--quiet"])`==0 subprocess; (b) 역테스트 7종: bare python 위반 / 없는 모듈 / 없는 경로(백슬래시 표기) / 없는 `.ps1` / 깨진 링크 / 쪼개진 표 / 없는 백틱 경로; (c) 오탐 방지 6종: 전체 경로 python 허용, `Activate.ps1` 뒤 bare python 허용, `$env:` 토큰 무시, 별개의 두 표, 코드펜스 안 파이프, 자리표시자·`data/`·`경로:행` |
|---|---|---|

## 17. `frontend/` — 스캐폴드

**대응**: FR-31

### 12.1 구성

```
frontend/
├── package.json          # scripts: dev / build(tsc --noEmit && vite build) / test(vitest run) / test:watch
├── vite.config.ts        # react plugin, test: { environment: "jsdom", globals: true, setupFiles }
├── tsconfig.json         # strict, ES2022, react-jsx, include src
├── index.html
└── src/
    ├── main.tsx  App.tsx            # 자리 문구
    ├── lib/time.ts  lib/time.test.ts   # formatTimestamp (A, 테스트 먼저)
    ├── lib/api.ts   lib/api.test.ts    # API_BASE_URL (B)
    └── test/setup.ts                   # @testing-library/jest-dom
```

`formatTimestamp(ms)`: `Math.floor(ms/1000)` → `h:mm:ss`(h≥1) 또는 `m:ss`. 음수·NaN·Infinity → `RangeError`.
`API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8765"` (끝 슬래시 제거).

### 12.2 설계 판단

- **왜 지금 스캐폴드만 만드나** — P3 화면 설계 전에 UI를 만들면 설계서 없는 코드가 된다. 그러나 빌드·테스트 파이프라인(`npm test`·`npm run build`)이 P0 완료 기준에 있어야 P3가 "코드만" 얹을 수 있다.
- **왜 `create-vite` 대화형 대신 파일을 직접 두나** — 비대화형 셸에서 프롬프트가 멈춘다. 파일 8개면 충분하고 버전을 우리가 고른다.
- **왜 TanStack Query 등 런타임 의존성을 넣지 않나** — 디스크 여유가 4GB 안팎(C 4.78 / D 3.90GB)이다. 필요할 때(P3) 설계와 함께 추가한다.
- `formatTimestamp`가 A등급인 이유 — 스크립트 뷰어의 모든 세그먼트에 붙는 순수 함수. 틀리면 전부 틀린다.

### 12.3 검증 방법

| A | `frontend/src/lib/time.test.ts` | 0 / 65000 / 3_600_000 / 3_661_000 / 반올림 아닌 내림 / 음수·NaN·Infinity 거부 |
| B | `frontend/src/lib/api.test.ts` | 기본값, 끝 슬래시 제거 |

## 18. 설정값 배치 (하드코딩 금지 — CLAUDE.md 5절)

| 값 | 위치 | 이유 |
|---|---|---|
| 데이터·상태·모델 경로, 포트, CORS, 런타임 이름, bgutil 경로, 스레드 수, 분석기 목록, 디스크 기준 | `.env` → `Settings` | 환경마다 다르다 |
| kind/source/status/kind 값, `-orig`, 파이프라인 버전, DB 파일명, status 패턴, ID 패턴 | `constants.py` | 설계상 고정. 바뀌면 재생성·마이그레이션이 필요한 값 |
| Whisper 모델·프리셋·VAD·beam, yt-dlp 포맷·간격·재시도·번역 옵션, 동기화 탭·증분 규칙·배치 크기·언어 우선순위 | `backend/config/*.json` | 실행마다 조절. `_comment`로 근거 동반 |
| `check_env` 필수 모듈 목록, `verify_docs` 접두사·펜스 목록 | 각 스크립트 모듈 상수 | 도구 자체의 규칙. 설정으로 빼면 검사가 약해진다 |

## 19. 구현 순서

| 순서 | 작업 | 등급 | 테스트 먼저? | 산출물 |
|---|---|---|---|---|
| 1 | `backend/pyproject.toml`, `.env.example`, `backend/config/*.json` 3종, `pip install -e backend[youtube,stt,dev]` | — | — | 패키징·설정 |
| 2 | `constants.py`, `exceptions.py` | A | 예 | + `tests/unit/test_constants.py`, `test_exceptions.py` |
| 3 | `domain/models.py`, `domain/interfaces.py` | A | 예 | + `tests/unit/test_domain_models.py` |
| 4 | `config.py` | B | 아니오 | + `tests/integration/test_config.py` |
| 5 | `logging_config.py` | B | 아니오 | + `tests/integration/test_logging_config.py` |
| 6 | `workflow/run_context.py` | A | 예 | + `tests/unit/test_run_context.py` |
| 7 | `repository/db.py` | B | 아니오 | + `tests/integration/test_db.py` |
| 8 | `analysis/null_analyzer.py`, `analysis/registry.py` | A / B | 예 / 아니오 | + `tests/unit/test_null_analyzer.py`, `tests/integration/test_analysis_registry.py` |
| 9 | `scripts/verify_docs.py` → `tests/integration/test_docs.py` | A(함수)/B | 역테스트 동반 | 문서 검사 통과까지 문서 수정 |
| 10 | `cli/check_env.py`, `scripts/check_env.ps1` | B | 아니오 | + `tests/integration/test_check_env.py` |
| 11 | `frontend/` 스캐폴드 → `time.test.ts` 먼저 → `time.ts` → `api.ts` | A / B | 예 / 아니오 | `npm test`·`npm run build` |
| 12 | 커버리지 측정 → `docs/internal/P0_실측기록_Common.md` | — | — | 테스트결과서 |

## 20. 비기능 요구사항

| 항목 | 기준 |
|---|---|
| 테스트 등급 A (≥ 90%) | `constants.py`, `domain/models.py`, `workflow/run_context.py`, `analysis/null_analyzer.py`, `scripts/verify_docs.py`(검사 함수), `frontend/src/lib/time.ts` — **테스트 먼저** |
| 테스트 등급 B (≥ 70%) | `config.py`, `logging_config.py`, `repository/db.py`, `analysis/registry.py`, `cli/check_env.py`, `frontend/src/lib/api.ts` |
| A+B 가중 | ≥ 80% |
| 테스트 배치 | A → `backend/tests/unit/`, B → `backend/tests/integration/`, 파일 1:1(`test_<module>.py`) |
| 거부 케이스 | 모델 검증·설정 검증·상태 파일 덮어쓰기·레지스트리 중복은 **거부 테스트 필수** |
| 추적성 | 모듈 docstring 첫 줄 `<역할> — 대응: docs/P0_설계서_Common.md N절 (FR-x~y). 등급 A|B` |
| 하드코딩 금지 | FR-1(.env) / FR-6·7(constants) / FR-34(json) 3분류 준수. 코드에 경로·포트·모델명 리터럴 없음 |
| 재현성 | `new_run_id`·`full_text`·`split_caption_key`는 같은 입력에 같은 출력. 상태 파일 JSON은 키 정렬·`ensure_ascii=False`·LF |
| 인코딩 | 모든 파일 쓰기 `encoding="utf-8"`, `newline="\n"` |
| 문서 검증 | `scripts/verify_docs.py` 종료 0, pytest 포함 |
| 성능 | 이 Phase 목표 없음. `check_env`는 10초 이내(네트워크 호출 없음) |

## 21. 산출물

| 산출물 | 종류 | 경로 |
|---|---|---|
| 요구사항정의서 | 문서 | `docs/P0_설계서_Common.md` |
| 설계서 | 문서 | `docs/P0_설계서_Common.md` |
| 테스트결과서 | 문서 | `docs/internal/P0_실측기록_Common.md` |
| 공통 모듈 | 코드 | `backend/src/youtube_learner/` — `config.py` `constants.py` `exceptions.py` `logging_config.py` `domain/` `workflow/` `repository/db.py` `analysis/` `cli/check_env.py` |
| 테스트 | 테스트 | `backend/tests/unit/`, `backend/tests/integration/`, `backend/tests/conftest.py` |
| 스크립트 | 코드 | `scripts/check_env.ps1`, `scripts/verify_docs.py` |
| 프론트 | 코드 | `frontend/` (Vite+React+TS, Vitest) |
| 설정 | 설정 | `backend/pyproject.toml`, `.env.example`, `backend/config/stt_default.json` `ytdlp_default.json` `sync_default.json` |
| 내부 | 문서 | `docs/internal/P0_실측기록_Common.md`, `docs/internal/P0_학습가이드_Common.md`, `history/` 세션 기록 |

## 22. 완료 기준 (Acceptance Criteria)

- [ ] FR-1~34 전건에 대응하는 테스트가 존재하고 통과한다 (테스트결과서 4절)
- [ ] 등급 A 커버리지 ≥ 90%, B ≥ 70%, A+B ≥ 80% 실측 기록 (테스트결과서 3절)
- [ ] `.\scripts\check_env.ps1` 마지막 줄 `==> READY`, 종료 코드 0 — 출력 복사 (테스트결과서 5절)
- [ ] `check_env`가 bgutil 스크립트를 임시로 숨기면 `[FAIL]`과 `NOT READY`를 낸다 (거부 케이스, 통합 테스트)
- [ ] `backend\.venv\Scripts\python.exe scripts\verify_docs.py` 종료 코드 0, pytest에 포함되어 함께 돈다
- [ ] 검사 7종 각각의 역테스트가 통과한다 (`test_docs.py`)
- [ ] `frontend`: `npm test` 통과(`formatTimestamp` 거부 케이스 포함), `npm run build` 성공
- [ ] `build_registry(settings)`의 `available()`이 빈 목록이고 `get("summary")`가 `AnalyzerNotConfiguredError`를 낸다
- [ ] 상태 파일 덮어쓰기 시 `OutputExistsError`; 예외 발생 시 `failed` 기록 후 재전파
- [ ] `.env.example`의 키 집합 == `Settings` 필드 집합 (테스트로 대조)
- [ ] `backend/config/*.json` 3종 모두 `_comment` 보유, 로더 통과
- [ ] 모듈·테스트 docstring 첫 줄 규약(대응 절·FR·등급) 전 파일 준수 (테스트로 대조)
- [ ] `scripts/verify_docs.py` 종료 0

## 23. 리스크 및 참고사항

| # | 리스크 | 대응 | 확인 시점 |
|---|---|---|---|
| 1 | `.env` 키를 P0에 전부 확정했는데 P1~P2에서 이름이 바뀐다 | 키는 **추가만** 허용, 변경 시 정정 이력 + `.env.example`·Settings 대조 테스트가 잡는다 | 매 Phase |
| 2 | `verify_docs`의 Windows 규칙 오탐(백슬래시·드라이브 문자·PowerShell 변수 `$env:`) | 역테스트에 오탐 케이스 포함, 위반 발견 시 규칙 좁히고 테스트 추가 | P0 테스트 |
| 3 | 프론트 스캐폴드 의존성(node_modules)이 디스크를 압박 | 여유 확인 후 설치(실측 155 패키지 102MB). `node_modules`는 git 미추적 | P0 |
| 4 | `check_env`가 네트워크 호출 없이 판정하므로 YouTube 차단 상태는 못 본다 | 의도된 범위. 차단 감지는 P2 실패 카운트 | P2 |
| 5 | pydantic `frozen` 모델과 SQLAlchemy ORM 사이 변환 비용 | P1에서 ORM ↔ 도메인 변환 함수를 저장소 계층에 둔다 | P1 |

## 24. 보류 결정 등재 후보

| 결정 | 왜 지금 안 하나 | 트리거 | 판정법 |
|---|---|---|---|
| `check_env` 디스크 경고 기준값(임시 10GB) | P4 빌드 요구 용량 미측정 | P4 프롬프트 | P4 빌드 산출물 크기 실측 → `DISK_FREE_WARN_GB` 갱신 (보류 결정 8에 흡수) |
| 로그 파일 출력(현재 stdout만) | 데스크톱 앱에서 로그를 어디에 남길지는 P4 사이드카 설계에 종속 | P4 | 사이드카 stdout 캡처 방식 확정 후 `LOG_FILE` 키 추가 여부 |

## 25. ⚠️ 다음 Phase 인계

| 항목 | 내용 | 받는 Phase |
|---|---|---|
| `Settings.apply_process_env()` 호출 계약 | faster-whisper import **전에** 진입점이 호출 | P2 |
| `resource_root()` frozen 분기 | `sys.frozen`/`_MEIPASS` 처리 자리만 있음 — 실제 검증은 패키징 시 | P4 |
| `Base` 빈 스키마 | 첫 테이블(`channels`·`videos`·`analyses`)과 Alembic 초기 리비전 | P1 |
| `build_registry` 미구현 이름 예외 | 이름→팩토리 표로 대체 | P5 |
| `check_env` 디스크 기준 10GB 임시 | P4 빌드 실측 후 갱신 | P4 |
| `VideoStub`/`Video` ↔ ORM 변환 함수 | 저장소 계층에 둔다 | P1 |

## 26. 관련 문서

| 문서 | 관계 |
|---|---|
| `docs/P0_설계서_Common.md` | 상위 — FR 정의 |
| `docs/설계서_Architecture.md` 2절·5절·6절·7절·9절 | 상위 — 전체 골격·DIP 경계·규약 |
| `docs/internal/P0_실측기록_Common.md` | 근거 — 실측(원어 트랙, bgutil, HF 캐시, 코어 수) |
| `docs/internal/검토서_트러블슈팅.md` T-001·T-002 | 근거 — `check_env` 항목, `HF_HOME` 기본값 |
| `docs/internal/templates/README.md` | 문서 규약 |
