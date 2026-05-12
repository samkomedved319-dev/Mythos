# Mythos CLI Installation Script for Windows

Write-Host "--- Mythos Sovereign Architect Setup ---" -ForegroundColor Cyan

$RepoUrl = "https://github.com/samkomedved319-dev/Mythos.git"
$InstallDir = "$HOME\Mythos"

# 1. Bootstrap check: Are we running from the repo or as a remote script?
if (!(Test-Path "$PSScriptRoot\Modelfile") -and !(Test-Path ".\Modelfile")) {
    Write-Host "`n[0/3] Bootstrapping: Downloading Mythos repository..." -ForegroundColor Yellow
    
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

# 2. Install Python dependencies
Write-Host "`n[1/3] Installing Python dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# 3. Build the Ollama model
Write-Host "`n[2/3] Building Ollama model 'mythos'..." -ForegroundColor Yellow
if (Get-Command "ollama" -ErrorAction SilentlyContinue) {
    ollama create mythos -f Modelfile
} else {
    Write-Host "[!] Ollama not found in PATH. Please install Ollama first: https://ollama.com" -ForegroundColor Red
    exit
}

# 4. Setup the 'mythos' command shortcut
Write-Host "`n[3/3] Setting up 'mythos' command shortcut..." -ForegroundColor Yellow
$localBin = "$HOME\.local\bin"
if (!(Test-Path $localBin)) {
    New-Item -ItemType Directory -Path $localBin -Force | Out-Null
}

$scriptContent = "@echo off`npython ""$InstallDir\mythos_cli.py"" %*"
$scriptContent | Out-File -FilePath "$localBin\mythos.cmd" -Encoding ascii

# Ensure .local\bin is in PATH for the current session if not already
if ($env:PATH -notlike "*$localBin*") {
    $env:PATH += ";$localBin"
}

Write-Host "`n--- Setup Complete! ---" -ForegroundColor Green
Write-Host "You can now start the assistant by typing 'mythos' in your terminal." -ForegroundColor Cyan
Write-Host "Note: If 'mythos' is not recognized, please add '$localBin' to your system PATH." -ForegroundColor Gray

