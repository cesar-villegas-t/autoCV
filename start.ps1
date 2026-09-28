# One-click local dev launcher: Postgres (Docker), backend and frontend, each
# in its own window. Reads .env from the repo root (create it from .env.example
# if missing) since the app itself never loads .env files automatically.
$root = $PSScriptRoot
$envFile = Join-Path $root ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "Falta $envFile. Copia .env.example a .env y rellena GEMINI_API_KEY." -ForegroundColor Red
    exit 1
}

$vars = @{}
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*([A-Z_]+)\s*=\s*(.*)\s*$') { $vars[$matches[1]] = $matches[2] }
}
if (-not $vars["GEMINI_API_KEY"]) {
    Write-Host "GEMINI_API_KEY está vacío en .env. Añade tu clave antes de arrancar." -ForegroundColor Red
    exit 1
}

Write-Host "Levantando PostgreSQL (Docker)..." -ForegroundColor Cyan
Push-Location $root
docker compose up -d --wait db
Pop-Location

$backendEnv = ($vars.GetEnumerator() | ForEach-Object { "`$env:$($_.Key)='$($_.Value)'" }) -join "; "
$backendCmd = "cd '$root'; $backendEnv; .\.venv\Scripts\Activate.ps1; python -m uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000"
$frontendCmd = "cd '$root\apps\web'; npm run dev"

Write-Host "Arrancando el backend en una ventana nueva..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

Write-Host "Arrancando el frontend en una ventana nueva..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Write-Host "Esperando a que el frontend responda..." -ForegroundColor Cyan
$ready = $false
for ($i = 0; $i -lt 40; $i++) {
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:5173" -UseBasicParsing -TimeoutSec 1 | Out-Null
        $ready = $true
        break
    } catch { Start-Sleep -Milliseconds 500 }
}

if ($ready) {
    Start-Process "http://127.0.0.1:5173"
    Write-Host "Listo: http://127.0.0.1:5173 (usa siempre 127.0.0.1, no localhost)." -ForegroundColor Green
} else {
    Write-Host "El frontend no respondió a tiempo. Revisa la ventana que abrió npm run dev." -ForegroundColor Yellow
}
