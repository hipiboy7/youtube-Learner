# 환경 검사 래퍼 — 대응: docs/P0_설계서_Common.md 10절 (FR-27). CLAUDE.md 1절 0단계.
# 하는 일은 하나: backend\.venv 의 python 을 찾아 youtube_learner.cli.check_env 를 그대로 실행하고 종료 코드를 전달한다.
# 검사 로직은 Python 에 있다(pytest 로 검증). 사용: .\scripts\check_env.ps1 [--json] [--strict]

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$py = Join-Path $repoRoot "backend\.venv\Scripts\python.exe"

if (-not (Test-Path $py)) {
    Write-Host "[FAIL] venv — $py 가 없다. 생성 절차:"
    Write-Host "       py -3.12 -m venv backend\.venv"
    Write-Host "       backend\.venv\Scripts\python.exe -m pip install -e `"backend[youtube,stt,dev]`""
    Write-Host "==> NOT READY (1 failures)"
    exit 1
}

$env:PYTHONUTF8 = "1"
Push-Location $repoRoot
try {
    & $py -m youtube_learner.cli.check_env @args
    $code = $LASTEXITCODE
}
finally {
    Pop-Location
}
exit $code
