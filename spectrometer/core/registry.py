import os
import shlex

from spectrometer.core import out

COMMANDS = {}
ALIASES = {"q": "quit", "exit": "quit"}


def load(modules):
    COMMANDS.clear()
    for module in modules:
        for name, text, func in module.COMMANDS:
            COMMANDS[name] = (text, func)


def run_command(state, line):
    if os.name == "nt":
        line = line.replace("\\", "\\\\")
    words = shlex.split(line.lstrip().removeprefix("spektro>"), comments=True)
    if not words:
        return None
    words[0] = ALIASES.get(words[0].lower(), words[0].lower())
    if " ".join(words[:2]) in COMMANDS:
        return COMMANDS[" ".join(words[:2])][1](state, words[2:])
    if words[0] not in COMMANDS:
        raise ValueError(f"unknown command {words[0]}. Type help for a list.")
    return COMMANDS[words[0]][1](state, words[1:])


def to_frames(text):
    n = int(text)
    if not 1 <= n <= 1000:
        raise ValueError("N must be 1 to 1000")
    return n


def ready(state, prompt):
    if state["settings"]["source"][0] != "camera" or not out.interactive():
        return True
    try:
        answer = out.ask(prompt)
    except EOFError:
        return False
    return answer.strip().lower() != "cancel"


def need_spectrum(state):
    if state["spectrum"] is None:
        raise ValueError("No measurement yet. Run step first.")
    return state["spectrum"]
