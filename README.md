# Mythos: Sovereign Architect

A high-performance terminal interface for the Mythos AI model with web search,
network scanning, security auditing, and real-time AI chat.

## One-Command Install (Windows)

Open **PowerShell** and paste this:

```powershell
powershell -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/samkomedved319-dev/Mythos/main/install.ps1 | iex"
```

This downloads the repo, installs dependencies, builds the AI model, and sets up
the `mythos` command. After it finishes, just type:

```
mythos
```

## Requirements

1. **Python 3.10+** (with pip in PATH)
2. **Ollama** — [Download here](https://ollama.com/) (must be running)

## Quick Start (if you already cloned the repo)

Double-click `setup.bat` or run:

```
setup.bat
```

Then type `mythos` anywhere.

## First-Time Auth

1. Type `mythos` in your terminal
2. It shows a link to the Mythos web portal
3. Open the link, sign up, get your email + API token
4. Paste them back in the terminal
5. Done -- next time just type `mythos`

## Commands

| Command | What it does |
|---------|-------------|
| `/help` | Show all commands |
| `/search <q>` | Search the web (DuckDuckGo) |
| `/fetch <url>` | Fetch a web page |
| `/scan <host>` | Scan for open TCP ports |
| `/ssl <host>` | Inspect SSL certificate |
| `/whois <domain>` | WHOIS domain lookup |
| `/subdomains <domain>` | Find common subdomains |
| `/banner <host> <port>` | Grab service banner |
| `/dns <domain>` | DNS resolution |
| `/http <url>` | HTTP headers & security |
| `/ip [host]` | Resolve IP / show public IP |
| `/status` | System health |
| `/doctor` | Full diagnostics |
| `/session` | Session info |
| `/auth` | Auth status |
| `/reauth` | Re-authenticate |
| `/logout` | Clear credentials |
| `/clear` | Clear chat |
| `/exit` | Quit |

## License

MIT
