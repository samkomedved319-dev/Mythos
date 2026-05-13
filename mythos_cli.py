import json
import httpx
import sys
import os
import re
import time
import socket
import threading
import asyncio
import msvcrt
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.theme import Theme
from rich.status import Status
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich import box

# Configuration
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "mythos"
AUTH_URL = "https://samkomedved319-dev.github.io/Mythos"
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".mythos")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
TOKEN_PATTERN = re.compile(r"^mth_[a-z0-9]{8}-[a-z0-9]{8}-[a-z0-9]{8}-[a-z0-9]{8}$")
ADMIN_EMAIL = "samkomedved319@gmail.com"

# Auth callback globals
_auth_event = threading.Event()
_auth_result = {}

# Setup Rich console
custom_theme = Theme({
    "info": "dim cyan",
    "user": "bold green",
    "assistant": "bold magenta",
    "prompt": "bold white",
    "error": "bold red",
    "command": "bold yellow",
    "success": "bold green",
    "warning": "bold yellow",
})
console = Console(theme=custom_theme)

# =============================================================
#  AUTH CALLBACK HTTP SERVER
# =============================================================

class AuthCallbackHandler(BaseHTTPRequestHandler):
    """Tiny local server that captures the auth callback from the browser."""

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == '/auth':
            email = params.get('email', [None])[0]
            token = params.get('token', [None])[0]
            name  = params.get('name', [None])[0]
            role  = params.get('role', [None])[0]

            if email and token and TOKEN_PATTERN.match(token):
                # Store credentials
                store_credentials(email, token)

                _auth_result['email'] = email
                _auth_result['token'] = token
                _auth_result['name']  = name or email
                _auth_result['role']  = role or 'user'

                # Redirect browser back to website dashboard
                self.send_response(302)
                self.send_header('Location', f'{AUTH_URL}/dashboard.html?auth=success')
                self.end_headers()

                # Signal the waiting CLI thread
                _auth_event.set()
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'<html><body><h1>Missing or invalid parameters</h1></body></html>')
        else:
            # Health check or unknown path
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'''
                <html>
                <body style="background:#0a0a0f;color:#e8e8f0;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;">
                    <div style="text-align:center;">
                        <h1 style="color:#6c5ce7;">Mythos Auth Server</h1>
                        <p>Waiting for browser authentication...</p>
                        <div style="margin-top:20px;width:40px;height:40px;border:3px solid #2a2a3e;border-top-color:#6c5ce7;border-radius:50%;animation:spin 1s linear infinite;display:inline-block;"></div>
                        <style>@keyframes spin{to{transform:rotate(360deg);}}</style>
                    </div>
                </body>
                </html>
            ''')

    def log_message(self, fmt, *args):
        pass  # Suppress HTTP server log output


def find_free_port():
    """Find a free TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def start_auth_server():
    """Start the local auth callback server on a random port.
    Returns (port, server) so the caller can shut it down."""
    port = find_free_port()
    server = HTTPServer(('127.0.0.1', port), AuthCallbackHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return port, server


# =============================================================
#  CONFIG / CREDENTIALS
# =============================================================

def load_config():
    """Load the local config file."""
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_config(config):
    """Save the local config file."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_stored_token():
    config = load_config()
    return config.get("token", None)


def get_stored_email():
    config = load_config()
    return config.get("email", None)


def store_credentials(email, token):
    config = load_config()
    config["email"] = email
    config["token"] = token
    save_config(config)


def clear_credentials():
    config = load_config()
    config.pop("email", None)
    config.pop("token", None)
    save_config(config)


def is_valid_token(token):
    return bool(token and TOKEN_PATTERN.match(token))


def is_admin_email(email):
    return email and email.lower() == ADMIN_EMAIL


def get_user_role(email):
    return "admin" if is_admin_email(email) else "user"


# =============================================================
#  AUTH FLOW
# =============================================================

def manual_auth():
    """Fallback: prompt the user to paste their email + token manually."""
    console.print("\n[info]--- Manual Credential Entry ---[/info]")
    console.print(f"Visit [bold cyan]{AUTH_URL}[/bold cyan] in your browser,")
    console.print("log in, and copy your credentials from the Dashboard.\n")

    while True:
        email_input = Prompt.ask("[yellow]Enter your Mythos email[/yellow]").strip().lower()

        if email_input.lower() in ("exit", "quit", "q"):
            console.print("\n[info]Authentication skipped. Exiting.[/info]")
            return False

        if not email_input or "@" not in email_input:
            console.print("[error]Please enter a valid email address.[/error]\n")
            continue

        token_input = Prompt.ask("[yellow]Enter your Mythos API token[/yellow]").strip()

        if token_input.lower() in ("exit", "quit", "q"):
            console.print("\n[info]Authentication skipped. Exiting.[/info]")
            return False

        if not token_input:
            console.print("[error]Token cannot be empty.[/error]\n")
            continue

        if not is_valid_token(token_input):
            console.print(
                "[error]Invalid token format. Tokens look like:[/error]\n"
                "  [bold]mth_xxxxxxxx-xxxxxxxx-xxxxxxxx-xxxxxxxx[/bold]\n"
                "[error]Check your dashboard and try again.[/error]\n"
            )
            continue

        role = get_user_role(email_input)
        store_credentials(email_input, token_input)
        role_icon = "👑 " if role == "admin" else ""
        console.print(f"\n[success]{role_icon}✓ Authentication successful! Credentials saved.[/success]")
        if role == "admin":
            console.print("[warning]You are logged in as Mythos Admin / Owner.[/warning]")
        return True


def require_auth():
    """Main auth gate. Checks stored credentials first. If missing:
    1. Start a local HTTP server on a random port
    2. Print a clickable URL (with the port)
    3. Wait up to 120s for browser callback
    4. Fall back to manual entry on timeout or 'Q' press
    """
    email = get_stored_email()
    token = get_stored_token()

    if email and token and is_valid_token(token):
        return True

    # --- Attempt seamless browser auth first ---
    port, server = start_auth_server()
    _auth_event.clear()
    _auth_result.clear()

    console.clear()
    console.print(Panel(
        "[bold]Welcome to Mythos — Sovereign Architect[/bold]\n\n"
        "[yellow]🔐 Authentication Required[/yellow]\n\n"
        "Click the link below to log in or sign up — "
        "the CLI will connect automatically:\n\n"
        f"[bold cyan underline]{AUTH_URL}/?cli_port={port}[/bold cyan underline]\n\n"
        "Or open your browser and visit:\n"
        f"  [dim]{AUTH_URL}/?cli_port={port}[/dim]\n\n"
        "[dim]⏳ Waiting for browser authentication...[/dim]\n"
        "[dim]• The CLI will wait up to 120 seconds[/dim]\n"
        "[dim]• Press [bold]Q[/bold] to switch to manual entry[/dim]\n"
        "[dim]• Press [bold]X[/bold] to exit[/dim]",
        title="Mythos",
        border_style="cyan"
    ))

    # Wait for callback with periodic key-check
    timeout = 120
    start_time = time.time()
    timed_out = False
    manual = False

    while not _auth_event.is_set():
        elapsed = time.time() - start_time
        remaining = timeout - elapsed

        if remaining <= 0:
            timed_out = True
            break

        # Check for key press every 0.3 seconds
        if _auth_event.wait(0.3):
            break

        if msvcrt.kbhit():
            key = msvcrt.getch().lower()
            if key == b'q':
                manual = True
                break
            elif key == b'x':
                server.shutdown()
                console.print("\n[info]Exiting.[/info]")
                return False

    server.shutdown()

    if _auth_event.is_set():
        role = _auth_result.get('role', 'user')
        role_icon = "👑 " if role == "admin" else ""
        console.print(f"\n[success]{role_icon}✓ Authenticated as {_auth_result.get('email')}[/success]")
        return True

    if timed_out:
        console.print("\n[warning]⏰ Timed out waiting for browser authentication.[/warning]")

    # Fallback to manual entry
    return manual_auth()


# =============================================================
#  CHAT LOOP
# =============================================================

def check_stop_key():
    """Check if ESC (27) was pressed."""
    if msvcrt.kbhit():
        key = msvcrt.getch()
        if ord(key) == 27:
            return True
    return False


async def chat():
    messages = []

    # ---------- Auth gate ----------
    if not require_auth():
        return

    email = get_stored_email()
    role = get_user_role(email)
    role_tag = " 👑 Admin" if role == "admin" else ""
    token = get_stored_token()

    console.print(f"\n[info]Mythos Sovereign Architect | model: {MODEL_NAME} | {email}{role_tag}[/info]")
    console.print("[info]Type [command]/help[/command] for commands, [command]/exit[/command] to quit.[/info]\n")

    while True:
        try:
            user_input = console.input("[user]You[/user] [prompt]›[/prompt] ").strip()

            if not user_input:
                continue

            # ---------- Slash commands ----------
            if user_input.startswith('/'):
                cmd = user_input.lower().split()[0]

                # --- /exit ---
                if cmd in ['/exit', '/quit']:
                    console.print("\n[info]Farewell.[/info]")
                    break

                # --- /clear ---
                elif cmd == '/clear':
                    messages = []
                    console.clear()
                    console.print("[info]Memory cleared. Mythos is ready again.[/info]\n")
                    continue

                # --- /help ---
                elif cmd == '/help':
                    help_lines = [
                        ("/clear", "Clear chat history"),
                        ("/exit", "Exit the program"),
                        ("/help", "Show this help"),
                        ("/model", "Show AI model info"),
                        ("/auth", "Show authentication status"),
                        ("/whoami", "Show your account details"),
                        ("/session", "Show full session information"),
                        ("/status", "Show system & session status"),
                        ("/doctor", "Run system health checks"),
                        ("/config", "Show config file location"),
                        ("/reauth", "Re-authenticate with new credentials"),
                        ("/logout", "Clear stored credentials and exit"),
                    ]
                    if role == "admin":
                        help_lines.append(("/admin", "Admin panel (owner only)"))

                    table = Table(title="Mythos Commands", border_style="yellow", box=box.ROUNDED)
                    table.add_column("Command", style="bold yellow", no_wrap=True)
                    table.add_column("Description", style="dim")
                    for cmd_name, desc in help_lines:
                        table.add_row(f"/{cmd_name}" if not cmd_name.startswith("/") else cmd_name, desc)

                    console.print(table)
                    console.print("\n[dim]Tip: Press [bold]ESC[/bold] while Mythos is typing to stop a response.[/dim]")
                    continue

                # --- /auth ---
                elif cmd == '/auth':
                    tok = get_stored_token()
                    em = get_stored_email()
                    if em and tok and is_valid_token(tok):
                        r = get_user_role(em)
                        icon = "👑 " if r == "admin" else ""
                        console.print(f"[success]{icon}✓ Authenticated[/success]")
                        console.print(f"  Email: [bold]{em}[/bold]")
                        console.print(f"  Token: [dim]{tok[:20]}...[/dim]")
                        console.print(f"  Role:  [bold]{r}[/bold]")
                    else:
                        console.print("[warning]No valid credentials found.[/warning]")
                        console.print("[info]Type [command]/reauth[/command] to authenticate.[/info]")
                    continue

                # --- /whoami ---
                elif cmd == '/whoami':
                    em = get_stored_email()
                    tok = get_stored_token()
                    if em:
                        r = get_user_role(em)
                        icon = "👑 " if r == "admin" else ""
                        table = Table(title=f"{icon}Account Details", border_style="cyan", box=box.ROUNDED)
                        table.add_column("Field", style="bold cyan")
                        table.add_column("Value")
                        table.add_row("Email", em)
                        table.add_row("Role", r.upper())
                        table.add_row("Authenticated", "✅ Yes" if tok and is_valid_token(tok) else "❌ No")
                        table.add_row("Config File", CONFIG_FILE)
                        console.print(table)
                    else:
                        console.print("[warning]No account configured. Type /reauth to log in.[/warning]")
                    continue

                # --- /session ---
                elif cmd == '/session':
                    em = get_stored_email()
                    tok = get_stored_token()
                    r = get_user_role(em) if em else "—"
                    icon = "👑 " if r == "admin" else ""
                    table = Table(title=f"{icon}Session Info", border_style="cyan", box=box.ROUNDED)
                    table.add_column("Property", style="bold cyan")
                    table.add_column("Value")
                    table.add_row("User", em or "—")
                    table.add_row("Role", r.upper())
                    table.add_row("Auth", "✅ Active" if em and tok and is_valid_token(tok) else "❌ Inactive")
                    table.add_row("Model", MODEL_NAME)
                    table.add_row("Ollama", OLLAMA_URL)
                    table.add_row("Portal", AUTH_URL)
                    table.add_row("Config Dir", CONFIG_DIR)
                    table.add_row("Session Messages", str(len(messages)))
                    console.print(table)
                    continue

                # --- /status ---
                elif cmd == '/status':
                    em = get_stored_email()
                    tok = get_stored_token()
                    has_auth = em and tok and is_valid_token(tok)
                    config_exists = os.path.exists(CONFIG_FILE)
                    ollama_alive = False
                    try:
                        r = httpx.get("http://localhost:11434/api/tags", timeout=2)
                        ollama_alive = r.status_code == 200
                    except Exception:
                        ollama_alive = False

                    table = Table(title="Mythos Status", border_style="cyan", box=box.ROUNDED)
                    table.add_column("Check", style="bold cyan")
                    table.add_column("Status")
                    table.add_row("Auth", "✅ Authenticated" if has_auth else "❌ Not authenticated")
                    table.add_row("Config", f"✅ {CONFIG_FILE}" if config_exists else "⚠️  No config file")
                    table.add_row("Ollama", "✅ Connected" if ollama_alive else "❌ Not reachable")
                    if em:
                        table.add_row("User", em)
                        table.add_row("Role", get_user_role(em).upper())
                    console.print(table)
                    if not ollama_alive:
                        console.print("[warning]⚠️  Ollama is not running. Start it with 'ollama serve'.[/warning]")
                    continue

                # --- /doctor ---
                elif cmd == '/doctor':
                    console.print("[bold]🔍 Mythos Health Check[/bold]\n")

                    checks = []

                    # 1. Config directory
                    config_dir_ok = os.path.exists(CONFIG_DIR)
                    checks.append(("Config directory", "✅" if config_dir_ok else "❌", CONFIG_DIR))

                    # 2. Config file
                    config_file_ok = os.path.exists(CONFIG_FILE)
                    checks.append(("Config file", "✅" if config_file_ok else "⚠️  Not found", CONFIG_FILE))

                    # 3. Credentials
                    em = get_stored_email()
                    tok = get_stored_token()
                    tok_valid = is_valid_token(tok)
                    if em and tok and tok_valid:
                        checks.append(("Credentials", "✅ Valid", f"{em} / {tok[:20]}..."))
                    elif em and tok:
                        checks.append(("Credentials", "⚠️  Invalid token", "Token format is wrong"))
                    else:
                        checks.append(("Credentials", "❌ Missing", "Run /reauth"))

                    # 4. Python version
                    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
                    checks.append(("Python", f"✅ {py_ver}", ""))

                    # 5. Ollama connectivity
                    try:
                        r = httpx.get("http://localhost:11434/api/tags", timeout=2)
                        if r.status_code == 200:
                            checks.append(("Ollama", "✅ Connected", "http://localhost:11434"))
                        else:
                            checks.append(("Ollama", f"⚠️  Status {r.status_code}", ""))
                    except Exception as e:
                        checks.append(("Ollama", "❌ Not reachable", str(e)))

                    table = Table(border_style="cyan", box=box.ROUNDED)
                    table.add_column("Check", style="bold cyan")
                    table.add_column("Result")
                    table.add_column("Detail", style="dim")
                    for name, status, detail in checks:
                        table.add_row(name, status, detail)
                    console.print(table)

                    all_pass = all("✅" in c[1] for c in checks)
                    if all_pass:
                        console.print("\n[success]✅ All systems operational.[/success]")
                    else:
                        console.print("\n[warning]⚠️  Some checks failed. See details above.[/warning]")
                    continue

                # --- /config ---
                elif cmd == '/config':
                    console.print(f"[info]Config file location:[/info] [bold]{CONFIG_FILE}[/bold]")
                    if os.path.exists(CONFIG_FILE):
                        try:
                            cfg = load_config()
                            display_cfg = {k: (v[:20] + "..." if k == "token" and len(v) > 20 else v) for k, v in cfg.items()}
                            console.print(Panel(
                                json.dumps(display_cfg, indent=2),
                                title="Config Contents",
                                border_style="cyan"
                            ))
                        except Exception:
                            console.print("[error]Could not read config file.[/error]")
                    else:
                        console.print("[warning]No config file exists yet.[/warning]")
                    continue

                # --- /reauth ---
                elif cmd == '/reauth':
                    clear_credentials()
                    if require_auth():
                        console.print("[success]✓ Re-authentication successful.[/success]")
                    continue

                # --- /logout ---
                elif cmd == '/logout':
                    clear_credentials()
                    console.print("[info]Credentials cleared. You are logged out.[/info]")
                    console.print("[info]Run [command]mythos[/command] again to re-authenticate.[/info]")
                    break

                # --- /admin ---
                elif cmd == '/admin':
                    em = get_stored_email()
                    if not is_admin_email(em):
                        console.print("[error]Access denied. This command is for Mythos Admin only.[/error]")
                        continue

                    cfg = load_config()
                    tok = cfg.get("token", "—")
                    tok_display = tok[:20] + "..." if len(tok) > 20 else tok
                    console.print(Panel(
                        f"[bold yellow]👑 Mythos Admin Console[/bold yellow]\n\n"
                        f"  Admin:       {em}\n"
                        f"  Token:       {tok_display}\n"
                        f"  Config:      {CONFIG_FILE}\n"
                        f"  Model:       {MODEL_NAME}\n"
                        f"  Ollama URL:  {OLLAMA_URL}\n"
                        f"  Web Portal:  {AUTH_URL}\n\n"
                        "[dim]As the Mythos owner, you have full control over this instance. [/dim]",
                        title="Admin Console",
                        border_style="yellow"
                    ))
                    continue

                # --- /model ---
                elif cmd == '/model':
                    console.print(f"[info]Model: [bold]{MODEL_NAME}[/bold] via Ollama at {OLLAMA_URL}[/info]")
                    continue

                else:
                    console.print(f"[error]Unknown command: {cmd}. Type /help for a list.[/error]\n")
                    continue

            # ========== NORMAL MESSAGE ==========
            messages.append({"role": "user", "content": user_input})

            full_response = ""
            console.print("\n[assistant]Mythos[/assistant]")

            payload = {
                "model": MODEL_NAME,
                "messages": messages,
                "stream": True,
            }

            while msvcrt.kbhit():
                msvcrt.getch()

            with Live("", console=console, refresh_per_second=15, vertical_overflow="visible") as live:
                live.update(Status("[dim italic]Thinking...[/dim italic]", spinner="dots", console=console))

                try:
                    async with httpx.AsyncClient() as client:
                        async with client.stream("POST", OLLAMA_URL, json=payload, timeout=None) as response:
                            if response.status_code != 200:
                                live.update(f"[error]Error: Ollama returned status {response.status_code}[/error]")
                                continue

                            started = False
                            async for line in response.aiter_lines():
                                if check_stop_key():
                                    live.update(Markdown(full_response + "\n\n[yellow italic](Response stopped by user)[/yellow italic]"))
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
            console.print("\n[info]Interrupted. Type /exit to close.[/info]")
            continue
        except EOFError:
            break


if __name__ == "__main__":
    try:
        asyncio.run(chat())
    except KeyboardInterrupt:
        pass
