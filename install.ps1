# Mythos: Sovereign Architect -- One-Command Installer for Windows
# Run in PowerShell:
#   irm https://raw.githubusercontent.com/samkomedved319-dev/Mythos/main/install.ps1 | iex

$Host.UI.RawUI.WindowTitle = "Mythos Setup"

$RepoUrl    = "https://github.com/samkomedved319-dev/Mythos.git"
$InstallDir = "$HOME\Mythos"
$BinDir     = "$HOME\.local\bin"

Write-Host "== Mythos Sovereign Architect Setup ==" -ForegroundColor Cyan
Write-Host ""

# ----- Step 0: Bootstrap -----
$RunningLocal = (Test-Path "$PSScriptRoot\mythos_cli.py") -or (Test-Path ".\mythos_cli.py")

if (-not $RunningLocal) {
    Write-Host "[0] Downloading Mythos..." -ForegroundColor Yellow
    if (Get-Command "git" -ErrorAction SilentlyContinue) {
        if (Test-Path $InstallDir) {
            Write-Host "  Updating existing repo..." -ForegroundColor Gray
            Set-Location $InstallDir
            git pull
        } else {
            git clone $RepoUrl $InstallDir
            Set-Location $InstallDir
        }
    } else {
        Write-Host "  Git not found. Downloading ZIP..." -ForegroundColor Gray
        $ZipPath = "$env:TEMP\mythos.zip"
        Invoke-WebRequest "https://github.com/samkomedved319-dev/Mythos/archive/refs/heads/main.zip" -OutFile $ZipPath
        Expand-Archive -Path $ZipPath -DestinationPath $HOME -Force
        Remove-Item $ZipPath
        $InstallDir = "$HOME\Mythos-main"
        Set-Location $InstallDir
    }
} else {
    $InstallDir = Get-Location
}

# ----- Step 1: Python dependencies -----
Write-Host "[1/3] Installing Python dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "  FAILED. Install Python 3.10+ from https://python.org" -ForegroundColor Red
    exit 1
}
Write-Host "  OK" -ForegroundColor Green
Write-Host ""

# ----- Step 2: Check Ollama -----
Write-Host "[2/3] Setting up Ollama model..." -ForegroundColor Yellow

$ollamaPath = (Get-Command "ollama" -ErrorAction SilentlyContinue).Source
if (-not $ollamaPath) {
    Write-Host "  Ollama not found. Install from https://ollama.com first." -ForegroundColor Red
    exit 1
}

# Check if Ollama server is running
try {
    $ollamaStatus = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 3 -ErrorAction Stop
    Write-Host "  Ollama server: OK" -ForegroundColor Gray
} catch {
    Write-Host "  Ollama server is not running." -ForegroundColor Yellow
    Write-Host "  Starting Ollama..." -ForegroundColor Gray
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

# Pull base model if needed
Write-Host "  Pulling base model (llama3)..." -ForegroundColor Gray
ollama pull llama3
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Failed to pull llama3. Check your internet connection." -ForegroundColor Red
    exit 1
}

# Create Mythos model
Write-Host "  Creating Mythos model..." -ForegroundColor Gray
ollama create mythos -f Modelfile
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Failed to create model. Check Modelfile." -ForegroundColor Red
    exit 1
}
Write-Host "  OK" -ForegroundColor Green
Write-Host ""

# ----- Step 3: Install mythos command -----
Write-Host "[3/3] Installing 'mythos' command..." -ForegroundColor Yellow

if (-not (Test-Path $BinDir)) {
    New-Item -ItemType Directory -Path $BinDir -Force | Out-Null
}

@"
@echo off
set "MYTHOS_DIR=$InstallDir"
if not exist "%MYTHOS_DIR%\mythos_cli.py" (
    echo [ERROR] Mythos not found at %MYTHOS_DIR%
    pause
    exit /b 1
)
python "%MYTHOS_DIR%\mythos_cli.py" %*
if errorlevel 1 (
    echo.
    pause
)
"@ | Out-File -FilePath "$BinDir\mythos.cmd" -Encoding ascii

Write-Host "  Installed to: $BinDir\mythos.cmd" -ForegroundColor Green

# Add to PATH
if ($env:PATH -notlike "*$BinDir*") {
    $env:PATH = "$BinDir;$env:PATH"
}
try {
    $userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    if ($userPath -notlike "*$BinDir*") {
        [Environment]::SetEnvironmentVariable("PATH", "$BinDir;$userPath", "User")
        Write-Host "  Added to PATH permanently." -ForegroundColor Green
    }
} catch {
    Write-Host "  Run: set PATH=%USERPROFILE%\.local\bin;%PATH%" -ForegroundColor Gray
}

Write-Host ""
Write-Host "== Setup Complete! ==" -ForegroundColor Green
Write-Host "Type 'mythos' in any terminal to start." -ForegroundColor Cyan
Write-Host ""
Write-Host "First time? Get your API token at:" -ForegroundColor Gray
Write-Host "  https://samkomedved319-dev.github.io/Mythos" -ForegroundColor Gray
