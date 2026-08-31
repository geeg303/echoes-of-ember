"""Immutable authored overworld graph and monotonic runtime navigation state."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
import pygame

from systems.level_completion import CompletionRating


class MapDefinitionError(ValueError):
    """Authored overworld graph is malformed or disconnected."""


class NodeType(str, Enum):
    START = "start"
    LEVEL = "level"
    WORLD_GOAL = "world_goal"
    OPTIONAL = "optional"
    SECRET = "secret"


class RequirementType(str, Enum):
    ALWAYS = "always"
    LEVEL_COMPLETE = "level_complete"
    SECRET_EXIT_DISCOVERED = "secret_exit_discovered"
    WORLD_COMPLETE = "world_complete"


class NodeState(str, Enum):
    HIDDEN = "hidden"
    LOCKED = "locked"
    AVAILABLE = "available"
    COMPLETED = "completed"
    MASTERED = "mastered"


class ConnectionState(str, Enum):
    HIDDEN = "hidden"
    LOCKED = "locked"
    AVAILABLE = "available"
    TRAVERSED = "traversed"


@dataclass(frozen=True, slots=True)
class UnlockRequirement:
    kind: RequirementType
    level_id: str | None = None
    exit_id: str | None = None


@dataclass(frozen=True, slots=True)
class MapNode:
    node_id: str
    kind: NodeType
    position: tuple[float, float]
    title: str
    level_id: str | None = None


@dataclass(frozen=True, slots=True)
class MapConnection:
    connection_id: str
    source: str
    target: str
    waypoints: tuple[tuple[float, float], ...]
    unlock: UnlockRequirement


@dataclass(frozen=True, slots=True)
class WorldMapDefinition:
    start_node: str
    nodes: dict[str, MapNode]
    connections: tuple[MapConnection, ...]

    @classmethod
    def from_data(cls, data: object, level_ids: tuple[str, ...], valid_secret_exits: set[tuple[str, str]] | None = None) -> "WorldMapDefinition":
        errors: list[str] = []
        if not isinstance(data, dict):
            raise MapDefinitionError("map must be an object")
        raw_nodes = data.get("nodes")
        raw_connections = data.get("connections")
        if not isinstance(raw_nodes, list):
            errors.append("map.nodes must be a list")
            raw_nodes = []
        if not isinstance(raw_connections, list):
            errors.append("map.connections must be a list")
            raw_connections = []
        nodes: dict[str, MapNode] = {}
        represented_levels: set[str] = set()
        for index, raw in enumerate(raw_nodes):
            prefix = f"map.nodes[{index}]"
            if not isinstance(raw, dict):
                errors.append(f"{prefix} must be an object")
                continue
            node_id = raw.get("id")
            try:
                kind = NodeType(raw.get("type"))
            except (TypeError, ValueError):
                errors.append(f"{prefix} has unknown node type")
                continue
            if not isinstance(node_id, str) or not node_id:
                errors.append(f"{prefix}.id must be non-empty")
                continue
            if node_id in nodes:
                errors.append(f"duplicate map node: {node_id}")
                continue
            position = (raw.get("x"), raw.get("y"))
            if not all(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) for value in position):
                errors.append(f"{prefix} has invalid position")
                continue
            level_id = raw.get("level_id")
            if kind is NodeType.LEVEL:
                if level_id not in level_ids:
                    errors.append(f"{prefix} references unknown level: {level_id!r}")
                else:
                    represented_levels.add(level_id)
            elif level_id is not None:
                errors.append(f"{prefix} non-level node cannot reference a level")
            title = raw.get("title", node_id)
            if not isinstance(title, str) or not title:
                errors.append(f"{prefix}.title must be non-empty")
                title = node_id
            nodes[node_id] = MapNode(node_id, kind, (float(position[0]), float(position[1])), title, level_id)
        start = data.get("start_node")
        if start not in nodes or (start in nodes and nodes[start].kind is not NodeType.START):
            errors.append("map.start_node must reference a start node")
        if represented_levels != set(level_ids):
            errors.append("map must represent every registered campaign level exactly once")
        connections: list[MapConnection] = []
        connection_ids: set[str] = set()
        for index, raw in enumerate(raw_connections):
            prefix = f"map.connections[{index}]"
            if not isinstance(raw, dict):
                errors.append(f"{prefix} must be an object")
                continue
            connection_id = raw.get("id")
            source, target = raw.get("from"), raw.get("to")
            if not isinstance(connection_id, str) or not connection_id or connection_id in connection_ids:
                errors.append(f"{prefix} has missing or duplicate id")
                continue
            connection_ids.add(connection_id)
            if source not in nodes or target not in nodes:
                errors.append(f"{prefix} references a missing node")
                continue
            points = raw.get("waypoints", [])
            if not isinstance(points, list) or not all(_point(value) for value in points):
                errors.append(f"{prefix} has malformed waypoint")
                points = []
            unlock = _requirement(raw.get("unlock"), level_ids, prefix, errors, valid_secret_exits)
            if unlock is not None:
                connections.append(MapConnection(connection_id, source, target, tuple((float(p[0]), float(p[1])) for p in points), unlock))
        if not any(node.kind is NodeType.WORLD_GOAL for node in nodes.values()):
            errors.append("map requires a world_goal node")
        if isinstance(start, str):
            reachable = _structurally_reachable(start, connections)
            required = {node.node_id for node in nodes.values() if node.kind in {NodeType.LEVEL, NodeType.WORLD_GOAL}}
            if not required <= reachable:
                errors.append("normal campaign nodes are not structurally reachable from start")
        if errors:
            raise MapDefinitionError("; ".join(errors))
        return cls(str(start), nodes, tuple(connections))


def _point(value: object) -> bool:
    return isinstance(value, list) and len(value) == 2 and all(isinstance(item, (int, float)) and not isinstance(item, bool) and math.isfinite(item) for item in value)


def _requirement(raw: object, level_ids: tuple[str, ...], prefix: str, errors: list[str], valid_secret_exits: set[tuple[str, str]] | None) -> UnlockRequirement | None:
    if not isinstance(raw, dict):
        errors.append(f"{prefix}.unlock must be an object")
        return None
    try:
        kind = RequirementType(raw.get("type"))
    except (TypeError, ValueError):
        errors.append(f"{prefix} has invalid unlock requirement")
        return None
    level_id = raw.get("level_id")
    exit_id = raw.get("exit_id")
    if kind in {RequirementType.LEVEL_COMPLETE, RequirementType.SECRET_EXIT_DISCOVERED} and level_id not in level_ids:
        errors.append(f"{prefix}.unlock references unknown level")
    if kind is RequirementType.SECRET_EXIT_DISCOVERED and (not isinstance(exit_id, str) or not exit_id):
        errors.append(f"{prefix}.unlock requires exit_id")
    elif kind is RequirementType.SECRET_EXIT_DISCOVERED and valid_secret_exits is not None and (level_id, exit_id) not in valid_secret_exits:
        errors.append(f"{prefix}.unlock references unknown secret exit")
    return UnlockRequirement(kind, level_id, exit_id)


def _structurally_reachable(start: str, connections: list[MapConnection]) -> set[str]:
    reached = {start}
    changed = True
    while changed:
        changed = False
        for connection in connections:
            if connection.source in reached and connection.target not in reached:
                reached.add(connection.target)
                changed = True
    return reached


class WorldMapRuntime:
    """Node-to-node travel. Progress remains authoritative in WorldProgress."""

    def __init__(self, definition: WorldMapDefinition, progress: object, travel_speed: float = 360.0) -> None:
        self.definition = definition
        self.progress = progress
        self.current_node_id = definition.start_node
        self.avatar_position = pygame.Vector2(definition.nodes[self.current_node_id].position)
        self.travel_speed = travel_speed
        self._route: list[pygame.Vector2] = []
        self._destination: str | None = None
        self.traversed_connections: set[str] = set()

    @property
    def travelling(self) -> bool:
        return bool(self._route)

    def node_state(self, node_id: str) -> NodeState:
        node = self.definition.nodes[node_id]
        if node.kind is NodeType.START:
            return NodeState.COMPLETED
        if node.kind is NodeType.SECRET and not self._node_has_available_connection(node_id):
            return NodeState.HIDDEN
        if node.kind is NodeType.LEVEL and node.level_id in self.progress.completed_levels_once:
            result = self.progress.results.get(node.level_id)
            return NodeState.MASTERED if result and result.rating is CompletionRating.GOLD else NodeState.COMPLETED
        if node.kind is NodeType.WORLD_GOAL and self.progress.world_completed_once:
            return NodeState.COMPLETED
        return NodeState.AVAILABLE if self._node_has_available_connection(node_id) else NodeState.LOCKED

    def connection_state(self, connection: MapConnection) -> ConnectionState:
        if connection.target in self.definition.nodes and self.definition.nodes[connection.target].kind is NodeType.SECRET and not self._requirement_met(connection.unlock):
            return ConnectionState.HIDDEN
        if not self._requirement_met(connection.unlock):
            return ConnectionState.LOCKED
        return ConnectionState.TRAVERSED if connection.connection_id in self.traversed_connections else ConnectionState.AVAILABLE

    def connections_from_current(self) -> list[MapConnection]:
        return [item for item in self.definition.connections if item.source == self.current_node_id or item.target == self.current_node_id]

    def available_destinations(self) -> list[tuple[MapConnection, str]]:
        result = []
        for connection in self.connections_from_current():
            if self.connection_state(connection) not in {ConnectionState.AVAILABLE, ConnectionState.TRAVERSED}:
                continue
            destination = connection.target if connection.source == self.current_node_id else connection.source
            result.append((connection, destination))
        return result

    def choose_direction(self, direction: pygame.Vector2) -> bool:
        if self.travelling or not direction.length_squared():
            return False
        origin = pygame.Vector2(self.definition.nodes[self.current_node_id].position)
        candidates: list[tuple[float, MapConnection, str]] = []
        for connection, destination in self.available_destinations():
            delta = pygame.Vector2(self.definition.nodes[destination].position) - origin
            if delta.length_squared() and delta.normalize().dot(direction.normalize()) > 0.25:
                candidates.append((delta.normalize().dot(direction.normalize()), connection, destination))
        if not candidates:
            return False
        _, connection, destination = max(candidates, key=lambda item: item[0])
        self._begin_travel(connection, destination)
        return True

    def _begin_travel(self, connection: MapConnection, destination: str) -> None:
        points = list(connection.waypoints)
        if destination == connection.source:
            points.reverse()
        points.append(self.definition.nodes[destination].position)
        self._route = [pygame.Vector2(point) for point in points]
        self._destination = destination
        self.traversed_connections.add(connection.connection_id)

    def update(self, dt: float) -> None:
        distance = self.travel_speed * dt
        while self._route and distance >= 0:
            delta = self._route[0] - self.avatar_position
            segment = delta.length()
            if segment <= distance + 0.0001:
                self.avatar_position.update(self._route.pop(0))
                distance -= segment
                if not self._route and self._destination:
                    self.current_node_id = self._destination
                    self._destination = None
                    return
            else:
                self.avatar_position += delta.normalize() * distance
                return

    def return_to_level_node(self, level_id: str) -> None:
        node = next(item for item in self.definition.nodes.values() if item.level_id == level_id)
        self.current_node_id = node.node_id
        self.avatar_position.update(node.position)
        self._route.clear()
        self._destination = None

    def _node_has_available_connection(self, node_id: str) -> bool:
        if node_id == self.definition.start_node:
            return True
        return any(
            (item.source == node_id or item.target == node_id) and self._requirement_met(item.unlock)
            for item in self.definition.connections
        )

    def _requirement_met(self, requirement: UnlockRequirement) -> bool:
        if requirement.kind is RequirementType.ALWAYS:
            return True
        if requirement.kind is RequirementType.LEVEL_COMPLETE:
            return requirement.level_id in self.progress.completed_levels_once
        if requirement.kind is RequirementType.SECRET_EXIT_DISCOVERED:
            return (requirement.level_id, requirement.exit_id) in self.progress.discovered_secret_exits
        return self.progress.world_completed_once

