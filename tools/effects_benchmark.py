"""Repeatable 600-frame Phase 15 particle performance scenarios."""
from __future__ import annotations
import argparse, os, statistics, time, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("SDL_VIDEODRIVER","dummy"); os.environ.setdefault("SDL_AUDIODRIVER","dummy")
import pygame
from systems.effects_system import EffectsSystem
FRAMES=600; DT=1/60

def run(scenario:str)->dict[str,float|int]:
    pygame.init(); surface=pygame.Surface((1280,720)); view=pygame.Rect(0,0,1280,720); fx=EffectsSystem(seed=1515)
    if scenario in {"normal","stress"}: fx.start_emitter("leaves","drifting_leaves",(0,0),region=view); fx.start_emitter("pollen","pollen_motes",(0,0),region=view)
    else: fx.start_emitter("sanctum","sanctum_motes",(0,0),region=view)
    timings=[]; peak=0
    for frame in range(FRAMES):
        if scenario=="normal" and frame%90==0: fx.spawn("ember_shard_pickup",(640,360))
        elif scenario=="stress":
            fx.spawn("enemy_hit",(frame%1280,360)); fx.spawn("ember_pulse_impact",(640,frame%720));
            if frame%30==0: fx.spawn("enemy_defeat",(640,360))
        elif scenario=="phase3" and frame%45==0:
            fx.spawn("warden_ground_slam",(640,600)); fx.spawn("warden_bolt_launch",(640,280)); fx.spawn("warden_core_burst",(640,360))
        elif scenario=="defeat" and frame in {0,180,360}: fx.spawn("warden_defeat",(640,360))
        start=time.perf_counter(); fx.update(DT,view); fx.draw_world(surface,(0,0),view); fx.draw_screen(surface); timings.append((time.perf_counter()-start)*1000); peak=max(peak,fx.particle_count)
    pygame.quit(); ordered=sorted(timings)
    return {"mean_ms":statistics.mean(timings),"p95_ms":ordered[int(len(ordered)*.95)-1],"max_ms":max(timings),"peak_particles":peak,"peak_emitters":fx.emitter_count}

def main()->None:
    parser=argparse.ArgumentParser(); parser.add_argument("scenario",choices=("normal","stress","phase3","defeat")); args=parser.parse_args()
    result=run(args.scenario); print(args.scenario," ".join(f"{k}={v:.3f}" if isinstance(v,float) else f"{k}={v}" for k,v in result.items()))
if __name__=="__main__": main()
