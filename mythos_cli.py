import json
import httpx
import sys
import asyncio
import msvcrt
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.theme import Theme
from rich.status import Status
from rich.panel import Panel

# Configuration
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "mythos"

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

def check_stop_key():
    """Check if ESC (27) was pressed."""
    if msvcrt.kbhit():
        key = msvcrt.getch()
        if ord(key) == 27:
            return True
    return False

async def chat():
    messages = []
    
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
                        "\n[dim]Tip: Press [bold]ESC[/bold] while Mythos is typing to stop the response.[/dim]",
                        title="Commands", border_style="yellow"
                    ))
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
