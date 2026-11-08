"""World 2 Ember Current prototype runtime, format, and tooling coverage."""

from __future__ import annotations
from copy import deepcopy
import json
import pygame

from core.debug_manager import DebugManager
from debug.snapshot import build_snapshot
from editor.commands import CommandHistory
from editor.document import LevelDocument
from editor.palette import current_template
from entities.player import Player, PlayerControls
from entities.projectile import EmberPulseProjectile, Faction
from settings import PROJECT_ROOT
from systems.projectile_system import ProjectileManager
from systems.powerup_system import PowerUpSystem, PowerUpType
from systems.combat import DamageSource
from systems.world_object_system import WorldObjectManager
from tools.validation import validate_level_data
from world.collision import CollisionEngine
from world.ember_current import MAX_CURRENT_INFLUENCE, EmberCurrentSystem, parse_ember_currents
from world.level import Level, WorldObjectSpawn
from world.tilemap import TileMap


def definition(current_id="flow", bounds=(0, 0, 200, 200), direction=(1, 0), strength=600, affects=("player",)):
    return parse_ember_currents(
        [
            {
                "id": current_id,
                "bounds": list(bounds),
                "direction": list(direction),
                "strength": strength,
                "affects": list(affects),
            }
        ]
    )[0]


def empty_map(width=12, height=8):
    return TileMap.from_data({"width": width, "height": height, "tile_size": 64, "tiles": []})


def valid_level_data():
    return json.loads((PROJECT_ROOT / "data" / "levels" / "prototype_glassreach_currents.json").read_text())


def test_no_current_backward_compatibility_and_prototype_load():
    level = Level.load(PROJECT_ROOT / "data" / "levels" / "verdant_01.json")
    assert level.ember_currents == ()
    prototype = Level.load(PROJECT_ROOT / "data" / "levels" / "prototype_glassreach_currents.json")
    assert len(prototype.ember_currents) == 8


def test_horizontal_vertical_arbitrary_entry_exit_and_normalization():
    system = EmberCurrentSystem(
        (
            definition(),
            definition("lift", direction=(0, -2), strength=300),
            definition("diagonal", direction=(3, 4), strength=500),
        )
    )
    inside = pygame.Rect(20, 20, 20, 20)
    outside = pygame.Rect(300, 300, 20, 20)
    force = system.influence(inside, "player")
    assert force.x == 900 and force.y == 100
    assert system.influence(outside, "player") == pygame.Vector2()
    assert set(system.overlapping_ids(inside)) == {"flow", "lift", "diagonal"}


def test_overlap_adds_then_clamps_deterministically():
    system = EmberCurrentSystem(tuple(definition(str(i), strength=1000) for i in range(4)))
    force = system.influence(pygame.Rect(10, 10, 10, 10), "player")
    assert force.length() == MAX_CURRENT_INFLUENCE and force.x == MAX_CURRENT_INFLUENCE


def test_reset_enable_disable_and_reverse():
    system = EmberCurrentSystem((definition(direction=(1, 0)),))
    rect = pygame.Rect(10, 10, 10, 10)
    system.set_enabled("flow", False)
    assert not system.influence(rect, "player")
    system.reset()
    system.reverse("flow")
    assert system.influence(rect, "player").x < 0
    system.reset()
    assert system.influence(rect, "player").x > 0


def test_player_current_composes_with_control_and_collision():
    tilemap = TileMap.from_data(
        {"width": 8, "height": 8, "tile_size": 64, "tiles": [{"id": 1, "position": [3, 0], "size": [1, 8]}]}
    )
    player = Player((80, 120))
    collision = CollisionEngine(tilemap)
    for _ in range(90):
        player.update(1 / 60, PlayerControls(move_axis=-1), collision, external_acceleration=pygame.Vector2(900, 0))
    assert player.velocity.x < 0, "control remains authoritative enough to oppose a medium Current"
    player.reposition((160, 120))
    player.velocity.update(600, 0)
    for _ in range(30):
        player.update(1 / 60, PlayerControls(), collision, external_acceleration=pygame.Vector2(1800, 0))
    assert player.rect.right <= 192


def test_player_jump_and_ground_state_survive_current():
    tilemap = TileMap.from_data(
        {"width": 8, "height": 8, "tile_size": 64, "tiles": [{"id": 1, "position": [0, 6], "size": [8, 2]}]}
    )
    player = Player((100, 300))
    collision = CollisionEngine(tilemap)
    for _ in range(30):
        player.update(1 / 60, PlayerControls(), collision, external_acceleration=pygame.Vector2(400, -300))
    assert player.grounded
    player.update(
        1 / 60,
        PlayerControls(jump_pressed=True, jump_held=True),
        collision,
        external_acceleration=pygame.Vector2(0, -500),
    )
    assert not player.grounded and player.velocity.y < 0


def test_platform_carry_and_current_are_composed_once():
    tilemap = empty_map()
    collision = CollisionEngine(tilemap)
    player = Player((110, 80))
    manager = WorldObjectManager(
        (
            WorldObjectSpawn(
                "p", "moving_platform", (100, 150), {"movement": "horizontal", "distance": 200, "speed": 60}
            ),
        ),
        (0, 0),
    )
    manager.riding_id = "p"
    manager.update_before_player(1 / 60, player, tilemap)
    carried_x = player.position.x
    player.update(1 / 60, PlayerControls(), collision, external_acceleration=pygame.Vector2(600, 0))
    assert carried_x > 110 and player.position.x > carried_x


def test_powerups_damage_and_current_regressions():
    collision = CollisionEngine(empty_map())
    player = Player((80, 80))
    powers = PowerUpSystem(player)
    powers.activate(PowerUpType.WIND_BOOTS)
    player.update(1 / 60, PlayerControls(move_axis=1), collision, powers.movement_modifiers, pygame.Vector2(-300, 0))
    assert player.velocity.x > 0
    powers.activate(PowerUpType.AETHER_WING)
    player.grounded = False
    player.extra_jump_available = True
    player.update(
        1 / 60, PlayerControls(jump_pressed=True), collision, powers.movement_modifiers, pygame.Vector2(0, -200)
    )
    assert not player.extra_jump_available and player.velocity.y < 0
    powers.activate(PowerUpType.STONE_GUARD)
    health = player.health
    result = player.apply_damage(1, DamageSource.ENEMY, pygame.Vector2(-390, -430))
    assert result.absorbed and player.health == health
    player.invulnerability_timer = 0
    result = player.apply_damage(1, DamageSource.ENEMY, pygame.Vector2(-390, -430))
    assert result.applied
    player.update(1 / 60, PlayerControls(), collision, external_acceleration=pygame.Vector2(300, 0))
    assert player.velocity.x < 0, "knockback composes with rather than being erased by Current force"


def test_projectile_current_preserves_faction_lifetime_and_cleanup():
    manager = ProjectileManager()
    shot = EmberPulseProjectile("p", (50, 50), pygame.Vector2(100, 0), 1, Faction.PLAYER, 0.05)
    manager.spawn(shot)
    currents = EmberCurrentSystem((definition(affects=("player_projectiles",), direction=(0, -1)),))
    manager.update(0.02, empty_map(), currents)
    assert shot.velocity.y < 0 and shot.faction is Faction.PLAYER
    manager.update(0.04, empty_map(), currents)
    assert manager.projectiles == []


def test_validation_rejects_malformed_currents_and_preserves_existing_rules():
    data = valid_level_data()
    data["ember_currents"] = [
        {
            "id": "crawler_01",
            "bounds": [-1, 0, 0, 10],
            "direction": [0, 0],
            "strength": float("inf"),
            "affects": ["mystery"],
            "enabled": "yes",
            "style": "unknown",
            "extra": 1,
        }
    ]
    errors = validate_level_data(data)
    joined = " | ".join(errors)
    for phrase in (
        "duplicate id",
        "bounds is invalid",
        "non-zero",
        "strength",
        "unknown target",
        "enabled",
        "style",
        "unknown field",
    ):
        assert phrase in joined


def test_editor_current_round_trip_duplicate_undo_redo_and_unknown_fields(tmp_path):
    doc = LevelDocument.new("prototype_editor_current", 20, 12)
    doc.data["future_root"] = {"kept": True}
    history = CommandHistory()
    item = current_template(200, 200)
    item["future_field"] = "kept"
    history.execute(doc, "add current", lambda: doc.add_object(item, "ember_currents"))
    assert len(doc.data["ember_currents"]) == 1
    history.execute(doc, "duplicate", doc.duplicate_selected)
    assert len(doc.data["ember_currents"]) == 2
    assert history.undo(doc) and len(doc.data["ember_currents"]) == 1
    assert history.redo(doc) and len(doc.data["ember_currents"]) == 2
    # Unknown Current fields are rejected authoritatively; unrelated root fields remain lossless.
    for current in doc.data["ember_currents"]:
        current.pop("future_field", None)
    path = tmp_path / "prototype_editor_current.json"
    doc.save(path)
    loaded = LevelDocument.load(path)
    assert loaded.data["future_root"] == {"kept": True} and len(loaded.data["ember_currents"]) == 2


def test_current_visual_remains_visible_without_particle_system(pygame_headless):
    system = EmberCurrentSystem((definition(),))
    surface = pygame.Surface((240, 240))
    before = surface.copy()
    system.draw(surface, pygame.Rect(0, 0, 240, 240), (0, 0))
    assert pygame.image.tobytes(surface, "RGB") != pygame.image.tobytes(before, "RGB")


def test_debug_snapshot_and_commands_expose_safe_current_data(game_factory):
    from dataclasses import replace
    from world.campaign import DEFAULT_WORLD_REGISTRY, WorldRegistry

    registry = WorldRegistry.load(DEFAULT_WORLD_REGISTRY)
    paths = dict(registry.level_paths)
    path = PROJECT_ROOT / "data" / "levels" / "prototype_glassreach_currents.json"
    paths["prototype_glassreach_currents"] = path
    registry = replace(registry, level_ids=registry.level_ids + ("prototype_glassreach_currents",), level_paths=paths)
    game = game_factory(level_id="prototype_glassreach_currents", registry=registry, debug_enabled=True)
    snapshot = build_snapshot(game, 1, {})
    assert snapshot.world["ember_currents"] == 8 and snapshot.world["current_influence"]
    game.debug.execute(game, "current disable current_horizontal_weak")
    assert not game.ember_currents.currents["current_horizontal_weak"].enabled
    game.debug.execute(game, "current reverse current_vertical_lift")
    assert game.ember_currents.currents["current_vertical_lift"].definition.direction.y > 0
