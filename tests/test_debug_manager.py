from __future__ import annotations
import json
from types import SimpleNamespace
import pygame,pytest
from core.debug_manager import DebugManager
from debug.commands import DebugCommand,DebugCommandError,DebugCommandRegistry
from debug.profiler import DebugProfiler
from debug.snapshot import build_snapshot

@pytest.fixture(autouse=True)
def pygame_ready():
 pygame.init();pygame.display.set_mode((1,1));yield;pygame.quit()

def manager(tmp_path,enabled=True):return DebugManager(enabled,pygame.font.Font(None,18),export_root=tmp_path)

def test_debug_disabled_is_inert(tmp_path):
 d=manager(tmp_path,False);assert not d.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_F1,mod=0),SimpleNamespace()) and not d.overlay_visible

def test_overlay_pages_and_visualization_toggles(tmp_path):
 d=manager(tmp_path);game=SimpleNamespace(input=SimpleNamespace(clear_all=lambda:None),app_mode="gameplay")
 d.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_F1,mod=0),game);assert d.overlay_visible
 d.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_F2,mod=0),game);assert d.page=="PLAYER"
 d.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_F3,mod=0),game);d.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_F4,mod=0),game);assert d.collision_visible and d.triggers_visible

def test_command_registry_parsing_and_context():
 r=DebugCommandRegistry();r.register(DebugCommand("ping","ping <value>","test",frozenset({"gameplay"}),lambda g,a:" ".join(a)))
 assert r.dispatch(SimpleNamespace(app_mode="gameplay"),'ping "hello world"')==( "hello world",False)
 with pytest.raises(DebugCommandError):r.dispatch(SimpleNamespace(app_mode="map"),"ping x")
 with pytest.raises(DebugCommandError):r.dispatch(SimpleNamespace(app_mode="gameplay"),"unknown")

def test_profiler_is_bounded_and_exports(tmp_path):
 p=DebugProfiler(10)
 for i in range(40):p.record("frame",10+i,"gameplay")
 assert len(p.samples["frame"])==10 and len(p.spikes)<=20 and p.summary()["frame"]["max"]==49
 path=p.export(tmp_path);assert json.loads(path.read_text())["frame"]["max"]==49

def test_pause_step_and_time_scale(tmp_path):
 d=manager(tmp_path);assert d.simulation_dt(.02)==.02
 d.simulation_paused=True;assert d.simulation_dt(.02)==0
 d.step_requested=True;assert d.simulation_dt(.02)>0 and d.simulation_paused
 d.time_scale=.5;d.simulation_paused=False;assert d.simulation_dt(.02)==pytest.approx(.01)

def test_snapshot_is_read_only_and_exportable(tmp_path):
 game=SimpleNamespace(app_mode="frontend",debug=SimpleNamespace(enabled=True),effects=None,audio=None,input=None,achievements=None,world_progress=None,save_session=None)
 snap=build_snapshot(game,7,{"fps":60});assert snap.frame==7
 with pytest.raises(TypeError):snap.player["health"]=4
 d=manager(tmp_path);d.snapshot=snap;path=d.export_repro(game);payload=json.loads(path.read_text());assert payload["snapshot"]["frame"]==7

def test_palette_captures_text_without_forwarding(tmp_path):
 d=manager(tmp_path);inp=SimpleNamespace(clear_all=lambda:None);game=SimpleNamespace(input=inp,app_mode="frontend")
 assert d.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_BACKQUOTE,mod=0,unicode="`"),game)
 assert d.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_f,mod=0,unicode="f"),game)
 assert d.command_text=="f"
