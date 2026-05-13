# Mythos: Sovereign Architect — One-Command Installer for Windows
# Run this in PowerShell:
#   irm https://raw.githubusercontent.com/samkomedved319-dev/Mythos/main/install.ps1 | iex

$Host.UI.RawUI.WindowTitle = "Mythos Setup"

$RepoUrl    = "https://github.com/samkomedved319-dev/Mythos.git"
$InstallDir = "$HOME\Mythos"
$BinDir     = "$HOME\.local\bin"   # Already in PATH on this system

Write-Host "== Mythos Sovereign Architect Setup ==" -ForegroundColor Cyan
Write-Host ""

# ----- Step 0: Bootstrap (download repo if running remotely) -----
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
pip install -r requirements.txt 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [!] pip failed. Install Python 3.10+ from https://python.org" -ForegroundColor Red
    exit 1
}
Write-Host "  OK" -ForegroundColor Green

# ----- Step 2: Build Ollama model -----
Write-Host "[2/3] Building Ollama model 'mythos'..." -ForegroundColor Yellow
if (Get-Command "ollama" -ErrorAction SilentlyContinue) {
    ollama create mythos -f Modelfile 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [!] Model build failed. Is Ollama running?" -ForegroundColor Red
        Write-Host "  Run: ollama serve" -ForegroundColor Gray
        exit 1
    }
    Write-Host "  OK" -ForegroundColor Green
} else {
    Write-Host "  [!] Ollama not found. Install from https://ollama.com" -ForegroundColor Red
    exit 1
}

# ----- Step 3: Install 'mythos' command -----
Write-Host "[3/3] Installing 'mythos' command..." -ForegroundColor Yellow

if (-not (Test-Path $BinDir)) {
    New-Item -ItemType Directory -Path $BinDir -Force | Out-Null
}

# Create mythos.cmd that points to the installed location
@"
@echo off
set "MYTHOS_DIR=$InstallDir"
if not exist "%MYTHOS_DIR%\mythos_cli.py" (
    echo [ERROR] Mythos not found at %MYTHOS_DIR%
    echo Re-run the installer.
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

# Add to current session PATH if not there
if ($env:PATH -notlike "*$BinDir*") {
    $env:PATH = "$BinDir;$env:PATH"
}

# Add to user PATH permanently
try {
    $userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    if ($userPath -notlike "*$BinDir*") {
        [Environment]::SetEnvironmentVariable("PATH", "$BinDir;$userPath", "User")
        Write-Host "  Added to PATH permanently." -ForegroundColor Green
    }
} catch {
    Write-Host "  [!] Could not update PATH automatically." -ForegroundColor Gray
    Write-Host "  Run: set PATH=%USERPROFILE%\.local\bin;%PATH%" -ForegroundColor Gray
}

Write-Host ""
Write-Host "== Setup Complete! ==" -ForegroundColor Green
Write-Host "Type 'mythos' in any terminal to start." -ForegroundColor Cyan
Write-Host ""
Write-Host "First time? You'll need an API token from:" -ForegroundColor Gray
Write-Host "  https://samkomedved319-dev.github.io/Mythos" -ForegroundColor Gray
