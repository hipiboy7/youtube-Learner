# 프로토타입 실행 — 백엔드(uvicorn :8765) + 프론트(Vite :5173) 를 각각 새 창으로 띄운다.
# 대응: docs/internal/검토서_Prototype.md 2절. 사전: .\scripts\check_env.ps1 → READY, frontend\node_modules 설치.
# 사용: .\scripts\dev_proto.ps1      종료: 두 창을 닫는다 (이 스크립트를 다시 실행하면 남아 있는 옛 서버를 먼저 정리한다).

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$py = Join-Path $repoRoot "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Host "backend\.venv 없음 — README 최초 1회 절차를 먼저"; exit 1 }
if (-not (Test-Path (Join-Path $repoRoot "frontend\node_modules"))) { Write-Host "frontend\node_modules 없음 — Push-Location frontend; npm install; Pop-Location"; exit 1 }

# 창을 닫아도 uvicorn·vite 자식 프로세스가 살아남아 옛 코드로 계속 응답하는 일이 있었다(2026-09-15).
# 같은 포트를 듣는 프로세스를 먼저 끝내서 "재실행 = 새 코드" 를 보장한다.
foreach ($port in 8765, 5173) {
    $pids = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $pids) {
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if ($proc) { Write-Host ("포트 {0} 의 이전 프로세스 종료: {1} (PID {2})" -f $port, $proc.ProcessName, $procId); Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue }
    }
}
Start-Sleep -Milliseconds 800

$env:PYTHONUTF8 = "1"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$repoRoot'; `$env:PYTHONUTF8='1'; & '$py' -m uvicorn youtube_learner.proto.app:app --host 127.0.0.1 --port 8765"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$repoRoot\frontend'; npm run dev"
Write-Host "백엔드: http://127.0.0.1:8765/health   프론트: http://localhost:5173   (각각 새 창에서 실행 중)"
Write-Host "백엔드 버전 확인: http://127.0.0.1:8765/health 의 version 값 — 화면 상단 경고가 뜨면 이 스크립트를 다시 실행한다"
