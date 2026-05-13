import json
import httpx
import sys
import os
import re
import asyncio
import socket
import ssl
import datetime
import ipaddress
import msvcrt
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.theme import Theme
from rich.status import Status
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich import box
from rich.text import Text
from rich.align import Align
from rich.syntax import Syntax
from rich.columns import Columns
from rich.layout import Layout

# ---------------------------------------------------------------------------
#  CONFIG
# ---------------------------------------------------------------------------

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "mythos"
AUTH_URL   = "https://samkomedved319-dev.github.io/Mythos"
CONFIG_DIR  = os.path.join(os.path.expanduser("~"), ".mythos")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
TOKEN_PATTERN = re.compile(r"^mth_[a-z0-9]{8}-[a-z0-9]{8}-[a-z0-9]{8}-[a-z0-9]{8}$")
ADMIN_EMAIL = "samkomedved319@gmail.com"

# Common ports for /scan
COMMON_PORTS = {
    21:"FTP",22:"SSH",23:"Telnet",25:"SMTP",53:"DNS",80:"HTTP",
    110:"POP3",111:"RPC",135:"RPC",139:"NetBIOS",143:"IMAP",
    443:"HTTPS",445:"SMB",993:"IMAPS",995:"POP3S",
    1433:"MSSQL",1521:"Oracle",2049:"NFS",3306:"MySQL",
    3389:"RDP",5432:"PostgreSQL",5900:"VNC",5985:"WinRM",
    5986:"WinRMS",6379:"Redis",8080:"HTTP-Alt",8443:"HTTPS-Alt",
    9000:"WebApp",9090:"WebApp",27017:"MongoDB"
}

# ---------------------------------------------------------------------------
#  RICH THEME  (Claude Code inspired -- clean, minimal, high contrast)
# ---------------------------------------------------------------------------

custom_theme = Theme({
    "meta":       "dim white",
    "user":       "bold green",
    "assistant":  "bold cyan",
    "prompt":     "bold white",
    "cmd":        "bold yellow",
    "error":      "bold red",
    "success":    "bold green",
    "warning":    "bold yellow",
    "info":       "dim cyan",
    "dim":        "dim white",
    "accent":     "bold cyan",
})
console = Console(theme=custom_theme, safe_box=True, legacy_windows=True)

# ---------------------------------------------------------------------------
#  TOOL CALL RENDERING  (Claude Code style -- ">" prefix, clean separator)
# ---------------------------------------------------------------------------

def tool_header(name, target=""):
    """Render a Claude Code-style tool call header."""
    label = name.upper()
    if target:
        console.print(f"  [dim]>[/dim] [accent]{label}[/accent] [dim]{target}[/dim]")
    else:
        console.print(f"  [dim]>[/dim] [accent]{label}[/accent]")

def tool_result(content):
    """Render tool result content indented."""
    for line in content.strip().split("\n"):
        console.print(f"  [dim]|[/dim] {line}")

def tool_error(msg):
    console.print(f"  [dim]>[/dim] [error]! {msg}[/error]")

def tool_table(title, columns, rows, style="cyan"):
    """Render a table as a tool result."""
    t = Table(title=title, border_style=style, box=box.ROUNDED, title_justify="left")
    for col in columns:
        t.add_column(col[0], style=col[1] if len(col) > 1 else "", no_wrap=col[2] if len(col) > 2 else False)
    for row in rows:
        t.add_row(*row)
    console.print(t)

# Status badge: short, one-line session header
def render_status(email, role, messages_len):
    r = "o" if role == "admin" else "o"
    role_tag = f" {r} Admin" if role == "admin" else ""
    return f"[dim]{email}{role_tag}[/dim] [dim]|[/dim] [accent]{MODEL_NAME}[/accent] [dim]| msgs: {messages_len}[/dim]"

# ---------------------------------------------------------------------------
#  CONFIG / CREDENTIALS
# ---------------------------------------------------------------------------

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def save_config(config):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

def get_stored_token():
    return load_config().get("token", None)

def get_stored_email():
    return load_config().get("email", None)

def store_credentials(email, token):
    cfg = load_config()
    cfg["email"] = email
    cfg["token"] = token
    save_config(cfg)

def clear_credentials():
    cfg = load_config()
    cfg.pop("email", None)
    cfg.pop("token", None)
    save_config(cfg)

def is_valid_token(token):
    return bool(token and TOKEN_PATTERN.match(token))

def is_admin_email(email):
    return email and email.lower() == ADMIN_EMAIL

def get_user_role(email):
    return "admin" if is_admin_email(email) else "user"

# ---------------------------------------------------------------------------
#  AUTH
# ---------------------------------------------------------------------------

def require_auth():
    email = get_stored_email()
    token = get_stored_token()
    if email and token and is_valid_token(token):
        return True

    console.clear()
    console.print()
    console.print(Panel(
        "[bold]Welcome to Mythos -- Sovereign Architect[/bold]\n\n"
        "This CLI requires authentication.\n\n"
        f"  [accent]>[/accent] Open: [bold cyan underline]{AUTH_URL}[/bold cyan underline]\n"
        "  [accent]>[/accent] Sign up or log in\n"
        "  [accent]>[/accent] Copy your email + token from Dashboard\n"
        "  [accent]>[/accent] Paste them below\n",
        title="Authentication Required",
        border_style="yellow",
    ))
    console.print()

    while True:
        ei = Prompt.ask("[yellow]Your email[/yellow]").strip().lower()
        if ei.lower() in ("exit", "quit", "q", ""):
            console.print("\n[info]Exiting.[/info]")
            return False
        if "@" not in ei or "." not in ei:
            console.print("[error]Valid email required.[/error]\n")
            continue
        break

    while True:
        ti = Prompt.ask("[yellow]Your API token[/yellow]").strip()
        if ti.lower() in ("exit", "quit", "q"):
            console.print("\n[info]Exiting.[/info]")
            return False
        if not ti:
            console.print("[error]Token cannot be empty.[/error]\n")
            continue
        if not is_valid_token(ti):
            console.print("[error]Invalid format. Expected: mth_xxxx-xxxx-xxxx-xxxx[/error]\n")
            continue
        break

    role = get_user_role(ei)
    store_credentials(ei, ti)
    console.print()
    if role == "admin":
        console.print("[success]  Authenticated as Mythos Admin[/success]")
    else:
        console.print("[success]  Authenticated[/success]")
    console.print("[info]Type /help for commands.[/info]\n")
    return True

# ---------------------------------------------------------------------------
#  WEB / NETWORK TOOLS
# ---------------------------------------------------------------------------

def web_search(query, max_results=5):
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({"title": r.get("title",""), "href": r.get("href",""), "body": r.get("body","")})
        return results
    except Exception as e:
        return {"error": str(e)}

def fetch_page(url, timeout=10):
    try:
        if not url.startswith(("http://","https://")):
            url = "https://" + url
        r = httpx.get(url, timeout=timeout, follow_redirects=True)
        text = r.text
        if len(text) > 5000:
            text = text[:5000] + f"\n\n[dim]... truncated ({len(r.text)} bytes total)[/dim]"
        return {"status": r.status_code, "headers": dict(r.headers), "content": text, "url": str(r.url)}
    except Exception as e:
        return {"error": str(e)}

def scan_ports(host, ports=None, timeout=1.5):
    if ports is None:
        ports = list(COMMON_PORTS.keys())
    host = re.sub(r'^https?://', '', host).split('/')[0].split(':')[0]
    open_ports = []
    def check(port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            r = s.connect_ex((host, port))
            s.close()
            return port if r == 0 else None
        except:
            return None
    with ThreadPoolExecutor(max_workers=50) as ex:
        for f in as_completed([ex.submit(check, p) for p in ports]):
            r = f.result()
            if r: open_ports.append(r)
    open_ports.sort()
    return open_ports

def dns_lookup(domain):
    domain = re.sub(r'^https?://', '', domain).split('/')[0].split(':')[0]
    r = {}
    try:
        r["A (IPv4)"] = list(set(info[4][0] for info in socket.getaddrinfo(domain, 80, socket.AF_INET)))
    except: r["A (IPv4)"] = ["[error]No record[/error]"]
    try:
        r["AAAA (IPv6)"] = list(set(info[4][0] for info in socket.getaddrinfo(domain, 80, socket.AF_INET6)))
    except: r["AAAA (IPv6)"] = ["[error]No record[/error]"]
    return r

def http_headers(url, timeout=10):
    try:
        if not url.startswith(("http://","https://")):
            url = "https://" + url
        r = httpx.head(url, timeout=timeout, follow_redirects=True)
        h = dict(r.headers)
        return {
            "Status": r.status_code,
            "Server": h.get("server","N/A"),
            "Powered By": h.get("x-powered-by","N/A"),
            "HSTS": "Yes" if "strict-transport-security" in h else "No",
            "XSS Protection": h.get("x-xss-protection","N/A"),
            "Content-Type Options": h.get("x-content-type-options","N/A"),
            "Frame Options": h.get("x-frame-options","N/A"),
            "CSP": "Yes" if "content-security-policy" in h else "No",
            "CORS": h.get("access-control-allow-origin","N/A"),
            "Final URL": str(r.url),
        }
    except Exception as e:
        return {"error": str(e)}

def resolve_ip(host):
    host = re.sub(r'^https?://', '', host).split('/')[0].split(':')[0]
    try:
        ips = set()
        try:
            for info in socket.getaddrinfo(host, 80):
                ips.add(info[4][0])
        except: pass
        if ips: return {"host": host, "ips": list(ips)}
        ip = socket.gethostbyname(host)
        return {"host": host, "ips": [ip]}
    except Exception as e:
        return {"error": str(e), "host": host}

# ---------------------------------------------------------------------------
#  SECURITY AUDIT TOOLS  (legitimate security assessment)
# ---------------------------------------------------------------------------

def ssl_check(host, port=443, timeout=5):
    """Check SSL certificate details for a host."""
    host = re.sub(r'^https?://', '', host).split('/')[0].split(':')[0]
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                return {
                    "host": host,
                    "port": port,
                    "subject": dict(cert.get("subject", [])[0]) if cert.get("subject") else {},
                    "issuer": dict(cert.get("issuer", [])[0]) if cert.get("issuer") else {},
                    "version": cert.get("version", ""),
                    "serial": cert.get("serialNumber", ""),
                    "not_before": cert.get("notBefore", ""),
                    "not_after": cert.get("notAfter", ""),
                    "sans": [entry for d in cert.get("subjectAltName", []) for entry in d if entry],
                    "cipher": ssock.cipher(),
                    "ocsp": cert.get("OCSP", "N/A"),
                    "ca_issuers": cert.get("caIssuers", "N/A"),
                }
    except Exception as e:
        return {"error": str(e), "host": host}

def whois_lookup(domain, timeout=10):
    """Perform WHOIS lookup using system command or public API."""
    domain = re.sub(r'^https?://', '', domain).split('/')[0].split(':')[0]
    try:
        # Try using httpx to query a free WHOIS API
        r = httpx.get(f"https://whois.freeaiapi.com/?domain={domain}", timeout=timeout)
        if r.status_code == 200:
            data = r.json()
            return data
    except: pass
    try:
        # Fallback: try system whois command
        result = subprocess.run(["whois", domain], capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.split("\n")[:30]
            return {"raw": "\n".join(lines) + "\n[dim]... truncated[/dim]"}
    except: pass
    return {"error": "WHOIS lookup failed"}

def subdomain_enum(domain, timeout=8):
    """Check common subdomains via DNS resolution."""
    domain = re.sub(r'^https?://', '', domain).split('/')[0].split(':')[0]
    common = ["www", "mail", "ftp", "admin", "blog", "shop", "api", "cdn",
              "webmail", "vpn", "remote", "portal", "dev", "test", "stage",
              "beta", "app", "m", "status", "help", "support", "forum",
              "wiki", "docs", "download", "cloud", "auth", "login", "sso",
              "git", "jenkins", "jira", "confluence", "wiki", "kb"]
    found = []
    def check(sub):
        try:
            full = f"{sub}.{domain}"
            ip = socket.gethostbyname(full)
            return (sub, ip)
        except:
            return None
    with ThreadPoolExecutor(max_workers=15) as ex:
        for f in as_completed([ex.submit(check, s) for s in common]):
            r = f.result()
            if r: found.append(r)
    found.sort(key=lambda x: x[0])
    return found

def banner_grab(host, port, timeout=3):
    """Grab a service banner from an open port."""
    host = re.sub(r'^https?://', '', host).split('/')[0].split(':')[0]
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        # Send generic probe for common services
        if port in (80, 8080, 443, 8443):
            s.send(b"GET / HTTP/1.0\r\nHost: " + host.encode() + b"\r\n\r\n")
        elif port in (21,):
            pass  # FTP sends banner on connect
        elif port in (22,):
            pass  # SSH sends banner on connect
        else:
            s.send(b"\r\n")
        try:
            banner = s.recv(1024).decode("utf-8", errors="replace").strip()
        except:
            banner = ""
        s.close()
        # Clean up
        lines = banner.split("\n")
        cleaned = [l.strip() for l in lines if l.strip()][:5]
        return {"port": port, "service": COMMON_PORTS.get(port, "Unknown"), "banner": "\n".join(cleaned) if cleaned else "No banner"}
    except Exception as e:
        return {"port": port, "service": COMMON_PORTS.get(port, "Unknown"), "error": str(e)}

# ---------------------------------------------------------------------------
#  UTILITY
# ---------------------------------------------------------------------------

def check_stop_key():
    if msvcrt.kbhit():
        if ord(msvcrt.getch()) == 27:
            return True
    return False

def check_ollama():
    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=2)
        return r.status_code == 200
    except:
        return False

# ---------------------------------------------------------------------------
#  MAIN CHAT LOOP
# ---------------------------------------------------------------------------

async def chat():
    messages = []

    if not require_auth():
        return

    email = get_stored_email()
    role  = get_user_role(email)

    console.clear()
    console.print("  " + "-" * 50)
    console.print(f"  [accent]Mythos[/accent] [dim]| {email} [/dim]" + ("[warning] Admin[/warning]" if role == "admin" else "") + f" [dim]| model: {MODEL_NAME}[/dim]")
    console.print(f"  [dim]Type /help for commands, /exit to quit[/dim]")
    console.print("  " + "-" * 50)

    while True:
        try:
            # -- Claude Code-style prompt --
            user_input = console.input("  [dim]>[/dim] ").strip()

            if not user_input:
                continue

            # -- Parse command --
            cmd = user_input.lower().split()[0]
            args = user_input[len(cmd):].strip()
            is_cmd = user_input.startswith('/')

            # =========================== SYSTEM COMMANDS ===========================

            if is_cmd:
                if cmd in ('/exit', '/quit'):
                    console.print("\n  [info]Farewell.[/info]")
                    break

                elif cmd == '/clear':
                    messages = []
                    console.clear()
                    console.print("  " + "-" * 50)
                    console.print(f"  [accent]Mythos[/accent] [dim]| {email}[/dim]" + ("[warning] Admin[/warning]" if role == "admin" else "") + f" [dim]| model: {MODEL_NAME}[/dim]")
                    console.print("  " + "-" * 50)
                    continue

                elif cmd == '/help':
                    console.print()
                    tool_header("help", "all commands")
                    console.print("  [dim]System[/dim]")
                    sys_cmds = [
                        ("/auth", "Show auth status"),
                        ("/whoami", "Your account details"),
                        ("/session", "Session info"),
                        ("/status", "System health"),
                        ("/doctor", "Full diagnostics"),
                        ("/config", "Config location"),
                        ("/model", "AI model info"),
                        ("/reauth", "Re-authenticate"),
                        ("/logout", "Clear credentials & exit"),
                        ("/clear", "Clear chat"),
                        ("/exit", "Quit"),
                    ]
                    if role == "admin":
                        sys_cmds.insert(0, ("/admin", "Admin console"))
                    for c, d in sys_cmds:
                        console.print(f"    [cmd]{c:12}[/cmd] [dim]{d}[/dim]")
                    console.print("  [dim]Web / Network[/dim]")
                    web_cmds = [
                        ("/search <q>", "Search web via DuckDuckGo"),
                        ("/fetch <url>", "Fetch web page content"),
                        ("/http <url>", "HTTP headers & security"),
                        ("/scan <host>", "TCP port scan"),
                        ("/dns <domain>", "DNS resolution"),
                        ("/ip [host]", "Resolve IP / show public IP"),
                    ]
                    for c, d in web_cmds:
                        console.print(f"    [cmd]{c:15}[/cmd] [dim]{d}[/dim]")
                    console.print("  [dim]Security Audit[/dim]")
                    sec_cmds = [
                        ("/ssl <host>", "SSL certificate check"),
                        ("/whois <domain>", "WHOIS domain lookup"),
                        ("/subdomains <d>", "Find common subdomains"),
                        ("/banner <h> <p>", "Grab service banner"),
                    ]
                    for c, d in sec_cmds:
                        console.print(f"    [cmd]{c:15}[/cmd] [dim]{d}[/dim]")
                    console.print()
                    continue

                elif cmd == '/auth':
                    tok = get_stored_token()
                    em = get_stored_email()
                    if em and tok and is_valid_token(tok):
                        r = get_user_role(em)
                        tool_header("auth", em)
                        console.print(f"  [dim]|[/dim]  Status: [success]Authenticated[/success]")
                        console.print(f"  [dim]|[/dim]  Role:   [accent]{r.upper()}[/accent]")
                        console.print(f"  [dim]|[/dim]  Token:  [dim]{tok[:20]}...[/dim]")
                    else:
                        tool_error("Not authenticated. Use /reauth")
                    continue

                elif cmd == '/whoami':
                    em = get_stored_email()
                    tok = get_stored_token()
                    if em:
                        r = get_user_role(em)
                        tool_header("whoami")
                        tool_result(f"Email:   {em}")
                        tool_result(f"Role:    {r.upper()}")
                        tool_result(f"Auth:    {'Yes' if tok and is_valid_token(tok) else 'No'}")
                        tool_result(f"Config:  {CONFIG_FILE}")
                    continue

                elif cmd == '/session':
                    em = get_stored_email()
                    tok = get_stored_token()
                    r = get_user_role(em) if em else "?"
                    ollama = check_ollama()
                    tool_header("session")
                    tool_result(f"User:     {em or '?'}")
                    tool_result(f"Role:     {r.upper()}")
                    tool_result(f"Auth:     {'Active' if em and tok and is_valid_token(tok) else 'Inactive'}")
                    tool_result(f"Model:    {MODEL_NAME}")
                    tool_result(f"Ollama:   {'Connected' if ollama else 'Disconnected'}")
                    tool_result(f"Ollama:   {OLLAMA_URL}")
                    tool_result(f"Portal:   {AUTH_URL}")
                    tool_result(f"Config:   {CONFIG_DIR}")
                    tool_result(f"Messages: {len(messages)}")
                    continue

                elif cmd == '/status':
                    em = get_stored_email()
                    tok = get_stored_token()
                    has = em and tok and is_valid_token(tok)
                    ollama = check_ollama()
                    tool_header("status")
                    console.print(f"  [dim]|[/dim]  Auth:   {'[success]Active[/success]' if has else '[error]Inactive[/error]'}")
                    console.print(f"  [dim]|[/dim]  Ollama: {'[success]Running[/success]' if ollama else '[error]Not reachable[/error]'}")
                    console.print(f"  [dim]|[/dim]  Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
                    if not ollama:
                        console.print(f"  [dim]|[/dim]  [warning]! Start Ollama with: ollama serve[/warning]")
                    continue

                elif cmd == '/doctor':
                    ollama = check_ollama()
                    em = get_stored_email()
                    tok = get_stored_token()
                    tok_ok = is_valid_token(tok)
                    tool_header("doctor")
                    console.print(f"  [dim]|[/dim]  Config dir:  {'[success]OK[/success]' if os.path.exists(CONFIG_DIR) else '[error]MISSING[/error]'}")
                    console.print(f"  [dim]|[/dim]  Config file: {'[success]OK[/success]' if os.path.exists(CONFIG_FILE) else '[warning]Not found[/warning]'}")
                    if em and tok and tok_ok:
                        console.print(f"  [dim]|[/dim]  Credentials: [success]Valid[/success]")
                    elif em and tok:
                        console.print(f"  [dim]|[/dim]  Credentials: [error]Bad token[/error]")
                    else:
                        console.print(f"  [dim]|[/dim]  Credentials: [error]Missing (run /reauth)[/error]")
                    console.print(f"  [dim]|[/dim]  Python:      {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
                    console.print(f"  [dim]|[/dim]  Ollama:      {'[success]Connected[/success]' if ollama else '[error]Not reachable[/error]'}")
                    continue

                elif cmd == '/config':
                    tool_header("config")
                    tool_result(f"Config: {CONFIG_FILE}")
                    if os.path.exists(CONFIG_FILE):
                        try:
                            cfg = load_config()
                            safe = {k: (v[:20]+"..." if k=="token" and len(v)>20 else v) for k,v in cfg.items()}
                            tool_result(json.dumps(safe, indent=2))
                        except: tool_error("Could not read config")
                    else:
                        tool_result("[warning]No config file[/warning]")
                    continue

                elif cmd == '/reauth':
                    clear_credentials()
                    if require_auth():
                        console.print("  [success]  Re-authenticated[/success]")
                    continue

                elif cmd == '/logout':
                    clear_credentials()
                    console.print("  [info]Credentials cleared. Run mythos again.[/info]")
                    break

                elif cmd == '/admin':
                    em = get_stored_email()
                    if not is_admin_email(em):
                        tool_error("Access denied. Admin only.")
                        continue
                    tok = get_stored_token() or ""
                    td = tok[:20]+"..." if len(tok)>20 else tok
                    tool_header("admin", "Admin Console")
                    tool_result(f"Admin:  {em}")
                    tool_result(f"Token:  {td}")
                    tool_result(f"Config: {CONFIG_FILE}")
                    tool_result(f"Model:  {MODEL_NAME}")
                    tool_result(f"Ollama: {OLLAMA_URL}")
                    continue

                elif cmd == '/model':
                    tool_header("model")
                    tool_result(f"Model: {MODEL_NAME}")
                    tool_result(f"Engine: Ollama ({OLLAMA_URL})")
                    continue

            # =========================== WEB / NETWORK COMMANDS ===========================

            if is_cmd:
                if cmd == '/search':
                    if not args:
                        tool_error("Usage: /search <query>")
                        continue
                    tool_header("search", args)
                    results = web_search(args)
                    if isinstance(results, dict) and "error" in results:
                        tool_error(f"Search failed: {results['error']}")
                        continue
                    if not results:
                        tool_result("[warning]No results[/warning]")
                        continue
                    for i, r in enumerate(results, 1):
                        console.print(f"  [dim]|[/dim] [bold]{i}.[/bold] {r.get('title','')}")
                        console.print(f"  [dim]|[/dim]  [cyan]{r.get('href','')}[/cyan]")
                        snippet = r.get('body','')[:150]
                        if snippet:
                            console.print(f"  [dim]|[/dim]  [dim]{snippet}[/dim]")
                        if i < len(results):
                            console.print(f"  [dim]|[/dim]")
                    continue

                elif cmd == '/fetch':
                    if not args:
                        tool_error("Usage: /fetch <url>")
                        continue
                    tool_header("fetch", args)
                    result = fetch_page(args)
                    if "error" in result:
                        tool_error(f"Failed: {result['error']}")
                        continue
                    tool_result(f"Status: {result['status']}  |  URL: {result['url']}")
                    tool_result(f"Size: {len(result['content'])} bytes")
                    text = result['content']
                    if text.strip():
                        # Remove HTML tags for cleaner display
                        clean = re.sub(r'<[^>]+>', '', text)
                        clean = re.sub(r'\s+', ' ', clean).strip()
                        if len(clean) > 2000:
                            clean = clean[:2000] + " [dim]...[/dim]"
                        lines = clean.split(". ")
                        display = ".\n  [dim]|[/dim]  ".join(lines[:10])
                        console.print(f"  [dim]|[/dim]  {display}")
                    continue

                elif cmd == '/scan':
                    if not args:
                        tool_error("Usage: /scan <host>")
                        continue
                    tool_header("scan", args)
                    console.print(f"  [dim]|[/dim]  Scanning...")
                    ports = scan_ports(args)
                    if not ports:
                        tool_result("[warning]No open ports found[/warning]")
                        continue
                    for p in ports:
                        svc = COMMON_PORTS.get(p, "?")
                        console.print(f"  [dim]|[/dim]  [bold]{p}[/bold]/tcp  [cyan]{svc}[/cyan]")
                    console.print(f"  [dim]|[/dim]  [dim]{len(ports)} open port(s)[/dim]")
                    continue

                elif cmd == '/dns':
                    if not args:
                        tool_error("Usage: /dns <domain>")
                        continue
                    tool_header("dns", args)
                    records = dns_lookup(args)
                    for rtype, vals in records.items():
                        for v in vals:
                            console.print(f"  [dim]|[/dim]  {rtype:16} {v}")
                    continue

                elif cmd == '/http':
                    if not args:
                        tool_error("Usage: /http <url>")
                        continue
                    tool_header("http", args)
                    result = http_headers(args)
                    if "error" in result:
                        tool_error(f"Failed: {result['error']}")
                        continue
                    for k, v in result.items():
                        val = str(v)
                        if v in ("Yes", "No"):
                            val = f"[success]{v}[/success]" if v == "Yes" else f"[dim]{v}[/dim]"
                        elif k == "Status":
                            color = "success" if 200 <= int(v) < 400 else "error"
                            val = f"[{color}]{v}[/{color}]"
                        console.print(f"  [dim]|[/dim]  {k:20} {val}")
                    continue

                elif cmd == '/ip':
                    if not args:
                        tool_header("ip", "your public IP")
                        try:
                            r = httpx.get("https://api.ipify.org?format=json", timeout=5)
                            data = r.json()
                            tool_result(f"Public IP: [accent]{data.get('ip','?')}[/accent]")
                        except:
                            tool_error("Could not determine public IP")
                        continue
                    tool_header("ip", args)
                    result = resolve_ip(args)
                    if "error" in result:
                        tool_error(f"Failed: {result['error']}")
                        continue
                    for ip in result.get("ips", []):
                        try:
                            t = "IPv6" if isinstance(ipaddress.ip_address(ip), ipaddress.IPv6Address) else "IPv4"
                        except: t = "?"
                        console.print(f"  [dim]|[/dim]  {t:6}  [accent]{ip}[/accent]")
                    continue

            # =========================== SECURITY AUDIT COMMANDS ===========================

            if is_cmd:
                if cmd == '/ssl':
                    if not args:
                        tool_error("Usage: /ssl <host> [port]")
                        continue
                    parts = args.split()
                    host = parts[0]
                    port = int(parts[1]) if len(parts) > 1 else 443
                    tool_header("ssl", f"{host}:{port}")
                    result = ssl_check(host, port)
                    if "error" in result:
                        tool_error(f"Failed: {result['error']}")
                        continue
                    console.print(f"  [dim]|[/dim]  Subject:    {result.get('subject',{}).get('commonName','?')}")
                    console.print(f"  [dim]|[/dim]  Issuer:     {result.get('issuer',{}).get('organizationName','?')}")
                    console.print(f"  [dim]|[/dim]  Valid From: {result.get('not_before','?')}")
                    console.print(f"  [dim]|[/dim]  Valid To:   {result.get('not_after','?')}")
                    console.print(f"  [dim]|[/dim]  Serial:     {result.get('serial','?')[:30]}")
                    if result.get('sans'):
                        console.print(f"  [dim]|[/dim]  SANs:       {', '.join(result['sans'][:5])}" + ("..." if len(result['sans'])>5 else ""))
                    cipher = result.get('cipher')
                    if cipher:
                        console.print(f"  [dim]|[/dim]  Cipher:     {cipher[0]} ({cipher[1]} bits)")
                    now = datetime.datetime.utcnow()
                    try:
                        expiry = datetime.datetime.strptime(result['not_after'], "%b %d %H:%M:%S %Y %Z")
                        days = (expiry - now).days
                        if days < 0:
                            console.print(f"  [dim]|[/dim]  [error]EXPIRED ({abs(days)} days ago)[/error]")
                        elif days < 30:
                            console.print(f"  [dim]|[/dim]  [warning]Expiring in {days} days[/warning]")
                        else:
                            console.print(f"  [dim]|[/dim]  Expires in {days} days")
                    except: pass
                    continue

                elif cmd == '/whois':
                    if not args:
                        tool_error("Usage: /whois <domain>")
                        continue
                    tool_header("whois", args)
                    result = whois_lookup(args)
                    if "error" in result:
                        tool_error(f"WHOIS lookup failed: {result['error']}")
                        # Show what we can from DNS as fallback
                        tool_header("dns", args + " (fallback)")
                        records = dns_lookup(args)
                        for rtype, vals in records.items():
                            for v in vals:
                                console.print(f"  [dim]|[/dim]  {rtype:16} {v}")
                        continue
                    if "raw" in result:
                        for line in result["raw"].split("\n")[:20]:
                            console.print(f"  [dim]|[/dim]  {line}")
                    else:
                        for k, v in list(result.items())[:15]:
                            console.print(f"  [dim]|[/dim]  {str(k):25} {str(v)[:100]}")
                    continue

                elif cmd == '/subdomains':
                    if not args:
                        tool_error("Usage: /subdomains <domain>")
                        continue
                    tool_header("subdomains", args)
                    console.print(f"  [dim]|[/dim]  Probing 30 common subdomains...")
                    found = subdomain_enum(args)
                    if not found:
                        tool_result("[warning]No subdomains found[/warning]")
                        continue
                    for sub, ip in found:
                        console.print(f"  [dim]|[/dim]  [accent]{sub}[/accent].[dim]{args}[/dim]  ->  [cyan]{ip}[/cyan]")
                    console.print(f"  [dim]|[/dim]  [dim]{len(found)} subdomain(s) found[/dim]")
                    continue

                elif cmd == '/banner':
                    parts = args.split()
                    if len(parts) < 2:
                        tool_error("Usage: /banner <host> <port>")
                        continue
                    host = parts[0]
                    try:
                        port = int(parts[1])
                    except:
                        tool_error("Port must be a number")
                        continue
                    tool_header("banner", f"{host}:{port}")
                    result = banner_grab(host, port)
                    if "error" in result:
                        tool_error(f"{result['service']}: {result['error']}")
                        continue
                    tool_result(f"Port {result['port']} ({result['service']})")
                    if result.get('banner'):
                        for line in result['banner'].split("\n"):
                            console.print(f"  [dim]|[/dim]  [dim]{line}[/dim]")
                    continue

            # =========================== NORMAL AI MESSAGE ===========================

            if is_cmd:
                console.print(f"  [error]Unknown: {cmd}. Type /help[/error]\n")
                continue

            # Send to AI model
            messages.append({"role": "user", "content": user_input})
            full_response = ""

            # Tool-call-style header
            tool_header("think")

            payload = {"model": MODEL_NAME, "messages": messages, "stream": True}

            while msvcrt.kbhit(): msvcrt.getch()

            with Live("", console=console, refresh_per_second=15, vertical_overflow="visible") as live:
                live.update(Status("[dim italic]Thinking...[/dim italic]", spinner="dots", console=console))
                try:
                    async with httpx.AsyncClient() as client:
                        async with client.stream("POST", OLLAMA_URL, json=payload, timeout=None) as resp:
                            if resp.status_code != 200:
                                live.update(f"[error]Ollama returned {resp.status_code}[/error]")
                                continue
                            started = False
                            async for line in resp.aiter_lines():
                                if check_stop_key():
                                    live.update(Markdown(full_response + "\n\n[yellow italic](Stopped)[/yellow italic]"))
                                    break
                                if line:
                                    try:
                                        chunk = json.loads(line)
                                        content = chunk.get("message", {}).get("content", "")
                                        if not started and content:
                                            started = True
                                            full_response = content
                                        else:
                                            full_response += content
                                        if full_response:
                                            live.update(Markdown(full_response))
                                    except json.JSONDecodeError:
                                        pass
                            if not full_response and not started:
                                live.update("[dim italic]... no response ...[/dim italic]")
                except Exception as e:
                    live.update(f"[error]Connection Error: {e}[/error]")

            console.print("")
            messages.append({"role": "assistant", "content": full_response})

        except KeyboardInterrupt:
            console.print("\n  [info]Interrupted.[/info]")
            continue
        except EOFError:
            break

if __name__ == "__main__":
    try:
        asyncio.run(chat())
    except KeyboardInterrupt:
        sys.exit(0)
    except EOFError:
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[error]Error: {e}[/error]")
        sys.exit(1)
