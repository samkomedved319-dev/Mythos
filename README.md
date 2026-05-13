# Mythos

AI terminal assistant with web search, network scanning, and security tools.

## Install (Windows)

**One command** — paste this in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/samkomedved319-dev/Mythos/main/install.ps1 | iex"
```

Or **double-click** `install.bat` after cloning.

Requirements: Python 3.10+, Ollama (https://ollama.com)

## Use

```
mythos
```

First time? You need an API token from https://samkomedved319-dev.github.io/Mythos

## Commands

System: `/help` `/auth` `/whoami` `/session` `/status` `/doctor` `/reauth` `/logout`
Web:    `/search` `/fetch` `/ip` `/dns` `/http` `/scan` `/ssl` `/whois` `/subdomains` `/banner`
