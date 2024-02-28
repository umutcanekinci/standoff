from settings import *
from path import *
import sys, os
from pygame import mixer
from object import Object
from text import Text


class Application:

    # Those will be current monitor size
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

        infoObject = pygame.display.Info()
        infoObject.current_w, infoObject.current_h
        self.window = pygame.display.set_mode(self.rect.size)

    def CenterWindow(self) -> None:

        os.environ['SDL_VIDEO_CENTERED'] = '1'

    def SetFPS(self, FPS: int) -> None:
        
        self.FPS = FPS

    def SetTitle(self, title: str) -> None:
        
        self.title = title
        pygame.display.set_caption(self.title)

    def SetSize(self, size: tuple) -> None:

        self.rect = pygame.Rect((0, 0), WINDOW_SIZE)

    def SetBackgorundColor(self, colors: list = {}) -> None:

        self.backgroundColors = colors

    def SetDevelopMode(self, value: bool):

        self.developMode = value

    def Exit(self) -> None:

        self.isRunning = False
        sys.exit()

    def SetCursorVisible(self, value=True) -> None:

        pygame.mouse.set_visible(value)

    def SetCursorImage(self, image: Object) -> None:

        self.cursor = image

    def DebugLog(self, text):

        if hasattr(self, "debugLog"):

            self.debugLog.UpdateText(str(text))

        else:

            self.debugLog = Text((0, 0), str(text), 25, backgroundColor=Black)

    def Run(self) -> None:
        
        #-# Starting App #-#
        self.isRunning = True

        #-# Main Loop #-#
        while self.isRunning:

            #-# FPS #-#
            self.deltaTime = self.clock.tick(self.FPS) * .001 * self.FPS
            self.DebugLog(f"{int(self.clock.get_fps())} FPS")

            #-# Getting Mouse Position #-#
            self.mousePosition = pygame.mouse.get_pos()

            #-# Getting Pressed Keys #-#
            self.keys = pygame.key.get_pressed()

            #-# Handling Events #-#
            for event in pygame.event.get():

                self.HandleEvents(event)

            self.Update()

            #-# Draw Objects #-#
            self.Draw()
    

    def HandleEvents(self, event: pygame.event.Event) -> None:
        
        self.HandleExitEvents(event)
        
        #-# Set Cursor Position #-#
        if hasattr(self, "cursor"):

            self.cursor.SetPosition(self.mousePosition)   

        if event.type == pygame.KEYDOWN and event.key == pygame.K_F3:

            self.SetDevelopMode(not self.developMode)

    def HandleExitEvents(self, event: pygame.event.Event) -> None:

        if event.type == pygame.QUIT:

            self.Exit()

        elif event.type == pygame.KEYDOWN:

            if event.key == pygame.K_ESCAPE:

                self.Exit()
    
    def Update(self):

        pass

    def Draw(self):

        #-# Draw Cursor #-#
        if hasattr(self, "cursor"):

            self.cursor.Draw(self.window)    

        #-# Draw debug log #-#
        if self.developMode and hasattr(self, "debugLog"):

            self.debugLog.Draw(self.window)

        pygame.display.update()
