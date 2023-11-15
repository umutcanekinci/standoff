#-# Importing Packages #-#
import pygame
from default.object import *
from default.text import *

#-# Button Class #-#
class Button(Object):

    def __init__(self, position: tuple = ..., size: tuple = ..., imagePaths={}, text: str = "", selectedText: str = "", textSize: int = 20, textColor: tuple = White, selectedTextColor: tuple = White, textFontPath: pygame.font.Font = None, surfaceRect: pygame.Rect = None, show=True):

        super().__init__(position, size, imagePaths, surfaceRect, show)

        if text:

            if not selectedText:

                selectedText = text

            self.AddText("Normal", text, textSize, True, textColor, None, textFontPath)
            self.AddText("Mouse Over", selectedText, textSize, True, selectedTextColor, None, textFontPath)

    def AddText(self, status, text: str, textSize: int, antialias: bool, color: tuple, backgroundColor, fontPath: pygame.font.Font = None) -> None:

        if not hasattr(self, "text"):

            self.text = Text(("CENTER", "CENTER"), text, textSize, True, color, backgroundColor, fontPath, True, status, surfaceRect=self.screenRect)

        else:
            
            self.text.AddText(status, text, textSize, antialias, color, backgroundColor, fontPath)
         
    def Draw(self, surface):

        super().Draw(surface)

        if hasattr(self, "text") and self.show:
            
            self.text.SetStatus(self.status)
            self.text.Draw(surface)

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

