#region Import Packages

try:

    import pygame
    from pygame.math import Vector2 as Vec

    from default.application import Application
    from default.text import Text
    from default.object import Object
    from default.inputBox import InputBox
    from default.
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


class Game(Application):

    def __init__(self) -> None:

        super().__init__(WINDOW_TITLE, WINDOW_SIZE)

        self.CreateCamera()
        self.CreateMap()
        self.CreateMainPlayer()

        self.playerCountText = Text((500, 0), " ", 20, isCentered=False, backgroundColor=Black, color=Yellow)


        #Lobby
        lobbyPanel = Object((0, 0), WINDOW_SIZE)
        lobbyPanel.AddSurface("Normal", pygame.Surface(WINDOW_SIZE, pygame.SRCALPHA))
        lobbyPanel["Normal"].fill((*Gray, 100))

        playerNameEntry = InputBox(100, 100, 150, 60, '')

        
        self.AddObject("lobby", "panel", lobbyPanel)
        self.AddObject("lobby", "player_name", playerNameEntry)
        self.AddObject("lobby", "menu", Menu)


        self.AddObject("game", "player count text", self.playerCountText)

        self.OpenTab("lobby")
        self.StartClient()

    def StartClient(self) -> None:

        self.client = Client(self)
        self.client.Start()
        self.previousMessage = None

    def GetMessage(self, message) -> None:
        print(message)
        if message:

            if message['command'] == "!NEW_PLAYER":
                
                if hasattr(self.player, "ID"):

                    self.CreatePlayer(message['data'])

                else:

                    self.player.ID = message['data']

            elif message['command'] == "!PLAYER_IDs":

                for ID in message['data']:

                    self.CreatePlayer(ID)

            elif message['command'] == "!PLAYER_RECT":

                print("AAAAAAA")
                self.players[message['playerID']].rect.topleft = message['data'].topleft
                
    def CreateCamera(self) -> None:

        self.camera = Camera()

    def CreateMap(self) -> None:

        self.map = TileMap(self.camera)
        self.map.LoadLevel(level1, TILE_SIZE, BORDER_WIDTH)
        self.map.Render()

        self.AddObject("game", "map", self.map)

    def CreateMainPlayer(self) -> None:

        self.players = {}
        self.player = Player(TILE_SIZE, self.map.spawnPoints[1], Yellow)
        #self.players[1] = self.player
        self.AddObject("game", "player", self.player)

    def CreatePlayer(self, playerID) -> None:

        player = Player(TILE_SIZE, (0, 0), Red)
        self.players[playerID] = player

    def Draw(self) -> None:

        if hasattr(self.player, "ID"):

            self.player.Move(self.deltaTime)
            self.camera.Move(self.player.position, WINDOW_SIZE, self.map.rect.size)
            self.client.SendMessage({'command' : "!PLAYER_RECT", 'playerID' : self.player.ID, 'data' : self.player.rect})

        super().Draw()

        for player in self.players.values():

            player.Draw(self.window)

    def Exit(self) -> None:

        self.client.DisconnectFromServer()
        return super().Exit()
            