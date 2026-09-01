"""Validator-compatible object templates for the editor palette."""
from copy import deepcopy
OBJECT_TYPES=("spawn","goal","npc","secret_cache","secret_room","challenge_room","alternate_route","secret_exit","ember_shard","rare_crystal","secret_token","health_item","crawler","flyer","jumper","turret","armored","ember_pulse","wind_boots","aether_wing","stone_guard","checkpoint","moving_horizontal","moving_vertical","falling_platform","disappearing_platform","switch","door")
def object_template(kind,x,y):
 base={"id":"","type":kind,"x":x,"y":y}
 if kind in {"crawler","flyer","jumper","turret","armored"}:base.update(type="enemy",enemy_type=kind,properties={})
 elif kind in {"ember_pulse","wind_boots","aether_wing","stone_guard"}:base.update(type="powerup",powerup_type=kind)
 elif kind.startswith("moving_"):base.update(type="moving_platform",properties={"movement":kind.split('_')[1],"distance":256,"speed":90})
 elif kind=="falling_platform":base["properties"]={"activation_delay":.7,"fall_acceleration":1450,"reset_delay":3}
 elif kind=="disappearing_platform":base["properties"]={"visible_duration":2.3,"warning_duration":.7,"hidden_duration":1.5}
 elif kind=="switch":base["properties"]={"target_id":"door_01"}
 elif kind=="door":base["properties"]={"width":48,"height":128,"opening_duration":.55}
 return base
SECRET_TYPES=("secret_cache","secret_room","challenge_room","alternate_route","secret_exit")
def secret_template(kind,x,y):return {"id":"","secret_type":kind,"properties":{"trigger_type":"interact" if kind=="secret_exit" else "enter_region","bounds":[x,y,256,192],"clue":"Editor-authored discovery"}}
def npc_template(level_id,x,y):return {"id":"","display_name":"Mira","level_id":level_id,"position":[x,y],"interaction_radius":82,"style":"mira","facing":"right","dialogues":[{"dialogue_id":"mira_repeat","priority":10,"conditions":[]}]}
