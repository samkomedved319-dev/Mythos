# Mythos: Sovereign Architect - PowerShell launcher
# Run this once to install the 'mythos' command for all PowerShell sessions:
#   . .\mythos.ps1 -Install

param([switch]$Install)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$cliScript = Join-Path $scriptDir "mythos_cli.py"

function Invoke-Mythos {
    python $cliScript @args
}

if ($Install) {
    $profilePath = $PROFILE.CurrentUserAllHosts
    $profileDir = Split-Path $profilePath -Parent
    if (-not (Test-Path $profileDir)) {
        New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
    }

    $line = "`n# Mythos CLI`nfunction mythos { python `"$cliScript`" @args }`n"

    if (Test-Path $profilePath) {
        $content = Get-Content $profilePath -Raw
        if ($content -notlike "*mythos*") {
            Add-Content $profilePath $line
            Write-Host "Added 'mythos' function to $profilePath" -ForegroundColor Green
        } else {
            Write-Host "'mythos' already in profile." -ForegroundColor Yellow
        }
    } else {
        Set-Content $profilePath $line
        Write-Host "Created profile and added 'mythos' at $profilePath" -ForegroundColor Green
    }

    Write-Host "`nRestart PowerShell or run: . $profilePath" -ForegroundColor Cyan
} else {
    Invoke-Mythos @args
}
