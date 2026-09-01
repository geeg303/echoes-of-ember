"""Repeatable headless Phase 22 integrated debug-overhead benchmark."""
from __future__ import annotations
import argparse,os,statistics,time
os.environ.setdefault("SDL_VIDEODRIVER","dummy");os.environ.setdefault("SDL_AUDIODRIVER","dummy")
from core.game import Game

def run(mode:str,frames:int=300)->dict[str,float]:
 game=Game(level_id="verdant_boss",debug_enabled=mode!="off",achievements_enabled=False,persistence=False)
 try:
  if mode!="off":
   game.debug.overlay_visible=True
   if mode=="collision":game.debug.collision_visible=True
   elif mode=="triggers":game.debug.triggers_visible=True
   elif mode=="performance":game.debug.page_index=9
  game.player.reposition((game.boss_system.definition.trigger.centerx,game.boss_system.definition.trigger.bottom-game.player.rect.height))
  samples=[]
  for _ in range(frames):
   started=time.perf_counter();game.update(1/60);game.draw();samples.append((time.perf_counter()-started)*1000)
  ordered=sorted(samples);return {"mean_ms":statistics.mean(samples),"p95_ms":ordered[int(len(ordered)*.95)-1],"max_ms":max(samples)}
 finally:game.shutdown()

def main():
 parser=argparse.ArgumentParser();parser.add_argument("mode",choices=("off","summary","collision","triggers","performance"));parser.add_argument("--frames",type=int,default=300);args=parser.parse_args();result=run(args.mode,max(30,args.frames));print(args.mode," ".join(f"{k}={v:.3f}" for k,v in result.items()))
if __name__=="__main__":main()
