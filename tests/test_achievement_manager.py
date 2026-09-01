import json
from pathlib import Path
import pytest
from core.achievement_manager import AchievementManager,AchievementStore,AchievementProfile,PROFILE_SCHEMA_VERSION
from systems.achievement_system import AchievementDataError,load_achievement_definitions
CATALOG=Path("data/achievements/achievements.json")
def manager(tmp_path):return AchievementManager.create(CATALOG,tmp_path/"achievements.json")
def test_catalog_is_valid_stable_and_complete():
 defs=load_achievement_definitions(CATALOG);assert len(defs)==19 and len({x.id for x in defs})==19 and [x.sort_order for x in defs]==sorted(x.sort_order for x in defs)
def test_definition_rejects_unknown_condition_and_duplicate_order(tmp_path):
 raw=json.loads(CATALOG.read_text());raw[0]["condition"]={"type":"python"};p=tmp_path/"bad.json";p.write_text(json.dumps(raw))
 with pytest.raises(AchievementDataError):load_achievement_definitions(p)
 raw=json.loads(CATALOG.read_text());raw[1]["sort_order"]=raw[0]["sort_order"];p.write_text(json.dumps(raw))
 with pytest.raises(AchievementDataError):load_achievement_definitions(p)
def test_unlock_is_idempotent_timestamp_stable_and_persistent(tmp_path):
 m=manager(tmp_path);first=m.emit("ember_shard_collected");assert {x.id for x in first}=={"spark_in_the_dark"};stamp=m.profile.unlocked["spark_in_the_dark"]
 assert m.emit("unrelated")==() and m.profile.unlocked["spark_in_the_dark"]==stamp and len(m.notifications)==1
 loaded=manager(tmp_path);assert loaded.profile.unlocked["spark_in_the_dark"]==stamp and not loaded.notifications
def test_counters_sets_and_multiple_unlocks(tmp_path):
 m=manager(tmp_path)
 for npc in ("mira","mira","orin","talen","vesper"):m.emit("npc_conversation_completed",npc_id=npc)
 assert m.profile.counters["npc_conversations_completed"]==4 and {x.id for x in m.notifications}=={"friendly_voice","four_voices"}
 m.profile.counters["ember_shards_collected"]=99;new=m.emit("ember_shard_collected");assert {x.id for x in new}=={"spark_in_the_dark","ember_gatherer"}
def test_corrupt_and_future_profiles_preserved_and_disabled(tmp_path):
 for content,status in (("{bad","corrupt"),(json.dumps({"schema_version":99}),"unsupported")):
  p=tmp_path/f"{status}.json";p.write_text(content);before=p.read_text();store=AchievementStore(p);m=AchievementManager(load_achievement_definitions(CATALOG),store)
  assert store.status==status and m.profile.unlocked=={} and not store.writable;m.emit("ember_shard_collected");assert p.read_text()==before
def test_disabled_manager_never_reads_or_writes_profile(tmp_path):
 p=tmp_path/"achievements.json";m=AchievementManager.create(CATALOG,p,enabled=False);assert m.emit("ember_shard_collected")==() and not p.exists()
def test_profile_validation_rejects_bad_counter(tmp_path):
 p=tmp_path/"achievements.json";p.write_text(json.dumps({"schema_version":1,"unlocked":{},"progress":{"counters":{"wrong":1},"sets":{},"flags":[]}}));store=AchievementStore(p);store.load({x.id for x in load_achievement_definitions(CATALOG)});assert store.status=="corrupt"
