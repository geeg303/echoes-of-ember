"""Isolated persistence/resource diagnostic used only by the release builder."""
from __future__ import annotations
import os
from core.achievement_manager import AchievementManager
from core.audio_manager import AudioSettings
from core.paths import DATA_ROOT, user_data_root
from core.save_manager import SaveManager, SlotState
from core.settings_manager import ApplicationSettings, SettingsManager
from world.campaign import DEFAULT_WORLD_REGISTRY, WorldRegistry

def run_package_self_test() -> None:
    if os.environ.get("ECHOES_PACKAGE_SELF_TEST") != "1":
        raise PermissionError("package self-test is available only to the release verifier")
    root = user_data_root(); registry = WorldRegistry.load(DEFAULT_WORLD_REGISTRY)
    saves = SaveManager(registry, root / "saves"); saves.new_game(1, overwrite=True)
    if saves.load(1).state is not SlotState.VALID: raise RuntimeError("campaign persistence failed")
    settings_path = root / "settings.json"; settings = SettingsManager(settings_path)
    settings.save(ApplicationSettings(audio=AudioSettings(master_volume=.42), effects_quality="reduced", fullscreen=False, vibration_enabled=False))
    loaded = SettingsManager(settings_path).load()
    if loaded.audio.master_volume != .42 or loaded.effects_quality != "reduced" or loaded.vibration_enabled: raise RuntimeError("settings persistence failed")
    achievements_path = root / "achievements.json"
    achievements = AchievementManager.create(DATA_ROOT / "achievements/achievements.json", profile_path=achievements_path, enabled=True)
    achievements.emit("ember_shard_collected"); achievements.flush()
    reloaded = AchievementManager.create(DATA_ROOT / "achievements/achievements.json", profile_path=achievements_path, enabled=True)
    if not reloaded.profile.unlocked: raise RuntimeError("achievement persistence failed")
