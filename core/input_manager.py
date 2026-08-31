"""Authoritative keyboard/controller to logical-action translation."""
from __future__ import annotations
from dataclasses import dataclass,field
from enum import Enum
import math
from typing import Protocol
import pygame

class Action(str,Enum):
 MOVE_LEFT="move_left";MOVE_RIGHT="move_right";MOVE_X="move_x";JUMP="jump";ATTACK="attack";INTERACT="interact";PAUSE="pause"
 MENU_UP="menu_up";MENU_DOWN="menu_down";MENU_LEFT="menu_left";MENU_RIGHT="menu_right";CONFIRM="confirm";BACK="back"
 DEBUG_EFFECTS="debug_effects";DEBUG_RESET="debug_reset";DEBUG_MUTE="debug_mute";DEBUG_ATTACK="debug_attack"
class InputDevice(str,Enum):KEYBOARD="keyboard";CONTROLLER="controller"
@dataclass(frozen=True,slots=True)
class ControllerSnapshot:
 instance_id:int;name:str="Generic Controller";guid:str="";axes:tuple[float,...]=(0.0,0.0);buttons:tuple[bool,...]=();hat:tuple[int,int]=(0,0)
class ControllerBackend(Protocol):
 def discover(self)->None:...
 def handle_event(self,event:pygame.event.Event)->None:...
 def snapshots(self)->tuple[ControllerSnapshot,...]:...
 def rumble(self,instance_id:int,low:float,high:float,duration_ms:int)->bool:...
class PygameControllerBackend:
 def __init__(self)->None:self.devices:dict[int,pygame.joystick.Joystick]={};self.available=True
 def discover(self)->None:
  try:
   pygame.joystick.init()
   for index in range(pygame.joystick.get_count()):self._add(index)
  except (pygame.error,AttributeError):self.available=False;self.devices.clear()
 def _add(self,index:int)->None:
  try:
   stick=pygame.joystick.Joystick(index);stick.init();self.devices[stick.get_instance_id()]=stick
  except (pygame.error,AttributeError):pass
 def handle_event(self,event:pygame.event.Event)->None:
  if event.type==getattr(pygame,"JOYDEVICEADDED",-1):self._add(event.device_index)
  elif event.type==getattr(pygame,"JOYDEVICEREMOVED",-1):self.devices.pop(event.instance_id,None)
 def snapshots(self)->tuple[ControllerSnapshot,...]:
  result=[]
  for instance_id,stick in tuple(self.devices.items()):
   try:
    axes=tuple(stick.get_axis(i) for i in range(stick.get_numaxes()));buttons=tuple(bool(stick.get_button(i)) for i in range(stick.get_numbuttons()));hat=stick.get_hat(0) if stick.get_numhats() else (0,0)
    result.append(ControllerSnapshot(instance_id,stick.get_name() or "Generic Controller",stick.get_guid() if hasattr(stick,"get_guid") else "",axes,buttons,hat))
   except (pygame.error,AttributeError):self.devices.pop(instance_id,None)
  return tuple(result)
 def rumble(self,instance_id:int,low:float,high:float,duration_ms:int)->bool:
  stick=self.devices.get(instance_id)
  if stick is None or not hasattr(stick,"rumble"):return False
  try:return bool(stick.rumble(max(0,min(1,low)),max(0,min(1,high)),max(0,duration_ms)))
  except (pygame.error,AttributeError):return False
class FakeControllerBackend:
 def __init__(self)->None:self.states:dict[int,ControllerSnapshot]={};self.rumbles=[]
 def discover(self)->None:pass
 def handle_event(self,event:pygame.event.Event)->None:pass
 def snapshots(self)->tuple[ControllerSnapshot,...]:return tuple(self.states[k] for k in sorted(self.states))
 def connect(self,instance_id:int=1,name:str="Test Controller",guid:str="test")->None:self.states[instance_id]=ControllerSnapshot(instance_id,name,guid,(0.0,0.0),(False,)*8,(0,0))
 def disconnect(self,instance_id:int=1)->None:self.states.pop(instance_id,None)
 def set_state(self,instance_id:int=1,*,axes=None,buttons=None,hat=None)->None:
  old=self.states[instance_id];self.states[instance_id]=ControllerSnapshot(instance_id,old.name,old.guid,tuple(axes if axes is not None else old.axes),tuple(buttons if buttons is not None else old.buttons),tuple(hat if hat is not None else old.hat))
 def rumble(self,instance_id:int,low:float,high:float,duration_ms:int)->bool:
  if instance_id not in self.states:return False
  self.rumbles.append((instance_id,low,high,duration_ms));return True

KEY_ACTIONS={
 pygame.K_LEFT:(Action.MOVE_LEFT,Action.MENU_LEFT),pygame.K_a:(Action.MOVE_LEFT,Action.MENU_LEFT),pygame.K_RIGHT:(Action.MOVE_RIGHT,Action.MENU_RIGHT),pygame.K_d:(Action.MOVE_RIGHT,Action.MENU_RIGHT),
 pygame.K_UP:(Action.JUMP,Action.MENU_UP),pygame.K_w:(Action.MENU_UP,),pygame.K_DOWN:(Action.MENU_DOWN,),pygame.K_s:(Action.MENU_DOWN,),
 pygame.K_SPACE:(Action.JUMP,Action.CONFIRM),pygame.K_z:(Action.JUMP,),pygame.K_RETURN:(Action.CONFIRM,),pygame.K_e:(Action.INTERACT,),pygame.K_f:(Action.ATTACK,),
 pygame.K_ESCAPE:(Action.PAUSE,Action.BACK),pygame.K_F5:(Action.DEBUG_ATTACK,),pygame.K_F6:(Action.DEBUG_EFFECTS,),pygame.K_F7:(Action.DEBUG_RESET,),pygame.K_F8:(Action.DEBUG_MUTE,),
}
BUTTON_ACTIONS={0:(Action.JUMP,Action.CONFIRM),1:(Action.BACK,),2:(Action.ATTACK,),3:(Action.INTERACT,),6:(Action.BACK,),7:(Action.PAUSE,)}
MENU_ACTIONS=(Action.MENU_UP,Action.MENU_DOWN,Action.MENU_LEFT,Action.MENU_RIGHT)
PROMPTS={
 InputDevice.KEYBOARD:{Action.CONFIRM:"ENTER",Action.BACK:"ESC",Action.INTERACT:"E",Action.ATTACK:"F",Action.JUMP:"SPACE",Action.PAUSE:"ESC",Action.DEBUG_RESET:"F7"},
 InputDevice.CONTROLLER:{Action.CONFIRM:"A",Action.BACK:"B",Action.INTERACT:"Y",Action.ATTACK:"X",Action.JUMP:"A",Action.PAUSE:"START"},
}
class InputManager:
 def __init__(self,backend:ControllerBackend|None=None,*,deadzone:float=.22,menu_threshold:float=.58,repeat_delay:float=.38,repeat_interval:float=.12)->None:
  self.backend=backend or PygameControllerBackend();self.deadzone=max(0,min(.8,deadzone));self.menu_threshold=max(self.deadzone,min(.95,menu_threshold));self.repeat_delay=repeat_delay;self.repeat_interval=repeat_interval
  self.active_device=InputDevice.KEYBOARD;self.active_controller_id=None;self.controller_name="";self.move_x=0.0;self._keyboard_keys=set();self._held=set();self._pressed=set();self._released=set();self._controller_actions=set();self._repeat={a:0.0 for a in MENU_ACTIONS};self._suppressed=set();self.backend.discover();self._sync_controller(False)
 @property
 def connected_count(self)->int:return len(self.backend.snapshots())
 def begin_frame(self,dt:float)->None:
  self._pressed.clear();self._released.clear();self._sync_controller(True);self._update_repeat(max(0,dt))
 def process_event(self,event:pygame.event.Event)->None:
  if event.type in {pygame.WINDOWFOCUSLOST,getattr(pygame,"ACTIVEEVENT",-99)} and (event.type!=getattr(pygame,"ACTIVEEVENT",-99) or getattr(event,"gain",1)==0):self.clear_all();return
  if event.type==pygame.KEYDOWN:
   if event.key not in self._keyboard_keys:
    self._keyboard_keys.add(event.key);self._set_actions(KEY_ACTIONS.get(event.key,()),True,InputDevice.KEYBOARD)
  elif event.type==pygame.KEYUP:
   self._keyboard_keys.discard(event.key);self._set_actions(KEY_ACTIONS.get(event.key,()),False,InputDevice.KEYBOARD)
  elif event.type in {getattr(pygame,"JOYDEVICEADDED",-1),getattr(pygame,"JOYDEVICEREMOVED",-1),getattr(pygame,"JOYBUTTONDOWN",-1),getattr(pygame,"JOYBUTTONUP",-1),getattr(pygame,"JOYAXISMOTION",-1),getattr(pygame,"JOYHATMOTION",-1)}:
   self.backend.handle_event(event);self._sync_controller(event.type not in {getattr(pygame,"JOYDEVICEADDED",-1),getattr(pygame,"JOYDEVICEREMOVED",-1)})
 def _set_actions(self,actions,down:bool,device:InputDevice)->None:
  for action in actions:
   if down:
    if action not in self._held and action not in self._suppressed:self._pressed.add(action)
    self._held.add(action)
   else:
    if action in self._held:self._released.add(action)
    self._held.discard(action);self._suppressed.discard(action)
  if down and actions:self.active_device=device
 def _sync_controller(self,meaningful:bool)->None:
  snapshots=self.backend.snapshots()
  if not snapshots:
   for action in self._controller_actions:self._held.discard(action)
   self._controller_actions.clear();self.move_x=0.0;self.active_controller_id=None;self.controller_name="";return
  snap=next((x for x in snapshots if x.instance_id==self.active_controller_id),snapshots[0]);self.active_controller_id=snap.instance_id;self.controller_name=snap.name
  raw_x=snap.axes[0] if snap.axes else 0.0;raw_y=snap.axes[1] if len(snap.axes)>1 else 0.0;length=math.hypot(raw_x,raw_y)
  if length<=self.deadzone:nx=ny=0.0
  else:
   magnitude=min(1.0,(length-self.deadzone)/(1-self.deadzone));nx=raw_x/length*magnitude;ny=raw_y/length*magnitude
  hat=snap.hat;new=set()
  if nx< -self.menu_threshold or hat[0]<0:new.update((Action.MOVE_LEFT,Action.MENU_LEFT))
  if nx> self.menu_threshold or hat[0]>0:new.update((Action.MOVE_RIGHT,Action.MENU_RIGHT))
  if ny< -self.menu_threshold or hat[1]>0:new.add(Action.MENU_UP)
  if ny> self.menu_threshold or hat[1]<0:new.add(Action.MENU_DOWN)
  for index,actions in BUTTON_ACTIONS.items():
   if index<len(snap.buttons) and snap.buttons[index]:new.update(actions)
  removed=self._controller_actions-new;added=new-self._controller_actions
  for action in removed:
   if not any(action in KEY_ACTIONS.get(key,()) for key in self._keyboard_keys):self._held.discard(action);self._released.add(action)
   self._suppressed.discard(action)
  for action in added:
   if action not in self._held and action not in self._suppressed:self._pressed.add(action)
   self._held.add(action)
  self._controller_actions=new;self.move_x=nx if abs(nx)>0 else float(hat[0])
  if meaningful and (added or abs(nx)>=self.menu_threshold or abs(ny)>=self.menu_threshold):self.active_device=InputDevice.CONTROLLER
 def _update_repeat(self,dt:float)->None:
  for action in MENU_ACTIONS:
   if action not in self._held:self._repeat[action]=0;continue
   if action in self._pressed:self._repeat[action]=self.repeat_delay;continue
   self._repeat[action]-=dt
   if self._repeat[action]<=0:self._pressed.add(action);self._repeat[action]+=self.repeat_interval
 def axis(self,action:Action)->float:
  if action is not Action.MOVE_X:return 0.0
  keyboard=float(Action.MOVE_RIGHT in self._held)-float(Action.MOVE_LEFT in self._held)
  return keyboard if keyboard else self.move_x
 def is_down(self,action:Action)->bool:return action in self._held
 def was_pressed(self,action:Action)->bool:return action in self._pressed
 def was_released(self,action:Action)->bool:return action in self._released
 def consume(self,action:Action)->bool:
  if action not in self._pressed:return False
  self._pressed.discard(action);return True
 def suppress_edges(self)->None:self._suppressed.update(self._held);self._pressed.clear();self._released.clear()
 def clear_all(self)->None:
  self._keyboard_keys.clear();self._held.clear();self._pressed.clear();self._released.clear();self._controller_actions.clear();self._suppressed.clear();self.move_x=0.0
 def get_prompt(self,action:Action)->str:return PROMPTS.get(self.active_device,{}).get(action,action.value.replace("_"," ").upper())
 def rumble(self,low:float,high:float,duration_ms:int)->bool:
  return self.active_controller_id is not None and self.backend.rumble(self.active_controller_id,low,high,duration_ms)
