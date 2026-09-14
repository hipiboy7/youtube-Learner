# P0 설계서 — Common

- 상위 문서: `docs/P0_요구사항정의서_Common.md` (초안 2026-09-14) 4절 FR-1~34, `docs/설계서_Architecture.md` (v1) 2절·5절·6절·7절·9절
- 규칙: `CLAUDE.md` 4절 2단계 산출물. 다음 산출물은 코드+테스트(3절 등급, A는 테스트 먼저) → `docs/P0_테스트결과서_Common.md`
- 작성일: 2026-09-14 / 작성 LLM: Fable 5.1
- 상태: 초안

## 0. 모듈 구성 및 의존 방향

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

## 1. `constants.py` — 설계 고정값

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

## 2. `exceptions.py` — 예외 계층

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

## 3. `config.py` — 환경별 설정

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
    bgutil_script_path: Path = Path("~/bgutil-ytdlp-pot-provider/server/build/generate_once.js")
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
- **왜 pydantic-settings인가** — 타입 변환·검증·`.env` 로딩을 한 번에. 콤마 구분 목록(`CORS_ORIGINS`)은 `field_validator(mode="before")`로 분할. → `os.environ` 직접 읽기는 검증이 흩어진다.
- **왜 `_comment`를 필수로 하나** — 설정 JSON은 "왜 이 값인가"를 잃기 쉽다. 파일이 스스로 근거를 들고 다니게 강제한다. 로더가 제거해 코드에 새지 않는다.
- **왜 `get_settings()`에 캐시가 없나** — 테스트가 환경변수를 바꿔 다른 Settings를 만든다. 캐시는 API 앱(P1)이 자기 수명 안에서 한다.

### 3.3 검증 방법

| B | `backend/tests/integration/test_config.py` | 기본값, `.env` 로딩(tmp_path + `monkeypatch.chdir`), 파생 경로 절대화·`~` 확장, 잘못된 값 5종 **거부**, `cors_origins` 콤마 분할, `ensure_dirs` 생성, `apply_process_env` 3키, `load_json_config` 정상 + 3종 거부, 실제 `backend/config/*.json` 3종 로드, `.env.example` 키 집합 == 필드 집합 |
|---|---|---|

## 4. `domain/models.py` — 도메인 모델

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

## 5. `domain/interfaces.py` — Protocol 4종

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

## 6. `logging_config.py` — JSON 한 줄 로깅

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

## 7. `workflow/run_context.py` — 실행 기록

**대응**: FR-20, FR-21

### 7.1 인터페이스

```python
def new_run_id(now: datetime | None = None) -> str            # "20260914-043000-1a2b3c4d" (UTC)
def status_path(settings: Settings, stage: str, run_id: str) -> Path
@contextmanager
def run_context(stage: str, settings: Settings, logger: logging.Logger | None = None, *, extra: Mapping[str, Any] | None = None
               ) -> Iterator[tuple[str, ContextLoggerAdapter]]
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

## 8. `repository/db.py` — SQLite 엔진

**대응**: FR-22, FR-23

### 8.1 인터페이스

```python
class Base(DeclarativeBase): ...
def make_engine(settings: Settings, *, echo: bool = False) -> Engine     # sqlite:///<db_path>, connect 이벤트에서 PRAGMA
def make_session_factory(engine: Engine) -> sessionmaker[Session]
def init_db(engine: Engine) -> dict[str, Any]                            # create_all + {"journal_mode": "wal", "foreign_keys": 1, "busy_timeout": 5000}
```

### 8.2 설계 판단

- **왜 SQLite 단일 파일인가** — 단일 사용자·단일 PC·수천 행. 서버 프로세스가 없어 데스크톱 배포(P4)가 단순하다. → PostgreSQL은 설치·운영 부담이 목적을 넘는다.
- **왜 WAL인가** — API가 읽는 동안 워커가 쓴다(P2). 기본 rollback journal은 쓰기 중 읽기를 막아 화면이 멎는다. `busy_timeout=5000`으로 짧은 잠금 경합은 대기로 넘긴다.
- **왜 `foreign_keys=ON`을 연결마다 켜나** — SQLite는 기본이 OFF이고 연결 단위 설정이다. 연결 풀에서 새 연결이 나올 때마다 켜야 한다(`event.listens_for(engine, "connect")`).
- **왜 `init_db`가 PRAGMA 적용값을 반환하나** — "설정했다"와 "적용됐다"는 다르다(WAL은 파일 DB에서만 유효). 반환값을 `check_env`가 표시하고 테스트가 검증한다.
- Alembic은 P1(첫 테이블)부터. P0는 `Base`만 둔다 — 빈 스키마에 마이그레이션 도구를 얹는 것은 과설계.

### 8.3 검증 방법

| B | `backend/tests/integration/test_db.py` | tmp DB에서 `init_db` 반환값 `wal`·`1`·`5000`, 세션 열고 `SELECT 1`, 두 연결 모두 FK ON, 없는 디렉토리 → 생성 |
|---|---|---|

## 9. `analysis/` — 분석 슬롯

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
- **왜 `build_registry`가 미구현 이름에 예외를 내나** — `.env`에 `ANALYZERS=ollama`를 적었는데 조용히 무시되면 사용자는 "왜 안 되지"를 몇 시간 찾는다. 기동 시점에 시끄럽게 실패한다.
- P5 완료 기준("`analysis/` 밖 수정 없음")을 지키는 구조: 구현체 추가 = `analysis/` 안에 파일 추가 + `build_registry`의 이름→팩토리 표 한 줄.

### 9.3 검증 방법

| A | `backend/tests/unit/test_null_analyzer.py` | Protocol 만족(`isinstance`), `info().kinds == []`, `analyze` 예외·`available=()` |
| B | `backend/tests/integration/test_analysis_registry.py` | 등록·조회, **중복 거부**, 없는 이름 예외의 `available`, `available()`·`names()`가 null 제외, `build_registry` 기본/미구현 이름 거부 |

## 10. `cli/check_env.py` + `scripts/check_env.ps1` — 환경 검사

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

## 11. `scripts/verify_docs.py` + `backend/tests/integration/test_docs.py` — 문서 실검사

**대응**: FR-28, FR-29, FR-30

### 11.1 인터페이스

```python
ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = ROOT / "backend" / ".venv" / "Scripts" / "python.exe"
DOC_GLOBS = ("README.md", "CLAUDE.md", "docs/*.md", "docs/internal/*.md", "docs/internal/templates/*.md")
SKIP_DIRS = ("docs/prompts",)
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
- **왜 `docs/prompts/`를 검사하지 않나** — 요구사항 기록이라 고치지 않는다(`CLAUDE.md` 10절). 검사하면 "고칠 수 없는 위반"이 쌓여 관문이 무시된다.
- **왜 템플릿은 검사하나** — 템플릿의 자리표시자는 `<>{}`로 건너뛰고, 그 밖의 경로(`docs/internal/templates/README.md` 등)는 실재해야 한다. 템플릿이 깨진 경로를 퍼뜨리는 것을 막는다.
- 구조(검사 함수 1개 = kind 1개, `Finding`)는 참조와 같다 — 역테스트를 함수 단위로 쓰기 위해서다.

### 11.3 검증 방법

| B | `backend/tests/integration/test_docs.py` | (a) 저장소 전체 `main(["--quiet"])`==0 subprocess; (b) 역테스트 7종: bare python 위반 / 없는 모듈 / 없는 경로(백슬래시 표기) / 없는 `.ps1` / 깨진 링크 / 쪼개진 표 / 없는 백틱 경로; (c) 오탐 방지 6종: 전체 경로 python 허용, `Activate.ps1` 뒤 bare python 허용, `$env:` 토큰 무시, 별개의 두 표, 코드펜스 안 파이프, 자리표시자·`data/`·`경로:행` |
|---|---|---|

## 12. `frontend/` — 스캐폴드

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
- **왜 TanStack Query 등 런타임 의존성을 넣지 않나** — 디스크 4.7GB. 필요할 때(P3) 설계와 함께 추가한다.
- `formatTimestamp`가 A등급인 이유 — 스크립트 뷰어의 모든 세그먼트에 붙는 순수 함수. 틀리면 전부 틀린다.

### 12.3 검증 방법

| A | `frontend/src/lib/time.test.ts` | 0 / 65000 / 3_600_000 / 3_661_000 / 반올림 아닌 내림 / 음수·NaN·Infinity 거부 |
| B | `frontend/src/lib/api.test.ts` | 기본값, 끝 슬래시 제거 |

## 13. 설정값 배치 (하드코딩 금지 — CLAUDE.md 5절)

| 값 | 위치 | 이유 |
|---|---|---|
| 데이터·상태·모델 경로, 포트, CORS, 런타임 이름, bgutil 경로, 스레드 수, 분석기 목록, 디스크 기준 | `.env` → `Settings` | 환경마다 다르다 |
| kind/source/status/kind 값, `-orig`, 파이프라인 버전, DB 파일명, status 패턴, ID 패턴 | `constants.py` | 설계상 고정. 바뀌면 재생성·마이그레이션이 필요한 값 |
| Whisper 모델·프리셋·VAD·beam, yt-dlp 포맷·간격·재시도·번역 옵션, 동기화 탭·증분 규칙·배치 크기·언어 우선순위 | `backend/config/*.json` | 실행마다 조절. `_comment`로 근거 동반 |
| `check_env` 필수 모듈 목록, `verify_docs` 접두사·펜스 목록 | 각 스크립트 모듈 상수 | 도구 자체의 규칙. 설정으로 빼면 검사가 약해진다 |

## 14. 구현 순서

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
| 12 | 커버리지 측정 → `docs/P0_테스트결과서_Common.md` | — | — | 테스트결과서 |

## 15. ⚠️ 다음 Phase 인계

| 항목 | 내용 | 받는 Phase |
|---|---|---|
| `Settings.apply_process_env()` 호출 계약 | faster-whisper import **전에** 진입점이 호출 | P2 |
| `resource_root()` frozen 분기 | `sys.frozen`/`_MEIPASS` 처리 자리만 있음 — 실제 검증은 패키징 시 | P4 |
| `Base` 빈 스키마 | 첫 테이블(`channels`·`videos`·`analyses`)과 Alembic 초기 리비전 | P1 |
| `build_registry` 미구현 이름 예외 | 이름→팩토리 표로 대체 | P5 |
| `check_env` 디스크 기준 10GB 임시 | P4 빌드 실측 후 갱신 | P4 |
| `VideoStub`/`Video` ↔ ORM 변환 함수 | 저장소 계층에 둔다 | P1 |

## 16. 관련 문서

| 문서 | 관계 |
|---|---|
| `docs/P0_요구사항정의서_Common.md` | 상위 — FR 정의 |
| `docs/설계서_Architecture.md` 2절·5절·6절·7절·9절 | 상위 — 전체 골격·DIP 경계·규약 |
| `docs/internal/P0_검토서_TechSpike.md` | 근거 — 실측(원어 트랙, bgutil, HF 캐시, 코어 수) |
| `docs/internal/검토서_트러블슈팅.md` T-001·T-002 | 근거 — `check_env` 항목, `HF_HOME` 기본값 |
| `docs/internal/templates/README.md` | 문서 규약 |
