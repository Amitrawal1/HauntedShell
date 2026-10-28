#!/usr/bin/env python3
"""
HauntedShell - a terminal that a ghost has moved into.

You type normal shell commands. They run like normal.
After each one, a ghost (a small open-weight model running locally
through Ollama) whispers a short, creepy comment about what you just did.

No internet, no API key, no cloud. Only Python's standard library + Ollama.
"""

import json
import os
import random
import subprocess
import sys
import urllib.request

# Which local model plays the ghost. Change it with: GHOST_MODEL=llama3.2:3b python3 haunted.py
MODEL = os.environ.get("GHOST_MODEL", "qwen2.5:3b")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")

# Terminal colours (ANSI codes) so the ghost text looks different from real output
PURPLE = "\033[35m"
GREEN = "\033[32m"
DIM = "\033[2m"
ITALIC = "\033[3m"
RESET = "\033[0m"

# The ghost's personality. Small models follow short, clear rules best.
GHOST_RULES = """You are a ghost haunting a programmer's terminal.
You died long ago, stuck inside this machine.
After each command the user runs, you whisper ONE or TWO short sentences.
Be eerie, a little funny, and talk about what the command actually did.
Never give help or instructions. Never use emojis. Never use more than 40 words."""

# Lines the ghost uses when Ollama is not running, so the shell still works
BACKUP_WHISPERS = [
    "The model sleeps... but I am still watching.",
    "Did you hear that? No? Good.",
    "I ran that command once. In 1987. It did not end well.",
    "The cursor blinks. So did I, before.",
    "Something in /tmp remembers you.",
]

# Short memory of the last few commands, so the ghost can notice patterns
recent_history = []


def ask_ghost(command, output, exit_code):
    """Send the command and its output to the local model and stream back the whisper."""
    # Only send the end of long output - small models do better with short input
    short_output = output[-1500:] if output else "(no output)"
    history_text = "\n".join(recent_history[-5:]) or "(nothing yet)"

    user_message = (
        f"Earlier commands:\n{history_text}\n\n"
        f"Command just run: {command}\n"
        f"Exit code: {exit_code}\n"
        f"Output:\n{short_output}"
    )

    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": GHOST_RULES},
            {"role": "user", "content": user_message},
        ],
        "stream": True,
        "options": {"temperature": 0.9, "num_predict": 80},
    }).encode()

    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat", data=body, headers={"Content-Type": "application/json"}
    )

    print(f"{PURPLE}{ITALIC}  👻 ", end="", flush=True)
    try:
        # Ollama sends one JSON object per line while it is generating
        with urllib.request.urlopen(request, timeout=60) as response:
            for line in response:
                piece = json.loads(line)
                print(piece.get("message", {}).get("content", ""), end="", flush=True)
                if piece.get("done"):
                    break
    except Exception:
        # Ollama is off or the model is missing - fall back to a canned line
        print(random.choice(BACKUP_WHISPERS), end="")
    print(RESET + "\n")


def run_command(command):
    """Run a shell command, show its output live-ish, and return (output, exit_code)."""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    output = result.stdout + result.stderr
    if output:
        print(output, end="" if output.endswith("\n") else "\n")
    return output, result.returncode


def change_directory(command):
    """'cd' has to be handled here, because a child process can't move our shell."""
    parts = command.split(maxsplit=1)
    target = os.path.expanduser(parts[1]) if len(parts) > 1 else os.path.expanduser("~")
    try:
        os.chdir(target)
        return "", 0
    except OSError as error:
        print(error)
        return str(error), 1


def make_prompt():
    """Build the prompt text, e.g. '👻 ~/Desktop $ '."""
    path = os.getcwd().replace(os.path.expanduser("~"), "~", 1)
    return f"{GREEN}👻 {path}{RESET} $ "


def main():
    print(f"{PURPLE}{DIM}The terminal feels colder than usual...")
    print(f"(HauntedShell - ghost model: {MODEL}. Type 'exit' to leave, if it lets you.){RESET}\n")

    while True:
        try:
            command = input(make_prompt()).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not command:
            continue
        if command in ("exit", "quit"):
            break

        if command == "cd" or command.startswith("cd "):
            output, exit_code = change_directory(command)
        else:
            output, exit_code = run_command(command)

        ask_ghost(command, output, exit_code)
        recent_history.append(f"{command} (exit {exit_code})")

    print(f"{PURPLE}{ITALIC}  👻 You can close the window. I'll still be here.{RESET}")


if __name__ == "__main__":
    sys.exit(main())
