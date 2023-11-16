#-# Importing Packages #-#
import pygame
from default.object import *
from default.text import *

#-# Button Class #-#
class Button(Object):

    def __init__(self, position: tuple = ..., surfaceRect: pygame.Rect = None, size: tuple = ..., imagePaths={}, text: str = "", selectedText: str = "", textSize: int = 20, textColor: tuple = White, selectedTextColor: tuple = White, textFontPath: pygame.font.Font = None, visible=True):

        super().__init__(position, surfaceRect, size, imagePaths, visible)

        if text:

            if not selectedText:

                selectedText = text

            self.AddText("Normal", text, textSize, True, textColor, None, textFontPath)
            self.AddText("Mouse Over", selectedText, textSize, True, selectedTextColor, None, textFontPath)

    def AddText(self, status, text: str, textSize: int, antialias: bool, color: tuple, backgroundColor, fontPath: pygame.font.Font = None) -> None:

        if not hasattr(self, "text"):

            self.text = Text(("CENTER", "CENTER"), self.screenRect, text, textSize, True, color, backgroundColor, fontPath, "Normal", status)

        else:
            
            self.text.AddText(status, text, textSize, antialias, color, backgroundColor, fontPath)
        
    def HandleEvents(self, event, mousePosition, keys):

        super().HandleEvents(event, mousePosition, keys)
        
        if hasattr(self, "text") and self.visible:
            
            self.text.SetStatus(self.status)

    def Draw(self, surface):

        if hasattr(self, "text") and self.visible:
            
            self.text.Draw(self[self.status])

        super().Draw(surface)



#-# Menu Button Class #-#
class MenuButton(Button):

    def __init__(
            self,     
            color: str,
            position: tuple,
            selectedColor: str = None,
            text: str = None,
            selectedText: str = None,
            textColor: tuple = None,
            selectedTextColor: tuple = None,
            textSize: int = 10,
            fontPath: str = None,
            size: tuple = None,
            selectedSize: tuple = [0, 0]
        ) -> None:
        
        imagePath = ImagePath(color, "gui/buttons")
        if not selectedColor: selectedColor = color
        selectedImagePath = ImagePath(selectedColor, "gui/buttons")

        super().__init__(position, size, {"Unselected" : imagePath})
        self.AddSurface("Selected", GetImage(selectedImagePath, selectedSize))
        self.status = "Unselected"

        if text:

            if not selectedText:

                selectedText = text

            self.AddText("Selected", text, textSize, True, textColor, None, fontPath)
            self.AddText("Unselected", selectedText, textSize, True, selectedTextColor, None, fontPath)

