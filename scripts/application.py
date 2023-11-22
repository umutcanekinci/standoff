from settings import *
from path import *
import sys, os
from pygame import mixer
from object import Object
from text import Text

class Application(dict[str : pygame.Surface]):
    
    def __init__(self, developMode=False) -> None:
        
        super().__init__()
        self.InitPygame()
        self.InitClock()
        self.InitMixer()
        self.SetTitle(WINDOW_TITLE)
        self.SetSize(WINDOW_SIZE)
        self.SetDevelopMode(developMode)
        self.OpenWindow()
        self.SetFPS(FPS)
        self.SetBackgorundColor(BACKGROUND_COLORS)
        self.tab = ""

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

        self.window = pygame.display.set_mode(self.rect.size)

    def CenterWindow(self) -> None:

        os.environ['SDL_VIDEO_CENTERED'] = '1'

    def SetFPS(self, FPS: int) -> None:
        
        self.FPS = FPS

    def SetTitle(self, title: str) -> None:
        
        self.title = title
        pygame.display.set_caption(self.title)

    def SetSize(self, size: tuple) -> None:

        self.rect = pygame.Rect((0, 0), size)

    def SetBackgorundColor(self, colors: list = {}) -> None:

        self.backgroundColors = colors

    def SetDevelopMode(self, value: bool):

        self.developMode = value


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

            self["debugLog"].UpdateText(str(text))

        else:

            self["debugLog"] = Text((0, 0), str(text), 25, backgroundColor=Black)

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

            self.Update()

            #-# Fill Background #-#
            if self.tab in self.backgroundColors:

                self.window.fill(self.backgroundColors[self.tab])

            #-# Draw Objects #-#
            self.Draw()

            #-# Draw Cursor #-#
            if hasattr(self, "cursor"):

                self.cursor.Draw(self.window)    

            #-# Draw debug log #-#
            if self.developMode and "debugLog" in self:

                self["debugLog"].Draw(self.window)
    
            pygame.display.update()

    def HandleEvents(self, event: pygame.event.Event) -> None:
        
        #-# Set Cursor Position #-#
        if hasattr(self, "cursor"):

            self.cursor.SetPosition(self.mousePosition)   

        if event.type == pygame.KEYDOWN and event.key == pygame.K_F3:

            self.SetDevelopMode(not self.developMode)

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
    
    def Update(self):

        pass

    def Draw(self):

        #-# Draw Objects #-#
        if self.tab in self:

            for object in self[self.tab].values():
                    
                object.Draw(self.window)
