import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame
import pytest
from effects import EFFECT_DEFINITIONS, EffectPriority, EffectSpace, Particle
from systems.effects_system import EffectQuality, EffectsSystem

@pytest.fixture(scope="module",autouse=True)
def pygame_ready():
    pygame.init(); yield; pygame.quit()

def signature(system):
    return [(round(p.velocity.x,5),round(p.velocity.y,5),round(p.lifetime,5),p.color) for p in system.particles]

def test_particle_dt_motion_interpolation_and_expiration():
    p=Particle(pygame.Vector2(),pygame.Vector2(10,0),pygame.Vector2(0,20),0,.5,10,0,200,0,0,0,0,pydummy(),(1,2,3),EffectSpace.WORLD,EffectPriority.NORMAL,"test")
    p.update(.25)
    assert p.position.x==pytest.approx(2.5); assert p.position.y==pytest.approx(1.25)
    assert p.progress==pytest.approx(.5); assert p.size==pytest.approx(5); assert p.alpha==100
    p.update(.25); assert not p.active

def pydummy():
    from effects import ParticlePrimitive
    return ParticlePrimitive.CIRCLE

def test_known_unknown_and_deterministic_spawn():
    a=EffectsSystem(seed=7); b=EffectsSystem(seed=7)
    assert a.spawn("enemy_hit",(20,30))==8; b.spawn("enemy_hit",(20,30))
    assert signature(a)==signature(b)
    with pytest.raises(ValueError): a.spawn("not_an_effect",(0,0))

def test_lifetime_cleanup_and_clear():
    fx=EffectsSystem(); fx.spawn("player_jump_dust",(0,0)); fx.update(5)
    assert fx.particle_count==0
    fx.start_emitter("ambient","pollen_motes",(20,20)); fx.request_flash((255,0,0)); fx.request_shake(4,.2); fx.clear()
    assert fx.particle_count==fx.emitter_count==fx.screen_effect_count==0

def test_global_cap_and_critical_evicts_ambient():
    fx=EffectsSystem(capacity=12)
    fx.spawn("pollen_motes",(0,0),count_scale=20)
    assert fx.particle_count<=12
    fx.spawn("warden_phase_three",(0,0))
    assert fx.particle_count==12
    assert any(p.priority is EffectPriority.CRITICAL for p in fx.particles)

def test_quality_reduced_and_off():
    full=EffectsSystem(seed=1); reduced=EffectsSystem(seed=1,quality=EffectQuality.REDUCED); off=EffectsSystem(quality=EffectQuality.OFF)
    assert full.spawn("enemy_hit",(0,0))==8; assert reduced.spawn("enemy_hit",(0,0))==4
    assert off.spawn("enemy_hit",(0,0))==0
    assert off.spawn("player_death",(0,0))>0

def test_emitter_ownership_rate_and_stop():
    fx=EffectsSystem(seed=2); fx.start_emitter("owner","pollen_motes",(10,10)); fx.update(1)
    assert fx.emitter_count==1 and fx.particle_count>0
    fx.update_emitter_position("owner",(30,40)); assert fx.emitters["owner"].position==pygame.Vector2(30,40)
    fx.stop_emitter("owner"); assert fx.emitter_count==0

def test_screen_flash_is_bounded_and_expires():
    fx=EffectsSystem(); fx.request_flash((255,255,255),999,.1)
    assert fx.flashes[0].opacity==112
    fx.update(.11); assert not fx.flashes

def test_shake_requests_combine_once():
    class Camera:
        def __init__(self): self.calls=[]
        def shake(self,a,b): self.calls.append((a,b))
    c=Camera(); fx=EffectsSystem(); fx.request_shake(3,.1); fx.request_shake(7,.2); fx.apply_shake(c)
    assert c.calls==[(7,.2)]; fx.apply_shake(c); assert len(c.calls)==1

def test_world_and_screen_render_do_not_change_world_positions():
    fx=EffectsSystem(); fx.spawn("enemy_hit",(100,100)); fx.spawn("route_unlocked",(40,40))
    before=[p.position.copy() for p in fx.particles]; surface=pygame.Surface((200,150)); fx.draw_world(surface,(-50,-20),pygame.Rect(0,0,200,150)); fx.draw_screen(surface)
    assert [p.position for p in fx.particles]==before

def test_all_definitions_are_bounded_and_well_formed():
    assert len(EFFECT_DEFINITIONS)>=40
    for key,d in EFFECT_DEFINITIONS.items():
        assert key==d.effect_id and d.count>=1 and d.max_particles>=1
        assert 0<d.lifetime[0]<=d.lifetime[1]
        assert d.colors and all(len(c)==3 for c in d.colors)
