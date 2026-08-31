"""Reusable pause and Game Over menu controllers."""
from __future__ import annotations
from ui.menu import ConfirmationDialog,Menu,MenuAction,MenuItem,draw_dialog,draw_menu
class PauseController:
    def __init__(self,host,title,font,small,audio)->None:self.host=host;self.title=title;self.font=font;self.small=small;self.audio=audio;self.menu=Menu([MenuItem("RESUME","resume"),MenuItem("SETTINGS","settings"),MenuItem("RESTART LEVEL","restart"),MenuItem("RETURN TO WORLD MAP","map"),MenuItem("QUIT TO MAIN MENU","main")]);self.dialog=None
    def handle(self,action:MenuAction)->None:
        if self.dialog:
            keep=self.dialog.handle(action)
            if not keep:self.dialog=None
            return
        if action in {MenuAction.UP,MenuAction.DOWN}:self.menu.move(-1 if action is MenuAction.UP else 1);self.audio.play_sound("ui_move");return
        if action in {MenuAction.BACK,MenuAction.PAUSE}:self.host.resume_game();return
        if action is not MenuAction.CONFIRM:return
        item=self.menu.focused.item_id;self.audio.play_sound("ui_confirm")
        if item=="resume":self.host.resume_game()
        elif item=="settings":self.host.open_settings("pause")
        elif item=="restart":self.dialog=ConfirmationDialog("RESTART LEVEL?","Current run progress will be abandoned.","RESTART",self.host.restart_from_menu)
        elif item=="map":self.dialog=ConfirmationDialog("RETURN TO MAP?","Current run will not produce a result.","RETURN",self.host.abandon_to_map)
        elif item=="main":self.dialog=ConfirmationDialog("QUIT TO MAIN MENU?","Committed progress will be saved.","QUIT",self.host.return_to_main_menu)
    def draw(self,surface)->None:
        draw_menu(surface,self.title,self.font,self.small,"PAUSED",self.menu,"Gameplay simulation is frozen")
        if self.dialog:draw_dialog(surface,self.title,self.font,self.dialog)
class GameOverController:
    def __init__(self,host,title,font,small,audio)->None:self.host=host;self.title=title;self.font=font;self.small=small;self.audio=audio;self.menu=Menu([MenuItem("RETRY LEVEL","retry"),MenuItem("RETURN TO WORLD MAP","map"),MenuItem("QUIT TO MAIN MENU","main")])
    def handle(self,action:MenuAction)->None:
        if action in {MenuAction.UP,MenuAction.DOWN}:self.menu.move(-1 if action is MenuAction.UP else 1);self.audio.play_sound("ui_move");return
        if action is not MenuAction.CONFIRM:return
        self.audio.play_sound("ui_confirm");item=self.menu.focused.item_id
        if item=="retry":self.host.retry_after_game_over()
        elif item=="map":self.host.abandon_to_map()
        else:self.host.return_to_main_menu()
    def draw(self,surface)->None:draw_menu(surface,self.title,self.font,self.small,"GAME OVER",self.menu,"The Ember fades, but Nova can try again")
