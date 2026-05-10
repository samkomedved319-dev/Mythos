# Mythos CLI Installation Script for Windows

Write-Host "--- Mythos Sovereign Architect Setup ---" -ForegroundColor Cyan

# 1. Install Python dependencies
Write-Host "`n[1/3] Installing Python dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# 2. Build the Ollama model
Write-Host "`n[2/3] Building Ollama model 'mythos'..." -ForegroundColor Yellow
if (Get-Command "ollama" -ErrorAction SilentlyContinue) {
    ollama create mythos -f Modelfile
} else {
    Write-Host "[!] Ollama not found in PATH. Please install Ollama first: https://ollama.com" -ForegroundColor Red
    exit
}

# 3. Setup the 'mythos' command shortcut
Write-Host "`n[3/3] Setting up 'mythos' command shortcut..." -ForegroundColor Yellow
$localBin = "$HOME\.local\bin"
if (!(Test-Path $localBin)) {
    New-Item -ItemType Directory -Path $localBin -Force | Out-Null
}

$scriptContent = "@echo off`npython ""$PSScriptRoot\mythos_cli.py"" %*"
$scriptContent | Out-File -FilePath "$localBin\mythos.cmd" -Encoding ascii

Write-Host "`n--- Setup Complete! ---" -ForegroundColor Green
Write-Host "You can now start the assistant by typing 'mythos' in a new terminal." -ForegroundColor Cyan
Write-Host "Note: Ensure '$localBin' is in your system PATH." -ForegroundColor Gray
