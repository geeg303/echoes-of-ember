"""Compact multi-page overlay, command palette, and world diagnostics rendering."""
from __future__ import annotations
import pygame
from debug.snapshot import DebugSnapshot

PAGES=("SUMMARY","PLAYER","WORLD","ENTITIES","BOSS","INPUT","AUDIO","EFFECTS","PROGRESSION","PERFORMANCE")
COLORS={"player":(64,220,255),"enemy":(255,82,111),"projectile":(255,205,74),"terrain":(86,231,132),"trigger":(201,107,255),"platform":(71,193,210),"camera":(255,255,255)}

class DebugOverlay:
    def __init__(self,font:pygame.font.Font,small:pygame.font.Font|None=None):self.font=font;self.small=small or font
    def draw(self,surface:pygame.Surface,snapshot:DebugSnapshot,page:str,manager:object)->None:
        lines=self._lines(snapshot,page,manager); width=min(500,max(330,max((self.font.size(x)[0] for x in lines),default=0)+28));height=38+len(lines)*21
        panel=pygame.Surface((width,height),pygame.SRCALPHA);panel.fill((7,10,22,218));pygame.draw.rect(panel,(76,177,217),panel.get_rect(),2,border_radius=7)
        title=self.font.render(f"DEBUG · {page}",True,(118,223,255));panel.blit(title,(12,8))
        for i,line in enumerate(lines):panel.blit(self.small.render(line,True,(224,232,244)),(12,34+i*21))
        surface.blit(panel,(12,12))
        if getattr(manager,"god_mode",False):self._badge(surface,"GOD MODE",(239,78,87),surface.get_width()-18,18)
        if getattr(manager,"simulation_paused",False):self._badge(surface,"DEBUG PAUSED",(255,177,66),surface.get_width()-18,52)
        scale=getattr(manager,"time_scale",1.0)
        if scale!=1.0:self._badge(surface,f"TIME SCALE {scale:g}x",(170,125,255),surface.get_width()-18,86)
        if getattr(manager,"tainted",False):self._badge(surface,"NONPERSISTENT · TAINTED",(240,139,72),surface.get_width()-18,120)
    def _badge(self,surface,text,color,right,top):
        image=self.font.render(text,True,(255,255,255));rect=image.get_rect(topright=(right,top));bg=rect.inflate(18,10);pygame.draw.rect(surface,(*color,220),bg,border_radius=5);surface.blit(image,rect)
    def _lines(self,s,page,m):
        p=s.player;perf=s.performance
        if page=="SUMMARY":return [f"FPS {perf.get('fps',0):5.1f}   FRAME {perf.get('frame_ms',0):5.2f} ms",f"MODE {s.app_mode}   LEVEL {s.level_id}",f"PLAYER {p.get('position')}  VEL {p.get('velocity')}",f"HP {p.get('health')}/{p.get('max_health')}  LIVES {p.get('lives')}  GROUND {p.get('grounded')}",f"CAMERA {s.camera.get('position')}",f"ENEMIES {s.entities.get('enemies')}  SHOTS {s.entities.get('projectiles')}  FX {s.effects.get('particles')}",f"CHECKPOINT {s.world.get('current_checkpoint')}  INPUT {s.input.get('device')}",f"SLOT {s.progression.get('slot') or '-'}  ACH QUEUE {s.progression.get('achievement_queue')}"]
        if page=="PLAYER":return [f"POS {p.get('position')}  COLLIDER {p.get('bounds')}",f"VEL {p.get('velocity')}  FACING {p.get('facing')}",f"GROUND {p.get('grounded')}  DEAD {p.get('dead')}",f"COYOTE {p.get('coyote')}  BUFFER {p.get('jump_buffer')}",f"INVULN {p.get('invulnerability')}",f"HP {p.get('health')}/{p.get('max_health')}  LIVES {p.get('lives')}",f"POWER {p.get('powerup')}  {p.get('powerup_timer')}s  GUARD {p.get('stone_guard')}",f"ANIM {p.get('animation')}  FRAME {p.get('frame')}"]
        if page=="WORLD":return [f"SIZE {s.world.get('dimensions')}  TILE {s.world.get('tile')}",f"CAMERA {s.camera.get('position')}  VIEW {s.camera.get('view')}",f"CAMERA BOUNDS {s.camera.get('bounds')}",f"GOAL {s.world.get('goal')}",f"CHECKPOINTS {s.world.get('checkpoints')}  CURRENT {s.world.get('current_checkpoint')}",f"PLATFORMS {s.world.get('platforms')}  NPCS {s.world.get('npcs')}",f"SECRETS {s.world.get('secrets')}  TIME {s.world.get('timer')}",f"PHASE {s.world.get('phase')}"]
        if page=="ENTITIES":return [f"ENEMIES {s.entities.get('enemies')}: {s.entities.get('enemies_by_type')}",f"PROJECTILES {s.entities.get('projectiles')}: {s.entities.get('projectiles_by_faction')}",f"COLLECTIBLES LEFT {s.entities.get('collectibles_remaining')}",f"POWERUPS LEFT {s.entities.get('powerups_remaining')}",f"PLATFORMS {s.entities.get('platforms')}  NPCS {s.entities.get('npcs')}",f"PARTICLES {s.entities.get('particles')}"]
        if page=="BOSS":
            b=s.boss
            return ["No active boss."] if not b.get("id") else [f"{b.get('name')} [{b.get('id')}]",f"HP {b.get('health')}/{b.get('max_health')}  PHASE {b.get('phase')}",f"STATE {b.get('state')}  TIMER {b.get('state_timer')}",f"ATTACK {b.get('attack')}  PREVIOUS {b.get('previous_attack')}",f"VULNERABLE {b.get('vulnerable')}  ARENA {b.get('arena_locked')}",f"DEFEATED {b.get('defeated')}"]
        if page=="INPUT":return [f"DEVICE {s.input.get('device')}  CONTROLLERS {s.input.get('controllers')}",f"NAME {s.input.get('controller')}",f"MOVE AXIS {s.input.get('move_axis')}  DEADZONE {s.input.get('deadzone')}",f"HELD {s.input.get('held')}",f"PRESSED {s.input.get('pressed')}"]
        if page=="AUDIO":return [f"AVAILABLE {s.audio.get('available')}  MUTED {s.audio.get('muted')}",f"MUSIC {s.audio.get('music')}",f"AMBIENCE {s.audio.get('ambience')}",f"CHANNELS {s.audio.get('channels')}",f"RECENT {s.audio.get('recent')}"]
        if page=="EFFECTS":return [f"QUALITY {s.effects.get('quality')}",f"PARTICLES {s.effects.get('particles')}/{s.effects.get('cap')}",f"EMITTERS {s.effects.get('emitters')}",f"SCREEN EFFECTS {s.effects.get('screen')}"]
        if page=="PROGRESSION":return [f"SLOT {s.progression.get('slot') or '-'}  NONPERSISTENT {s.progression.get('debug_nonpersistent')}",f"CAMPAIGN SCHEMA {s.progression.get('campaign_schema')}",f"COMPLETED LEVELS {s.progression.get('completed_levels')}",f"BOSSES {s.progression.get('bosses')}  FLAGS {s.progression.get('dialogue_flags')}",f"ACHIEVEMENTS {s.progression.get('achievements')}  SCHEMA {s.progression.get('achievement_schema')}",f"DIALOGUE {s.progression.get('dialogue') or '-'}"]
        summary=getattr(m,"profiler",None).summary() if getattr(m,"profiler",None) else {}
        result=[f"FPS {perf.get('fps',0):.1f}  FRAME {perf.get('frame_ms',0):.3f} ms",f"UPDATE {perf.get('update_ms',0):.3f} ms  RENDER {perf.get('render_ms',0):.3f} ms"]
        for name in ("frame","update","render"):
            x=summary.get(name,{})
            result.append(f"{name.upper():6} now {x.get('current',0):6.2f} mean {x.get('mean',0):6.2f} p95 {x.get('p95',0):6.2f} max {x.get('max',0):6.2f}")
        result.extend((f"SPIKES {summary.get('spike_counts',{})}",f"LAST {summary.get('last_spike')}"));return result
    def draw_palette(self,surface,manager):
        h=164;panel=pygame.Surface((surface.get_width()-32,h),pygame.SRCALPHA);panel.fill((4,7,17,238));pygame.draw.rect(panel,(130,98,220),panel.get_rect(),2,border_radius=7)
        panel.blit(self.font.render("> "+manager.command_text,True,(255,244,186)),(14,12))
        for i,line in enumerate(tuple(manager.command_output)[-5:]):panel.blit(self.small.render(line,True,(205,217,236)),(14,43+i*21))
        surface.blit(panel,(16,surface.get_height()-h-16))
    def draw_inspector(self,surface,selected):
        if not selected:return
        lines=[f"INSPECT {selected.get('type','object').upper()}"]+[f"{k}: {v}" for k,v in selected.items() if k!="type"]
        width=min(430,max(self.small.size(x)[0] for x in lines)+22);panel=pygame.Surface((width,12+len(lines)*20),pygame.SRCALPHA);panel.fill((8,12,25,222));pygame.draw.rect(panel,(255,205,83),panel.get_rect(),2)
        for i,line in enumerate(lines):panel.blit(self.small.render(line,True,(240,235,214)),(10,7+i*20))
        surface.blit(panel,(surface.get_width()-width-12,surface.get_height()-panel.get_height()-12))
