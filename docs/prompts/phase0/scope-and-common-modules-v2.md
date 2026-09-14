# Phase 0 작업 프롬프트 v2 — 범위 정의 + 공통 모듈 (Direct 리뷰 반영)

- 일자: 2026-09-14
- 요청 LLM 모델: Fable 5.1
- 성격: Phase 0 종속. v1(`scope-and-common-modules-v1.md`)에 사용자 Direct 리뷰 지시 3건을 더한 개정판. v1 은 이력으로 남긴다
- 대응 산출물: `docs/scope-definition.md` v2, `CLAUDE.md`(0절·1절 보류 8·7절), `docs/설계서_Architecture.md`(3.2·4·5.2절), `backend/src/youtube_learner/constants.py`·`config.py`, `.env.example`, `README.md`, `docs/P0_요구사항정의서_Common.md`(FR-1·FR-7), `docs/P0_설계서_Common.md`(1.1·3.1·3.2·9.2절)
- 상태: 반영 완료 — Direct 리뷰 계속

## 사용자 요청 (원문, 2026-09-14 Direct 리뷰 중)

> 로컬 디스크를 사용할 떄는 항상 D드라이브를 우선적으로 사용하도록 해.

> phase가 진행됨에 따라 디스크가 필요하면 D드라이브를 증설하도록 할게.
> 추가로 변경할 내용이 있다면, 요약 및 핵심 도출 기능은 추후 구현을 하지만, 현재는 사용자가 직접 스크립트를 복사해서 각자 사용중인 AI 챗 서비스에 붙여넣기하고 요약 및 핵심 정보 기능을 받아서 그 정보를 붙여넣기 할 수 있도록 그 기능과 저장기능이 필요해.
> 즉, 스크립트를 추출하면, 버튼 클릭 하나로 해당 스크립트 '복사'가 되어야하고, 또 외부에서 요약 및 핵심 정리 한 글을 붙여놓을 '요약 및 정리' 메뉴와 저장 기능이 필요해.

## 해석 및 반영 방침

| # | 지시 | 해석 | 반영 위치 |
|---|---|---|---|
| 1 | 로컬 디스크는 D: 우선 | 저장소·venv·`node_modules`·`DATA_DIR`·모델 캐시·도구·pip/npm 캐시 전부 D:. C: 는 OS 전용. `~`(홈) 기준 기본 경로 금지 | `CLAUDE.md` 7절 규칙, scope 8.1절 디스크 정책, bgutil → `tools/`, `Settings.bgutil_script_path` 기본값, `.env.example`, README 최초 1회, Architecture 3.2절 |
| 2 | 부족하면 D: 증설 | 보류 결정 8 의 해법이 "증설"로 정해짐. 트리거(P4 착수)는 유지, P2 에서 모델 2개 이상이면 조기 | `CLAUDE.md` 1절 보류 8, scope 8.1절 |
| 3 | 원클릭 복사 + '요약 및 정리' 붙여넣기·저장 | **자동** 분석은 P5 그대로. **수동 흐름**을 v1(P3)에 넣는다: 스크립트 전체 텍스트 복사 버튼, 외부 AI 결과를 붙여 넣는 편집기 + 저장. 저장은 `analyses` 테이블에 `analyzer_name="manual"`·`analyzer_version="user"`. 종류별 영상당 1건 편집·재저장. 수동 입력은 `Analyzer` 가 아니므로 레지스트리를 거치지 않는다 | scope v2 1·2.3·2.4·2.5·6.1·6.2·7·9절, `CLAUDE.md` 0절, Architecture 4절 흐름·5.2절, `constants.MANUAL_ANALYZER_NAME/VERSION`, 요구사항 FR-7, 설계서 1.1·9.2, 용어집, 학습가이드 Q1 |

## v1 대비 변경 요약

- **Phase 로드맵**: P1 은 `analyses` 테이블을 "예약"이 아니라 생성. P3 에 "원클릭 복사"·"'요약 및 정리' 수동 입력·저장(API 포함)" 추가. P5 는 자동 분석기만.
- **In/Out of Scope**: In-Scope 10 추가(복사·수동 저장). Out-of-Scope 는 "자동 분석 구현"으로 좁힘.
- **제품 v1 성공 기준(6.1절)**: 복사 → 붙여넣기 → 저장 → 재표시가 들어감.
- **P0 코드**: 상수 2개 추가 + 테스트 1건. `bgutil_script_path` 기본값 변경 + 테스트 1건. 그 외 P0 코드는 그대로 — 수동 저장 구현은 P1(스키마)·P3(API·화면).

## 완료 기준 (v1 에 추가)

- [ ] `scope-definition.md` 머리에 v2 개정 사유, 11절 개정 이력 v2 행
- [ ] `check_env.ps1` 이 이동한 `tools/` 스크립트로 `==> READY` (테스트결과서 5.1절 재실행)
- [ ] `test_config.py::test_bgutil_default_lives_under_project_tools_on_project_drive`, `test_constants.py::test_manual_analysis_identity` 통과
- [ ] `verify_docs.py` 종료 0, `doc-consistency` 2회차 어긋남 반영
- [ ] 질의응답 기록 `docs/internal/qa/P0_질의응답_디스크와수동요약.md`

## 하지 않는 것

P3 화면·API 의 상세 설계(복사 시 타임스탬프 포함 여부, 요약 요청 프롬프트 머리말, 종류 선택 UI)는 P3 요구사항정의서·설계서에서 정한다. 여기서는 범위와 데이터 모델 계약만 확정한다.
