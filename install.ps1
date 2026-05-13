# Mythos: Sovereign Architect -- One-Command Installer
# Paste this in PowerShell:
#   irm https://raw.githubusercontent.com/samkomedved319-dev/Mythos/main/install.ps1 | iex

$Host.UI.RawUI.WindowTitle = "Mythos Install"

$Repo      = "https://github.com/samkomedved319-dev/Mythos.git"
$InstallDir = "$HOME\Mythos"
$BinDir    = "$HOME\.local\bin"

Write-Host "== Mythos Install ==" -ForegroundColor Cyan

# ----- Prerequisites -----
$pythonOk = (Get-Command "python" -ErrorAction SilentlyContinue) -ne $null
$ollamaOk = (Get-Command "ollama" -ErrorAction SilentlyContinue) -ne $null

if (-not $pythonOk) {
    Write-Host "FAILED: Python not found. Install Python 3.10+ from https://python.org" -ForegroundColor Red
    exit 1
}
if (-not $ollamaOk) {
    Write-Host "FAILED: Ollama not found. Install from https://ollama.com" -ForegroundColor Red
    exit 1
}

# ----- Download repo -----
$here = Test-Path ".\mythos_cli.py"
if (-not $here) {
    Write-Host "Downloading Mythos..." -ForegroundColor Yellow
    if (Get-Command "git" -ErrorAction SilentlyContinue) {
        if (Test-Path $InstallDir) { Set-Location $InstallDir; git pull }
        else { git clone $Repo $InstallDir; Set-Location $InstallDir }
    } else {
        $z = "$env:TEMP\mythos.zip"
        Invoke-WebRequest "https://github.com/samkomedved319-dev/Mythos/archive/refs/heads/main.zip" -OutFile $z
        Expand-Archive $z $HOME -Force; Remove-Item $z
        $InstallDir = "$HOME\Mythos-main"; Set-Location $InstallDir
    }
} else {
    $InstallDir = Get-Location
}

Write-Host ""

# ----- Install deps -----
Write-Host "[1/3] pip install..."
pip install -r requirements.txt | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Host "FAILED: pip install" -ForegroundColor Red; exit 1 }
Write-Host "  OK" -ForegroundColor Green

# ----- Build model -----
Write-Host "[2/3] ollama create mythos..."

# Make sure ollama server is running
try { Invoke-RestMethod "http://localhost:11434/api/tags" -TimeoutSec 2 | Out-Null }
catch {
    Write-Host "  Starting Ollama server..." -ForegroundColor Yellow
    Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep 3
}

ollama pull llama3 | Out-Null
ollama create mythos -f Modelfile 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Host "FAILED: ollama create mythos" -ForegroundColor Red; exit 1 }
Write-Host "  OK" -ForegroundColor Green

# ----- Install command -----
Write-Host "[3/3] installing 'mythos' command..."
if (-not (Test-Path $BinDir)) { New-Item $BinDir -ItemType Directory -Force | Out-Null }

@"
@echo off
python "$InstallDir\mythos_cli.py" %*
if errorlevel 1 ( echo. & pause )
"@ | Out-File "$BinDir\mythos.cmd" -Encoding ascii

if ($env:PATH -notlike "*$BinDir*") { $env:PATH = "$BinDir;$env:PATH" }
try {
    $p = [Environment]::GetEnvironmentVariable("PATH","User")
    if ($p -notlike "*$BinDir*") { [Environment]::SetEnvironmentVariable("PATH","$BinDir;$p","User") }
} catch {}

Write-Host "  OK" -ForegroundColor Green
Write-Host ""
Write-Host "== DONE ==" -ForegroundColor Green
Write-Host "Type:  mythos" -ForegroundColor Cyan
Write-Host ""
Write-Host "Need a token? https://samkomedved319-dev.github.io/Mythos" -ForegroundColor Gray
