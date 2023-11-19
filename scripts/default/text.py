import pygame
from default.object import *
from default.color import *

class Text(Object):

    def __init__(self, position, surfaceRect=pygame.Rect(0, 0, 0, 0), text='', textSize=25, antialias=True, color=White, backgroundColor=None, fontPath = None, status="Normal", visible=True) -> None:

        self.textArgs = {}
        
        super().__init__(position, surfaceRect=surfaceRect, visible=visible)
        
        self.AddText(status, text, textSize, antialias, color, backgroundColor, fontPath)
        self.SetStatus("Normal")
        self.__UpdateSize()
        
    def AddText(self, status, text, textSize, antialias=True, color=White, backgroundColor=None, fontPath=None):
        
        super().AddText(status, text, textSize, antialias, color, backgroundColor, fontPath)
        
        self.textArgs[status] = [text, textSize, antialias, color, backgroundColor, fontPath]
 
    def UpdateText(self, status, text) -> None:

        self.AddText(status, text, *self.textArgs[status][1:])
        self.__UpdateSize()

    def UpdateSize(self, status, size: int) -> None:

        self.AddText(status, self.textArgs[status][0], size, *self.textArgs[status][2:])

    def __UpdateSize(self):

        if self.status in self:
            
            self.rect = self[self.status].get_rect()
            self.SetPosition(self.position, self.surfaceRect)

    def SetStatus(self, status: str):

        super().SetStatus(status)

        self.__UpdateSize()