import os
os.environ.setdefault("SDL_VIDEODRIVER","dummy");os.environ.setdefault("SDL_AUDIODRIVER","dummy")
import pygame
from core.input_manager import Action,FakeControllerBackend,InputDevice,InputManager

def keys(manager,key,down=True):manager.process_event(pygame.event.Event(pygame.KEYDOWN if down else pygame.KEYUP,key=key))
def buttons(*pressed):
 values=[False]*8
 for i in pressed:values[i]=True
 return values

def test_keyboard_press_hold_release_and_shared_context_actions():
 m=InputManager(FakeControllerBackend());m.begin_frame(0);keys(m,pygame.K_SPACE)
 assert m.was_pressed(Action.JUMP) and m.was_pressed(Action.CONFIRM) and m.is_down(Action.JUMP)
 m.begin_frame(.01);assert not m.was_pressed(Action.JUMP) and m.is_down(Action.JUMP)
 keys(m,pygame.K_SPACE,False);assert m.was_released(Action.JUMP) and not m.is_down(Action.JUMP)

def test_keyboard_axis_and_prompt_device_switch():
 b=FakeControllerBackend();m=InputManager(b);m.begin_frame(0);keys(m,pygame.K_a);assert m.axis(Action.MOVE_X)==-1 and m.get_prompt(Action.CONFIRM)=="ENTER"
 keys(m,pygame.K_a,False);b.connect();b.set_state(axes=(.8,0));m.begin_frame(.016)
 assert m.active_device is InputDevice.CONTROLLER and m.get_prompt(Action.CONFIRM)=="A"
 keys(m,pygame.K_e);assert m.active_device is InputDevice.KEYBOARD and m.get_prompt(Action.INTERACT)=="E"

def test_radial_deadzone_and_normalized_analog_axis():
 b=FakeControllerBackend();b.connect();m=InputManager(b,deadzone=.2)
 b.set_state(axes=(.1,.1));m.begin_frame(.016);assert m.axis(Action.MOVE_X)==0 and m.active_device is InputDevice.KEYBOARD
 b.set_state(axes=(.6,0));m.begin_frame(.016);assert .49<m.axis(Action.MOVE_X)<.51
 b.set_state(axes=(1,0));m.begin_frame(.016);assert m.axis(Action.MOVE_X)==1

def test_controller_buttons_map_to_contextual_actions_without_duplicates():
 b=FakeControllerBackend();b.connect();m=InputManager(b);b.set_state(buttons=buttons(0,2,3,7));m.begin_frame(.016)
 assert all(m.was_pressed(x) for x in (Action.JUMP,Action.CONFIRM,Action.ATTACK,Action.INTERACT,Action.PAUSE))
 m.begin_frame(.016);assert not m.was_pressed(Action.JUMP) and m.is_down(Action.JUMP)

def test_dpad_supports_movement_and_menu_navigation():
 b=FakeControllerBackend();b.connect();m=InputManager(b);b.set_state(hat=(-1,1));m.begin_frame(.016)
 assert m.axis(Action.MOVE_X)==-1 and m.was_pressed(Action.MENU_LEFT) and m.was_pressed(Action.MENU_UP)

def test_menu_repeat_has_delay_and_bounded_interval():
 b=FakeControllerBackend();b.connect();m=InputManager(b,repeat_delay=.3,repeat_interval=.1);b.set_state(hat=(0,-1));m.begin_frame(.01);assert m.was_pressed(Action.MENU_DOWN)
 m.begin_frame(.2);assert not m.was_pressed(Action.MENU_DOWN)
 m.begin_frame(.11);assert m.was_pressed(Action.MENU_DOWN)
 m.begin_frame(.05);assert not m.was_pressed(Action.MENU_DOWN)

def test_disconnect_clears_movement_and_buttons_with_keyboard_fallback():
 b=FakeControllerBackend();b.connect();m=InputManager(b);b.set_state(axes=(1,0),buttons=buttons(2));m.begin_frame(.016);assert m.axis(Action.MOVE_X)==1 and m.is_down(Action.ATTACK)
 b.disconnect();m.begin_frame(.016);assert m.axis(Action.MOVE_X)==0 and not m.is_down(Action.ATTACK) and m.connected_count==0
 keys(m,pygame.K_d);assert m.axis(Action.MOVE_X)==1 and m.active_device is InputDevice.KEYBOARD

def test_reconnect_and_deterministic_controller_policy():
 b=FakeControllerBackend();b.connect(2,"Second");b.connect(1,"First");m=InputManager(b);m.begin_frame(0);assert m.active_controller_id==1 and m.controller_name=="First"
 b.disconnect(1);m.begin_frame(0);assert m.active_controller_id==2
 b.connect(1,"First Again");m.begin_frame(0);assert m.active_controller_id==2

def test_transition_suppression_prevents_double_action_until_release():
 b=FakeControllerBackend();b.connect();m=InputManager(b);b.set_state(buttons=buttons(0));m.begin_frame(.016);assert m.was_pressed(Action.CONFIRM)
 m.suppress_edges();m.begin_frame(.016);assert not m.was_pressed(Action.CONFIRM) and not m.was_pressed(Action.JUMP)
 b.set_state(buttons=buttons());m.begin_frame(.016);b.set_state(buttons=buttons(0));m.begin_frame(.016);assert m.was_pressed(Action.CONFIRM)

def test_focus_loss_clears_stuck_inputs_and_rumble_is_centralized():
 b=FakeControllerBackend();b.connect();m=InputManager(b);b.set_state(axes=(1,0),buttons=buttons(2));m.begin_frame(.016)
 m.process_event(pygame.event.Event(pygame.WINDOWFOCUSLOST));assert m.axis(Action.MOVE_X)==0 and not m.is_down(Action.ATTACK)
 assert m.rumble(.2,.5,100) and b.rumbles[-1]==(1,.2,.5,100)
