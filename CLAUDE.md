# CLAUDE.md — 작업 규칙

`youtubeLearner` 프로젝트(유튜브 채널 롱폼·숏폼 목록 + 스크립트 추출, 자막 → 로컬 Whisper)에서
코드·문서를 만들 때 항상 지켜야 할 규칙이다.

- **무엇을/왜**: [`docs/scope-definition.md`](docs/scope-definition.md)
- **어떻게**: [`docs/설계서_Architecture.md`](docs/설계서_Architecture.md)
- **어떤 규칙으로**: 이 문서 (충돌 시 이 문서 우선)
- **기획서(승인 2026-09-14)**: [`docs/prompts/phase0/project-plan-v1.md`](docs/prompts/phase0/project-plan-v1.md)

## 0. 프로젝트 요약 (작업 전 필수 확인)

- **목적**: 사용자가 고른 유튜브 채널의 **롱폼·숏폼 영상 목록**과 각 영상의 **전체 스크립트**(세그먼트+타임스탬프)를 확보해 학습에 쓴다.
- **스크립트 소스 우선순위**: 수동 자막(`manual`) → 원어 자동 자막(`auto`, yt-dlp 트랙 키 `<lang>-orig`) → 로컬 faster-whisper(`whisper`, CPU). 번역 자막은 기본 꺼짐 — **다른 언어를 요청하면 HTTP 429**가 난다(실측 2026-09-14).
- **자동 요약·핵심 도출은 v1에 없다.** `Analyzer` Protocol·레지스트리(`NullAnalyzer`)·자동 분석 API 501·화면 **자리만** 만든다(구현은 Phase 5). **수동 흐름은 v1 이다**(사용자 결정 2026-09-14): 스크립트 **원클릭 복사** → 사용자가 외부 AI 챗에서 요약 → **'요약 및 정리' 메뉴에 붙여 넣어 저장**(`analyses`, `analyzer_name="manual"`) — Phase 3.
- **롱/숏 판정은 탭 소속**(`/videos` vs `/shorts`)이다. 길이로 판정하지 않는다(롱폼 탭에 42초 영상 실재).
- **스택**: Python 3.12 (`backend\.venv`), FastAPI, SQLite(WAL)+SQLAlchemy, Huey(SQLite), yt-dlp[default]+bgutil PO 토큰 제공자(Node), faster-whisper int8, React+Vite+TS → Tauri(P4) → Capacitor(P6).
- **개발 환경(실측)**: Windows Server 2022, **물리 코어 1/논리 2**, RAM 16GB, GPU 없음, 디스크 여유 C·D 각 **5GB 미만**, Node 24, ffmpeg·Rust·gh 없음, 사내 고정 IP(프록시 없음). → STT 워커 1개·기본 모델 `small`, 모델 캐시는 `HF_HOME`으로 지정, **Phase 4 전 디스크 확보**(보류 결정 8).
- **핵심 상수**(`constants.py`): `VideoKind = long|short|live`, `TranscriptSource = manual|auto|whisper`(+옵션 `translated`), `ORIGINAL_CAPTION_SUFFIX = "-orig"`, `LANG_PRIORITY_DEFAULT = ["ko"]`, `PIPELINE_VERSION`, `MANUAL_ANALYZER_NAME = "manual"`(수동 요약 출처), DB 파일 `youtube_learner.db`.
- **자연키**: `yt_channel_id`(UC…), `yt_video_id`. 스크립트 유일성은 (video, source, language, model_name, pipeline_version).
- **외부 서비스 3종**: YouTube(yt-dlp 경유) / bgutil PO 토큰 제공자(저장소 안 `tools/bgutil-ytdlp-pot-provider/server/build/generate_once.js` — git 미추적, Node ≥ 20) / Hugging Face Hub(모델 1회 다운로드). YouTube Data API·클라우드 STT/LLM은 쓰지 않는다.

## 1. Phase 진행 절차 (반복 사이클)

총 7단계(Phase 0~6)를 아래 절차로 반복한다. 각 Phase는 **완료 기준을 충족할 때까지** 이 사이클을 돈다.

| Phase | 명칭 | 산출물 |
|---|---|---|
| 0 | 범위 정의 + 공통 모듈 | 상위 문서 3종, 템플릿, 에이전트/스킬, `config`/`constants`/`domain`/`exceptions`/`logging_config`/`workflow`/`repository/db`/`analysis` 슬롯 + 테스트, 프론트 스캐폴드, `check_env`·`verify_docs` |
| 1 | 채널·영상 목록 | 채널 해석, `/videos`·`/shorts` 탭 리스팅, 증분 동기화, 메타 보충, DB 스키마(`channels`·`videos`·`analyses`), API·CLI |
| 2 | 스크립트 파이프라인 | Provider 체인, json3 파싱·정규화, 오디오→Whisper, Huey 큐·재시도·재개, 모델 벤치마크 |
| 3 | 웹 UI | React 화면 일체 — 목록·뷰어(**원클릭 복사**)·**'요약 및 정리' 수동 입력·저장(API 포함, `analyses` manual)**·작업·설정, 자동 분석 자리 |
| 4 | 빌드·배포 | PyInstaller onedir 사이드카 + Tauri + NSIS, 모델 최초 다운로드. **깨끗한 Windows VM 검증** |
| 5 | 분석 플러그인 | **자동** 분석기 구현(`analysis/` 안에서만), `analyses` 자동 결과, 화면에 출처(`manual`/분석기) 표시 |
| 6 | 모바일 | Capacitor Android, 서버 URL 설정 |

### 각 Phase의 진행 순서

0. **⚠️ 환경 확인 (필수 선행)** — 가장 먼저 실행한다.

   ```powershell
   .\scripts\check_env.ps1
   ```

   마지막 줄이 `==> READY`가 아니면 그 Phase의 개발·테스트·검증을 시작하지 않는다. 무엇이 빠졌는지는 출력이 말해준다
   (venv 3.12 · 필수 패키지 · Node ≥ 20 · bgutil 스크립트 · `DATA_DIR` 쓰기 가능 · 디스크 여유). 몇 번을 실행해도 안전하다.

0-1. **⚠️ 보류된 결정 확인 (필수 선행)** — 이전 Phase에서 "나중에 판단한다"로 넘긴 사항이 이번 Phase의 트리거인지 확인한다.

   | # | 열린 결정 | 트리거 | 확인 방법 | 이정표 문서 |
   |---|---|---|---|---|
   | 1 | **분석 엔진 선택** — 추출식(TextRank류) / 로컬 LLM(Ollama) / Claude API. v1은 `NullAnalyzer`만 | Phase 5 착수 | `GET /analyzers`가 빈 목록을 반환하는가 (아직 슬롯만인가) | `docs/scope-definition.md` 2.4절, `docs/설계서_Architecture.md` 5.2절 |
   | 2 | **Whisper 기본 모델** — 실측(2026-09-14, 코어 1개): small 3.05x / large-v3-turbo 0.86x, 품질 차이 작음. medium 미측정, 긴 강연·WER 미측정. 임시 기본 `small` | Phase 2 벤치마크 | `backend/config/stt_default.json`의 `model` + P2 테스트결과서의 모델별 벤치표(x실시간·RAM·WER) | `docs/internal/P0_검토서_TechSpike.md` 3.5~3.6절 |
   | 3 | ~~숏폼 판정 기준(탭 vs 길이 보조)~~ → **탭 소속으로 결정 (2026-09-14)**. 롱폼 탭에 42초 영상 실재, 상위 60건 겹침 0. 전량에서 겹침이 나오면 P1에서 규칙 추가 | 종료 (P1 전량 실측 시 재확인) | P1 동기화 결과에서 두 kind에 모두 있는 `yt_video_id` 건수 = 0 | `docs/internal/P0_검토서_TechSpike.md` 3.1절 |
   | 4 | **Python 3.14 전환** — 휠은 있으나 PyInstaller·라이브러리 검증 부족. 3.12 고정 | Phase 4 패키징 완료 후 | CI 매트릭스 3.14 잡 통과 여부 | `docs/설계서_Architecture.md` 7절 |
   | 5 | **P5(분석) vs P6(모바일) 순서** | Phase 4 종료 | 사용자 결정 기록 (`docs/internal/qa/`) | `docs/scope-definition.md` 7절 |
   | 6 | **서버 배포(Docker) 여부** — 데스크톱 우선 | Phase 6 착수 | 모바일이 LAN 밖 접속을 요구하는가 | `docs/설계서_Architecture.md` 8.3절 |
   | 7 | **YouTube Data API 키 병행** | yt-dlp 목록 경로 차단 발생 시 | `VideoListSource` 구현체가 2개인가 | `docs/scope-definition.md` 3.6절 |
   | 8 | **디스크 확보** — C 4.78GB / D 3.90GB 여유(2026-09-14, 도구·캐시를 D: 로 모으고 C: 캐시를 지운 뒤). P4의 Rust 툴체인(≈2GB)·PyInstaller 산출물·NSIS 빌드가 들어갈 자리가 없다. **부족하면 D: 를 증설한다 — 사용자 결정(2026-09-14)**. 정리 대상은 `data/audio` 캐시만 남았다 | Phase 4 착수 (P2 벤치마크에서 모델 2개 이상 보유 시 조기 트리거) | `check_env`의 디스크 여유 항목이 경고 없이 통과(기준값은 P4 프롬프트에서 정함, 임시 10GB) | `docs/scope-definition.md` 8.1절 |

   **결정을 문서 각주로만 남기지 않는다.** 보류하는 순간 (a) 트리거, (b) 기계로 판정하는 방법, (c) 돌아갈 이정표 문서를 이 표에 함께 등재한다. 기억에 의존하면 돌아오지 못한다.

1. **요구사항 도출 + 기술 검증(TechSpike)** — `docs/scope-definition.md`에서 이 Phase가 책임질 범위를 확정하고 달성 수준을 정의한다.
   **프롬프트를 쓰기 전에** 이 Phase가 의존하는 외부 동작(yt-dlp 옵션, 자막 엔드포인트, Whisper 속도 등)을 **실제로 호출해** 확인하고
   `docs/internal/P{N}_검토서_TechSpike.md`에 **실제 출력을 복사해** 남긴다(템플릿: `docs/internal/templates/템플릿_검토서_TechSpike.md`).

   > **왜 프롬프트 전인가.** 참조 방법론의 프로젝트는 참조 구현 비교를 구현 뒤에 해서, 처음부터 알 수 있었던 항목을 완료 기준에 넣지 못했다.
   > 우리에게는 따라갈 완성본이 없고, 대신 외부 서비스가 문서와 다르게 동작하는 것이 최대 위험이다(Phase 0에서 실제로 7건이 달랐다 — TechSpike 4절).
   > 먼저 보면 완료 기준에 들어간다.
2. **프롬프트 작성 및 제시** — 그 결과물이 나올 수 있는 작업 프롬프트를 Claude가 작성해 **사용자에게 쉽고 자세한 설명과 함께 제시**한다.
   `docs/prompts/phase{N}/<산출물>-v1.md`로 저장한다. 사용자 수정 요청은 `-v2`로 개정하고 구버전은 남긴다.
3. **브랜치 생성** — `main`에서 `impl-phase{N}` 분기. 첫 커밋과 함께 `origin`에 push.
4. **4단계 산출** — 4절(요구사항정의서 → 설계서 → 코드+테스트 → 테스트결과서) 순서를 지킨다.
5. **실제 연동 테스트** — 8절에 따라 YouTube·Whisper를 **실제로 호출해** 검증하고 출력·일자를 테스트결과서 5절에 남긴다.
6. **자체 점검·개선** — 리뷰 전에 완료 기준 대비 누락과 품질 위험을 스스로 점검해 개선한다. `docs/internal/P{N}_검토서_SelfReview.md`.
7. **학습 가이드 제공** — 사용자가 내용을 숙지·체화할 수 있도록 `docs/internal/P{N}_학습가이드_*.md`를 작성하고 대화로 설명한다.
8. **Direct 리뷰** — 사용자가 **직접 리뷰**한다(PR 리뷰가 아님). 지적을 반영할 때는 **Phase 0부터 전체 문서를 다시 읽는다**(4절).
8-1. **Phase 종료 루틴** — 병합 **전에** 한다.

   ```
   ① doc-consistency 에이전트 실행 ("무엇이 바뀌었나" 한 문장) → 어긋남 반영. 처음 2~3회는 메인이 결과를 독립 재검토
   ② pytest (test_docs 포함) / scripts\verify_docs.py / 프론트 npm test·build / check_env — 전부 통과
   ③ history/<날짜>_<작업자>_<주제>.md — 종료 시점 상태·다음 단계
   ④ 산출물 커밋 → push (브랜치에)
   ⑤ merge --no-ff → push (브랜치는 삭제하지 않는다 — 11절)
   ```

   에이전트 정의는 `.claude/agents/`, 설계 근거는 `docs/internal/설계서_Agents.md`. 심사용 에이전트(report-writer·prompt-finest)는 만들지 않았다 — 같은 문서 4절.
9. **`main` 병합** — 11절 Git 규칙. PR은 올리지 않는다(혼자 진행).

### 원칙: 근거는 우리 것으로

작업 중 선행 사례나 외부 자료를 참고할 수 있다. 그러나 **산출물(문서·코드)에는 우리 판단의 근거만 남긴다.** "다른 곳이 이렇게 했으므로"는 근거가 아니다.

- 어떤 결정이든 **그 자체로 정당한 이유**를 서술한다. 이유를 쓸 수 없다면 그 결정을 다시 검토한다.
- 요구사항 → 설계 → 구현 순서를 우리가 직접 밟는다. **근거 없이 옮겨 적은 코드나 문서는 두지 않는다.**
- 판단이 바뀌면 지우지 말고 정정 이력으로 남긴다(10절).

## 2. SOLID 준수

- **SRP**: 모듈/클래스/함수는 하나의 책임만. "유튜브에서 가져오기", "json3 파싱", "저장", "일 시키기"는 별도 모듈.
- **OCP**: 변경 가능성 있는 값(자막 언어 우선순위, Whisper 모델·스레드, 요청 간격·재시도)은 코드 수정 없이 설정으로.
- **LSP**: 공통 인터페이스 구현을 대체 구현으로 바꿔도 호출부가 안 깨진다.
- **ISP**: 거대한 클래스보다 필요한 기능만 노출하는 작은 인터페이스.
- **DIP**: 상위 로직은 구체 클래스가 아니라 **Protocol**에 의존한다 — `VideoListSource`·`TranscriptProvider`·`SttEngine`·`Analyzer`(`domain/interfaces.py`).
  **영상 목록 소스·스크립트 소스·STT 엔진·분석기는 이 프로젝트에서 변경 가능성이 가장 높은 네 축**이다(`설계서_Architecture` 2.2절). 구체 구현 선택은 조립 지점 한 곳에서만.

## 3. TDD — 선별 적용

코드 성격에 따라 3등급. 판단이 애매하면 **"입출력이 결정적인가"**(같은 입력 → 항상 같은 출력)를 기준으로.

| 등급 | 대상 | 규칙 | 커버리지 |
|---|---|---|---|
| **A. 핵심 순수 로직** | `constants`(검증 로직), `domain/models`, `workflow/run_context`(상태 전이·파일명), `analysis/null_analyzer`, `youtube/channel_resolver`, `transcripts/json3_parser`·`normalizer`, `jobs/state`, `scripts/verify_docs.py`의 검사 함수, 프론트 순수 유틸(`formatTimestamp` 등) | Red→Green→Refactor로 **테스트 먼저**. 테스트 없는 변경은 미완료 | **≥ 90%** |
| **B. 오케스트레이션/통합** | `config`, `logging_config`, `repository/*`, `cli/*`, `analysis/registry`, `youtube/tab_lister`·`metadata_fetcher`, `transcripts/providers`·`chain`, `stt/*`, `jobs/tasks`, `api/*`, React 컴포넌트 | 구현 후 통합 테스트 허용. 외부 의존성은 Protocol fake 또는 기록된 응답. 프론트는 MSW | **≥ 70%** |
| **C. 탐색/실측** | `scripts/spike/*`, 벤치마크 | 자동 테스트 미강제. **산출물 검증 + TechSpike 문서**로 대체 | 측정 제외 |

- A+B 가중 평균 **≥ 80%**가 기본 목표. 테스트 파일은 대상 코드와 1:1 대응. `domain/interfaces.py`(Protocol 선언만)는 측정 제외.
- 배치: A → `backend/tests/unit/`, B → `backend/tests/integration/`, 프론트는 대상 파일 옆 `*.test.ts(x)`.
- 실제 YouTube·Whisper를 호출하는 E2E(`backend/tests/e2e/`)는 기본 pytest에서 제외(`-m 'not e2e'`)하고 수동·선택 실행.
  외부 서비스가 내려가면 관계없는 변경도 빨간불이 되고, 그러면 실패를 무시하기 시작한다. **무시되는 관문은 없는 것보다 나쁘다.**
- **거부 케이스 필수**: 부적합 입력을 거부하는 모듈은 정상 케이스만 테스트하면 아무것도 안 하는 구현도 통과한다.
- `P{N}_테스트결과서`에 그 Phase가 건드린 모듈의 등급과 **실측 커버리지**를 기록한다.

## 4. Phase 내부 작업 순서

건너뛰거나 역순으로 진행하지 않는다.

1. **요구사항 정의서** — 무엇을, 왜 (`docs/P{N}_요구사항정의서_*.md`) — FR 번호대: P0 = FR-1~, P1 = FR-101~, P2 = FR-201~ …
2. **설계서** — 입출력, 인터페이스, 데이터 흐름, **설계 판단**(왜 + 기각 대안) (`docs/P{N}_설계서_*.md`)
3. **코드 + 테스트** — 3절 등급 기준 (A는 테스트 먼저). 모듈 docstring 첫 줄: `<역할> — 대응: docs/P{N}_설계서_*.md N절 (FR-x~y). 등급 A|B`
4. **테스트 결과서** — 실행 결과, 등급별 커버리지, FR 전건 검증표, 실호출 출력, 실패·재작업 (`docs/P{N}_테스트결과서_*.md`)

템플릿은 `docs/internal/templates/`. 요구사항–설계–코드–결과가 서로 추적 가능해야 한다(문서에서 코드 경로를, 코드 docstring에서 문서 경로를).

### 리뷰·수정 반영은 Phase 0부터 전체를 다시 읽고 한다

**리뷰 지적, 개선 사항, 판단 변경을 반영할 때는 찾아 바꾸기로 끝내지 않는다.** `CLAUDE.md`와 `docs/` 산출물 문서를 **Phase 0부터 현재까지** 읽고 어긋난 곳을 모두 고친다.

#### 왜 — 부분 치환은 같은 뜻의 다른 표현을 놓친다

본문은 고쳤는데 표(`| 항목 | Phase 2 |`)와 다른 말로 쓴 곳("정제를 앞당기는 실수")은 검색에 걸리지 않아 한 문서 안에서 본문과 표가 반대말을 하는 사고가 참조 프로젝트에서 실제로 있었다. 이 프로젝트에서 같은 형태가 나올 자리: **In/Out of Scope 표, 보류 결정 표, 완료 기준 체크박스, 데이터 흐름 그림, 스크립트 소스 우선순위 표, 모델 기본값.**

#### 기계가 잡아주지 않는다

`scripts/verify_docs.py`는 **"이 문장대로 하면 실제로 되는가"**(명령·경로·링크·표 형식)를 본다. **"두 문장이 서로 반대말을 하는가"**는 보지 못한다. 사람이 읽어야 알 수 있다 — 또는 `doc-consistency` 에이전트에 맡긴다.

#### 읽을 대상과 순서

상위 문서부터 내려간다. 상위가 바뀌면 하위가 따라 바뀌어야 하기 때문이다.

```
1. CLAUDE.md                          규칙
2. docs/scope-definition.md           무엇을·왜
3. docs/설계서_Architecture.md         어떻게 (전체 골격)
4. docs/P0_*.md                       Phase 0 산출물
5. docs/P1_*.md …                     이후 Phase 산출물 (Glob P*_*.md)
6. docs/internal/*.md                 TechSpike·SelfReview·학습가이드·용어집·트러블슈팅·Agents
7. README.md                          실행 안내
```

#### 특히 놓치기 쉬운 곳

| 위치 | 이유 |
|---|---|
| **In / Out of Scope 표** | 본문만 고치고 표를 빼먹는다. 가장 자주 어긋난다 |
| 보류 결정 표 (1절) | 종료된 결정을 취소선으로 바꾸지 않고 둔다 |
| 완료 기준·리스크 표 | 항목이 늘거나 정반대가 되는데 그대로 둔다 |
| 산출물·TDD 등급 목록 | 새 모듈을 추가하고 목록에 안 넣는다 |
| 데이터 흐름 그림 | 단계가 늘었는데 그림은 옛날 그대로다 |
| 다른 Phase의 문서 | Phase 0의 Out of Scope에 "Phase 2 책임"이 남아 있다 |
| 학습가이드 Q&A | 답이 정반대가 되는데 질문이 그대로 남는다 |
| 실측값(건수·초·%) | 재측정했는데 옛 숫자가 남는다 |

#### 전체 재독은 `doc-consistency` 에이전트에 맡길 수 있다

`.claude/agents/doc-consistency.md`가 위 순서·"놓치기 쉬운 곳"을 그대로 따라 읽고 **어긋난 곳 목록**만 돌려준다. 읽기 전용이라 판단과 수정은 메인이 한다.
호출 시 "무엇이 바뀌었나"를 한 문장으로 넘긴다. **처음 2~3회는 결과를 메인이 독립적으로 재검토**한다.

트러블을 해결한 직후에는 `.claude/skills/troubleshoot/SKILL.md`에 따라 `docs/internal/검토서_트러블슈팅.md`에 기록한다.

### 문서에 적은 명령은 적은 그대로 실행해 확인한다

**개발할 때 쓴 명령과 문서에 적은 명령이 다르면, 실패하는 것은 독자뿐이고 작성자는 모른다.**

- 이 저장소는 Windows다. 문서의 명령은 **PowerShell**로 쓰고, Python은 **`backend\.venv\Scripts\python.exe`** 전체 경로 또는 앞선 `backend\.venv\Scripts\Activate.ps1` 안내 뒤의 `python`으로 쓴다. 시스템 `python`은 3.14라 패키지가 없다.
- 편집기에서 복사한 명령을 **터미널에 그대로 붙여넣어** 실행한다. 오류 메시지는 **실제 출력을 복사**한다.
- 기계가 검사한다:

  ```powershell
  .\backend\.venv\Scripts\python.exe scripts\verify_docs.py
  ```

  `pytest`가 이 검사를 포함하므로(`backend/tests/integration/test_docs.py`) 별도로 기억할 필요는 없다.
  검사 항목: venv 전제 · `python -m` 모듈 존재 · 경로 실재 · `.ps1` 실재 · 마크다운 링크 · 표 쪼개짐 · 백틱 경로 실재.

## 5. 하드코딩 금지

- 매직 넘버, URL, 토큰, 파일 경로, 모델 이름 기본값 등 **환경/실행마다 달라지는 값**은 코드에 직접 쓰지 않는다.
- **`.env`** = 환경에 따라 달라지는 값(`DATA_DIR`, `HF_HOME`, `API_PORT`, `CORS_ORIGINS`, `BGUTIL_SCRIPT_PATH`, `STT_CPU_THREADS`, `LOG_LEVEL`). **`.env`는 커밋 금지**, `.env.example`만 커밋(모든 키 + 근거 절 주석).
- **`constants.py`** = 설계상 고정된 값(kind/source 값, `-orig` 접미사, `PIPELINE_VERSION`, DB 파일명, status 패턴). 단일 정의, 재사용.
- **`backend/config/*.json`** = 실행마다 조절하는 값(Whisper 모델·스레드·VAD, yt-dlp 포맷·간격·재시도, 동기화 페이지 규칙). 파일마다 `"_comment"`로 근거 절·기본값 이유.
- **재현성 관련 값은 반드시 고정한다.** 정규화 규칙·모델·파이프라인 버전은 스크립트 레코드에 **동반 저장**한다. 동일 원본 + 동일 버전 → 동일 결과.

## 6. Workflow 친화 구성

향후 워크플로 도구(Airflow류) 이식을 대비해 각 단계를 독립적으로 구성한다(`설계서_Architecture` 6절).

- **독립성**: 단계마다 별도 CLI 진입점(`cli/run_*.py`). 단계 간 연동은 **DB·파일로만**.
- **명시적 trigger/input/output**: docstring에 `Trigger / Input / Output / ⚠️ 사전 조건`. 입력은 명시적 인자로만.
- **모니터링·재시작**: `status/<stage>_<run_id>.json`(started/succeeded/failed). 실패 시 그 단계·그 영상만 재실행.
- **멱등성 (Phase 1~ 필수)**: 같은 입력으로 **다시 실행해도 산출물과 외부 상태가 같아야 한다.** 자연키(`yt_video_id`) upsert, 스크립트는 (video, source, language, model, pipeline_version) 존재 시 건너뜀. 재실행이 중복·누적·다른 결과를 만들면 결함이다.
  → 왜 필수인가: 파이프라인은 중간에 끊기고 다시 돌아가는 것이 정상 운영이다(429·차단·CPU 시간). 재실행이 안전하지 않으면 사람이 "어디까지 됐나"를 손으로 확인해야 하고 그 순간 자동화가 무너진다.
- **입출력 보존 (rewrite 금지)**: `captions/*.json3`·`whisper/*.json` 원본은 **덮어쓰지 않는다**(코드가 거부). 방향은 `원본 → DB 세그먼트 → 전체 텍스트 → [분석]` 한쪽. **하류를 직접 수정하면 재생성 시 사라진다** — 수정은 항상 상류에서. `audio/*.m4a`만 삭제 가능 캐시.

## 7. 배포·컨테이너

- **1차 배포 경로는 Windows 설치파일**(P4): PyInstaller **onedir** 백엔드를 Tauri v2 사이드카로 동봉, NSIS. 개발 실행 경로는 `backend\.venv` 직접 실행.
- Docker는 서버 배포용 **선택지**(보류 결정 6). 이미지를 만들 때는 `.env`로 설정 주입, 호스트 경로 하드코딩 금지, `DATA_DIR` 볼륨.
- 의존성은 `backend/pyproject.toml`에 **하한·상한 고정**. yt-dlp는 YouTube 변경이 잦아 예외적으로 **설정에서 갱신 가능**하게 둔다(8절).
- **자원 제약**: 개발 VM은 코어 1·디스크 5GB 미만. 메모리·디스크 영향이 큰 값(모델·오디오 캐시·동시 작업 수)은 설정으로 빼고 기본값을 작게 잡는다.
- **로컬 디스크는 D: 우선** (사용자 규칙 2026-09-14). 저장소·venv·`node_modules`·`DATA_DIR`(DB·파일·모델 캐시)·도구(`tools/`)·pip/npm 캐시(`D:\claude\.cache\`)를 **D:** 에 둔다. C: 는 OS 와 시스템 도구 전용이다.
  새로 캐시·임시 파일·다운로드를 만드는 도구를 도입할 때는 **저장 위치를 먼저 D: 로 지정한 뒤 실행**한다 — HF 캐시가 C: 로 가서 여유가 2.4GB 까지 떨어진 T-002 가 그 사례다. `~`(홈 디렉토리) 기준 기본 경로를 코드·문서에 쓰지 않는다.
- **이식성**: 개발 Windows Server / 사용자 Windows 10·11 / (P6) 서버는 Linux 가능. OS 패키지 직접 의존을 피한다(ffmpeg 바이너리 미동봉이 그 예).

## 8. YouTube 연동 규칙

### 작업 전 확인 (필수)

`.\scripts\check_env.ps1` → `==> READY`. 특히 bgutil 스크립트와 Node가 없으면 PO 토큰 없이 요청하게 되어 "코드 문제"로 오진한다.

### 실제 호출로 검증한다

설계 문서·라이브러리 README만으로 API 동작을 단정하지 않는다. **반드시 실제로 호출해 응답을 확인**하고, 확인한 사실과 **확인 일자·yt-dlp 버전**을 문서에 남긴다. Phase 0에서 문서와 달랐던 것 7건이 그 이유다(`docs/internal/P0_검토서_TechSpike.md` 4절). 모킹 테스트만으로는 완료가 아니다 — 테스트결과서 5절에 실호출 출력이 있어야 한다.

### 실측으로 확정된 규칙 (2026-09-14)

| 규칙 | 근거 |
|---|---|
| 목록은 **탭 URL**(`/videos`, `/shorts`)로 flat 추출. 플레이리스트 URL은 쓰지 않는다 | 숏츠 플레이리스트 100개 상한 이슈; 탭 60건/2.4초 확인 |
| flat 결과를 믿지 않는 필드: `duration`(숏폼 없음), `upload_date`(둘 다 없음), `playlist_count`(없음) → **영상별 메타 보충** | TechSpike 3.1절 |
| 자막은 **원어 트랙만**: `subtitles[<lang>]` → `automatic_captions[<lang>-orig]`. 다른 언어는 번역 요청이 되어 **429** | TechSpike 3.2절 |
| 언어는 **한 번에 하나씩** 요청한다. yt-dlp는 한 언어 실패로 명령 전체를 실패시킨다 | TechSpike 3.2절 |
| 오디오는 `bestaudio[ext=m4a]/bestaudio`, 후처리 없음. ffmpeg를 요구하는 옵션을 넣지 않는다 | TechSpike 3.4절 |
| JS 런타임은 Node(`--js-runtimes node`). PO 토큰은 bgutil **스크립트 모드**, HTTP 제공자는 끈다(서버 없으면 경고 반복) | TechSpike 3.3절 |
| 네트워크 작업 **워커 1개**, 요청 간 1~3초 지터, 429는 지수 백오프 후 재시도, 상한 후 `failed` | scope 5.4절 |
| yt-dlp API 호출은 `youtube/`·`transcripts/providers.py`·`stt/audio_fetcher.py` **세 곳으로 한정** | 옵션 변경 파급 차단 |
| 차단(`Sign in to confirm you're not a bot`)이 나오면 코드를 고치기 전에 **회선·간격·제공자 상태**를 먼저 확인하고 트러블슈팅에 기록 | 원인 오진 방지 |

## 9. 문서 파일명 규칙

`docs/` 아래 flat하게 저장하고 아래 패턴을 따른다.

```
[P<phase>_]<DocType>_<Topic>.md
```

- **`P<phase>`**: 특정 Phase(0~6)에 종속된 문서에만 붙인다. 전체를 다루는 문서는 생략.
- **`<DocType>`**: 아래 5개 중 하나로 고정.

  | DocType | 의미 | 위치 | 4절 단계 |
  |---|---|---|---|
  | `요구사항정의서` | 무엇을·왜 | `docs/` | 1 |
  | `설계서` | 입출력·인터페이스·흐름·설계 판단 | `docs/` | 2 |
  | `테스트결과서` | 실행 결과 + **등급별 커버리지 수치 필수** + 실호출 출력 | `docs/` | 4 |
  | `검토서` | 정규 4단계 밖의 점검·조사 — `TechSpike`(1절 1단계), `SelfReview`(1절 6단계), 트러블슈팅, 사고 분석 | `docs/internal/` | 보조 |
  | `학습가이드` | 사용자 숙지·체화용 (1절 7단계) | `docs/internal/` | 보조 |

- **`<Topic>`**: 다루는 대상. 가능하면 코드 모듈·패키지명과 맞춰 추적성을 확보한다(`Common`, `ChannelListing`, `Transcripts`).
- 문서 개정은 **제자리 개정 + 머리에 개정 사유(정정 이력)**. 전면 재작성이라 이전 판을 나란히 둘 가치가 있을 때만 `_v2` 새 파일.
- **예외**: `docs/scope-definition.md`·`docs/설계서_Architecture.md`(전체 문서). `docs/internal/README.md`·`docs/internal/templates/README.md`·`docs/prompts/*/README.md`는 디렉토리 안내. `docs/internal/용어집.md`는 공용 참조(독자 기준 "컴퓨터공학 학부 졸업"). `docs/internal/qa/P{N}_질의응답_<주제>.md`는 사용자 질의응답 기록.
- **`docs/` = 제출물(산출물), `docs/internal/` = 내부 자료.** 요구사항정의서·설계서·테스트결과서·scope-definition·설계서_Architecture는 제출물. TechSpike·SelfReview·학습가이드·용어집·트러블슈팅·에이전트 설계·템플릿은 내부.
- 모든 문서는 `#` 제목 아래 **머리말 불릿 메타 블록**(상위 문서·절번호, 사용 프롬프트, 규칙, 작성일/작성 LLM, 상태|결과|결론)을 둔다(`docs/internal/templates/README.md`).

## 10. 요구사항–산출물 페어링

채팅으로 작업이 진행되므로 대화 중 생성되는 요구사항을 반드시 파일로 남긴다.

- **과제에 반영되는 프롬프트는 예외 없이 `docs/prompts/`에 분류·구별해 저장한다.**
  - Phase 종속: `docs/prompts/phase{N}/{산출물명}-v{버전}.md`
  - 전체 적용: `docs/prompts/{산출물명}-v{버전}.md` (Phase 접두사 없음)
  - 기획서·사용자 요청 원문은 `docs/prompts/phase0/project-plan-v1.md`, 각 Phase 프롬프트의 "사용자 요청 (원문)" 절에 **그대로 인용**한다.
- 요구사항이 갱신되면 대응 산출물도 같은 버전으로 갱신해 **"요구사항 최신본 ↔ 산출물 최신본"이 항상 한 쌍**을 이루게 한다.
- 판단이 바뀐 경우 이전 기록을 지우지 않고 **정정 이력으로 남긴다**(왜 바뀌었는지가 중요).
- 사용자와의 판단 문답은 `docs/internal/qa/P{N}_질의응답_<주제>.md`에 보존한다.

## 11. Git / 협업 규칙

- **`main`에 직접 작업하지 않는다.** Phase당 브랜치 하나(**`impl-phase{N}`**)를 `main`에서 분기.
- **커밋하면 즉시 push한다**(사용자 규칙 2026-09-14). 로컬에만 있는 커밋을 두지 않는다. 첫 push는 `-u origin impl-phase{N}`.
- **Phase 브랜치는 병합 후에도 삭제하지 않는다.** 병합 커밋은 결과만 보여주고, 브랜치는 **과정**을 보여준다.
- **PR은 올리지 않는다**(혼자 진행). 품질 확인은 1절 6단계(자체 점검)와 8단계(Direct 리뷰)로 한다. 병합은 `git merge --no-ff impl-phase{N}` → push.
- 커밋 메시지: `<type>(<scope>): <요약>` (type = feat|fix|docs|test|chore|refactor, scope = phaseN|모듈). 본문에 무엇이 왜 바뀌었는지. 끝에 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- 세션 단위 작업 히스토리를 `history/<날짜>_<작업자>_<주제>.md`로 남긴다(작업자 표기 `park.sei`). 다음 세션이 이어받도록 종료 시점 상태와 다음 단계를 포함한다. 히스토리는 **사후에 고치지 않는다**(기록 위조).
- **커밋 금지**: `.env`, 토큰·API 키, `data/`(DB·자막 원본·오디오·모델), `status/`, `node_modules/`, 빌드 산출물. 자막·오디오는 저작물이므로 **저장소에 올리지 않는다** — 테스트 fixture는 자작 최소 샘플(수 초·수 줄)만.
- 원격: `https://github.com/hipiboy7/youtube-Learner.git` (`origin`).

## 12. 데이터 규칙

| 항목 | 기준 |
|---|---|
| 기록 원본 | **SQLite 한 파일**(`DATA_DIR/youtube_learner.db`), WAL, `busy_timeout`, 외래키 ON. 화면·API는 DB만 읽는다 |
| 파일 산출물 | `data/channels/<yt_channel_id>/{captions,audio,whisper}/` — `scope-definition.md` 4.3절. 원본(json3·Whisper 원출력)은 **읽기만**, 덮어쓰기 거부 |
| 자연키 | `yt_channel_id`, `yt_video_id`. 스크립트 유일성 (video, source, language, model_name, pipeline_version) |
| 버전 동반 | 스크립트 레코드에 `source`·`engine`·`model_name`·`pipeline_version` 필수. 규칙 변경 시 재생성 대상을 이 값으로 고른다 |
| 언어 | 트랙 키 `ko-orig`는 저장 시 `ko` + `source=auto`. 번역 트랙은 옵션, `source=translated`로 구분 |
| 파싱 검증 | json3 파싱 직후 세그먼트 수·시간 단조 증가·빈 텍스트 0건 확인 후 저장 |
| 인코딩·개행 | UTF-8(BOM 없음), LF. Windows에서도 `newline="\n"` 명시 |
| **필드명(키)** | **영문 ASCII만.** 값은 원문(한국어) 그대로 |
| 재현성 | 동일 원본 + 동일 `pipeline_version` → DB 세그먼트·전체 텍스트 **바이트 단위 동일** |
| 원문 보존 | 정규화(공백·특수문자·병합)는 DB에만. 원본 파일은 변형하지 않는다 |
| 삭제 가능 | `audio/*.m4a`만. 삭제 후에도 DB·원출력만으로 화면이 완전해야 한다 |
