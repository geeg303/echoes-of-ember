from __future__ import annotations
import json
from pathlib import Path
import pygame
import pytest
from core.input_manager import Action
from systems.dialogue_system import DialogueDataError, DialogueSystem, load_dialogue
from systems.npc_system import NPCDataError, NPCSystem, load_npc_catalog
from world.campaign import DEFAULT_WORLD_REGISTRY, WorldProgress, WorldRegistry

@pytest.fixture
def progress(): return WorldProgress(WorldRegistry.load(DEFAULT_WORLD_REGISTRY))

def write_dialogue(path: Path, **changes):
 data={"id":"test_talk","start":"start","nodes":[{"id":"start","type":"line","speaker":"Mira","text":"A long greeting.","next":"choice"},{"id":"choice","type":"choice","speaker":"Mira","text":"Choose.","responses":[{"label":"Yes","target":"end"}]},{"id":"end","type":"end","speaker":"Mira","text":"Done.","effects":[{"type":"set_flag","value":"met_test"}]}]}
 data.update(changes);path.write_text(json.dumps(data));return path

def test_authored_dialogues_and_npcs_validate(progress):
 root=Path("data"); system,definitions=NPCSystem.load(root,"verdant_01",progress,(6912,1152))
 assert len(definitions)==15 and [n.display_name for n in system.npcs]==["Mira"]
 for level in ("verdant_02","verdant_03","verdant_04"):
  loaded,_=NPCSystem.load(root,level,progress,(9000,1400));assert len(loaded.npcs)==1

def test_graph_rejects_unknown_targets_conditions_effects_and_unreachable(tmp_path):
 path=write_dialogue(tmp_path/"talk.json")
 data=json.loads(path.read_text());data["nodes"][0]["next"]="missing";path.write_text(json.dumps(data))
 with pytest.raises(DialogueDataError):load_dialogue(path)
 path=write_dialogue(path);data=json.loads(path.read_text());data["nodes"][2]["effects"]=[{"type":"grant_powerup","value":"ember"}];path.write_text(json.dumps(data))
 with pytest.raises(DialogueDataError):load_dialogue(path)
 path=write_dialogue(path);data=json.loads(path.read_text());data["nodes"].append({"id":"lost","type":"end","text":"Lost"});path.write_text(json.dumps(data))
 with pytest.raises(DialogueDataError):load_dialogue(path)

def test_typewriter_choices_completion_and_flag_callback(tmp_path,progress):
 definition=load_dialogue(write_dialogue(tmp_path/"talk.json"));flags=[];dialogue=DialogueSystem({definition.dialogue_id:definition},progress,flags.append,text_rate=10)
 assert dialogue.start("test_talk","mira")
 assert dialogue.handle(Action.CONFIRM)=="reveal"
 assert dialogue.handle(Action.CONFIRM)=="advance"
 dialogue.handle(Action.CONFIRM);assert dialogue.handle(Action.CONFIRM)=="choice"
 dialogue.handle(Action.CONFIRM);assert dialogue.handle(Action.CONFIRM)=="close"
 assert progress.dialogue_flags=={"met_test"} and flags==["met_test"] and not dialogue.active

def test_back_closes_optional_dialogue(tmp_path,progress):
 d=load_dialogue(write_dialogue(tmp_path/"talk.json"));runtime=DialogueSystem({d.dialogue_id:d},progress);runtime.start(d.dialogue_id,"mira")
 assert runtime.handle(Action.BACK)=="close" and not runtime.active

def test_npc_catalog_rejects_bounds_unknown_dialogue_and_bad_condition(tmp_path):
 base=[{"id":"mira_test","level_id":"verdant_01","position":[10,20],"dialogues":[{"dialogue_id":"known","conditions":[]}]}]
 path=tmp_path/"npcs.json";path.write_text(json.dumps(base));assert len(load_npc_catalog(path,"verdant_01",{"known"},(100,100)))==1
 base[0]["position"]=[101,20];path.write_text(json.dumps(base))
 with pytest.raises(NPCDataError):load_npc_catalog(path,"verdant_01",{"known"},(100,100))
 base[0]["position"]=[10,20];base[0]["dialogues"][0]["conditions"]=[{"type":"flag","value":"BAD FLAG"}];path.write_text(json.dumps(base))
 with pytest.raises(NPCDataError):load_npc_catalog(path,"verdant_01",{"known"})

def test_nearest_npc_variant_selection_and_range(progress):
 system,defs=NPCSystem.load(Path("data"),"verdant_01",progress,(6912,1152));npc=system.npcs[0]
 assert system.choose_dialogue(npc)=="mira_intro"
 progress.dialogue_flags.add("met_mira");assert system.choose_dialogue(npc)=="mira_repeat"
 near=pygame.Rect(npc.rect.x,npc.rect.y,44,62);far=pygame.Rect(2000,100,44,62)
 assert system.nearest(near) is npc and system.nearest(far) is None
