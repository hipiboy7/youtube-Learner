# youtubeLearner 프로젝트 기획서

- 일자: 2026-09-14 / 승인: 2026-09-14 (사용자, plan mode)
- 요청 LLM 모델: Fable 5.1
- 성격: 프로젝트 기획서 — 방법론 적합성 판정 + 기술 아키텍처 + Phase 로드맵. 모든 Phase 문서의 요구사항 원본
- 대응 산출물: `docs/scope-definition.md`, `docs/설계서_Architecture.md`, `CLAUDE.md`
- 비고: 세션 plan 파일을 그대로 보존한 것. 이후 판단 변경은 이 파일을 고치지 않고 scope-definition 개정 이력에 남긴다


## Context

사용자는 특정 유튜브 채널을 선택하면 그 채널의 **롱폼/숏폼 영상 목록**을 추출하고, 각 영상의 **전체 스크립트**를 확보하여 학습에 활용하는 프로그램을 원한다. 스크립트는 유튜브 자막이 없으면 **음성에서 직접 추출(STT)** 해야 한다. 요약·핵심 도출 기능은 v1에서 제외하되, **나중에 붙일 수 있는 슬롯(인터페이스 + UI 자리)** 만 마련한다.

확정된 결정(사용자 답변):
- 백엔드 **Python(FastAPI)**, STT는 **로컬 faster-whisper**(외부 API 없음). 요약은 슬롯만.
- 프론트 **React 웹 → Tauri(데스크톱) → Capacitor(모바일)**. 백엔드는 항상 별도 API 서버.
- 규모: 한국어 채널, 채널당 수백 개로 시작 → 다국어·수천 개 확장 가능 구조.
- 순서: **스크립트 추출 구현 → 빌드/배포 → 요약은 이후 플러그인.**
- 진행 방식: 기존 프로젝트 `SDS-MW-Team/embedding-based-llm-classifier`의 **문서 주도·Phase형 방법론**을 따른다. 문서 수준은 **참조와 동일**(심사 전용 문서만 제외). **혼자 진행**(PR 없이 `merge --no-ff`, 브랜치 보존). 원격은 **개인 GitHub**(사용자가 저장소 생성 후 URL 전달).

로컬 환경(실측): Windows Server 2022, Python 3.12/3.14, Node 24, **ffmpeg 없음, GPU 없음**, RAM 16GB, Xeon CPU, `gh` 없음(git 자격증명 있음). → Whisper는 CPU 전용, 셸은 PowerShell.

---

## 1. 참조 방법론 적합성 판정 — "따를 수 있다, 다섯 곳만 조정"

참조 저장소를 복제해 `CLAUDE.md`·`README`·워크플로 프롬프트·문서 템플릿·코드/테스트 규약·에이전트 정의를 분석했다.

### 1.1 그대로 채택

| 요소 | 내용 |
|---|---|
| 루트 단일 `CLAUDE.md` | 0절 프로젝트 요약 → 1절 Phase 절차 + **보류된 결정 표**(트리거·기계 판정법·이정표 3요소) → SOLID → TDD 3등급 → Phase 내부 4단계 → 하드코딩 금지 3분류 → Workflow 친화·멱등성 → 외부 연동 규칙 → 문서 파일명 규칙 → 요구사항–산출물 페어링 → Git 규칙 → 데이터 규칙 |
| Phase 사이클 | 선행 확인 → 요구사항 도출 → **Claude가 작업 프롬프트 작성·사용자 승인·`docs/prompts/phase{N}/`에 저장** → `impl-phase{N}` 분기 → 요구사항정의서 → 설계서 → 코드+테스트 → 테스트결과서 → 실연동 테스트 → SelfReview → 학습가이드 → Direct 리뷰(전체 재독) → 종료 루틴 → `merge --no-ff`(브랜치 보존) |
| 문서 세트 | `docs/`: `P{N}_요구사항정의서/설계서/테스트결과서`, `scope-definition.md`, `설계서_Architecture.md` / `docs/internal/`: `P{N}_검토서_SelfReview`, `P{N}_학습가이드`, `검토서_트러블슈팅`, `용어집`, `설계서_Agents`, `qa/` / `docs/prompts/phase{N}/<산출물>-v{k}.md` / `history/<날짜>_<작업자>_<주제>.md` |
| 문서 관행 | 머리말 불릿 메타 블록(상위 문서·절번호, 사용 프롬프트, 규칙, 작성일/작성 LLM, 상태/결과/결론), **FR 번호**(`**FR-1.**` + `| 값 | 근거 |`), 요구사항정의서 7절 **체크박스 완료 기준** ↔ 테스트결과서 7절 대조, 설계서의 **"설계 판단" 절**(왜 + 기각 대안), 테스트결과서 4절 **FR 전건 검증표**, 제자리 개정 + 머리 개정 이력(삭제 금지) |
| 코드 규약 | 모듈 docstring 첫 줄 `<역할> — 대응: docs/P{N}_설계서_*.md N절 (FR-x~y). 등급 A/B`; pydantic v2 모델 + `typing.Protocol` 인터페이스(ABC·dataclass 미사용); `Settings(BaseSettings)`로 `.env`; 단일 베이스 예외 + 외부 서비스별 하위 예외; JSON 한 줄 로깅(진입점 1회 setup); CLI `Trigger/Input/Output/사전조건` docstring + `_parse_args/_run/main` 분리; `run_context`로 `status/<phase>_<run_id>.json`; 출력 존재 시 덮어쓰기 거부 |
| 테스트 규약 | A→`tests/unit`(테스트 먼저) / B→`tests/integration` / E2E→`tests/e2e`(`-m e2e`, 기본 제외); 파일 1:1 대응; 테스트 docstring에 FR 번호; 거부 케이스 필수; **`scripts/verify_docs.py`를 pytest에 포함**(문서 속 명령·경로·링크·표 실검사 + 검사기 역테스트) |
| 운영 규약 | `.env.example`에 전체 키 + 근거 절번호 주석; `config/*.json`마다 `"_comment"`; 런타임 상태·대용량 산출물 미커밋 |
| 에이전트/스킬 | `.claude/agents/doc-consistency.md`(읽기 전용 전체 재독 → 어긋남 목록), `.claude/skills/troubleshoot/SKILL.md`(해결 직후 `T-0NN` 기록) — **그대로 이식**(프로젝트명·독서 순서만 치환) |

### 1.2 조정해서 채택

| 항목 | 참조 | 우리 조정안 | 이유 |
|---|---|---|---|
| **디렉토리 골격** | Python 단일 패키지 | **모노레포** `backend/`(참조와 같은 `src/` 레이아웃) + `frontend/` + `desktop/` + `mobile/`. `docs/ history/ scripts/ .claude/`는 루트 | 프론트가 있고 3개 플랫폼으로 확장. 도구 경계를 디렉토리로 분리 |
| **Phase 정의** | ML 파이프라인(데이터→임베딩→학습→검증→추론) | **제품 기능**: P0 범위+공통 → P1 채널·영상목록 → P2 스크립트 → P3 웹 UI → P4 빌드·배포 → P5 분석 플러그인 → P6 모바일 | 사용자 요구 순서(추출→배포→요약) |
| **"완성본 참조" 단계** | 각 Phase 착수 시 완성본 해당 Phase 읽고 `검토서_ReferenceComparison` | **"기술 검증(TechSpike)" 단계**: 프롬프트 작성 **전에** yt-dlp·faster-whisper 등을 **실제 호출**해 동작·제약을 확인하고 `docs/internal/P{N}_검토서_TechSpike.md`에 기록 | 따라갈 완성본이 없음. 대신 외부 라이브러리가 문서와 다르게 동작할 위험이 가장 큼(참조 8절 "실제 호출로 검증"의 취지) |
| **선행 기동 확인** | `start_aipro_plus.sh` → `==> READY` | `scripts/check_env.ps1` → venv(3.12)·Node·bgutil 서버·Whisper 모델 캐시·DB 확인 → `==> READY` | 외부 컨테이너 대신 로컬 도구 의존성 |
| **OS/셸** | RHEL·bash·`.venv/bin/python` | **Windows·PowerShell**·`.venv\Scripts\python.exe`. 스크립트 `.ps1`. `verify_docs.py`의 venv 전제·경로 검사를 Windows 규칙으로 | 개발 환경 |
| **데이터 규칙** | JSONL·클래스 균형 | **SQLite가 기록 원본**(WAL). 원본 자막(json3)·Whisper 원출력은 **파일로 보존**, 정규화본은 별도. 스크립트 레코드가 `source/engine/model/pipeline_version`을 **동반 저장** | 관계 데이터. "조용한 불일치" 방지 취지 동일 |
| **TDD 등급 대상** | text_cleaner, split… | A: URL/핸들 파싱, 롱/숏 판정, json3→세그먼트 파싱·병합·정규화, 작업 상태기계, 프론트 순수 유틸(Vitest) / B: yt-dlp·Whisper 래퍼(fake), 파이프라인, FastAPI 라우트, React 컴포넌트(MSW) / C: 실제 YouTube·STT E2E | 대상만 바뀜 |
| **배포 형태** | Docker 배치 컨테이너(선택) | **Windows 설치파일**(PyInstaller onedir 사이드카 + Tauri NSIS) 1차. Docker는 서버 배포용 선택지(P6에서 판단) | 데스크톱 앱이 목표 |
| **PR/리뷰** | Phase 3·4만 PR, 사수 리뷰 | **PR 없음**. SelfReview → 사용자 Direct 리뷰 → `merge --no-ff`. 브랜치 보존 | 혼자 진행 |
| **문서 템플릿** | 이전 문서를 보고 따라 씀(템플릿 파일 없음) | `docs/internal/templates/`에 5종 골격(요구사항정의서·설계서·테스트결과서·SelfReview·학습가이드) 추가 | 참조 프로젝트의 구조를 새 프로젝트에서 동일하게 재현하려면 명시적 골격이 필요 |

### 1.3 제외 (심사 과제 전용)

`docs/결과보고서_Final.md`·`report-writer` 에이전트, `검토서_성능개선측정.md`(§7.5 대장), `docs/artifacts/` 심사 자료, `prompt-finest` 에이전트(필요 시 추후), 기간계(AIPro+) 연동 규칙 8절 → **"YouTube/yt-dlp 연동 규칙"으로 교체**.

---

## 2. 기술 아키텍처 (2026-09-14 기술 검증 결과 반영)

### 2.1 검증된 기술 결정

| 영역 | 결정 | 검증 근거 |
|---|---|---|
| 목록 추출 | **yt-dlp** `extract_flat="in_playlist"`, 탭 URL 분리 `/@handle/videos`·`/@handle/shorts`(플레이리스트 아닌 **탭** 사용 — 숏츠 플레이리스트는 100개 상한 버그 #11130). flat 결과에 `upload_date` 없음 → 영상별 메타 보충 작업을 **증분**으로 | yt-dlp 2026.08.19 |
| 자막 | yt-dlp `json3`(`skip_download`) 1순위 → `youtube-transcript-api` 1.2.4 2순위 → Whisper 3순위. **PO 토큰 필수화**(#14307)로 `bgutil-ytdlp-pot-provider` 2.0.0을 같은 venv에 설치(Node 20+ 필요, Node 24 있음). JS 런타임은 `yt-dlp[default]` + `js_runtimes=node` | 2026-09 문서·이슈 |
| 오디오 | `bestaudio[ext=m4a]/bestaudio`, 후처리 없음 → **ffmpeg 바이너리 불필요**. 디코딩은 PyAV(ffmpeg 라이브러리 내장). 변환이 필요해지면 `imageio-ffmpeg` 휠 | PyAV 18.1 abi3 휠 |
| STT | **faster-whisper 1.2.1 / ctranslate2 4.8.2**(cp312·cp314 win 휠 있음). 기본 모델 `large-v3-turbo` int8(RAM ~1.5GB), 프리셋 `small/medium` 선택. `vad_filter=True, beam_size 1~2, cpu_threads=물리코어`. 속도는 **P2 벤치마크로 확정**(예상 실시간의 0.3~1배, 불확실). `SttEngine` Protocol로 whisper.cpp(`pywhispercpp`) 교체 가능 | PyPI·커뮤니티 벤치 |
| Python | **3.12 고정**(PyInstaller·라이브러리 성숙도). 3.14는 CI 매트릭스로 준비 상태만 추적 | |
| 작업 큐 | **Huey + SqliteHuey**, thread worker(Windows는 process worker 미지원). 네트워크 큐 1워커(레이트리밋) / STT 큐 1워커(CPU) 분리. UI 상태용 자체 `jobs` 테이블은 별도 유지 | Redis 등 추가 인프라 0 |
| 저장소 | **SQLite(WAL) + SQLAlchemy 2.x + Alembic**. 스키마: `channels, videos(kind: long/short/live), transcripts(source: manual/auto/translated/whisper), transcript_segments, jobs, analyses(v2 예약)` + 선택 FTS5 | |
| 프론트 | React + Vite + TS + TanStack Query. API base URL 설정 가능(모바일 대비) | |
| 데스크톱 | **Tauri v2 사이드카**: `bundle.externalBin` + `shell:allow-spawn`, PyInstaller **onedir**(onefile 금지 — 자식 PID 종료 불가·기동 느림), `PYTHONUTF8=1`, hidden imports(ctranslate2·onnxruntime·tokenizers·huggingface_hub·faster_whisper assets), 종료 시 `taskkill /T`, 사이드카에 버전 리소스(NSIS 교체 문제 #15134) | Tauri 문서·이슈 |
| 모바일 | Capacitor v8이 `frontend/dist`를 감싸고 원격 FastAPI 호출. CORS 허용목록, Android cleartext(개발) 또는 HTTPS, 서버 URL 설정 화면 | |

### 2.2 핵심 인터페이스 (P0에서 `domain/interfaces.py`에 확정)

```python
class VideoListSource(Protocol):      # yt-dlp ↔ (보류) YouTube Data API
    def list_tab(self, channel: ChannelRef, tab: Literal["videos","shorts"]) -> Iterator[VideoStub]: ...
class TranscriptProvider(Protocol):   # 체인: YtDlpCaption → YoutubeTranscriptApi → Whisper
    name: str
    def fetch(self, video: Video, langs: list[str]) -> TranscriptResult | None: ...
class SttEngine(Protocol):            # FasterWhisperEngine ↔ (보류) WhisperCppEngine
    def transcribe(self, audio_path: Path, language: str | None, on_progress) -> TranscriptResult: ...
class Analyzer(Protocol):             # v1: NullAnalyzer만. P5에서 Extractive/Ollama/Claude
    name: str; version: str
    def analyze(self, transcript: TranscriptResult, kind: AnalysisKind, opts: dict) -> AnalysisResult: ...
```
분석 슬롯: `analyses` 테이블·`GET /analyzers`·`POST /videos/{id}/analyses`(v1은 501 + 사용 가능 분석기 목록)·프론트 "분석" 탭("설정된 분석기 없음")까지 **P0~P3에서 자리만** 만든다.

### 2.3 디렉토리 골격 (목표 형태)

```
youtubeLearner/
├── CLAUDE.md  README.md  .env.example  .gitignore
├── .claude/agents/doc-consistency.md   .claude/skills/troubleshoot/SKILL.md
├── backend/
│   ├── pyproject.toml                 # name youtube-learner, requires-python >=3.12,<3.13
│   ├── config/*.json                  # stt_default.json, ytdlp_default.json, sync_default.json ("_comment" 필수)
│   ├── src/youtube_learner/
│   │   ├── config.py constants.py exceptions.py logging_config.py          # [P0]
│   │   ├── domain/{models.py, interfaces.py}                               # [P0] pydantic + Protocol
│   │   ├── repository/  (sqlite db, 파일 산출물 경계)                       # [P0 골격, P1~]
│   │   ├── workflow/run_context.py                                          # [P0]
│   │   ├── analysis/{registry.py, null_analyzer.py}                         # [P0 슬롯]
│   │   ├── youtube/     (channel_resolver, tab_lister, metadata_fetcher)    # [P1]
│   │   ├── transcripts/ (providers, json3_parser, normalizer, chain)        # [P2]
│   │   ├── stt/         (faster_whisper_engine, audio_fetcher)              # [P2]
│   │   ├── jobs/        (huey tasks: sync_channel, fetch_transcript, transcribe)  # [P2]
│   │   ├── api/         (FastAPI app, routers: health channels videos transcripts jobs analyzers)  # [P1~P3]
│   │   └── cli/         (run_sync.py, run_transcripts.py, serve.py)
│   └── tests/{unit,integration,e2e}/  conftest.py
├── frontend/   (Vite+React+TS; Vitest)                                      # [P0 스캐폴드, P3]
├── desktop/    (Tauri v2, src-tauri)                                        # [P4]
├── mobile/     (Capacitor)                                                  # [P6]
├── scripts/    check_env.ps1  verify_docs.py  dev.ps1  build_backend.ps1
├── data/ status/  (gitignore; 기본 ./data, .env DATA_DIR로 이동 가능 — 배포 시 %LOCALAPPDATA%)
├── docs/  docs/internal/  docs/internal/templates/  docs/internal/qa/  docs/prompts/phase{N}/
└── history/
```

---

## 3. Phase 로드맵

| Phase | 명칭 | 핵심 산출물 | 완료 판정(기계 확인) |
|---|---|---|---|
| **0** | 범위 정의 + 공통 모듈 | `scope-definition.md`, `설계서_Architecture.md`, `CLAUDE.md`, 문서 템플릿 5종, 에이전트/스킬 이식, `backend` 공통 모듈(config/constants/domain/exceptions/logging/run_context/analysis 슬롯)+테스트, `frontend` 스캐폴드, `check_env.ps1`, `verify_docs.py`, `P0_검토서_TechSpike`(yt-dlp 탭 목록·json3 자막·faster-whisper 30초 실측) | `check_env.ps1`→READY, `pytest` 통과(A≥90%), `verify_docs.py` 종료 0, `npm run build` 성공 |
| **1** | 채널·영상 목록 | 채널 URL/핸들 해석, `/videos`·`/shorts` 탭 리스팅, 증분 동기화(알려진 id 도달 시 중단, 전체 재스캔 옵션), 메타 보충 작업, `channels/videos` 테이블·API·CLI | 300개+ 채널과 숏츠 100개+ 채널이 **전량** 목록화; 재동기화 시 신규만 추가(멱등) |
| **2** | 스크립트 파이프라인 | Provider 체인, json3 파싱→세그먼트, 언어 우선순위(ko→en→any), 오디오 다운로드→Whisper 작업, Huey 큐·재시도·진행률·재시작, **small/medium/turbo 벤치마크** | 수동자막 영상→`manual`, 자동만→`auto`, 없음→`whisper`; 워커 강제 종료 후 재개; 벤치표 기록 |
| **3** | 웹 UI | 채널 추가/동기화, 롱폼·숏폼 탭 그리드, 타임스탬프 스크립트 뷰어(클릭→임베드 seek), 작업 모니터, 설정(언어·모델·스레드·서버 URL), **분석 탭 플레이스홀더** | Vitest A/B 통과, 주요 흐름 수동 시나리오 체크리스트 |
| **4** | 빌드·배포 | PyInstaller onedir 사이드카, Tauri 데스크톱(헬스체크 대기·정상 종료), NSIS 설치파일, 모델 최초 사용 시 다운로드(진행률) | **Python·ffmpeg 없는 깨끗한 Windows VM**에서 설치→채널 동기화→Whisper 1건 성공 |
| **5** | 분석 플러그인 | `ExtractiveAnalyzer`(기본) + `OllamaAnalyzer`/`ClaudeAnalyzer`(설정 토글), 세그먼트 청킹, `analyses` 기록, UI 렌더 | 분석기 교체가 `analysis/` 밖 코드 수정 없이 됨 |
| **6** | 모바일 | Capacitor Android, 서버 URL 설정, CORS/HTTPS 안내 | 폰에서 PC 서버 접속해 스크립트 열람 |

P5/P6 순서는 P4 종료 시 판단(보류 결정 5).

---

## 4. Phase 0 실행 계획 (승인 후 즉시 착수하는 범위)

방법론 사이클을 Phase 0에 그대로 적용한다. 순서를 건너뛰지 않는다.

1. **저장소 초기화** — `git init`, `.gitignore`(Python+Node 템플릿 + `.venv/ status/ data/ *.db *.m4a` 등), README 초안을 `main` 첫 커밋. 사용자가 개인 GitHub 저장소 생성 후 URL 전달 → `git remote add origin` → push. `impl-phase0` 분기.
2. **기술 검증(TechSpike)** — Python 3.12 venv, `yt-dlp[default]`+`bgutil-ytdlp-pot-provider`+`faster-whisper` 설치. 실제 채널 1개로 `/videos`·`/shorts` flat 목록, json3 자막 1건, 30초 오디오 Whisper(small) 실측. 결과·소요시간·확인 일자를 `docs/internal/P0_검토서_TechSpike.md`에 기록. (여기서 나온 사실이 scope-definition의 근거가 된다)
3. **작업 프롬프트** — `docs/prompts/phase0/scope-and-common-modules-v1.md`를 작성해 사용자에게 설명·승인.
4. **`docs/scope-definition.md`** — 1 개요 / 2 기능 정의(롱폼·숏폼·스크립트·분석 슬롯) / 3 외부 서비스(YouTube·yt-dlp 실측 사실) / 4 데이터 모델·보존 원칙 / 5 STT 전략 / 6 성공 기준 / 7 Phase 로드맵(3절) / 8 실행 환경 / 9 In·Out of Scope / 10 작업 원칙.
5. **`docs/설계서_Architecture.md`** — 참조 12절 구조 유지(0 경계 규약 / 1 개요 / 2 모듈·DIP 경계 / 3 외부 연동 / 4 데이터 흐름·파일 명명 / 5 STT·분석 슬롯 설계 / 6 Workflow·멱등성 규약 / 7 기술 스택·값의 3분류·도입하지 않은 것 / 8 배포 구성 / 9 테스트 전략 / 10 디렉토리 / 11 추적성 / 12 개정 이력).
6. **`CLAUDE.md`** — 참조 절 구조를 유지하되 0절(요약·환경·핵심 상수), 1절 선행 확인(`check_env.ps1`)·보류 결정 초기표(5절), 8절을 "YouTube/yt-dlp 연동 규칙"으로 교체, 11절 Git(혼자·PR 없음), 12절 데이터 규칙(SQLite·원본 보존).
7. **문서 템플릿** — `docs/internal/templates/` 5종 + `docs/internal/용어집.md`(초기 항목: 롱폼·숏폼·PO 토큰·json3·VAD·int8·멱등성 등).
8. **에이전트/스킬 이식** — `doc-consistency.md`(독서 순서·프로젝트명 치환), `troubleshoot/SKILL.md`. `docs/internal/설계서_Agents.md`에 이식 근거.
9. **P0 4단계 산출** — `P0_요구사항정의서_Common.md`(FR-1~) → `P0_설계서_Common.md` → 코드(config/constants/domain/exceptions/logging_config/workflow/analysis 슬롯; 테스트 먼저) + `frontend` 스캐폴드 + `scripts/check_env.ps1`·`verify_docs.py`·`tests/integration/test_docs.py` → `P0_테스트결과서_Common.md`(등급별 실측 커버리지).
10. **자체 점검·학습가이드** — `docs/internal/P0_검토서_SelfReview.md`, `docs/internal/P0_학습가이드_Common.md`.
11. **history** — `history/2026-09-14_park.sei_workspace-setup.md`(작업자 표기는 사용자 지정 가능).
12. **Direct 리뷰 → `merge --no-ff` → push.** 브랜치 보존.

### Phase 0 산출물 — 참조에서 재사용할 것(경로)

| 우리 파일 | 참조 원본(스크래치패드 복제본) | 재사용 방식 |
|---|---|---|
| `CLAUDE.md` | `ref-repo/CLAUDE.md` | 절 구조·문장 톤 유지, 내용 교체 |
| `scripts/verify_docs.py`, `backend/tests/integration/test_docs.py` | `ref-repo/scripts/verify_docs.py`, `tests/integration/test_docs.py` | Windows 경로·`.venv\Scripts`·`.ps1` 검사로 개조 |
| `backend/src/youtube_learner/{config,constants,exceptions,logging_config}.py`, `workflow/run_context.py` | `ref-repo/src/embedding_classifier/` 동명 파일 | 패턴 재구현(복사 금지 원칙 — "근거는 우리 것으로") |
| `.claude/agents/doc-consistency.md`, `.claude/skills/troubleshoot/SKILL.md` | 동명 | 프로젝트명·독서 순서만 치환 |
| `.env.example`, `backend/config/*.json` 주석 관행 | `ref-repo/.env.example`, `config/*.json` | 형식 재사용 |

---

## 5. 보류된 결정 — 초기 표 (CLAUDE.md 1절에 등재)

| # | 열린 결정 | 트리거 | 기계 판정법 | 이정표 |
|---|---|---|---|---|
| 1 | 분석 엔진(추출식/Ollama/Claude API) | P5 착수 | `GET /analyzers`가 `null`만 반환하는가 | scope 2절·5절 |
| 2 | Whisper 기본 모델(small/medium/large-v3-turbo) | P2 벤치마크 | `backend/config/stt_default.json` `model` + `P2_테스트결과서` 벤치표(x실시간·RAM) | P2_설계서 |
| 3 | 숏폼 판정 기준(탭 기반 vs 길이 보조) | P1 실측 | 같은 `yt_video_id`가 두 탭에 모두 나오는 건수 | P1_검토서_TechSpike |
| 4 | Python 3.14 전환 | P4 패키징 후 | CI 매트릭스 3.14 통과 여부 | 설계서_Architecture 7절 |
| 5 | P5(분석) vs P6(모바일) 순서 | P4 종료 | 사용자 결정 기록(`qa/`) | scope 7절 |
| 6 | 서버 배포(Docker) 여부 | P6 착수 | 모바일이 LAN 밖 접속을 요구하는가 | 설계서_Architecture 8절 |
| 7 | YouTube Data API 키 병행 | yt-dlp 목록 차단 발생 시 | `VideoListSource` 구현체 2개 존재 여부 | scope 3절 |

---

## 6. 주요 리스크와 대응

1. **YouTube 봇 차단·PO 토큰·EJS 변경** — bgutil 제공자 + Node 동봉, provider 체인이 Whisper로 강하(degrade), 요청 간 1~3초 지터·네트워크 워커 1개, yt-dlp 버전 고정 + 설정에서 업데이트 경로.
2. **CPU STT가 수천 개 규모에 느림** — 자막 우선 정책(한국어 채널 대부분 자동자막 있음), 큐 우선순위·야간 배치, 모델 프리셋, UI에 예상 소요시간 표시, `SttEngine` 교체 가능.
3. **패키징 취약(PyInstaller+ctranslate2/onnxruntime, 사이드카 수명)** — onedir, hidden-import 목록, 프로세스 트리 종료, P4 초반에 깨끗한 VM 빌드 검증.
4. **문서 부담으로 진행 지연** — 템플릿 5종으로 작성 비용 절감, `verify_docs`·`doc-consistency`로 정합성 검사 자동화.

---

## 7. 검증 방법 (Phase 0 기준, 이후 Phase는 각 테스트결과서에 명시)

```powershell
.\scripts\check_env.ps1                       # ==> READY
.\backend\.venv\Scripts\python.exe -m pytest  # backend 전체 (e2e 제외), test_docs 포함
.\backend\.venv\Scripts\python.exe -m pytest --cov=youtube_learner --cov-report=term   # A ≥ 90%, B ≥ 70%
.\backend\.venv\Scripts\python.exe scripts\verify_docs.py                            # 종료 0
cd frontend; npm test; npm run build
git log --oneline --graph main                # impl-phase0 merge --no-ff 커밋 + 브랜치 보존 확인
```
TechSpike 실측(yt-dlp 탭 목록 건수, json3 1건, Whisper 30초 소요시간)은 `docs/internal/P0_검토서_TechSpike.md`에 **실제 출력 복사**로 기록한다.
