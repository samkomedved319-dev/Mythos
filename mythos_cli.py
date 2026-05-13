import json
import httpx
import sys
import os
import re
import asyncio
import msvcrt
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

# --------------------------------------------------------------------------------------------
#  CONFIGURATION
# --------------------------------------------------------------------------------------------

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "mythos"
AUTH_URL   = "https://samkomedved319-dev.github.io/Mythos"
CONFIG_DIR  = os.path.join(os.path.expanduser("~"), ".mythos")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
TOKEN_PATTERN = re.compile(r"^mth_[a-z0-9]{8}-[a-z0-9]{8}-[a-z0-9]{8}-[a-z0-9]{8}$")
ADMIN_EMAIL = "samkomedved319@gmail.com"

# --------------------------------------------------------------------------------------------
#  RICH THEME
# --------------------------------------------------------------------------------------------

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

# --------------------------------------------------------------------------------------------
#  CONFIG / CREDENTIALS
# --------------------------------------------------------------------------------------------

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

# --------------------------------------------------------------------------------------------
#  AUTH  SIMPLE, RELIABLE, MANUAL
# --------------------------------------------------------------------------------------------

def require_auth():
    """Gate: check stored credentials; if missing, prompt user to
    visit the website, sign up, and paste email + token."""

    email = get_stored_email()
    token = get_stored_token()

    if email and token and is_valid_token(token):
        return True  # already authenticated

    # ---- Auth screen ----
    console.clear()
    console.print()
    console.print(Panel(
        "[bold]Welcome to Mythos  Sovereign Architect[/bold]\n\n"
        "This CLI requires authentication.\n\n"
        f"  Open this link in your browser:\n"
        f"    [bold cyan underline]{AUTH_URL}[/bold cyan underline]\n\n"
        "  Sign up or log in\n"
        "  Copy your [bold]email[/bold] and [bold]API token[/bold] from the Dashboard\n"
        "  Paste them below\n\n"
        "It takes 30 seconds.",
        title=" Authentication Required",
        border_style="yellow",
    ))
    console.print()

    while True:
        email_input = Prompt.ask("[yellow]Your email[/yellow]").strip().lower()

        if email_input.lower() in ("exit", "quit", "q", ""):
            console.print("\n[info]Authentication skipped. Exiting.[/info]")
            return False

        if "@" not in email_input or "." not in email_input:
            console.print("[error]Please enter a valid email address.[/error]\n")
            continue

        # email looks OK  ask for token
        break

    while True:
        token_input = Prompt.ask("[yellow]Your API token[/yellow]").strip()

        if token_input.lower() in ("exit", "quit", "q"):
            console.print("\n[info]Authentication skipped. Exiting.[/info]")
            return False

        if not token_input:
            console.print("[error]Token cannot be empty.[/error]\n")
            continue

        if not is_valid_token(token_input):
            console.print(
                "[error]Wrong format. Tokens look like:[/error]\n"
                f"  [bold]mth_xxxxxxxx-xxxxxxxx-xxxxxxxx-xxxxxxxx[/bold]\n"
                f"[info]Get yours at {AUTH_URL}/dashboard.html[/info]\n"
            )
            continue

        # Valid token
        break

    # Store & confirm
    role = get_user_role(email_input)
    store_credentials(email_input, token_input)

    console.print()
    if role == "admin":
        console.print("[success]  Authenticated as Mythos Admin / Owner[/success]")
    else:
        console.print("[success] Authentication successful![/success]")
    console.print("[info]Type [command]/help[/command] to see available commands.[/info]\n")
    return True


# --------------------------------------------------------------------------------------------
#  CHAT LOOP
# --------------------------------------------------------------------------------------------

def check_stop_key():
    if msvcrt.kbhit():
        key = msvcrt.getch()
        if ord(key) == 27:
            return True
    return False


async def chat():
    messages = []

    # ---- Auth gate ----
    if not require_auth():
        return

    email = get_stored_email()
    role  = get_user_role(email)
    role_tag = "  Admin" if role == "admin" else ""

    console.print(f"[info]Mythos Sovereign Architect | model: {MODEL_NAME} | {email}{role_tag}[/info]")
    console.print("[info]Type [command]/help[/command] for commands, [command]/exit[/command] to quit.[/info]\n")

    while True:
        try:
            user_input = console.input("[user]You[/user] [prompt][/prompt] ").strip()

            if not user_input:
                continue

            # ---- Slash commands ----
            if user_input.startswith('/'):
                cmd = user_input.lower().split()[0]

                # /exit /quit
                if cmd in ('/exit', '/quit'):
                    console.print("\n[info]Farewell.[/info]")
                    break

                # /clear
                elif cmd == '/clear':
                    messages = []
                    console.clear()
                    console.print("[info]Memory cleared. Mythos is ready again.[/info]\n")
                    continue

                # /help
                elif cmd == '/help':
                    cmds = [
                        ("/clear",   "Clear chat history"),
                        ("/exit",    "Exit the program"),
                        ("/help",    "Show this help"),
                        ("/model",   "Show AI model info"),
                        ("/auth",    "Show authentication status"),
                        ("/whoami",  "Show your account details"),
                        ("/session", "Show full session information"),
                        ("/status",  "Show system health"),
                        ("/doctor",  "Run diagnostic checks"),
                        ("/config",  "Show config file info"),
                        ("/reauth",  "Re-authenticate with new credentials"),
                        ("/logout",  "Clear stored credentials and exit"),
                    ]
                    if role == "admin":
                        cmds.append(("/admin", "Admin console (owner only)"))

                    table = Table(title="Commands", border_style="yellow", box=box.ROUNDED, title_justify="left")
                    table.add_column("Command", style="bold yellow", no_wrap=True)
                    table.add_column("Description", style="dim")
                    for c, d in cmds:
                        table.add_row(c, d)
                    console.print(table)
                    console.print("\n[dim]Tip: Press [bold]ESC[/bold] to stop a response mid-stream.[/dim]")
                    continue

                # /auth
                elif cmd == '/auth':
                    tok = get_stored_token()
                    em = get_stored_email()
                    if em and tok and is_valid_token(tok):
                        r = get_user_role(em)
                        icon = " " if r == "admin" else ""
                        console.print(f"[success]{icon} Authenticated[/success]")
                        console.print(f"  Email: [bold]{em}[/bold]")
                        console.print(f"  Token: [dim]{tok[:20]}...[/dim]")
                        console.print(f"  Role:  [bold]{r}[/bold]")
                    else:
                        console.print("[warning]Not authenticated.[/warning]")
                        console.print("[info]Type [command]/reauth[/command] to log in.[/info]")
                    continue

                # /whoami
                elif cmd == '/whoami':
                    em = get_stored_email()
                    tok = get_stored_token()
                    if em:
                        r = get_user_role(em)
                        icon = " " if r == "admin" else ""
                        t = Table(title=f"{icon}Account Details", border_style="cyan", box=box.ROUNDED)
                        t.add_column("Field", style="bold cyan")
                        t.add_column("Value")
                        t.add_row("Email", em)
                        t.add_row("Role", r.upper())
                        t.add_row("Authenticated", " Yes" if tok and is_valid_token(tok) else " No")
                        t.add_row("Config", CONFIG_FILE)
                        console.print(t)
                    else:
                        console.print("[warning]No account. Type /reauth to log in.[/warning]")
                    continue

                # /session
                elif cmd == '/session':
                    em = get_stored_email()
                    tok = get_stored_token()
                    r = get_user_role(em) if em else ""
                    icon = " " if r == "admin" else ""
                    t = Table(title=f"{icon}Session", border_style="cyan", box=box.ROUNDED)
                    t.add_column("Property", style="bold cyan")
                    t.add_column("Value")
                    t.add_row("User", em or "")
                    t.add_row("Role", r.upper())
                    t.add_row("Auth", " Active" if em and tok and is_valid_token(tok) else " Inactive")
                    t.add_row("Model", MODEL_NAME)
                    t.add_row("Ollama", OLLAMA_URL)
                    t.add_row("Portal", AUTH_URL)
                    t.add_row("Config", CONFIG_DIR)
                    t.add_row("Messages", str(len(messages)))
                    console.print(t)
                    continue

                # /status
                elif cmd == '/status':
                    em = get_stored_email()
                    tok = get_stored_token()
                    has_auth = em and tok and is_valid_token(tok)
                    cfg_ok = os.path.exists(CONFIG_FILE)
                    ollama_ok = False
                    try:
                        r = httpx.get("http://localhost:11434/api/tags", timeout=2)
                        ollama_ok = r.status_code == 200
                    except Exception:
                        pass

                    t = Table(title="System Status", border_style="cyan", box=box.ROUNDED)
                    t.add_column("Check", style="bold cyan")
                    t.add_column("Status")
                    t.add_row("Auth", " Authenticated" if has_auth else " Not authenticated")
                    t.add_row("Config", f" {CONFIG_FILE}" if cfg_ok else "  Missing")
                    t.add_row("Ollama", " Connected" if ollama_ok else " Not reachable")
                    if em:
                        t.add_row("User", em)
                        t.add_row("Role", get_user_role(em).upper())
                    console.print(t)
                    if not ollama_ok:
                        console.print("\n[warning]  Ollama is not running. Start it with: [bold]ollama serve[/bold][/warning]")
                    continue

                # /doctor
                elif cmd == '/doctor':
                    console.print("[bold] Mythos Health Check[/bold]\n")
                    checks = []

                    # config dir
                    checks.append(("Config dir", "" if os.path.exists(CONFIG_DIR) else "", CONFIG_DIR))
                    # config file
                    checks.append(("Config file", "" if os.path.exists(CONFIG_FILE) else "  Not found", CONFIG_FILE))
                    # credentials
                    em = get_stored_email()
                    tok = get_stored_token()
                    tok_ok = is_valid_token(tok)
                    if em and tok and tok_ok:
                        checks.append(("Credentials", " Valid", f"{em} / {tok[:20]}..."))
                    elif em and tok:
                        checks.append(("Credentials", "  Bad token", "Token format is wrong"))
                    else:
                        checks.append(("Credentials", " Missing", "Run /reauth"))
                    # python
                    py = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
                    checks.append(("Python", f" {py}", ""))
                    # ollama
                    try:
                        r = httpx.get("http://localhost:11434/api/tags", timeout=2)
                        if r.status_code == 200:
                            checks.append(("Ollama", " Connected", "localhost:11434"))
                        else:
                            checks.append(("Ollama", f"  Status {r.status_code}", ""))
                    except Exception as e:
                        checks.append(("Ollama", " Not reachable", str(e).split("(")[0]))

                    t = Table(border_style="cyan", box=box.ROUNDED)
                    t.add_column("Check", style="bold cyan")
                    t.add_column("Result")
                    t.add_column("Detail", style="dim")
                    for n, s, d in checks:
                        t.add_row(n, s, d)
                    console.print(t)

                    all_good = all("" in c[1] for c in checks)
                    console.print("\n[success] All systems operational.[/success]" if all_good else "\n[warning]  Some issues found.[/warning]")
                    continue

                # /config
                elif cmd == '/config':
                    console.print(f"[info]Config:[/info] [bold]{CONFIG_FILE}[/bold]")
                    if os.path.exists(CONFIG_FILE):
                        try:
                            cfg = load_config()
                            safe = {k: (v[:20] + "..." if k == "token" and len(v) > 20 else v) for k, v in cfg.items()}
                            console.print(Panel(json.dumps(safe, indent=2), title="Contents", border_style="cyan"))
                        except Exception:
                            console.print("[error]Could not read config.[/error]")
                    else:
                        console.print("[warning]No config file yet.[/warning]")
                    continue

                # /reauth
                elif cmd == '/reauth':
                    clear_credentials()
                    if require_auth():
                        console.print("[success] Re-authentication successful.[/success]")
                    continue

                # /logout
                elif cmd == '/logout':
                    clear_credentials()
                    console.print("[info]Credentials cleared. You are logged out.[/info]")
                    console.print("[info]Run [command]mythos[/command] again to re-authenticate.[/info]")
                    break

                # /admin
                elif cmd == '/admin':
                    em = get_stored_email()
                    if not is_admin_email(em):
                        console.print("[error]Access denied. Admin only.[/error]")
                        continue
                    tok = get_stored_token() or ""
                    td = tok[:20] + "..." if len(tok) > 20 else tok
                    console.print(Panel(
                        f"[bold yellow] Mythos Admin Console[/bold yellow]\n\n"
                        f"  Admin:      {em}\n"
                        f"  Token:      {td}\n"
                        f"  Config:     {CONFIG_FILE}\n"
                        f"  Model:      {MODEL_NAME}\n"
                        f"  Ollama:     {OLLAMA_URL}\n"
                        f"  Portal:     {AUTH_URL}\n",
                        title="Admin", border_style="yellow"
                    ))
                    continue

                # /model
                elif cmd == '/model':
                    console.print(f"[info]Model: [bold]{MODEL_NAME}[/bold] via Ollama at {OLLAMA_URL}[/info]")
                    continue

                # unknown
                else:
                    console.print(f"[error]Unknown command: {cmd}. Type /help for a list.[/error]\n")
                    continue

            # ====== NORMAL MESSAGE ======
            messages.append({"role": "user", "content": user_input})
            full_response = ""
            console.print("\n[assistant]Mythos[/assistant]")

            payload = {"model": MODEL_NAME, "messages": messages, "stream": True}

            while msvcrt.kbhit():
                msvcrt.getch()

            with Live("", console=console, refresh_per_second=15, vertical_overflow="visible") as live:
                live.update(Status("[dim italic]Thinking...[/dim italic]", spinner="dots", console=console))
                try:
                    async with httpx.AsyncClient() as client:
                        async with client.stream("POST", OLLAMA_URL, json=payload, timeout=None) as resp:
                            if resp.status_code != 200:
                                live.update(f"[error]Ollama returned status {resp.status_code}[/error]")
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
            console.print("\n[info]Interrupted. Type /exit to quit.[/info]")
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
