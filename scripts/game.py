#region Import Packages

try:

    import pygame
    from pygame.math import Vector2 as Vec

    from default.application import Application
    from default.text import Text
    from default.object import Object
    from default.inputBox import InputBox
    from default.button import Button

    from settings import *
    from level import *
    from client import Client

except ImportError as e:

    print("An error occured while importing packages:  " + str(e))

#endregion

class Camera():

    def __init__(self):

        self.x, self.y = 0, 0

    def Apply(self, rect: pygame.Rect):

        return (self.x, self.y)

    def Move(self, position, windowSize, mapSize):
        
        self.x, self.y = -position.x + (windowSize[0] / 2), -position.y + (windowSize[1] / 2)

        self.x = min(0, self.x)
        self.x = max(windowSize[0] - mapSize[0], self.x)
        self.y = min(0, self.y)
        self.y = max(windowSize[1] - mapSize[1], self.y)

    def Draw(self, surface, object):

        surface.blit(object.surface, self.Apply(object.rect))

class Tile():
    
    def __init__(self, size, rowNumber, columnNumber, color) -> None:

        self.surface = pygame.Surface((size, size))
        self.rect = self.surface.get_rect()
        self.rect.topleft = size*columnNumber, size*rowNumber
        self.color = color
        pygame.draw.rect(self.surface, self.color, pygame.Rect(0, 0, self.rect.width, self.rect.height))

    def Draw(self, surface: pygame.Surface):

        surface.blit(self.surface, self.rect)

class TileMap(list[Tile]):

    def __init__(self, camera):
        
        self.camera = camera
        self.spawnPoints = {}
        super().__init__()

    def LoadLevel(self, level, tileSize, borderWidth):

        if not level or len(level) == 0:

            print("This level is not suitable for rendering!")
            return ImportError
        
        for i in range(len(level)):

            if len(level[i]) != len(level[0]):

                print("This level is not suitable for rendering!")
                return ImportError
        
        self.level = level
        self.borderWidth = borderWidth
        self.rowCount = len(self.level)
        self.columnCount = len(self.level[0])
        self.tileSize = tileSize
        self.surface = pygame.Surface((self.columnCount*self.tileSize + borderWidth/2, self.rowCount*self.tileSize + borderWidth/2))
        self.rect = self.surface.get_rect()
        
        self.CreateTiles()

    def CreateTiles(self):

        for rowNumber, row in enumerate(self.level):

            self.append([])

            for columnNumber, tile in enumerate(row):

                self[rowNumber].append(Tile(self.tileSize, rowNumber, columnNumber, Black))
                
                if type(tile) is str and "P" in tile:

                    self.spawnPoints[int(tile[1:])] = self.tileSize*columnNumber, self.tileSize*rowNumber

    def Render(self):

        if self.level:

            # Draw tiles
            for rowNumber, row in enumerate(self):

                for columnNumber, tile in enumerate(row):

                    tile.Draw(self.surface)

            # Draw column lines
            for columnNumber in range(self.columnCount+1):

                pygame.draw.line(self.surface, Gray, (columnNumber*self.tileSize, 0), (columnNumber*self.tileSize, self.rect.height), self.borderWidth)

            # Draw row lines
            for rowNumber in range(self.rowCount+1):

                pygame.draw.line(self.surface, Gray, (0, rowNumber*self.tileSize), (self.rect.width, rowNumber*self.tileSize), self.borderWidth)

        else:

            print("Please load a level before rendering!")

    def Draw(self, surface: pygame.Surface):

        self.camera.Draw(surface, self)

class Player():

    def __init__(self, size, position, color) -> None:

        # Physics

        # Weight (Kilogram)
        self.weight = 10

        # Force (Newton)
        self.movForce = Vec(3, 3)
        self.frictionalForce = Vec(-.12, -.12)
        
        # Velocity / Speed (m/s*2)
        self.velocity = Vec()
        self.maxMovSpeed = 5

        # Acceleration (m/s**2)
        self.acceleration = Vec()

        # Position (m)
        self.position = Vec()

        # Rotation
        self.accelerationRotation = Vec(0, 0)
        self.movementRotation = Vec(0, 0)

        self.surface = pygame.Surface((size, size))
        self.rect = self.surface.get_rect()
        self.rect.topleft = position
        self.color = color

        pygame.draw.rect(self.surface, self.color, pygame.Rect(0, 0, self.rect.width, self.rect.height))

    def HandleEvents(self, event, mousePosition, keys):

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                
            self.accelerationRotation.x = -1

        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            
            self.accelerationRotation.x = 1

        else:

            self.accelerationRotation.x = 0

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            
            self.accelerationRotation.y = -1

        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            
            self.accelerationRotation.y = 1

        else:

            self.accelerationRotation.y = 0

        if self.accelerationRotation.length() != 0:
        
            self.accelerationRotation.normalize()

        self.acceleration = Vec()
        self.netForce = Vec()

        self.netForce.x += self.movForce.x * self.accelerationRotation.x
        self.netForce.y += self.movForce.y * self.accelerationRotation.y

        if self.velocity.length() != 0:

            self.netForce.x += self.frictionalForce.x * self.velocity.normalize().x
            self.netForce.y += self.frictionalForce.y * self.velocity.normalize().y


        if self.netForce.length() != 0:

            self.acceleration += self.netForce / self.weight
         
    def Move(self, deltaTime):

        if self.acceleration.length() != 0:
            
            self.velocity += self.acceleration * deltaTime

        if self.velocity.length() > self.maxMovSpeed:
            
            self.velocity = self.velocity.normalize() * self.maxMovSpeed

        self.position.xy = self.rect.topleft
        self.position += self.velocity * deltaTime + (self.acceleration * .5) * (deltaTime * deltaTime)
        self.rect.topleft = self.position

    def Draw(self, surface: pygame.Surface):

        surface.blit(self.surface, self.rect)

class MainMenu():

    def __init__(self) -> None:

        self.panel = Object(("CENTER", "CENTER"), (400, 800), surfaceRect=WINDOW_RECT)
        self.panel.AddSurface("Normal", pygame.Surface((400, 800), pygame.SRCALPHA))
        self.panel["Normal"].fill((*Gray, 100))
        
        self.playerNameEntry = InputBox(("CENTER", "CENTER"), (150, 60), self.panel.rect, 'asdas')
        
        self.playButton = Button(("CENTER", "CENTER"), (350, 100), text="PLAY", textSize=35, surfaceRect=WINDOW_RECT)
        self.playButton.AddSurface("Normal", pygame.Surface(self.playButton.rect.size))
        self.playButton.AddSurface("Mouse Over", pygame.Surface(self.playButton.rect.size))

        self.playButton["Normal"].fill(Black)
        self.playButton["Mouse Over"].fill(Gray)

        self.playerCountText = Text((150, 750), " ", 20, isCentered=False, backgroundColor=Black, color=Yellow)

    def HandleEvents(self, event, mousePosition, keys):

        self.playerNameEntry.HandleEvents(event, mousePosition, keys)
        self.playButton.HandleEvents(event, mousePosition, keys)

    def Draw(self, surface):

        self.playerCountText.Draw(self.panel["Normal"])

        self.panel.Draw(surface)

        self.playerNameEntry.Draw(surface)
        self.playButton.Draw(surface)
        

class Game(Application):

    def __init__(self) -> None:

        super().__init__(WINDOW_TITLE, WINDOW_SIZE, {"mainMenu" : CustomBlue})
        
        self.AddObject("mainMenu", "menu", MainMenu())
        self.StartClient()
        
        self.OpenTab("mainMenu")

    def StartClient(self) -> None:

        self.client = Client(self)
        self.client.Start()
        self.client.SendData({'command' : '!GET_PLAYERS'})

    def Start(self):
        
        self.CreateCamera()
        self.CreateMap()
        self.CreateMainPlayer()
        self.client.SendData({'command' : "!GET_PLAYER_ID", 'value' : self["mainMenu"]["menu"].playerNameEntry.text})
        self.OpenTab("game")

    def GetData(self, data) -> None:

        if data:

            if data['command'] == "!PLAYERS":
                
                self.players = []

                for playerID, playerName in data['value']:

                    self.CreatePlayer(playerID, playerName)

                self["mainMenu"]["menu"].playerCountText.UpdateText("Normal", str(len(self.players)) + " Players are Online")

            elif data['command'] == "!PLAYER_ID":

                self.player.ID = data['value']

            elif data['command'] == "!NEW_PLAYER":
                
                self.CreatePlayer(*data['value'])

            elif data['command'] == "!PLAYER_RECT":

                for player in self.players:

                    if player.ID == data['playerID']:
                        
                        player.rect.topleft = data['value'].topleft
                        break

    def CreateCamera(self) -> None:

        self.camera = Camera()

    def CreateMap(self) -> None:

        self.map = TileMap(self.camera)
        self.map.LoadLevel(level1, TILE_SIZE, BORDER_WIDTH)
        self.map.Render()

        self.AddObject("game", "map", self.map)

    def CreateMainPlayer(self) -> None:

        self.player = Player(TILE_SIZE, self.map.spawnPoints[1], Yellow)
        self.AddObject("game", "player", self.player)

    def CreatePlayer(self, playerID, playerName) -> None:

        player = Player(TILE_SIZE, (0, 0), Red)
        player.ID = playerID
        player.name = playerName
        self.players.append(player)

    def HandleEvents(self, event: pygame.event.Event) -> None:
        
        if self["mainMenu"]["menu"].playButton.isMouseClick(event, self.mousePosition):

            self.Start()
            
        return super().HandleEvents(event)

    def Draw(self) -> None:

        if self.tab == "game":

            if hasattr(self.player, "ID"):

                self.player.Move(self.deltaTime)
                self.camera.Move(self.player.position, WINDOW_SIZE, self.map.rect.size)
                self.client.SendData({'command' : "!PLAYER_RECT", 'playerID' : self.player.ID, 'value' : self.player.rect})

        super().Draw()

        if self.tab == "game":

            for player in self.players:

                player.Draw(self.window)

    def Exit(self) -> None:

        self.client.DisconnectFromServer()
        return super().Exit()
            