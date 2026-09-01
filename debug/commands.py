"""Explicit, validated debug command registry. No evaluation or arbitrary paths."""
from __future__ import annotations
from dataclasses import dataclass
import shlex
from typing import Callable

class DebugCommandError(ValueError): pass
@dataclass(frozen=True, slots=True)
class DebugCommand:
    name: str; syntax: str; description: str; contexts: frozenset[str]; handler: Callable[[object, tuple[str, ...]], str]; mutates: bool = False

class DebugCommandRegistry:
    def __init__(self) -> None: self.commands: dict[str, DebugCommand] = {}
    def register(self, command: DebugCommand) -> None:
        if not command.name or command.name in self.commands: raise ValueError(f"duplicate debug command: {command.name}")
        self.commands[command.name] = command
    def dispatch(self, game: object, text: str) -> tuple[str, bool]:
        try: parts=tuple(shlex.split(text))
        except ValueError as exc: raise DebugCommandError(str(exc)) from exc
        if not parts: raise DebugCommandError("Enter a command; use 'help' for the list.")
        if parts[0] == "help":
            if len(parts)==1: return ("Commands: "+", ".join(sorted(self.commands)), False)
            command=self.commands.get(parts[1])
            if command is None: raise DebugCommandError(f"Unknown command: {parts[1]}")
            return (f"{command.syntax} — {command.description}", False)
        command=self.commands.get(parts[0])
        if command is None: raise DebugCommandError(f"Unknown command: {parts[0]}")
        mode=str(getattr(game,"app_mode","unknown"))
        if "global" not in command.contexts and mode not in command.contexts: raise DebugCommandError(f"{command.name} is unavailable in {mode}")
        try: return command.handler(game, parts[1:]), command.mutates
        except DebugCommandError: raise
        except (TypeError, ValueError) as exc: raise DebugCommandError(str(exc)) from exc

def require_args(args: tuple[str,...], count: int, syntax: str) -> None:
    if len(args) != count: raise DebugCommandError(f"Usage: {syntax}")

def parse_int(value: str, minimum: int, maximum: int) -> int:
    try: result=int(value)
    except ValueError as exc: raise DebugCommandError(f"Expected integer, got {value!r}") from exc
    if not minimum <= result <= maximum: raise DebugCommandError(f"Value must be {minimum}..{maximum}")
    return result

def parse_float(value: str, minimum: float, maximum: float) -> float:
    try: result=float(value)
    except ValueError as exc: raise DebugCommandError(f"Expected number, got {value!r}") from exc
    if not minimum <= result <= maximum: raise DebugCommandError(f"Value must be {minimum:g}..{maximum:g}")
    return result
