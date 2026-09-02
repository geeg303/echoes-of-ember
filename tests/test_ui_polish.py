from __future__ import annotations

import pygame
import pytest

from systems.effects_system import EffectQuality,EffectsSystem
from ui.menu import menu_layout
from ui.style import SAFE_MARGIN_X,SAFE_MARGIN_Y,dim_screen,safe_area


@pytest.mark.parametrize("count",[1,5,7,9,11])
def test_menu_rows_and_footer_stay_inside_safe_panel(count) -> None:
    panel,first_y,step,row_height=menu_layout(count)
    last_bottom=first_y+(count-1)*step-5+row_height
    assert panel.left>=SAFE_MARGIN_X and panel.top>=SAFE_MARGIN_Y
    assert panel.right<=1280-SAFE_MARGIN_X and panel.bottom<=720
    assert last_bottom<=panel.bottom-45


def test_safe_area_and_dim_treatment_are_screen_space(pygame_headless) -> None:
    surface=pygame.Surface((1280,720));surface.fill((100,100,100));before=surface.get_at((0,0))
    assert safe_area(surface)==pygame.Rect(40,32,1200,656)
    dim_screen(surface)
    assert surface.get_at((0,0))!=before


class ShakeCamera:
    def __init__(self):self.calls=[]
    def shake(self,intensity,duration):self.calls.append((intensity,duration))


@pytest.mark.parametrize("quality,expected",[(EffectQuality.FULL,12.0),(EffectQuality.REDUCED,6.0),(EffectQuality.OFF,None)])
def test_effect_quality_controls_camera_motion(quality,expected) -> None:
    effects=EffectsSystem(quality=quality);camera=ShakeCamera();effects.request_shake(12,.25);effects.apply_shake(camera)
    if expected is None:assert not camera.calls
    else:assert camera.calls==[(expected,.25)]


def test_switching_effects_off_clears_pending_shake() -> None:
    effects=EffectsSystem();camera=ShakeCamera();effects.request_shake(12,.25);effects.set_quality(EffectQuality.OFF);effects.apply_shake(camera)
    assert not camera.calls
