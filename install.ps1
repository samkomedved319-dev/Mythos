# Mythos CLI Installation Script for Windows
# Run:  powershell -ExecutionPolicy Bypass -File install.ps1

Write-Host "--- Mythos Sovereign Architect Setup ---" -ForegroundColor Cyan

$RepoUrl   = "https://github.com/samkomedved319-dev/Mythos.git"
$InstallDir = "$HOME\Mythos"

# ── 1. Bootstrap / download ──
if (!(Test-Path "$PSScriptRoot\Modelfile") -and !(Test-Path ".\Modelfile")) {
    Write-Host "`n[0/3] Downloading Mythos repository..." -ForegroundColor Yellow

    if (Get-Command "git" -ErrorAction SilentlyContinue) {
        if (Test-Path $InstallDir) {
            Write-Host "Updating existing repository in $InstallDir..." -ForegroundColor Gray
            Set-Location $InstallDir
            git pull
        } else {
            git clone $RepoUrl $InstallDir
            Set-Location $InstallDir
        }
    } else {
        Write-Host "[!] Git not found. Downloading ZIP..." -ForegroundColor Gray
        $ZipPath = "$env:TEMP\mythos-main.zip"
        Invoke-WebRequest "https://github.com/samkomedved319-dev/Mythos/archive/refs/heads/main.zip" -OutFile $ZipPath
        Expand-Archive -Path $ZipPath -DestinationPath $HOME -Force
        Remove-Item $ZipPath
        $InstallDir = "$HOME\Mythos-main"
        Set-Location $InstallDir
    }
} else {
    $InstallDir = Get-Location
}

# ── 2. Install Python dependencies ──
Write-Host "`n[1/3] Installing Python dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] pip install failed. Make sure Python 3.10+ and pip are in PATH." -ForegroundColor Red
    exit 1
}

# ── 3. Build the Ollama model ──
Write-Host "`n[2/3] Building Ollama model 'mythos'..." -ForegroundColor Yellow
if (Get-Command "ollama" -ErrorAction SilentlyContinue) {
    ollama create mythos -f Modelfile
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] Failed to build model. Is Ollama running?" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[!] Ollama not found. Install from https://ollama.com then re-run." -ForegroundColor Red
    exit 1
}

# ── 4. Install the 'mythos' command ──
Write-Host "`n[3/3] Installing 'mythos' command..." -ForegroundColor Yellow

$BinDir = "$HOME\.mythos\bin"
if (!(Test-Path $BinDir)) {
    New-Item -ItemType Directory -Path $BinDir -Force | Out-Null
}

# Create a robust mythos.cmd that finds its own directory
$cmdContent = @"
@echo off
REM Mythos CLI launcher — installed by install.ps1
python "$InstallDir\mythos_cli.py" %*
"@
$cmdContent | Out-File -FilePath "$BinDir\mythos.cmd" -Encoding ascii

# Add to PATH for current session
if ($env:PATH -notlike "*$BinDir*") {
    $env:PATH = "$BinDir;$env:PATH"
}

# Attempt to add to user PATH permanently
try {
    $currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    if ($currentPath -notlike "*$BinDir*") {
        [Environment]::SetEnvironmentVariable("PATH", "$BinDir;$currentPath", "User")
        Write-Host "  Added $BinDir to your user PATH." -ForegroundColor Green
    }
} catch {
    Write-Host "  Could not update PATH automatically. See note below." -ForegroundColor Gray
}

Write-Host ""
Write-Host "--- Setup Complete! ---" -ForegroundColor Green
Write-Host "You can now start Mythos by typing:  mythos" -ForegroundColor Cyan
Write-Host ""
Write-Host "First time? You'll be asked for an API token." -ForegroundColor Gray
Write-Host "Visit the website to sign up and get yours:" -ForegroundColor Gray
Write-Host "  https://samkomedved319-dev.github.io/Mythos" -ForegroundColor Gray
Write-Host ""
Write-Host "If 'mythos' is not recognized, restart your terminal or run:" -ForegroundColor Yellow
Write-Host "  set PATH=%USERPROFILE%\.mythos\bin;%PATH%" -ForegroundColor Yellow
