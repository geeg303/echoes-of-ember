"""Builders for throwaway multi-world campaigns used by tests (real World 1 data + a tiny fake World 2)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from settings import PROJECT_ROOT

SOURCE = PROJECT_ROOT / "data"
WORLD_2 = "glassreach_test"


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1), encoding="utf-8")


def world_2_map(extra_nodes: list | None = None, extra_connections: list | None = None) -> dict:
    return {
        "start_node": "glass_landing",
        "nodes": [
            {"id": "glass_landing", "type": "start", "title": "Glass Landing", "x": 140, "y": 470},
            {"id": "node_glass_01", "type": "level", "level_id": "glass_01", "title": "2-1 Test", "x": 400, "y": 400},
            {
                "id": "glass_vault",
                "type": "boss",
                "level_id": "glass_boss",
                "boss_id": "glass_sentinel",
                "title": "BOSS  Test Vault",
                "x": 800,
                "y": 300,
            },
            {"id": "glass_goal", "type": "world_goal", "title": "Glass Goal", "x": 1100, "y": 150},
            *(extra_nodes or []),
        ],
        "connections": [
            {"id": "landing_to_01", "from": "glass_landing", "to": "node_glass_01", "unlock": {"type": "always"}},
            {
                "id": "g01_to_vault",
                "from": "node_glass_01",
                "to": "glass_vault",
                "unlock": {"type": "level_complete", "level_id": "glass_01"},
            },
            {
                "id": "vault_to_goal",
                "from": "glass_vault",
                "to": "glass_goal",
                "unlock": {"type": "boss_defeated", "boss_id": "glass_sentinel"},
            },
            *(extra_connections or []),
        ],
    }


def build_two_world_campaign(
    root: Path,
    world_order: tuple[str, ...] = ("verdant_reaches", WORLD_2),
    verdant_map_edit=None,
    world_2_map_data: dict | None = None,
) -> Path:
    """Copy real World 1 content and add a two-stage fake World 2. Returns the campaign.json path."""
    data = root / "data"
    for folder in ("levels", "bosses", "worlds", "dialogue", "npcs"):
        shutil.copytree(SOURCE / folder, data / folder, dirs_exist_ok=True)
    for source_id, new_id, number in (("verdant_01", "glass_01", 1), ("verdant_boss", "glass_boss", 2)):
        level = _read(SOURCE / "levels" / f"{source_id}.json")
        level.update(id=new_id, world_id=WORLD_2, level_number=number, theme="glassreach")
        level["name"] = f"Glassreach Test — {new_id}"
        if "boss_encounter" in level:
            level["boss_encounter"]["boss_id"] = "glass_sentinel"
        _write(data / "levels" / f"{new_id}.json", level)
    boss = _read(SOURCE / "bosses" / "ashen_warden.json")
    boss.update(id="glass_sentinel", display_name="The Glass Sentinel")
    _write(data / "bosses" / "glass_sentinel.json", boss)
    verdant = _read(SOURCE / "worlds" / "verdant_reaches.json")
    if verdant_map_edit is not None:
        verdant_map_edit(verdant["map"])
    _write(data / "worlds" / "verdant_reaches.json", verdant)
    _write(
        data / "worlds" / f"{WORLD_2}.json",
        {
            "id": WORLD_2,
            "display_name": "Glassreach Test",
            "map_theme": "glassreach",
            "levels": ["glass_01", "glass_boss"],
            "map": world_2_map_data or world_2_map(),
        },
    )
    campaign = data / "campaign.json"
    _write(campaign, {"worlds": list(world_order)})
    return campaign
