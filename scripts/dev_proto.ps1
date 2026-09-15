# 프로토타입 실행 — 백엔드(uvicorn :8765) + 프론트(Vite :5173) 를 각각 새 창으로 띄운다.
# 대응: docs/internal/검토서_Prototype.md 2절. 사전: .\scripts\check_env.ps1 → READY, frontend\node_modules 설치.
# 사용: .\scripts\dev_proto.ps1      종료: 두 창을 닫는다.

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$py = Join-Path $repoRoot "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Host "backend\.venv 없음 — README 최초 1회 절차를 먼저"; exit 1 }
if (-not (Test-Path (Join-Path $repoRoot "frontend\node_modules"))) { Write-Host "frontend\node_modules 없음 — Push-Location frontend; npm install; Pop-Location"; exit 1 }

$env:PYTHONUTF8 = "1"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$repoRoot'; `$env:PYTHONUTF8='1'; & '$py' -m uvicorn youtube_learner.proto.app:app --host 127.0.0.1 --port 8765"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$repoRoot\frontend'; npm run dev"
Write-Host "백엔드: http://127.0.0.1:8765/health   프론트: http://localhost:5173   (각각 새 창에서 실행 중)"
