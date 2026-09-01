"""Repeatable Phase 23 headless runtime/editor performance scenarios."""
from __future__ import annotations
import argparse,json,os,statistics,time,tracemalloc
from pathlib import Path
os.environ.setdefault("SDL_VIDEODRIVER","dummy");os.environ.setdefault("SDL_AUDIODRIVER","dummy")
from settings import PROJECT_ROOT

SCENARIOS=("quiet","busy","boss","boss_phase3","boss_defeat","effects","editor")

def metrics(samples:list[float],frames:int,memory:dict|None=None)->dict:
 ordered=sorted(samples)
 def percentile(p):return ordered[min(len(ordered)-1,max(0,int(len(ordered)*p)-1))]
 result={"frames":frames,"mean_ms":statistics.mean(samples),"median_ms":statistics.median(samples),"p95_ms":percentile(.95),"p99_ms":percentile(.99),"max_ms":ordered[-1],"spikes_16_67":sum(x>16.67 for x in samples),"spikes_25":sum(x>25 for x in samples),"spikes_33_3":sum(x>33.3 for x in samples)}
 if memory:result["memory_bytes"]=memory
 return result

def _game_scenario(name:str,frames:int,memory:bool)->dict:
 from core.game import Game
 level={"quiet":"verdant_01","busy":"verdant_04"}.get(name,"verdant_boss")
 game=Game(level_id=level,debug_enabled=False,achievements_enabled=False,persistence=False)
 try:
  if name=="busy":
   enemies=game.enemies.enemies
   if enemies:game.player.reposition((enemies[len(enemies)//2].rect.x-120,enemies[len(enemies)//2].rect.y));game.camera.snap_to(game.player.rect)
  elif name.startswith("boss"):
   trigger=game.boss_system.definition.trigger;game.player.reposition((trigger.centerx,trigger.bottom-game.player.rect.height));game.camera.snap_to(game.player.rect);game.update(1/60)
   if name=="boss_phase3":
    boss=game.boss_system.boss;boss.health=max(1,boss.config.phases[-1].minimum_health);boss.phase=boss.config.phase_for_health(boss.health)
   elif name=="boss_defeat":
    game.effects.spawn("enemy_defeat",game.boss_system.boss.rect.center,count_scale=2.0)
  elif name=="effects":
   for _ in range(20):game.effects.spawn("enemy_defeat",game.player.rect.center)
  if memory:tracemalloc.start()
  samples=[]
  for _ in range(frames):
   start=time.perf_counter();game.update(1/60);game.draw();samples.append((time.perf_counter()-start)*1000)
  mem=None
  if memory:
   current,peak=tracemalloc.get_traced_memory();tracemalloc.stop();mem={"current":current,"peak":peak}
  result=metrics(samples,frames,mem);result["particles_peak_observed"]=game.effects.particle_count;result["projectiles_final"]=len(game.projectiles.projectiles);return result
 finally:game.shutdown()

def _editor_scenario(frames:int,memory:bool)->dict:
 from tools.level_editor import LevelEditor
 editor=LevelEditor("verdant_03")
 try:
  if memory:tracemalloc.start()
  samples=[]
  for frame in range(frames):
   if frame%60==0:editor.view.pan(96 if (frame//60)%2==0 else -96,24)
   start=time.perf_counter();editor.draw();samples.append((time.perf_counter()-start)*1000)
  mem=None
  if memory:
   current,peak=tracemalloc.get_traced_memory();tracemalloc.stop();mem={"current":current,"peak":peak}
  return metrics(samples,frames,mem)
 finally:
  import pygame;pygame.quit()

def run(name:str,frames:int,memory:bool=False)->dict:return _editor_scenario(frames,memory) if name=="editor" else _game_scenario(name,frames,memory)
def compare(current:dict,baseline:dict)->dict:
 result={}
 for scenario,values in current.items():
  if scenario not in baseline:continue
  result[scenario]={key:values[key]-baseline[scenario][key] for key in ("mean_ms","p95_ms","max_ms","spikes_16_67","spikes_25","spikes_33_3")}
 return result
def main()->None:
 parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True);group.add_argument("--scenario",choices=SCENARIOS);group.add_argument("--all",action="store_true");parser.add_argument("--frames",type=int,default=600);parser.add_argument("--output",type=Path);parser.add_argument("--compare",type=Path);parser.add_argument("--memory",action="store_true");args=parser.parse_args();frames=max(30,args.frames);names=SCENARIOS if args.all else (args.scenario,);results={name:run(name,frames,args.memory) for name in names}
 for name,data in results.items():print(f"{name:12} frames={frames} mean={data['mean_ms']:.3f} median={data['median_ms']:.3f} p95={data['p95_ms']:.3f} p99={data['p99_ms']:.3f} max={data['max_ms']:.3f} spikes={data['spikes_16_67']}/{data['spikes_25']}/{data['spikes_33_3']}")
 payload={"environment":{"driver":os.environ.get("SDL_VIDEODRIVER"),"resolution":"1280x720","note":"Headless dummy SDL; compare only on the same host."},"scenarios":results}
 if args.compare:
  baseline=json.loads(args.compare.read_text());payload["comparison"]=compare(results,baseline.get("scenarios",baseline));print(json.dumps(payload["comparison"],indent=2))
 if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n")
if __name__=="__main__":main()
