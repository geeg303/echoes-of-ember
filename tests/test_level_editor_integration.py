import os
os.environ.setdefault("SDL_VIDEODRIVER","dummy");os.environ.setdefault("SDL_AUDIODRIVER","dummy")
from pathlib import Path
from editor.document import LevelDocument
from editor.palette import OBJECT_TYPES,object_template,secret_template,npc_template
from tools.level_editor import LevelEditor
from tools.validation import load_and_validate_level
from world.level import Level

def test_all_object_families_author_and_load(tmp_path):
 doc=LevelDocument.new("editor_test",40,16);x=200
 kinds=("ember_shard","rare_crystal","secret_token","health_item","crawler","flyer","jumper","turret","armored","ember_pulse","wind_boots","aether_wing","stone_guard","checkpoint","moving_horizontal","moving_vertical","falling_platform","disappearing_platform")
 for kind in kinds:
  item=object_template(kind,x,600);item["id"]=doc.unique_id(kind);doc.add_object(item);x+=70
 door=object_template("door",2200,600);door["id"]="door_01";doc.add_object(door);switch=object_template("switch",2100,600);switch["id"]="switch_01";doc.add_object(switch)
 for kind in ("secret_cache","secret_room","alternate_route","secret_exit"):
  item=secret_template(kind,500,300);item["id"]=doc.unique_id(kind);doc.add_object(item,"secrets")
 doc.add_object(npc_template("editor_test",300,600),"npcs");target=tmp_path/"data"/"levels"/"editor_test.json";doc.save(target);assert load_and_validate_level(target)["id"]=="editor_test"
 loaded=Level.load(target);assert len(loaded.enemy_spawns)==5 and len(loaded.powerup_spawns)==4 and len(loaded.secret_definitions)==4
 assert (tmp_path/"data"/"npcs"/"editor_test.json").exists()

def test_editor_headless_startup_pan_zoom_and_render():
 editor=LevelEditor("verdant_04");editor.run(frames=3)

def test_unsaved_playtest_preserves_document_and_profiles(tmp_path):
 editor=LevelEditor("verdant_01");editor.document.set_tiles({(5,5):4});before=editor.document.snapshot();editor.playtest();after=editor.document.snapshot();assert before==after and editor.document.dirty
