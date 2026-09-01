from copy import deepcopy
import pytest
from systems.save_data import CURRENT_SAVE_VERSION, SaveSession, SaveValidationError
from world.campaign import DEFAULT_WORLD_REGISTRY, WorldRegistry

def test_dialogue_flags_round_trip_and_v2_migration():
 registry=WorldRegistry.load(DEFAULT_WORLD_REGISTRY);session=SaveSession.fresh(1,registry);session.progress.dialogue_flags={"met_mira","vesper_secret_hint"};raw=session.to_dict()
 loaded=SaveSession.from_dict(raw,registry,1);assert loaded.progress.dialogue_flags==session.progress.dialogue_flags
 legacy=deepcopy(raw);legacy["schema_version"]=2;legacy["campaign"]["progression"].pop("dialogue_flags")
 migrated=SaveSession.from_dict(legacy,registry,1);assert migrated.progress.dialogue_flags==set() and CURRENT_SAVE_VERSION==3

def test_dialogue_flags_reject_duplicates_and_invalid_values():
 registry=WorldRegistry.load(DEFAULT_WORLD_REGISTRY);raw=SaveSession.fresh(1,registry).to_dict();progress=raw["campaign"]["progression"]
 for flags in (["met_mira","met_mira"],["BAD FLAG"],"met_mira"):
  progress["dialogue_flags"]=flags
  with pytest.raises(SaveValidationError):SaveSession.from_dict(raw,registry,1)
