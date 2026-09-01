from copy import deepcopy
import json
from pathlib import Path
import pytest
from editor.document import EditorDocumentError,LevelDocument
from editor.commands import CommandHistory
from editor.viewport import EditorViewport
from tools.validation import load_and_validate_level
from world.level import Level
LEVELS=("verdant_01","verdant_02","verdant_03","verdant_04","verdant_boss")
@pytest.mark.parametrize("level_id",LEVELS)
def test_existing_level_semantic_round_trip(level_id,tmp_path):
 source=Path("data/levels")/f"{level_id}.json";doc=LevelDocument.load(source);target=tmp_path/f"{level_id}.json";doc.save(target)
 assert json.loads(source.read_text())==json.loads(target.read_text());assert Level.load(target).metadata.level_id==level_id

def test_unknown_field_preserved(tmp_path):
 data=json.loads(Path("data/levels/verdant_01.json").read_text());data["future_extension"]={"keep":[1,2,3]};doc=LevelDocument(data);assert doc.data["future_extension"]["keep"]==[1,2,3]
 # Authoritative validator currently accepts forward-compatible root extensions.
 target=tmp_path/"verdant_01.json";doc.save(target);assert json.loads(target.read_text())["future_extension"]=={"keep":[1,2,3]}

def test_new_document_tile_rectangle_counts_and_validation():
 doc=LevelDocument.new("test_level");assert not doc.validate();doc.rectangle((2,2),(4,3),5);grid=doc.tile_grid();assert all(grid[y][x]==5 for y in (2,3) for x in (2,3,4));assert doc.dirty

def test_commands_undo_redo_history_and_divergence():
 doc=LevelDocument.new("test_level");history=CommandHistory(2);history.execute(doc,"paint",lambda:doc.set_tiles({(1,1):3}));history.execute(doc,"erase",lambda:doc.set_tiles({(1,1):0}));assert history.undo(doc) and doc.tile_grid()[1][1]==3;assert history.redo(doc) and doc.tile_grid()[1][1]==0;history.undo(doc);history.execute(doc,"new",lambda:doc.set_tiles({(2,2):4}));assert not history.redo(doc)

def test_object_add_duplicate_delete_and_id_integrity():
 doc=LevelDocument.new("test_level");item=doc.add_object({"type":"ember_shard","x":200,"y":200});copy=doc.duplicate_selected();assert item["id"]!=copy["id"];assert doc.remove_selected();assert len(doc.data["objects"])==1

def test_resize_refuses_out_of_bounds_object():
 doc=LevelDocument.new("test_level",30,12);doc.add_object({"id":"far","type":"ember_shard","x":1800,"y":200})
 with pytest.raises(EditorDocumentError):doc.resize(20,12)

def test_coordinate_transforms_zoom_and_pan():
 view=EditorViewport(origin_x=100,origin_y=50,zoom=.5);screen=view.world_to_screen((300,250));assert view.screen_to_world(screen)==pytest.approx((300,250));assert view.screen_to_tile(screen,64)==(4,3);view.step_zoom(1,screen);assert view.screen_to_world(screen)==pytest.approx((300,250));view.pan(50,25);assert view.origin_x>100

def test_invalid_save_never_overwrites_existing(tmp_path):
 target=tmp_path/"test_level.json";good=LevelDocument.new("test_level");good.save(target);before=target.read_text();good.data["player_spawn"]=[-1,-1]
 with pytest.raises(EditorDocumentError):good.save(target)
 assert target.read_text()==before
