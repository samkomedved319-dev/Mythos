# Mythos

AI terminal assistant with web search, port scanning, SSL inspection,
DNS tools, HTTP audits, and more.

## Install

### If you have the repo folder

Double-click **`install.bat`** or run in PowerShell:

```
.\install.ps1
```

### Fresh install (one command)

```powershell
powershell -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/samkomedved319-dev/Mythos/main/install.ps1 | iex"
```

### Requirements

- **Python 3.10+** with pip
- **Ollama** running (get it at https://ollama.com)

## Use

```
mythos
```

First time? Sign up at mythos website, then paste your email + token.

## Commands

### System
`/auth` `/whoami` `/session` `/status` `/doctor` `/config` `/reauth` `/logout` `/model` `/clear` `/exit`

### Web & Network
`/search <q>` – Web search (DuckDuckGo)
`/fetch <url>` – Fetch a web page
`/ip [host]` – Resolve IP or show public IP
`/dns <domain>` – DNS records
`/http <url>` – HTTP security headers
`/scan <host>` – Open port scan (30 ports)
`/ssl <host>` – SSL certificate details
`/whois <domain>` – WHOIS lookup
`/subdomains <domain>` – Subdomain enumeration
`/banner <host> <port>` – Service banner grab
