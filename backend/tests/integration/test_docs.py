"""문서 실검사 — 등급 B (검사 함수는 A 이지만 저장소 전체 실행이 IO 라 통합에 둔다).

대응: scripts/verify_docs.py, docs/P0_설계서_Common.md 11절, 요구사항 FR-28~FR-30.

**왜 테스트로 두는가** — 규칙으로 "문서 명령을 확인하자"고 적으면 잊는다. pytest 가 매번 검사하면 잊을 수 없다.
**왜 역테스트가 있는가** — 통과만 확인하면 아무것도 검사하지 않는 검사기도 통과한다.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
VERIFY = ROOT / "scripts" / "verify_docs.py"

sys.path.insert(0, str(ROOT / "scripts"))
import verify_docs  # noqa: E402  — 저장소 스크립트를 모듈로 import


def kinds(findings) -> set[str]:
    return {f.kind for f in findings}


class TestRepository:
    def test_script_exists(self):
        assert VERIFY.is_file()

    def test_all_docs_pass_verification(self):
        """FR-30(a) — 저장소 문서 전체에 위반이 없어야 한다. 실패 시 어느 문서 몇 줄이 왜 문제인지 출력된다."""
        proc = subprocess.run([sys.executable, str(VERIFY), "--quiet"], cwd=ROOT, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            pytest.fail(f"문서 검증 실패\n\n{proc.stdout}\n{proc.stderr}")

    def test_history_is_not_checked_but_qa_is(self):
        """FR-28 — history/ 는 사후 수정 금지 기록이라 검사하지 않고, qa/(요청 원문·결정)는 검사한다."""
        targets = {d.relative_to(ROOT).as_posix() for d in verify_docs.target_docs(None)}
        assert not any(t.startswith("history/") for t in targets)
        assert "CLAUDE.md" in targets and "docs/scope-definition.md" in targets
        assert any(t.startswith("docs/internal/templates/") for t in targets)
        assert any(t.startswith("docs/internal/qa/") for t in targets)


class TestVenvCheck:
    def test_detects_bare_python_in_powershell_fence(self, tmp_path: Path):
        """FR-29 venv — 역테스트."""
        doc = tmp_path / "bad.md"
        doc.write_text("# 예\n\n```powershell\npython -m youtube_learner.cli.check_env\n```\n", encoding="utf-8")
        assert "venv" in kinds(verify_docs.verify(doc))

    def test_detects_bare_pytest_in_bash_fence(self, tmp_path: Path):
        doc = tmp_path / "bad.md"
        doc.write_text("```bash\npytest -q\n```\n", encoding="utf-8")
        assert "venv" in kinds(verify_docs.verify(doc))

    def test_full_venv_path_is_accepted(self, tmp_path: Path):
        """오탐 방지 — 전체 경로(백슬래시·슬래시 둘 다)."""
        doc = tmp_path / "ok.md"
        doc.write_text(
            "```powershell\n.\\backend\\.venv\\Scripts\\python.exe -m pytest\n"
            "backend/.venv/Scripts/python.exe -m pytest\n```\n",
            encoding="utf-8",
        )
        assert "venv" not in kinds(verify_docs.verify(doc))

    def test_activate_hint_earlier_is_accepted(self, tmp_path: Path):
        doc = tmp_path / "ok.md"
        doc.write_text(
            "# 준비\n\n```powershell\n.\\backend\\.venv\\Scripts\\Activate.ps1\n```\n\n# 실행\n\n```powershell\npytest\n```\n",
            encoding="utf-8",
        )
        assert "venv" not in kinds(verify_docs.verify(doc))

    def test_venv_creation_is_exempt(self, tmp_path: Path):
        doc = tmp_path / "ok.md"
        doc.write_text("```powershell\npy -3.12 -m venv backend\\.venv\n```\n", encoding="utf-8")
        assert "venv" not in kinds(verify_docs.verify(doc))

    def test_powershell_variable_is_not_bare_python(self, tmp_path: Path):
        """오탐 방지 — `& $py -m ...` 의 $py 는 변수다."""
        doc = tmp_path / "ok.md"
        doc.write_text("```powershell\n$py = 'x'\n& $py -m youtube_learner.cli.check_env\n```\n", encoding="utf-8")
        assert "venv" not in kinds(verify_docs.verify(doc))


class TestModuleCheck:
    def test_detects_missing_project_module(self, tmp_path: Path):
        doc = tmp_path / "bad.md"
        doc.write_text("```powershell\nbackend\\.venv\\Scripts\\python.exe -m youtube_learner.cli.nope_module\n```\n", encoding="utf-8")
        assert "module" in kinds(verify_docs.verify(doc))

    def test_existing_project_module_passes(self, tmp_path: Path):
        doc = tmp_path / "ok.md"
        doc.write_text("```powershell\nbackend\\.venv\\Scripts\\python.exe -m youtube_learner.cli.check_env\n```\n", encoding="utf-8")
        assert "module" not in kinds(verify_docs.verify(doc))

    def test_third_party_modules_not_checked(self, tmp_path: Path):
        doc = tmp_path / "ok.md"
        doc.write_text("```powershell\nbackend\\.venv\\Scripts\\python.exe -m yt_dlp --version\n```\n", encoding="utf-8")
        assert "module" not in kinds(verify_docs.verify(doc))


class TestPathCheck:
    def test_detects_missing_path_written_with_backslashes(self, tmp_path: Path):
        """FR-29 path — 백슬래시 표기도 정규화해 본다."""
        doc = tmp_path / "bad.md"
        doc.write_text("```powershell\ntype scripts\\NOPE\\missing.py\n```\n", encoding="utf-8")
        assert "path" in kinds(verify_docs.verify(doc))

    def test_detects_missing_ps1(self, tmp_path: Path):
        doc = tmp_path / "bad.md"
        doc.write_text("```powershell\n.\\scripts\\nope.ps1\n```\n", encoding="utf-8")
        assert "ps1" in kinds(verify_docs.verify(doc))

    def test_existing_paths_pass(self, tmp_path: Path):
        doc = tmp_path / "ok.md"
        doc.write_text("```powershell\n.\\scripts\\check_env.ps1\ntype scripts\\verify_docs.py\n```\n", encoding="utf-8")
        assert not kinds(verify_docs.verify(doc)) & {"path", "ps1"}

    def test_runtime_venv_and_placeholder_paths_skipped(self, tmp_path: Path):
        """오탐 방지 — data/·status/ 런타임, .venv 환경, <자리표시자>, $변수."""
        doc = tmp_path / "ok.md"
        doc.write_text(
            "```powershell\ndir data\\spike\ndir status\\\ntype backend\\.venv\\Scripts\\python.exe\n"
            "type docs\\P<N>_x.md\ntype $env:TEMP\\x\n```\n",
            encoding="utf-8",
        )
        assert not kinds(verify_docs.verify(doc)) & {"path", "ps1"}

    def test_non_shell_fence_is_ignored(self, tmp_path: Path):
        doc = tmp_path / "ok.md"
        doc.write_text("```python\nimport scripts.nope\n```\n\n```\nscripts/nope.ps1\n```\n", encoding="utf-8")
        assert not verify_docs.verify(doc)


class TestLinkCheck:
    def test_detects_broken_link(self, tmp_path: Path):
        doc = tmp_path / "bad.md"
        doc.write_text("[없는 문서](./존재하지_않음.md)\n", encoding="utf-8")
        assert kinds(verify_docs.verify(doc)) == {"link"}

    def test_allows_parentheses_in_link_target_and_urls(self, tmp_path: Path):
        target = tmp_path / "흐름(Batch ML).mermaid"
        target.write_text("graph TD\n", encoding="utf-8")
        doc = tmp_path / "ok.md"
        doc.write_text("[다이어그램](./흐름(Batch%20ML).mermaid) [외부](https://example.com/x) [절](#1-절)\n", encoding="utf-8")
        assert not verify_docs.verify(doc)


class TestTableCheck:
    def test_detects_table_split_by_blank_line(self, tmp_path: Path):
        doc = tmp_path / "split.md"
        doc.write_text("| a | b |\n|---|---|\n| 1 | 2 |\n\n| 3 | 4 |\n", encoding="utf-8")
        assert kinds(verify_docs.check_tables(doc, doc.read_text(encoding="utf-8"))) == {"table"}

    def test_allows_two_separate_tables(self, tmp_path: Path):
        doc = tmp_path / "two.md"
        doc.write_text("| a | b |\n|---|---|\n| 1 | 2 |\n\n| c | d |\n|---|---|\n| 3 | 4 |\n", encoding="utf-8")
        assert verify_docs.check_tables(doc, doc.read_text(encoding="utf-8")) == []

    def test_ignores_pipes_inside_code_fence(self, tmp_path: Path):
        doc = tmp_path / "fence.md"
        doc.write_text("```\n| a | b |\n\n| 1 | 2 |\n```\n", encoding="utf-8")
        assert verify_docs.check_tables(doc, doc.read_text(encoding="utf-8")) == []


class TestBarePathCheck:
    def _findings(self, doc: Path):
        return verify_docs.check_bare_paths(doc, doc.read_text(encoding="utf-8"))

    def test_detects_nonexistent_backtick_path(self, tmp_path: Path):
        doc = tmp_path / "stale.md"
        doc.write_text("`docs/P9_요구사항정의서_Nope.md` 참고\n", encoding="utf-8")
        assert kinds(self._findings(doc)) == {"bare-path"}

    def test_detects_nonexistent_backslash_backtick_path(self, tmp_path: Path):
        doc = tmp_path / "stale.md"
        doc.write_text("`scripts\\nope.ps1` 실행\n", encoding="utf-8")
        assert kinds(self._findings(doc)) == {"bare-path"}

    def test_accepts_existing_path_and_line_suffix(self, tmp_path: Path):
        doc = tmp_path / "ok.md"
        doc.write_text("`docs/scope-definition.md` 와 `docs/scope-definition.md:158`, `CLAUDE.md` 참고\n", encoding="utf-8")
        assert self._findings(doc) == []

    def test_ignores_package_relative_placeholders_runtime_and_generated(self, tmp_path: Path):
        doc = tmp_path / "ok.md"
        doc.write_text(
            "`domain/interfaces.py`, `docs/P{N}_설계서.md`, `docs/P*_*.md`, `data/spike/x.json`, `status/`, "
            "`backend/.venv/Scripts/python.exe`, `data/x.db`, `frontend/dist/index.html`\n",
            encoding="utf-8",
        )
        assert self._findings(doc) == []

    def test_ignores_backticks_inside_code_fence(self, tmp_path: Path):
        doc = tmp_path / "ok.md"
        doc.write_text("```\n`docs/nope.md`\n```\n", encoding="utf-8")
        assert self._findings(doc) == []


class TestCommandLines:
    def test_extracts_only_shell_fence_commands(self):
        text = "```powershell\n# 주석\n.\\scripts\\x.ps1\nPS> git status\n$env:X = '1'\n```\n```python\nprint(1)\n```\n"
        assert verify_docs.command_lines(text) == [(3, ".\\scripts\\x.ps1"), (4, "git status")]

    def test_full_path_python_exe_is_a_command(self):
        """역테스트가 잡은 누락 — `backend\\.venv\\Scripts\\python.exe -m …` 도 명령이다."""
        text = "```powershell\nbackend\\.venv\\Scripts\\python.exe -m pytest\n```\n"
        assert len(verify_docs.command_lines(text)) == 1


class TestHelpersAndMain:
    def test_strip_comment_respects_quotes(self):
        assert verify_docs.strip_comment('echo "# 주석 아님" # 진짜 주석') == 'echo "# 주석 아님"'
        assert verify_docs.strip_comment("echo '#x'   ") == "echo '#x'"
        assert verify_docs.strip_comment("# 전부 주석") == ""

    def test_finding_str_for_doc_outside_root(self, tmp_path: Path):
        doc = tmp_path / "x.md"
        finding = verify_docs.Finding(doc, 3, "link", "깨진 링크")
        assert "[link]" in str(finding) and "x.md:3" in str(finding)

    def test_main_reports_missing_doc_and_returns_1(self, capsys: pytest.CaptureFixture[str]):
        """FR-28 — --path 로 없는 문서를 주면 missing 위반, 종료 1."""
        code = verify_docs.main(["--path", "docs/NOPE_없는문서.md", "--quiet"])
        out = capsys.readouterr().out
        assert code == 1 and "[missing]" in out

    def test_main_single_clean_doc_returns_0(self, capsys: pytest.CaptureFixture[str]):
        code = verify_docs.main(["--path", "CLAUDE.md"])
        out = capsys.readouterr().out
        assert code == 0 and "위반 없음" in out


class TestTrackedFiles:
    """T-008 역테스트 — git 출력 디코딩이 깨지면 "추적 파일 0건"으로 조용히 넘어갔다."""

    def test_korean_paths_are_decoded(self):
        """`core.quotepath=false` 인 이 저장소에서 한글 경로가 그대로 읽혀야 한다.

        로케일(cp1252) 디코딩이면 예외가 리더 스레드에서 터지고 stdout 이 None 이 되는데 종료 코드는 0 이라
        검사기가 통과해 버린다. 한글 문서가 목록에 있으면 utf-8 로 읽혔다는 뜻이다.
        """
        verify_docs._tracked_cache = None
        tracked = verify_docs.tracked_files()
        assert "docs/scope-definition.md" in tracked
        assert "docs/설계서_Architecture.md" in tracked


class TestPs1Encoding:
    """T-005 역테스트 — 한글이 든 BOM 없는 .ps1 은 PowerShell 5.1 에서 실행 자체가 안 된다."""

    def test_repository_ps1_files_all_have_bom(self):
        assert verify_docs.check_ps1_encoding() == []

    def test_detects_korean_ps1_without_bom(self, tmp_path: Path):
        (tmp_path / "bad.ps1").write_bytes("Write-Host '프론트'\n".encode())
        assert kinds(verify_docs.check_ps1_encoding(tmp_path)) == {"ps1-bom"}

    def test_accepts_korean_ps1_with_bom(self, tmp_path: Path):
        (tmp_path / "ok.ps1").write_bytes(verify_docs.UTF8_BOM + "Write-Host '프론트'\n".encode())
        assert verify_docs.check_ps1_encoding(tmp_path) == []

    def test_accepts_ascii_only_ps1_without_bom(self, tmp_path: Path):
        """오탐 방지 — ASCII 전용이면 코드페이지와 무관하게 같게 읽힌다."""
        (tmp_path / "ascii.ps1").write_bytes(b"Write-Host 'ok'\n")
        assert verify_docs.check_ps1_encoding(tmp_path) == []
