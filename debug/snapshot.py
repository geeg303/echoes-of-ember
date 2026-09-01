"""Immutable, cheap diagnostic snapshots built from authoritative runtime state."""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class DebugSnapshot:
    frame: int
    app_mode: str
    level_id: str
    player: Mapping[str, Any]
    camera: Mapping[str, Any]
    world: Mapping[str, Any]
    entities: Mapping[str, Any]
    boss: Mapping[str, Any]
    input: Mapping[str, Any]
    audio: Mapping[str, Any]
    effects: Mapping[str, Any]
    progression: Mapping[str, Any]
    performance: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame": self.frame, "app_mode": self.app_mode, "level_id": self.level_id,
            "player": dict(self.player), "camera": dict(self.camera), "world": dict(self.world),
            "entities": dict(self.entities), "boss": dict(self.boss), "input": dict(self.input),
            "audio": dict(self.audio), "effects": dict(self.effects),
            "progression": dict(self.progression), "performance": dict(self.performance),
        }


def _freeze(data: dict[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(data)


def _enum(value: object, default: str = "-") -> str:
    return str(getattr(value, "value", value if value is not None else default))


def build_snapshot(game: object, frame: int, performance: Mapping[str, Any]) -> DebugSnapshot:
    """Extract safe primitives without copying surfaces, managers, or live entities."""
    app_mode = str(getattr(game, "app_mode", "unknown"))
    level = getattr(game, "level", None)
    player = getattr(game, "player", None)
    camera = getattr(game, "camera", None)
    enemies = getattr(game, "enemies", None)
    projectiles = getattr(game, "projectiles", None)
    objects = getattr(game, "world_objects", None)
    secrets = getattr(game, "secrets", None)
    npcs = getattr(game, "npcs", None)
    boss_system = getattr(game, "boss_system", None)
    powers = getattr(game, "powerups", None)
    effects = getattr(game, "effects", None)
    audio = getattr(game, "audio", None)
    input_manager = getattr(game, "input", None)
    achievements = getattr(game, "achievements", None)
    save_session = getattr(game, "save_session", None)
    level_id = getattr(getattr(level, "metadata", None), "level_id", "-")
    p_rect = getattr(player, "rect", None)
    velocity = getattr(player, "velocity", None)
    animation = getattr(player, "animation", None)
    checkpoint_ids = sorted(getattr(objects, "activated_checkpoint_ids", ()))
    enemy_items = tuple(getattr(enemies, "enemies", ()))
    projectile_items = tuple(getattr(projectiles, "projectiles", ()))
    enemy_counts: dict[str, int] = {}
    for item in enemy_items:
        name = _enum(getattr(item, "kind", "unknown"))
        enemy_counts[name] = enemy_counts.get(name, 0) + 1
    projectile_counts: dict[str, int] = {}
    for item in projectile_items:
        name = _enum(getattr(item, "faction", "unknown"))
        projectile_counts[name] = projectile_counts.get(name, 0) + 1
    boss = getattr(boss_system, "boss", None)
    arena = getattr(boss_system, "arena", None)
    dialogue = getattr(game, "dialogue", None)
    current_music = getattr(audio, "current_music", None) or getattr(audio, "_current_music", None)
    ambience_value = getattr(audio, "ambience_owners", ())
    ambience = ambience_value() if callable(ambience_value) else ambience_value
    channel_value = getattr(audio, "active_channels", 0)
    channels = channel_value() if callable(channel_value) else channel_value
    return DebugSnapshot(
        frame=frame, app_mode=app_mode, level_id=str(level_id),
        player=_freeze({
            "position": tuple(p_rect.topleft) if p_rect else None,
            "bounds": tuple(p_rect) if p_rect else None,
            "velocity": (round(velocity.x, 2), round(velocity.y, 2)) if velocity else None,
            "grounded": bool(getattr(player, "grounded", False)),
            "health": getattr(player, "health", None), "max_health": getattr(player, "max_health", None),
            "lives": getattr(player, "lives", None), "facing": "right" if getattr(player, "facing", 1) > 0 else "left",
            "animation": getattr(animation, "current_name", "-"), "frame": getattr(animation, "frame_index", 0),
            "coyote": round(float(getattr(player, "coyote_timer", 0.0)), 3),
            "jump_buffer": round(float(getattr(player, "jump_buffer_timer", 0.0)), 3),
            "invulnerability": round(float(getattr(player, "invulnerability_timer", 0.0)), 3),
            "powerup": _enum(getattr(getattr(getattr(powers, "active", None), "definition", None), "kind", None)),
            "powerup_timer": round(float(getattr(getattr(powers, "active", None), "remaining", 0.0) or 0.0), 2),
            "stone_guard": bool(getattr(powers, "has", lambda _x: False)(getattr(__import__("systems.powerup_system", fromlist=["PowerUpType"]).PowerUpType, "STONE_GUARD"))) if powers else False,
            "dead": bool(getattr(player, "is_dead", False)),
        }),
        camera=_freeze({"position": tuple(round(v, 2) for v in getattr(camera, "position", (0, 0))), "view": tuple(getattr(camera, "view_rect", ())), "bounds": tuple(getattr(camera, "bounds", ())) if getattr(camera, "bounds", None) else None}),
        world=_freeze({
            "dimensions": (getattr(getattr(level, "tilemap", None), "pixel_width", 0), getattr(getattr(level, "tilemap", None), "pixel_height", 0)),
            "tile": (p_rect.centerx // getattr(getattr(level, "tilemap", None), "tile_size", 64), p_rect.centery // getattr(getattr(level, "tilemap", None), "tile_size", 64)) if p_rect and level else None,
            "goal": tuple(getattr(getattr(game, "goal", None), "rect", ())), "checkpoints": len(getattr(objects, "checkpoints", ())),
            "current_checkpoint": checkpoint_ids[-1] if checkpoint_ids else "spawn", "platforms": len(getattr(objects, "platforms", ())),
            "secrets": f"{getattr(secrets, 'discovered_count', 0)}/{len(getattr(secrets, 'areas', {}))}", "npcs": len(getattr(npcs, "npcs", ())),
            "timer": round(float(getattr(game, "elapsed_time", 0.0)), 2), "phase": _enum(getattr(game, "gameplay_phase", None)),
        }),
        entities=_freeze({"enemies": len(enemy_items), "enemies_by_type": tuple(sorted(enemy_counts.items())), "projectiles": len(projectile_items), "projectiles_by_faction": tuple(sorted(projectile_counts.items())), "collectibles_remaining": sum(bool(getattr(x, "active", False)) for x in getattr(getattr(game, "collectibles", None), "collectibles", ())), "powerups_remaining": sum(bool(getattr(x, "active", False)) for x in getattr(getattr(game, "powerup_pickups", None), "pickups", ())), "platforms": len(getattr(objects, "platforms", ())), "npcs": len(getattr(npcs, "npcs", ())), "particles": getattr(effects, "particle_count", 0)}),
        boss=_freeze({"active": bool(getattr(boss_system, "active", False)), "id": getattr(boss, "boss_id", None), "name": getattr(boss, "display_name", None), "health": getattr(boss, "health", None), "max_health": getattr(boss, "max_health", None), "phase": getattr(boss, "phase", None), "state": _enum(getattr(boss, "state", None)), "state_timer": round(float(getattr(boss, "state_timer", 0.0)), 2), "attack": getattr(boss, "current_attack", None), "previous_attack": getattr(boss, "previous_attack", None), "vulnerable": bool(getattr(boss, "vulnerable", False)), "arena_locked": bool(getattr(arena, "active", False)), "defeated": bool(getattr(boss_system, "defeated", False))}),
        input=_freeze({"device": _enum(getattr(input_manager, "active_device", None)), "controller": getattr(input_manager, "controller_name", "") or "none", "controllers": getattr(input_manager, "connected_count", 0), "move_axis": round(float(getattr(input_manager, "axis", lambda _a: 0)(getattr(__import__("core.input_manager", fromlist=["Action"]).Action, "MOVE_X"))), 2) if input_manager else 0, "deadzone": getattr(input_manager, "deadzone", 0), "held": tuple(sorted(_enum(x) for x in getattr(input_manager, "_held", ()))), "pressed": tuple(sorted(_enum(x) for x in getattr(input_manager, "_pressed", ())))}),
        audio=_freeze({"available": bool(getattr(audio, "available", False)), "muted": bool(getattr(getattr(audio, "settings", None), "muted", False)), "music": current_music or "none", "ambience": tuple(ambience), "channels": channels, "recent": getattr(audio, "recent_event", "-")}),
        effects=_freeze({"quality": _enum(getattr(effects, "quality", None)), "particles": getattr(effects, "particle_count", 0), "cap": getattr(effects, "capacity", 0), "emitters": getattr(effects, "emitter_count", 0), "screen": getattr(effects, "screen_effect_count", 0)}),
        progression=_freeze({"slot": getattr(save_session, "slot_id", None), "campaign_schema": getattr(save_session, "schema_version", 3) if save_session else 3, "completed_levels": getattr(getattr(game, "world_progress", None), "levels_completed", 0), "bosses": len(getattr(getattr(game, "world_progress", None), "defeated_bosses", ())), "dialogue_flags": len(getattr(getattr(game, "world_progress", None), "dialogue_flags", ())), "achievement_schema": 1, "achievements": f"{getattr(achievements, 'unlocked_count', 0)}/{len(getattr(achievements, 'definitions', ())) }", "achievement_queue": len(getattr(achievements, "notifications", ())), "dialogue": getattr(dialogue, "dialogue_id", None), "debug_nonpersistent": bool(getattr(getattr(game, "debug", None), "enabled", False))}),
        performance=_freeze(dict(performance)),
    )
