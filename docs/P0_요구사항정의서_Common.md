# P0 요구사항정의서 — Common

- 상위 문서: `docs/scope-definition.md` (v2) 2.4절·4절·5.3절·7절·8절, `docs/설계서_Architecture.md` (v2) 2절·5절·6절·7절·9절
- 사용 프롬프트: `docs/prompts/phase0/scope-and-common-modules-v1.md`, `docs/prompts/phase0/scope-and-common-modules-v2.md` (v2 개정 — FR-1 bgutil 경로, FR-7 MANUAL 상수)
- 규칙: `CLAUDE.md` 4절 1단계 산출물. 다음 산출물은 `docs/P0_설계서_Common.md`
- 선행 검증: `docs/internal/P0_검토서_TechSpike.md` (2026-09-14 실측)
- 작성일: 2026-09-14 / 작성 LLM: Fable 5.1
- 상태: 초안

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

## 4. 기능 요구사항

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

**FR-28.** 검사 대상: `README.md`, `CLAUDE.md`, `docs/*.md`, `docs/internal/*.md`, `docs/internal/templates/*.md`. 제외: `docs/prompts/`(요구사항 기록), `history/`(사후 수정 금지). `--path <상대경로>`로 단일 문서, `--quiet`로 위반만 출력. 종료 코드 0/1.

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

## 5. 비기능 요구사항

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

## 6. 산출물

| 산출물 | 종류 | 경로 |
|---|---|---|
| 요구사항정의서 | 문서 | `docs/P0_요구사항정의서_Common.md` |
| 설계서 | 문서 | `docs/P0_설계서_Common.md` |
| 테스트결과서 | 문서 | `docs/P0_테스트결과서_Common.md` |
| 공통 모듈 | 코드 | `backend/src/youtube_learner/` — `config.py` `constants.py` `exceptions.py` `logging_config.py` `domain/` `workflow/` `repository/db.py` `analysis/` `cli/check_env.py` |
| 테스트 | 테스트 | `backend/tests/unit/`, `backend/tests/integration/`, `backend/tests/conftest.py` |
| 스크립트 | 코드 | `scripts/check_env.ps1`, `scripts/verify_docs.py` |
| 프론트 | 코드 | `frontend/` (Vite+React+TS, Vitest) |
| 설정 | 설정 | `backend/pyproject.toml`, `.env.example`, `backend/config/stt_default.json` `ytdlp_default.json` `sync_default.json` |
| 내부 | 문서 | `docs/internal/P0_검토서_SelfReview.md`, `docs/internal/P0_학습가이드_Common.md`, `history/` 세션 기록 |

## 7. 완료 기준 (Acceptance Criteria)

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

## 8. 리스크 및 참고사항

| # | 리스크 | 대응 | 확인 시점 |
|---|---|---|---|
| 1 | `.env` 키를 P0에 전부 확정했는데 P1~P2에서 이름이 바뀐다 | 키는 **추가만** 허용, 변경 시 정정 이력 + `.env.example`·Settings 대조 테스트가 잡는다 | 매 Phase |
| 2 | `verify_docs`의 Windows 규칙 오탐(백슬래시·드라이브 문자·PowerShell 변수 `$env:`) | 역테스트에 오탐 케이스 포함, 위반 발견 시 규칙 좁히고 테스트 추가 | P0 테스트 |
| 3 | 프론트 스캐폴드 의존성(node_modules)이 디스크를 압박 | 여유 확인 후 설치(실측 155 패키지 102MB). `node_modules`는 git 미추적 | P0 |
| 4 | `check_env`가 네트워크 호출 없이 판정하므로 YouTube 차단 상태는 못 본다 | 의도된 범위. 차단 감지는 P2 실패 카운트 | P2 |
| 5 | pydantic `frozen` 모델과 SQLAlchemy ORM 사이 변환 비용 | P1에서 ORM ↔ 도메인 변환 함수를 저장소 계층에 둔다 | P1 |

## 9. 보류 결정 등재 후보

| 결정 | 왜 지금 안 하나 | 트리거 | 판정법 |
|---|---|---|---|
| `check_env` 디스크 경고 기준값(임시 10GB) | P4 빌드 요구 용량 미측정 | P4 프롬프트 | P4 빌드 산출물 크기 실측 → `DISK_FREE_WARN_GB` 갱신 (보류 결정 8에 흡수) |
| 로그 파일 출력(현재 stdout만) | 데스크톱 앱에서 로그를 어디에 남길지는 P4 사이드카 설계에 종속 | P4 | 사이드카 stdout 캡처 방식 확정 후 `LOG_FILE` 키 추가 여부 |
