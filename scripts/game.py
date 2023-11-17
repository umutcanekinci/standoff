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

        return (self.x + rect.x, self.y + rect.y)

    def Move(self, position, windowSize, mapSize):
        
        self.x, self.y = -position.x + (windowSize[0] / 2), -position.y + (windowSize[1] / 2)

        self.x = min(0, self.x)
        self.x = max(windowSize[0] - mapSize[0], self.x)
        self.y = min(0, self.y)
        self.y = max(windowSize[1] - mapSize[1], self.y)

    def Draw(self, surface, objectSurface, rect):

        surface.blit(objectSurface, self.Apply(rect))

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

        self.camera.Draw(surface, self.surface, self.rect)

class Player():

    def __init__(self, ID, name, size, position, color, camera) -> None:

        self.name = name
        self.nameText = Text((0, 0), WINDOW_RECT, self.name, 25, color=color)
        self.ID = ID
        self.camera = camera

        # Physics
        # Weight (Kilogram)
        self.weight = 10

        # Force (Newton)
        self.force = Vec(3, 3)
        self.frictionalForce = Vec(-.12, -.12)
        self.netForce = Vec()
        
        # Velocity / Speed (m/s*2)
        self.velocity = Vec()
        self.maxMovSpeed = 5

        # Acceleration (m/s**2)
        self.acceleration = Vec()

        # Position (m)
        self.position = Vec()

        # Rotation
        self.forceRotation = Vec()
        self.movementRotation = Vec()

        self.surface = pygame.Surface((size, size))
        self.rect = self.surface.get_rect()
        self.rect.topleft = position
        self.color = color

        pygame.draw.rect(self.surface, self.color, pygame.Rect(0, 0, self.rect.width, self.rect.height))

    def Move(self, keys, deltaTime):
        
        """
        #region Get the rotation of force

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:

            self.forceRotation.x = -1

        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            
            self.forceRotation.x = 1

        else:

            self.forceRotation.x = 0

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            
            self.forceRotation.y = -1

        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            
            self.forceRotation.y = 1

        else:

            self.forceRotation.y = 0

        #endregion

        # Normalize force rotation
        if self.forceRotation.length() != 0:
        
            self.forceRotation.normalize()

        # Normalize frictional force
        if self.frictionalForce.length() != 0:

            self.frictionalForce.normalize()
        
        self.acceleration = Vec()
        self.netForce = Vec()
        
        self.netForce.x += self.force.x * self.forceRotation.x
        self.netForce.y += self.force.y * self.forceRotation.y

        if self.velocity.length() != 0:

            self.netForce.x += self.frictionalForce.x * self.velocity.normalize().x
            self.netForce.y += self.frictionalForce.y * self.velocity.normalize().y

        if self.netForce.length() != 0:

            self.acceleration += self.netForce / self.weight
            
            # Limit acceleration to a maximum value
            max_acceleration = 5
            self.acceleration.x = max(-max_acceleration, min(max_acceleration, self.acceleration.x))
            self.acceleration.y = max(-max_acceleration, min(max_acceleration, self.acceleration.y))

        if self.acceleration.length() != 0:
            
            self.velocity += self.acceleration * deltaTime

        # Apply friction to slow down the player
        #self.velocity.x *= (1 - friction)
        #self.velocity.y *= (1 - friction)

        # Limit velocity to a maximum speed
        if self.velocity.length() > self.maxMovSpeed:
            
            self.velocity.scale_to_length(min(self.maxMovSpeed, self.velocity.length()))

        self.position.xy = self.rect.topleft
        self.position += (self.velocity * deltaTime) + (0.5 * self.acceleration * deltaTime * deltaTime)
        self.rect.topleft = self.position
        self.nameText.rect.topleft = (self.rect.x + self.nameText.rect.w/2, self.rect.y - self.nameText.rect.h - 5)
        """

            # Get the rotation of force
            
        rotation = Vec(0, 0)

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            rotation.x = -1
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            rotation.x = 1

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            rotation.y = -1
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            rotation.y = 1

        # Normalize force rotation
        if rotation.length() != 0:
            rotation.normalize()

        # Calculate net force
        self.netForce = self.force.elementwise() * rotation

        # Apply friction to slow down the player
        friction = 0.1
        self.velocity -= self.velocity * friction * deltaTime

        # Calculate acceleration
        self.acceleration = self.netForce / self.weight

        # Clamp acceleration
        max_acceleration = 5
        self.acceleration.x = max(-max_acceleration, min(max_acceleration, self.acceleration.x))
        self.acceleration.y = max(-max_acceleration, min(max_acceleration, self.acceleration.y))


        # Update velocity
        self.velocity += self.acceleration * deltaTime

        # Limit velocity to a maximum speed
        if self.velocity.length() > self.maxMovSpeed:
            self.velocity.scale_to_length(self.maxMovSpeed)
        if abs(self.velocity.x) < 0.01:
            self.velocity.x = 0
        if abs(self.velocity.y) < 0.01:
            self.velocity.y = 0
        
        self.UpdatePosition(self.rect.topleft + (self.velocity * deltaTime) + (0.5 * self.acceleration * deltaTime * deltaTime))

    def UpdatePosition(self, position):

        self.rect.topleft = position
        self.nameText.rect.topleft = (self.rect.x + self.nameText.rect.w / 2, self.rect.y - self.nameText.rect.h - 5)
    
    def Draw(self, surface: pygame.Surface):

        if self.camera:

            self.camera.Draw(surface, self.surface, self.rect)
            self.camera.Draw(surface, self.nameText["Normal"], self.nameText.rect)

        else:

            surface.blit(self.surface, self.rect)
            self.nameText.Draw(surface)

class Players(list[Player]):

    def __init__(self) -> None:
        
        super().__init__()

    def Add(self, playerID, playerName, playerSize=TILE_SIZE, playerPosition=(0, 0), playerColor=Red, camera=None):
        
        player = Player(playerID, playerName, playerSize, playerPosition, playerColor, camera)
        self.append(player)
        return player

    def Draw(self, surface):

        for i in range(len(self)):

            self[i].Draw(surface)

class MainMenu():

    def __init__(self) -> None:

        self.panel = Object(("CENTER", "CENTER"), WINDOW_RECT, (400, 400))
        self.panel.AddSurface("Normal", pygame.Surface((400, 400), pygame.SRCALPHA))
        self.panel["Normal"].fill((*Gray, 100))
        
        self.playerNameText = Text(("CENTER", 50), self.panel.screenRect, "PLAYER NAME", 40)
        self.playerNameEntry = InputBox(("CENTER", 100), self.panel.screenRect, (200, 60), '')

        self.playButton = Button(("CENTER", 200), self.panel.screenRect, (300, 75), text="PLAY", textSize=45)
        self.playButton.AddSurface("Normal", pygame.Surface(self.playButton.rect.size))
        self.playButton.AddSurface("Mouse Over", pygame.Surface(self.playButton.rect.size))

        self.playButton["Normal"].fill(Black)
        self.playButton["Mouse Over"].fill(Gray)
        
        self.playerCountText = Text(("CENTER", 350), self.panel.screenRect, "0 Players are Online", 20, backgroundColor=Black, color=Yellow)

    def HandleEvents(self, event, mousePosition, keys):

        self.playerNameEntry.HandleEvents(event, mousePosition, keys)
        self.playButton.HandleEvents(event, mousePosition, keys)

    def Draw(self, surface):

        self.playerNameText.Draw(self.panel["Normal"])
        self.playerNameEntry.Draw(self.panel["Normal"])
        self.playButton.Draw(self.panel["Normal"])
        self.playerCountText.Draw(self.panel["Normal"])
        self.panel.Draw(surface)

class Game(Application):

    def __init__(self) -> None:

        super().__init__(WINDOW_TITLE, WINDOW_SIZE, {"mainMenu" : CustomBlue})
        
        self.AddObject("mainMenu", "title", Text(("CENTER", 250), WINDOW_RECT, self.title, 60, color=Red))
        self.AddObject("mainMenu", "menu", MainMenu())
        
        self.StartClient()
        self.OpenTab("mainMenu")

    def StartClient(self) -> None:

        self.client = Client(self)
        self.client.Start()

        self.CreateCamera()
        self.CreateMap()
        self.CreatePlayers()

    def Start(self):
        
        if self.client.isConnected:

            self.OpenTab("game")
            self.CreateMainPlayer()

    def GetData(self, data) -> None:

        if data:

            if data['command'] == "!PLAYERS":

                for playerID, playerName in data['value']:

                    self.players.Add(playerID, playerName, camera=self.camera)

                self["mainMenu"]["menu"].playerCountText.UpdateText("Normal", str(len(self.players)) + " Players are Online")

            elif data['command'] == "!PLAYER_ID":
                
                self.player = self.players.Add(data['value'], self["mainMenu"]["menu"].playerNameEntry.text, TILE_SIZE, self.map.spawnPoints[1], Yellow)

            elif data['command'] == "!NEW_PLAYER":
                
                self.players.Add(*data['value'], camera=self.camera)

            elif data['command'] == "!PLAYER_RECT":

                for player in self.players:

                    if player.ID == data['value'][0]:
                        
                        player.UpdatePosition(data['value'][1].topleft)
                        break

            elif data['command'] == "!DISCONNECT":

                for player in self.players:

                    if player.ID == data['value'][0]:
                        
                        self.players.remove(player)
                        break

    def CreateCamera(self) -> None:

        self.camera = Camera()

    def CreateMap(self) -> None:

        self.map = TileMap(self.camera)
        self.map.LoadLevel(level1, TILE_SIZE, BORDER_WIDTH)
        self.map.Render()

        self.AddObject("game", "map", self.map)

    def CreatePlayers(self) -> None:

        self.players = Players()
        self.AddObject("game", "players", self.players)
        self.client.SendData({'command' : '!GET_PLAYERS'})

    def CreateMainPlayer(self):

        playerName = self["mainMenu"]["menu"].playerNameEntry.text
        self.client.SendData({'command' : "!GET_PLAYER_ID", 'value' : playerName})

    def HandleEvents(self, event: pygame.event.Event) -> None:

        if self["mainMenu"]["menu"].playButton.isMouseClick(event, self.mousePosition):

            self.Start()

        return super().HandleEvents(event)

    def Draw(self) -> None:
        
        if self.tab == "game":

            if hasattr(self, "player"):

                #self.DebugLog(f"""
                #    Velocity => {self.player.velocity}
                #    Acceleration => {self.player.acceleration}
                #    Position => {self.player.rect.topleft}              
                #    Force => {self.player.force}
                #    NetForce => {self.player.netForce}
                #""")

                self.player.Move(self.keys, self.deltaTime)
                self.camera.Move(self.player.rect, WINDOW_SIZE, self.map.rect.size)
                self.client.SendData({'command' : "!PLAYER_RECT", 'value' : [self.player.ID, pygame.Rect(self.player.rect.x - self.map.rect.x, self.player.rect.y - self.map.rect.y, self.player.rect.w, self.player.rect.h)]})
                self.DebugLog((self.player.rect.x - self.map.rect.x, self.player.rect.y - self.map.rect.y))

        super().Draw()

    def Exit(self) -> None:

        self.client.DisconnectFromServer()
        return super().Exit()
            