"""Bounded snapshot commands for safe editor undo/redo."""
from dataclasses import dataclass
@dataclass(slots=True)
class SnapshotCommand:label:str;before:object;after:object
class CommandHistory:
 def __init__(self,limit=150):self.limit=limit;self.undo_stack=[];self.redo_stack=[]
 def execute(self,document,label,operation):
  before=document.snapshot();operation();after=document.snapshot()
  if before==after:return False
  self.undo_stack.append(SnapshotCommand(label,before,after));self.undo_stack=self.undo_stack[-self.limit:];self.redo_stack.clear();return True
 def undo(self,document):
  if not self.undo_stack:return False
  command=self.undo_stack.pop();document.restore(command.before);self.redo_stack.append(command);return True
 def redo(self,document):
  if not self.redo_stack:return False
  command=self.redo_stack.pop();document.restore(command.after);self.undo_stack.append(command);return True
