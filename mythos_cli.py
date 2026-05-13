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

# Configuration
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "mythos"
AUTH_URL = "https://samkomedved319-dev.github.io/Mythos"
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".mythos")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
TOKEN_PATTERN = re.compile(r"^mth_[a-z0-9]{8}-[a-z0-9]{8}-[a-z0-9]{8}-[a-z0-9]{8}$")
ADMIN_EMAIL = "samkomedved319@gmail.com"

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

# ---------- Authentication ----------

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
    """Retrieve the stored auth token."""
    config = load_config()
    return config.get("token", None)

def get_stored_email():
    """Retrieve the stored email."""
    config = load_config()
    return config.get("email", None)

def store_credentials(email, token):
    """Persist both email and token."""
    config = load_config()
    config["email"] = email
    config["token"] = token
    save_config(config)

def clear_credentials():
    """Remove stored credentials."""
    config = load_config()
    config.pop("email", None)
    config.pop("token", None)
    save_config(config)

def is_valid_token(token):
    """Check if the token matches the expected format."""
    return bool(TOKEN_PATTERN.match(token))

def is_admin_email(email):
    """Check if the given email is the Mythos admin."""
    return email and email.lower() == ADMIN_EMAIL

def get_user_role(email):
    """Return 'admin' or 'user' based on email."""
    return "admin" if is_admin_email(email) else "user"

def require_auth():
    """Ensure the user is authenticated before proceeding.

    Returns True if authenticated, False if the user chose to exit.
    """
    email = get_stored_email()
    token = get_stored_token()

    if email and token and is_valid_token(token):
        return True

    # No valid credentials — guide the user through authentication.
    console.clear()
    console.print(Panel(
        "[bold]Welcome to Mythos — Sovereign Architect[/bold]\n\n"
        "This CLI requires authentication. You need your email and API token\n"
        "from the Mythos web portal.\n",
        title="🔐 Authentication Required",
        border_style="yellow"
    ))

    console.print("\n[info]Steps to get your credentials:[/info]")
    console.print(f"  1. Visit [bold cyan]{AUTH_URL}[/bold cyan] in your browser")
    console.print("  2. Sign up for a new account")
    console.print("  3. Log in and go to your Dashboard")
    console.print("  4. Copy your email and API token")
    console.print("  5. Paste them below\n")

    while True:
        email_input = Prompt.ask("[yellow]Enter your Mythos email[/yellow]").strip().lower()

        if email_input.lower() in ("exit", "quit", "q"):
            console.print("\n[info]Authentication skipped. Exiting.[/info]")
            return False

        if not email_input or "@" not in email_input:
            console.print("[error]Please enter a valid email address.[/error]\n")
            continue

        # Email looks reasonable — now ask for token
        token_input = Prompt.ask("[yellow]Enter your Mythos API token[/yellow]").strip()

        if token_input.lower() in ("exit", "quit", "q"):
            console.print("\n[info]Authentication skipped. Exiting.[/info]")
            return False

        if not token_input:
            console.print("[error]Token cannot be empty. Type 'exit' to quit.[/error]\n")
            continue

        if not is_valid_token(token_input):
            console.print(
                "[error]Invalid token format. Tokens look like:[/error]\n"
                "  [bold]mth_xxxxxxxx-xxxxxxxx-xxxxxxxx-xxxxxxxx[/bold]\n"
                "[error]Please check your dashboard and try again.[/error]\n"
            )
            continue

        # Both email and token look valid — store them
        role = get_user_role(email_input)
        store_credentials(email_input, token_input)
        role_icon = "👑 " if role == "admin" else ""
        console.print(f"\n[success]{role_icon}✓ Authentication successful! Credentials saved.[/success]")
        if role == "admin":
            console.print("[warning]You are logged in as Mythos Admin / Owner.[/warning]")
        console.print("[info]Type [command]/help[/command] to see available commands.[/info]")
        return True

def check_stop_key():
    """Check if ESC (27) was pressed."""
    if msvcrt.kbhit():
        key = msvcrt.getch()
        if ord(key) == 27:
            return True
    return False

async def chat():
    messages = []

    # Require authentication before entering the chat loop
    if not require_auth():
        return

    email = get_stored_email()
    role = get_user_role(email)
    role_tag = " 👑 Admin" if role == "admin" else ""

    console.print(f"\n[info]Mythos Sovereign Architect | model: {MODEL_NAME} | {email}{role_tag}[/info]")
    console.print("[info]Type [command]/help[/command] for commands, [command]/exit[/command] to quit.[/info]\n")

    while True:
        try:
            # Clean prompt
            user_input = console.input("[user]You[/user] [prompt]›[/prompt] ").strip()

            if not user_input:
                continue

            # Handle Slash Commands
            if user_input.startswith('/'):
                cmd = user_input.lower().split()[0]

                # --- Exit ---
                if cmd in ['/exit', '/quit']:
                    console.print("\n[info]Farewell.[/info]")
                    break

                # --- Clear ---
                elif cmd == '/clear':
                    messages = []
                    console.clear()
                    console.print(f"[info]Memory cleared. Mythos is ready again.[/info]\n")
                    continue

                # --- Help ---
                elif cmd == '/help':
                    console.print(Panel(
                        "[command]/clear[/command]   - Clear chat history\n"
                        "[command]/exit[/command]    - Exit the program\n"
                        "[command]/help[/command]    - Show this help\n"
                        "[command]/model[/command]   - Show model info\n"
                        "[command]/whoami[/command]  - Show your account details\n"
                        "[command]/auth[/command]    - Show authentication status\n"
                        "[command]/status[/command]  - Show system & session status\n"
                        "[command]/reauth[/command]  - Re-authenticate with new credentials\n"
                        "[command]/logout[/command]  - Clear stored credentials and exit\n"
                        + (("[command]/admin[/command]   - Admin panel (owner only)\n") if role == "admin" else "") +
                        "\n[dim]Tip: Press [bold]ESC[/bold] while Mythos is typing to stop the response.[/dim]",
                        title="Commands", border_style="yellow"
                    ))
                    continue

                # --- Auth ---
                elif cmd == '/auth':
                    tok = get_stored_token()
                    em = get_stored_email()
                    if em and tok and is_valid_token(tok):
                        r = get_user_role(em)
                        role_icon = "👑 " if r == "admin" else ""
                        console.print(f"[success]{role_icon}✓ Authenticated[/success]")
                        console.print(f"[info]Email: [bold]{em}[/bold][/info]")
                        console.print(f"[info]Token: [dim]{tok[:20]}...[/dim][/info]")
                        console.print(f"[info]Role:  [bold]{r}[/bold][/info]")
                    else:
                        console.print("[warning]No valid credentials found.[/warning]")
                        console.print("[info]Type [command]/reauth[/command] to authenticate.[/info]")
                    continue

                # --- Whoami ---
                elif cmd == '/whoami':
                    em = get_stored_email()
                    tok = get_stored_token()
                    if em:
                        r = get_user_role(em)
                        role_icon = "👑 " if r == "admin" else ""
                        table = Table(title=f"{role_icon}Account Details", border_style="cyan")
                        table.add_column("Field", style="bold cyan")
                        table.add_column("Value")
                        table.add_row("Email", em)
                        table.add_row("Role", r.upper())
                        table.add_row("Authenticated", "Yes" if tok and is_valid_token(tok) else "No")
                        table.add_row("Config File", CONFIG_FILE)
                        console.print(table)
                    else:
                        console.print("[warning]No account configured. Type /reauth to log in.[/warning]")
                    continue

                # --- Status ---
                elif cmd == '/status':
                    em = get_stored_email()
                    tok = get_stored_token()
                    has_auth = em and tok and is_valid_token(tok)

                    table = Table(title="Mythos Status", border_style="cyan")
                    table.add_column("Item", style="bold cyan")
                    table.add_column("Value")
                    table.add_row("Model", MODEL_NAME)
                    table.add_row("Ollama URL", OLLAMA_URL)
                    table.add_row("Web Portal", AUTH_URL)
                    table.add_row("Config File", CONFIG_FILE)
                    table.add_row("Config Exists", str(os.path.exists(CONFIG_FILE)))
                    table.add_row("Auth Status", "✅ Authenticated" if has_auth else "❌ Not authenticated")
                    if em:
                        table.add_row("Email", em)
                        table.add_row("Role", get_user_role(em).upper())
                    if tok:
                        table.add_row("Token", f"{tok[:20]}...")
                    console.print(table)
                    continue

                # --- Reauth ---
                elif cmd == '/reauth':
                    clear_credentials()
                    if require_auth():
                        console.print("[success]✓ Re-authentication successful.[/success]")
                    continue

                # --- Logout ---
                elif cmd == '/logout':
                    em = get_stored_email()
                    clear_credentials()
                    console.print("[info]Credentials cleared. You are logged out.[/info]")
                    console.print("[info]Run [command]mythos[/command] again to re-authenticate.[/info]")
                    break

                # --- Admin ---
                elif cmd == '/admin':
                    em = get_stored_email()
                    if not is_admin_email(em):
                        console.print("[error]Access denied. This command is for Mythos Admin only.[/error]")
                        continue

                    # Show admin panel
                    config = load_config()
                    console.print(Panel(
                        "[bold yellow]👑 Mythos Admin Panel[/bold yellow]\n\n"
                        f"[info]Admin:[/info]    {em}\n"
                        f"[info]Config:[/info]  {CONFIG_FILE}\n"
                        f"[info]Model:[/info]   {MODEL_NAME}\n"
                        f"[info]Portal:[/info]  {AUTH_URL}\n"
                        "\n[dim]As the Mythos owner, you have full control over this instance.[/dim]",
                        title="Admin Console",
                        border_style="yellow"
                    ))
                    continue

                # --- Model ---
                elif cmd == '/model':
                    console.print(f"[info]Model: [bold]{MODEL_NAME}[/bold] via Ollama at {OLLAMA_URL}[/info]\n")
                    continue

                else:
                    console.print(f"[error]Unknown command: {cmd}. Type /help for a list.[/error]\n")
                    continue

            # ---- Normal message (not a command) ----
            messages.append({"role": "user", "content": user_input})

            # Start the assistant response
            full_response = ""
            console.print("\n[assistant]Mythos[/assistant]")

            payload = {
                "model": MODEL_NAME,
                "messages": messages,
                "stream": True
            }

            # Flush any pending keypresses before starting
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
                                # Check for ESC key to stop response
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
