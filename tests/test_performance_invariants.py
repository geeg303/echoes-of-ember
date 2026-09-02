from __future__ import annotations
import pygame,pytest
from core.game import Game
from editor.document import LevelDocument
from systems.effects_system import EffectsSystem
from ui.hud import HUD
from world.background import ParallaxBackground
from world.tilemap import TileMap

@pytest.fixture(autouse=True)
def display(monkeypatch):
 monkeypatch.setenv("SDL_VIDEODRIVER","dummy");monkeypatch.setenv("SDL_AUDIODRIVER","dummy");pygame.init();pygame.display.set_mode((1280,720));yield;pygame.quit()

def test_tile_chunk_cache_is_bounded_and_reused():
 tilemap=TileMap.from_data({"width":40,"height":20,"tile_size":16,"tiles":[{"id":1,"position":[0,0],"size":[40,20]}]});surface=pygame.Surface((320,160));view=pygame.Rect(0,0,320,160)
 tilemap.draw(surface,view);first=tilemap.cached_chunk_count;tilemap.draw(surface,view)
 assert tilemap.cached_chunk_count==first and 0<first<=tilemap.maximum_chunk_count

def test_breakable_destruction_invalidates_only_affected_chunk():
 tilemap=TileMap.from_data({"width":32,"height":8,"tile_size":16,"tiles":[{"id":5,"position":[1,1]},{"id":1,"position":[20,1]}]});surface=pygame.Surface((512,128));tilemap.draw(surface,pygame.Rect(0,0,512,128));assert tilemap.cached_chunk_count==2
 destroyed=tilemap.destroy_breakables(pygame.Rect(16,16,16,16));assert destroyed and tilemap.cached_chunk_count==1 and tilemap.tile_at(1,1) is None and tilemap.tile_at(20,1) is not None

def test_background_gradient_cache_reuses_surface():
 bg=ParallaxBackground(2000,1000);surface=pygame.Surface((320,180));bg.draw(surface,pygame.Vector2());cached=bg._gradient;bg.draw(surface,pygame.Vector2(100,0));assert bg._gradient is cached

def test_empty_screen_effect_pass_allocates_no_overlay():
 effects=EffectsSystem();effects.draw_screen(pygame.Surface((320,180)));assert effects._overlay is None

def test_hud_text_cache_has_explicit_bound():
 hud=HUD(pygame.font.Font(None,20),pygame.font.Font(None,16),pygame.font.Font(None,24))
 for i in range(160):hud._render_cached(hud.font,str(i),(255,255,255))
 surface=pygame.Surface((320,180));hud._panel(surface,pygame.Rect(0,0,120,50));first=hud._panel_cache[(pygame.Rect(0,0,120,50).size,195)];hud._panel(surface,pygame.Rect(10,10,120,50))
 assert hud.text_cache_size==96 and hud._panel_cache[((120,50),195)] is first

def test_editor_tile_grid_rebuilds_only_after_terrain_mutation():
 document=LevelDocument.new("perf_level");first=document.tile_grid();assert document.tile_grid() is first and document._grid_builds==1
 document.set_tiles({(2,2):1});assert document.tile_grid()[2][2]==1 and document._grid_builds==1
 snapshot=document.snapshot();document.restore(snapshot);document.tile_grid();assert document._grid_builds==2

def test_same_size_present_skips_transform_scale(monkeypatch,tmp_path):
 game=Game(achievements_enabled=False,persistence=False)
 called=[];original=pygame.transform.scale
 monkeypatch.setattr(pygame.transform,"scale",lambda *args,**kwargs:(called.append(True),original(*args,**kwargs))[1])
 try:game._present();assert not called
 finally:game.shutdown()
