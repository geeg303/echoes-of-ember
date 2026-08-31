"""Generate original temporary WAV cues, loops, music, and ambience."""
from __future__ import annotations
import argparse, json, math, random, struct, wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; RATE=22050

def seed_for(name:str)->int:return sum((i+1)*ord(c) for i,c in enumerate(name))
def envelope(t:float,duration:float,loop:bool)->float:
    if loop:return min(1,t/.12,(duration-t)/.12)
    return min(1,t/.012,max(0,(duration-t)/min(.12,duration*.35)))
def write(path:Path,name:str,duration:float,kind:str)->None:
    rng=random.Random(seed_for(name)); base=150+seed_for(name)%430; count=int(RATE*duration); loop=kind in {'music','ambience'}; frames=bytearray()
    notes=(1,1.25,1.5,2) if kind=='music' else (1,)
    for i in range(count):
        t=i/RATE; env=envelope(t,duration,loop); note=notes[int(t/.75)%len(notes)]; phase=2*math.pi*base*note*t
        if kind=='ambience': sample=.07*math.sin(phase*.17)+.035*(rng.random()*2-1)
        elif kind=='music': sample=.11*math.sin(phase)+.055*math.sin(phase*.5)+.035*math.sin(phase*1.5)
        elif any(word in name for word in ('slam','break','damage','defeat','block','door')): sample=.18*(rng.random()*2-1)*math.exp(-t*7)+.10*math.sin(phase*.5)
        else: sample=.16*math.sin(phase)+.06*math.sin(phase*2.01)
        value=max(-32767,min(32767,round(sample*env*32767))); frames.extend(struct.pack('<h',value))
    path.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(path),'wb') as out:out.setnchannels(1); out.setsampwidth(2); out.setframerate(RATE); out.writeframes(frames)
def main()->None:
    parser=argparse.ArgumentParser(); parser.add_argument('--force',action='store_true'); args=parser.parse_args(); catalog=json.loads((ROOT/'data/audio/audio.json').read_text())
    generated=0
    for item in catalog['sounds']:
        path=ROOT/'assets'/item['path']; kind='ambience' if item['category']=='ambience' else 'sfx'; duration=4 if kind=='ambience' else (.65 if item['priority']>=3 else .28)
        if args.force or not path.exists():write(path,item['id'],duration,kind); generated+=1
    for item in catalog['music']:
        path=ROOT/'assets'/item['path']
        if args.force or not path.exists():write(path,item['id'],6,'music'); generated+=1
    print(f'generated {generated} original placeholder WAV files')
if __name__=='__main__':main()
