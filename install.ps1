# Mythos Install -- run this in PowerShell:
#   .\install.ps1

$Host.UI.RawUI.WindowTitle = "Mythos Install"
$Repo = "https://github.com/samkomedved319-dev/Mythos.git"
$BinDir = "$HOME\.local\bin"

Write-Host "== Mythos Install ==" -ForegroundColor Cyan

# Check prerequisites
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Host "FAILED: Python not found. Install from https://python.org" -ForegroundColor Red; exit 1
}
if (-not (Get-Command "ollama" -ErrorAction SilentlyContinue)) {
    Write-Host "FAILED: Ollama not found. Install from https://ollama.com" -ForegroundColor Red; exit 1
}

# Detect if we're running from the repo or need to download
$LocalRepo = (Test-Path ".\mythos_cli.py")
if (-not $LocalRepo) {
    Write-Host "Downloading Mythos..." -ForegroundColor Yellow
    $d = "$HOME\Mythos"
    if (Get-Command "git" -ErrorAction SilentlyContinue) {
        if (Test-Path $d) { Set-Location $d; git pull }
        else { git clone $Repo $d; Set-Location $d }
    } else {
        $z = "$env:TEMP\mythos.zip"
        Invoke-WebRequest "https://github.com/samkomedved319-dev/Mythos/archive/refs/heads/main.zip" -OutFile $z
        Expand-Archive $z $HOME -Force; Remove-Item $z
        Set-Location "$HOME\Mythos-main"
    }
}
$RepoDir = Get-Location
Write-Host ""

# Install deps
Write-Host "[1/3] pip install..."
pip install -r requirements.txt | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Host "FAILED: pip install" -ForegroundColor Red; exit 1 }
Write-Host "  OK" -ForegroundColor Green

# Build model
Write-Host "[2/3] ollama create mythos..."
try { Invoke-RestMethod "http://localhost:11434/api/tags" -TimeoutSec 2 | Out-Null }
catch { Write-Host "  Starting Ollama..." -ForegroundColor Yellow; Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden; Start-Sleep 3 }
ollama pull llama3 | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Host "FAILED: pull llama3" -ForegroundColor Red; exit 1 }
ollama create mythos -f "$RepoDir\Modelfile" *>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Host "FAILED: create model" -ForegroundColor Red; exit 1 }
Write-Host "  OK" -ForegroundColor Green

# Install the mythos command
Write-Host "[3/3] install 'mythos' command..."
if (-not (Test-Path $BinDir)) { New-Item $BinDir -ItemType Directory -Force | Out-Null }
@"
@echo off
python "$RepoDir\mythos_cli.py" %*
if errorlevel 1 ( echo. & pause )
"@ | Out-File "$BinDir\mythos.cmd" -Encoding ascii
Write-Host "  Installed: $BinDir\mythos.cmd" -ForegroundColor Green
if ($env:PATH -notlike "*$BinDir*") {
    $env:PATH = "$BinDir;$env:PATH"
    try { [Environment]::SetEnvironmentVariable("PATH","$BinDir;$([Environment]::GetEnvironmentVariable('PATH','User'))","User") } catch {}
}
Write-Host "  OK" -ForegroundColor Green

Write-Host ""
Write-Host "== DONE ==" -ForegroundColor Green
Write-Host "Type:  mythos" -ForegroundColor Cyan
Write-Host "Need a token? https://samkomedved319-dev.github.io/Mythos" -ForegroundColor Gray
