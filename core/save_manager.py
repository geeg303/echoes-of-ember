"""Three-slot atomic JSON persistence with validation and backup recovery."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import logging
import os
from pathlib import Path
import shutil

from core.paths import user_data_root
from systems.save_data import SaveSession, SaveValidationError, UnsupportedSaveVersion, utc_now
from world.campaign import WorldRegistry

LOGGER = logging.getLogger(__name__)
VALID_SLOTS = (1, 2, 3)


class SlotState(str, Enum):
    EMPTY = "empty"
    VALID = "valid"
    RECOVERED = "recovered"
    CORRUPT = "corrupt"
    UNSUPPORTED_VERSION = "unsupported_version"


@dataclass(frozen=True, slots=True)
class SlotSummary:
    slot_id: int
    state: SlotState
    levels_completed: int = 0
    score: int = 0
    secrets_discovered: int = 0
    secrets_total: int = 0
    secret_tokens_collected: int = 0
    secret_tokens_total: int = 0
    play_time_seconds: float = 0.0
    updated_at: str | None = None
    message: str = ""


@dataclass(frozen=True, slots=True)
class LoadOutcome:
    state: SlotState
    session: SaveSession | None
    message: str = ""


class SaveManager:
    def __init__(self, registry: WorldRegistry, save_root: Path | None = None) -> None:
        self.registry = registry
        self.save_root = save_root or default_save_root()
        self.save_root.mkdir(parents=True, exist_ok=True)

    def list_slots(self) -> tuple[SlotSummary, ...]:
        return tuple(self.inspect_slot(slot) for slot in VALID_SLOTS)

    def inspect_slot(self, slot_id: int) -> SlotSummary:
        outcome = self.load(slot_id)
        self._cleanup_temp(slot_id)
        if outcome.session is None:
            return SlotSummary(slot_id, outcome.state, message=outcome.message)
        session = outcome.session
        tokens = session.progress.aggregate("secret_tokens_collected", "secret_tokens_total")
        secrets = session.progress.secrets
        return SlotSummary(
            slot_id, outcome.state, session.progress.levels_completed,
            session.progress.score, secrets[0], secrets[1], tokens[0], tokens[1],
            session.play_time_seconds, session.updated_at, outcome.message,
        )

    def new_game(self, slot_id: int, overwrite: bool = False) -> SaveSession:
        self._slot(slot_id)
        if not overwrite and (self._primary(slot_id).exists() or self._backup(slot_id).exists()):
            raise FileExistsError(f"slot {slot_id} already contains save data")
        if overwrite:
            self.delete(slot_id)
        session = SaveSession.fresh(slot_id, self.registry)
        self.save(session)
        return session

    def load(self, slot_id: int) -> LoadOutcome:
        self._slot(slot_id)
        primary, backup = self._primary(slot_id), self._backup(slot_id)
        if not primary.exists() and not backup.exists():
            return LoadOutcome(SlotState.EMPTY, None)
        unsupported = False
        messages: list[str] = []
        for path, state in ((primary, SlotState.VALID), (backup, SlotState.RECOVERED)):
            if not path.exists():
                continue
            try:
                return LoadOutcome(state, self._read(path, slot_id), "recovered from backup" if state is SlotState.RECOVERED else "")
            except UnsupportedSaveVersion as exc:
                unsupported = True
                messages.append(str(exc))
            except (OSError, json.JSONDecodeError, SaveValidationError) as exc:
                messages.append(f"{path.name}: {exc}")
        state = SlotState.UNSUPPORTED_VERSION if unsupported else SlotState.CORRUPT
        return LoadOutcome(state, None, "; ".join(messages))

    def save(self, session: SaveSession) -> None:
        self._slot(session.slot_id)
        session.updated_at = utc_now()
        payload = json.dumps(session.to_dict(), indent=2, sort_keys=True) + "\n"
        primary, backup, temp = self._primary(session.slot_id), self._backup(session.slot_id), self._temp(session.slot_id)
        if primary.exists():
            try:
                self._read(primary, session.slot_id)
            except (OSError, json.JSONDecodeError, SaveValidationError):
                LOGGER.warning("Not backing up invalid primary save: %s", primary)
            else:
                backup_temp = backup.with_suffix(backup.suffix + ".tmp")
                shutil.copy2(primary, backup_temp)
                os.replace(backup_temp, backup)
        try:
            with temp.open("w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, primary)
            session.dirty = False
        except OSError:
            LOGGER.exception("Could not save slot %s", session.slot_id)
            raise

    def delete(self, slot_id: int) -> None:
        self._slot(slot_id)
        for path in (self._primary(slot_id), self._backup(slot_id), self._temp(slot_id), self._backup(slot_id).with_suffix(".bak.tmp")):
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    def _read(self, path: Path, slot_id: int) -> SaveSession:
        with path.open("r", encoding="utf-8") as handle:
            return SaveSession.from_dict(json.load(handle), self.registry, slot_id)

    def _cleanup_temp(self, slot_id: int) -> None:
        for path in (self._temp(slot_id), self._backup(slot_id).with_suffix(".bak.tmp")):
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    @staticmethod
    def _slot(slot_id: int) -> None:
        if slot_id not in VALID_SLOTS or isinstance(slot_id, bool):
            raise ValueError("slot must be 1, 2, or 3")

    def _primary(self, slot_id: int) -> Path:
        return self.save_root / f"slot_{slot_id}.json"

    def _backup(self, slot_id: int) -> Path:
        return self.save_root / f"slot_{slot_id}.json.bak"

    def _temp(self, slot_id: int) -> Path:
        return self.save_root / f"slot_{slot_id}.json.tmp"


def default_save_root() -> Path:
    return user_data_root() / "saves"
