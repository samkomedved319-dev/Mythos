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

# Configuration
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "mythos"
AUTH_URL = "https://samkomedved319-dev.github.io/Mythos"
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".mythos")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
TOKEN_PATTERN = re.compile(r"^mth_[a-z0-9]{8}-[a-z0-9]{8}-[a-z0-9]{8}-[a-z0-9]{8}$")

# Setup Rich console
custom_theme = Theme({
    "info": "dim cyan",
    "user": "bold green",
    "assistant": "bold magenta",
    "prompt": "bold white",
    "error": "bold red",
    "command": "bold yellow",
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

def store_token(token):
    """Persist the auth token."""
    config = load_config()
    config["token"] = token
    save_config(config)

def is_valid_token(token):
    """Check if the token matches the expected format."""
    return bool(TOKEN_PATTERN.match(token))

def require_auth():
    """Ensure the user is authenticated before proceeding.
    
    Returns True if authenticated, False if the user chose to exit.
    """
    token = get_stored_token()

    if token and is_valid_token(token):
        return True

    # No valid token — guide the user through authentication.
    console.clear()
    console.print(Panel(
        "[bold]Welcome to Mythos — Sovereign Architect[/bold]\n\n"
        "This CLI requires authentication. You need a personal API token\n"
        "from the Mythos web portal.\n",
        title="🔐 Authentication Required",
        border_style="yellow"
    ))

    console.print("\n[info]Steps to get your token:[/info]")
    console.print(f"  1. Visit [bold cyan]{AUTH_URL}[/bold cyan] in your browser")
    console.print("  2. Sign up for a new account")
    console.print("  3. Log in and copy your API token from the dashboard")
    console.print("  4. Paste it below\n")

    while True:
        token = Prompt.ask("[yellow]Enter your Mythos API token[/yellow]").strip()

        if token.lower() in ("exit", "quit", "q"):
            console.print("\n[info]Authentication skipped. Exiting.[/info]")
            return False

        if not token:
            console.print("[error]Token cannot be empty. Type 'exit' to quit.[/error]\n")
            continue

        if not is_valid_token(token):
            console.print(
                "[error]Invalid token format. Tokens look like:[/error]\n"
                "  [bold]mth_xxxxxxxx-xxxxxxxx-xxxxxxxx-xxxxxxxx[/bold]\n"
                "[error]Please check your dashboard and try again.[/error]\n"
            )
            continue

        # Token looks valid — store it
        store_token(token)
        console.print("\n[success]✓ Authentication successful! Token saved.[/success]")
        console.print("[info]You can now use Mythos freely. [/info]")
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

    console.print(f"\n[info]Mythos Sovereign Architect | model: {MODEL_NAME}[/info]")
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
                if cmd in ['/exit', '/quit']:
                    console.print("\n[info]Farewell.[/info]")
                    break
                elif cmd == '/clear':
                    messages = []
                    console.clear()
                    console.print(f"[info]Memory cleared. Mythos is ready again.[/info]\n")
                    continue
                elif cmd == '/help':
                    console.print(Panel(
                        "[command]/clear[/command] - Clear chat history\n"
                        "[command]/exit[/command]  - Exit the program\n"
                        "[command]/help[/command]  - Show this help\n"
                        "[command]/model[/command] - Show model info\n"
                        "[command]/auth[/command]  - Show token status / re-authenticate\n"
                        "\n[dim]Tip: Press [bold]ESC[/bold] while Mythos is typing to stop the response.[/dim]",
                        title="Commands", border_style="yellow"
                    ))
                    continue
                elif cmd == '/auth':
                    tok = get_stored_token()
                    if tok and is_valid_token(tok):
                        console.print(f"[success]✓ Authenticated[/success]")
                        console.print(f"[info]Token: [dim]{tok[:20]}...[/dim][/info]")
                    else:
                        console.print("[warning]No valid token found.[/warning]")
                        console.print("[info]Type [command]/reauth[/command] to re-authenticate.[/info]")
                    continue
                elif cmd == '/reauth':
                    # Force re-authentication
                    old_token = get_stored_token()
                    if old_token:
                        store_token("")  # clear it
                    if require_auth():
                        console.print("[success]✓ Re-authentication successful.[/success]")
                    continue
                elif cmd == '/model':
                    console.print(f"[info]Model: [bold]{MODEL_NAME}[/bold] via Ollama[/info]\n")
                    continue
                else:
                    console.print(f"[error]Unknown command: {cmd}. Type /help for a list.[/error]\n")
                    continue
                
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
