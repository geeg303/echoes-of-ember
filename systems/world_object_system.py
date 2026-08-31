"""Runtime orchestration for data-driven platforms and interactables."""

from __future__ import annotations

import pygame

from entities.player import Player
from world.checkpoint import Checkpoint
from world.moving_platform import DisappearingPlatform, FallingPlatform, MovingPlatform
from world.tile import TileKind
from world.tilemap import TileMap
from world.trigger import Door, Switch


class WorldObjectManager:
    def __init__(self, spawns: tuple[object, ...], initial_spawn: tuple[float, float]) -> None:
        self.platforms: list[MovingPlatform] = []
        self.switches: list[Switch] = []
        self.doors: list[Door] = []
        self.checkpoints: list[Checkpoint] = []
        self.respawn_position = pygame.Vector2(initial_spawn)
        self.riding_id: str | None = None
        self.activated_checkpoint_ids: set[str] = set()
        for spawn in spawns:
            props = spawn.properties
            if spawn.kind == "moving_platform":
                self.platforms.append(MovingPlatform(spawn.object_id, spawn.position, props["movement"], props["distance"], props["speed"], (props.get("width", 128), props.get("height", 22))))
            elif spawn.kind == "falling_platform":
                self.platforms.append(FallingPlatform(spawn.object_id, spawn.position, props.get("activation_delay", 0.65), props.get("fall_acceleration", 1500.0), props.get("reset_delay", 3.0), (props.get("width", 112), props.get("height", 22))))
            elif spawn.kind == "disappearing_platform":
                self.platforms.append(DisappearingPlatform(spawn.object_id, spawn.position, props.get("visible_duration", 2.2), props.get("warning_duration", 0.65), props.get("hidden_duration", 1.6), (props.get("width", 112), props.get("height", 20))))
            elif spawn.kind == "switch":
                targets = props["target_ids"]
                self.switches.append(Switch(spawn.object_id, spawn.position, tuple(targets)))
            elif spawn.kind == "door":
                self.doors.append(Door(spawn.object_id, spawn.position, (props.get("width", 48), props.get("height", 128)), props.get("opening_duration", 0.55)))
            elif spawn.kind == "checkpoint":
                self.checkpoints.append(Checkpoint(spawn.object_id, spawn.position))

    def update_before_player(self, dt: float, player: Player, tilemap: TileMap) -> None:
        for platform in self.platforms:
            platform.update(dt)
        for door in self.doors:
            door.update(dt)
        rider = next((p for p in self.platforms if p.object_id == self.riding_id and p.solid), None)
        if rider and rider.delta.length_squared() > 0:
            proposed = player.rect.move(round(rider.delta.x), round(rider.delta.y))
            blocked = any(proposed.colliderect(tile.rect) for tile in tilemap.tiles_in_rect(proposed, {TileKind.SOLID, TileKind.BREAKABLE, TileKind.BOUNCE, TileKind.SLIPPERY}))
            if not blocked:
                player.position += rider.delta
                player.sync_rect()
            else:
                self.riding_id = None

    def resolve_after_player(self, player: Player, interact_pressed: bool, tilemap: TileMap) -> bool:
        self.riding_id = None
        for platform in self.platforms:
            if not platform.solid:
                continue
            horizontally_overlapping = player.rect.right > platform.rect.left and player.rect.left < platform.rect.right
            crossed_top = player.previous_rect.bottom <= platform.previous_rect.top + 8 and player.rect.bottom >= platform.rect.top
            if player.velocity.y >= 0 and horizontally_overlapping and crossed_top:
                player.rect.bottom = platform.rect.top
                player.position.y = float(player.rect.y)
                player.velocity.y = 0.0
                player.grounded = True
                self.riding_id = platform.object_id
                platform.trigger()
                break
        for door in self.doors:
            if door.solid and player.rect.colliderect(door.rect):
                if player.previous_rect.right <= door.rect.left:
                    player.rect.right = door.rect.left
                elif player.previous_rect.left >= door.rect.right:
                    player.rect.left = door.rect.right
                elif player.previous_rect.bottom <= door.rect.top:
                    player.rect.bottom = door.rect.top
                    player.grounded = True
                    player.velocity.y = 0
                else:
                    player.rect.top = door.rect.bottom
                    player.velocity.y = max(0.0, player.velocity.y)
                player.position.update(player.rect.topleft)
                player.velocity.x = 0.0
        activated = False
        if interact_pressed:
            doors = {door.object_id: door for door in self.doors}
            for switch in self.switches:
                if switch.can_interact(player.rect) and switch.activate():
                    for target in switch.target_ids:
                        doors[target].open()
                    activated = True
        for checkpoint in self.checkpoints:
            if checkpoint.rect.colliderect(player.rect) and not checkpoint.active and self._safe_checkpoint(checkpoint, tilemap):
                for other in self.checkpoints:
                    other.active = False
                checkpoint.active = True
                self.activated_checkpoint_ids.add(checkpoint.object_id)
                self.respawn_position.update(checkpoint.respawn_position)
                activated = True
        return activated

    @staticmethod
    def _safe_checkpoint(checkpoint: Checkpoint, tilemap: TileMap) -> bool:
        spawn_rect = pygame.Rect(round(checkpoint.respawn_position.x), round(checkpoint.respawn_position.y), Player.WIDTH, Player.HEIGHT)
        forbidden = {TileKind.SOLID, TileKind.BREAKABLE, TileKind.BOUNCE, TileKind.SLIPPERY, TileKind.HAZARD}
        return not any(spawn_rect.colliderect(tile.rect) for tile in tilemap.tiles_in_rect(spawn_rect, forbidden))

    def draw(self, surface: pygame.Surface, view: pygame.Rect, offset: tuple[int, int]) -> None:
        padded = view.inflate(192, 160)
        for item in [*self.platforms, *self.doors, *self.switches, *self.checkpoints]:
            if padded.colliderect(item.rect):
                item.draw(surface, offset)
