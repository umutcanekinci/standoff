#region #-# Import Packages #-#

try:

    import pygame, sys, os
    from pygame import mixer

    from default.buttonxx import *
    from default.color import *
    from default.text import *
    from default.object import *
    from default.path import *

except Exception as error:

	print("An error occured during importing packages:", error)

#endregion

#-# Application Class #-#
class Application(dict[str : pygame.Surface]):
    
    def __init__(self, title: str = "Game", size: tuple = (640, 480), backgroundColors: list = {}, FPS: int = 60) -> None:
        
        super().__init__()
        self.InitPygame()
        self.InitClock()
        self.InitMixer()
        self.SetTitle(title)
        self.SetSize(size)
        self.OpenWindow()
        self.SetFPS(FPS)
        self.SetBackgorundColor(backgroundColors)
        self.tab = ""

    def Run(self) -> None:
        
        #-# Starting App #-#
        self.isRunning = True
        self.isDebugLogVisible = False

        #-# Main Loop #-#
        while self.isRunning:

            #-# FPS #-#
            self.deltaTime = self.clock.tick(self.FPS) * .001 * self.FPS

            #-# Getting Mouse Position #-#
            self.mousePosition = pygame.mouse.get_pos()

            #-# Getting Pressed Keys #-#
            self.keys = pygame.key.get_pressed()

            #-# Handling Events #-#
            for event in pygame.event.get():

                self.HandleEvents(event)

            #-# Set Cursor Position #-#
            if hasattr(self, "cursor"):

                self.cursor.SetPosition(self.mousePosition)    
            
            #-# Draw Objects #-#
            self.Draw()

    def HandleEvents(self, event: pygame.event.Event) -> None:

        if event.type == pygame.KEYDOWN and event.key == pygame.K_F3:

            self.isDebugLogVisible = not self.isDebugLogVisible

        if self.tab in self:
            
            for object in self[self.tab].values():
                
                if hasattr(object, "HandleEvents"):

                    object.HandleEvents(event, self.mousePosition, self.keys)

        self.HandleExitEvents(event)

    def HandleExitEvents(self, event: pygame.event.Event) -> None:

        if event.type == pygame.QUIT:

            self.Exit()

        elif event.type == pygame.KEYDOWN:

            if event.key == pygame.K_ESCAPE:

                self.Exit()

    def InitPygame(self) -> None:
        
        pygame.init()

    def InitMixer(self) -> None:

        pygame.mixer.init()

    def InitClock(self) -> None:

        self.clock = pygame.time.Clock()

    @staticmethod
    def PlaySound(channel: int, soundPath: SoundPath, volume: float, loops=0) -> None:

        mixer.Channel(channel).play(mixer.Sound(soundPath), loops)
        Application.SetVolume(channel, volume)

    @staticmethod
    def SetVolume(channel: int, volume: float):

        if volume < 0:

            volume = 0

        if volume > 1:

            volume = 1

        mixer.Channel(channel).set_volume(volume)

    def OpenWindow(self) -> None:

        self.window = pygame.display.set_mode(self.size)

    def CenterWindow(self) -> None:

        os.environ['SDL_VIDEO_CENTERED'] = '1'

    def SetFPS(self, FPS: int) -> None:
        
        self.FPS = FPS

    def SetTitle(self, title: str) -> None:
        
        self.title = title
        pygame.display.set_caption(self.title)

    def SetSize(self, size: tuple) -> None:

        self.size = self.width, self.height = size

    def SetBackgorundColor(self, colors: list = {}) -> None:

        self.backgroundColors = colors

    def AddObject(self, tab: str, name: str, object: Object) -> None:
        
        #-# Create Tab If not exist #-#
        self.AddTab(tab)

        self[tab][name] = object

    def AddTab(self, name: str) -> None:

        #-# Creat Tab If not exist #-#
        if not name in self:

            self[name] = {}

    def OpenTab(self, tab: str) -> None:

        self.tab = tab

    def Exit(self) -> None:

        self.isRunning = False
        pygame.quit()
        sys.exit()

    def SetCursorVisible(self, value=True) -> None:

        pygame.mouse.set_visible(value)

    def SetCursorImage(self, image: Object) -> None:

        self.cursor = image

    def DebugLog(self, text):

        if "debugLog" in self:

            self["debugLog"].UpdateText("Normal", text)

        else:

            self["debugLog"] = Text((0, 0), text, 25, backgroundColor=Black, isCentered=False)

    def Draw(self) -> None:

        #-# Fill Background #-#
        if self.tab in self.backgroundColors:

            self.window.fill(self.backgroundColors[self.tab])

        #-# Draw Objects #-#
        if self.tab in self:

            for object in self[self.tab].values():
                    
                object.Draw(self.window)

        #-# Draw Cursor #-#
        if hasattr(self, "cursor"):

            self.cursor.Draw(self.window)    

        if "debugLog" in self and self.isDebugLogVisible:

            self["debugLog"].Draw(self.window)

        pygame.display.update()
