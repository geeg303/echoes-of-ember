"""Central editor screen/world/grid transforms."""
from dataclasses import dataclass
@dataclass(slots=True)
class EditorViewport:
 origin_x:float=0;origin_y:float=0;zoom:float=1.0;panel_left:int=190;panel_top:int=20
 LEVELS=(.25,.5,.75,1.,1.5,2.)
 def screen_to_world(self,p):return ((p[0]-self.panel_left)/self.zoom+self.origin_x,(p[1]-self.panel_top)/self.zoom+self.origin_y)
 def world_to_screen(self,p):return ((p[0]-self.origin_x)*self.zoom+self.panel_left,(p[1]-self.origin_y)*self.zoom+self.panel_top)
 def screen_to_tile(self,p,tile_size):w=self.screen_to_world(p);return int(w[0]//tile_size),int(w[1]//tile_size)
 def pan(self,dx,dy):self.origin_x=max(0,self.origin_x+dx/self.zoom);self.origin_y=max(0,self.origin_y+dy/self.zoom)
 def step_zoom(self,direction,anchor):
  before=self.screen_to_world(anchor);i=min(range(len(self.LEVELS)),key=lambda n:abs(self.LEVELS[n]-self.zoom));self.zoom=self.LEVELS[max(0,min(len(self.LEVELS)-1,i+direction))];after=self.screen_to_world(anchor);self.origin_x+=before[0]-after[0];self.origin_y+=before[1]-after[1]
