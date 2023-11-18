#region Import Packages

try:

    import pygame
    from pygame.math import Vector2 as Vec
    import math

    from default.application import Application
    from default.text import Text
    from default.object import Object
    from default.inputBox import InputBox
    from default.button import Button
    from default.image import GetImage
    from default.path import *

    from settings import *
    from level import *
    from client import Client
    
except ImportError as e:

    print("An error occured while importing packages:  " + str(e))

#endregion

class Tile(Object):
    
    def __init__(self, size, rowNumber, columnNumber, color) -> None:

        super().__init__((size*columnNumber, size*rowNumber), WINDOW_RECT, (size, size))

        self.AddSurface("Normal", pygame.Surface((size, size)))
        self.color = color
        pygame.draw.rect(self["Normal"], self.color, pygame.Rect(0, 0, self.rect.width, self.rect.height))

class Wall(Tile):

    def __init__(self, size, rowNumber, columnNumber, color) -> None:
        
        super().__init__(size, rowNumber, columnNumber, color)

class TileMap(list[Tile]):

    def LoadLevel(self, level, tileSize, borderWidth):

        #region control level

        if not level or len(level) == 0:

            print("This level is not suitable for rendering!")
            return ImportError
        
        for i in range(len(level)):

            if len(level[i]) != len(level[0]):

                print("This level is not suitable for rendering!")
                return ImportError
        
        #endregion

        self.level = level
        self.borderWidth = borderWidth
        self.rowCount = len(self.level)
        self.columnCount = len(self.level[0])
        self.tileSize = tileSize
        self.surface = pygame.Surface((self.columnCount*self.tileSize + borderWidth/2, self.rowCount*self.tileSize + borderWidth/2))
        self.rect = self.surface.get_rect()

        self.CreateTiles()

    def CreateTiles(self):

        if hasattr(self, "level") and self.level:

            self.walls = []
            self.spawnPoints = {}

            for rowNumber, row in enumerate(self.level):

                self.append([])

                for columnNumber, tile in enumerate(row):

                    if tile == 1:

                        self[rowNumber].append(Tile(self.tileSize, rowNumber, columnNumber, Blue))
                        self.walls.append(Wall(self.tileSize, rowNumber, columnNumber, Blue))

                    else:

                        self[rowNumber].append(Tile(self.tileSize, rowNumber, columnNumber, Black))
                    
                    if type(tile) is str and "P" in tile:

                        self.spawnPoints[int(tile[1:])] = self.tileSize*columnNumber, self.tileSize*rowNumber

        else:

            print("Please load a level before rendering!")

    def Render(self):

        if hasattr(self, "level") and self.level:

            self.DrawTiles()
            self.DrawGrid()

        else:

            print("Please load a level before rendering!")

    def DrawTiles(self):

        # Draw tiles
        for row in self:

            for tile in row:

                tile.Draw(self.surface)

    def DrawGrid(self):

        # Draw column lines
        for columnNumber in range(self.columnCount+1):

            pygame.draw.line(self.surface, Gray, (columnNumber*self.tileSize, 0), (columnNumber*self.tileSize, self.rect.height), self.borderWidth)

        # Draw row lines
        for rowNumber in range(self.rowCount+1):

            pygame.draw.line(self.surface, Gray, (0, rowNumber*self.tileSize), (self.rect.width, rowNumber*self.tileSize), self.borderWidth)

    def Draw(self, surface: pygame.Surface):

        self.camera.Draw(surface, self.surface, self.rect)

class Camera():

    def __init__(self, size: tuple, map: TileMap):
        
        self.rect = pygame.Rect((0, 0), size)
        self.map = map
        self.map.camera = self
        
    def Follow(self, target):
        
        self.rect.x, self.rect.y = -target.x + (self.rect.width / 2), -target.y + (self.rect.height / 2)
        
        self.rect.x = max(self.rect.width - self.map.rect.width, min(0, self.rect.x))
        self.rect.y = max(self.rect.height - self.map.rect.height, min(0, self.rect.y))

    def Apply(self, rect: pygame.Rect):

        return (self.rect.x + rect.x, self.rect.y + rect.y)

    def Draw(self, surface, objectSurface, rect):

        surface.blit(objectSurface, self.Apply(rect))

class Bullet(Object):

    def __init__(self, position, targetPosition) -> None:

        super.__init__(position, WINDOW_RECT, (10, 5))
        self.AddSurface("Normal", pygame.Surface((self.rect.size)))
        self["Normal"].fill(Black)
        self.SetVelocity(Vec(targetPosition - self.rect.topleft).normalize())

    #def Move(self):

    #    self.rect.topleft += self.velocity

class Bullets(list[Bullet]):

    def __init__(self):

        pass

    def Draw(self, surface):

        for bullet in self:

            bullet.Draw(surface)

class Player():

    def __init__(self, ID, name, size, position, color, game) -> None:

        self.name = name
        self.ID = ID
        self.color = color
        self.game = game
        self.map = game.map
        self.camera = game.camera
        self.nameText = Text((0, 0), WINDOW_RECT, self.name, 25, color=color)
        
        # Player graphic
        self.surface = pygame.Surface((size, size), pygame.SRCALPHA)
        self.rect = self.surface.get_rect()

        self.originalImage = GetImage(ImagePath("idle", "characters/hitman"))
        self.surface.blit(self.originalImage, self.rect)

        self.collisionSurface = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        pygame.draw.rect(self.collisionSurface, self.color, self.rect, 2)

        self.rect.topleft = position

        #region Physical Variables

        # Force (Newton)
        self.force = Vec(3, 3)
        self.frictionalForce = Vec(-1., -1.)
        self.netForce = Vec()

        # Acceleration (m/s**2)
        self.acceleration = Vec()
        self.maxAcceleration = 5

        # Velocity / Speed (m/s*2)
        self.velocity = Vec()
        self.maxMovSpeed = 5

        # Rotation
        self.forceRotation = Vec()

        # Weight (Kilogram)
        self.density = 25 # d (kg/piksel**2)
        self.weight = (self.rect.width/TILE_SIZE * self.rect.height/TILE_SIZE) * self.density # m = d*v

        #endregion

    def Move(self, keys, deltaTime):
         
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

        # Calculate net force
        self.netForce = self.force.elementwise() * self.forceRotation

        # apply frictional force
        if self.velocity.length() != 0:

            if abs(self.netForce.x) > self.frictionalForce.x:

                self.netForce.x += self.frictionalForce.x * self.velocity.normalize().x * deltaTime

            if abs(self.netForce.y) > self.frictionalForce.y:

                self.netForce.y += self.frictionalForce.y * self.velocity.normalize().y * deltaTime
            
        # Calculate acceleration
        self.acceleration = self.netForce / self.weight

        # Clamp acceleration
        self.acceleration.x = max(-self.maxAcceleration, min(self.maxAcceleration, self.acceleration.x))
        self.acceleration.y = max(-self.maxAcceleration, min(self.maxAcceleration, self.acceleration.y))

        # Update velocity
        self.velocity += self.acceleration * deltaTime

        # Apply friction to slow down the player
        #friction = 0.1
        #self.velocity -= self.velocity * friction * deltaTime

        # Limit velocity to a maximum speed
        if self.velocity.length() > self.maxMovSpeed:

            self.velocity.scale_to_length(self.maxMovSpeed)

        if abs(self.velocity.x) < 0.01:

            self.velocity.x = 0

        if abs(self.velocity.y) < 0.01:
            
            self.velocity.y = 0
        
        newPosition = self.rect.copy()
        newPosition.topleft = newPosition.topleft + (self.velocity * deltaTime) + (0.5 * self.acceleration * deltaTime * deltaTime)

        for wall in self.map.walls:

            if pygame.Rect(newPosition.x, self.rect.y, self.rect.width, self.rect.height).colliderect(wall.rect):

                if newPosition.x > self.rect.x:

                    newPosition.right = wall.rect.left
                
                else:

                    newPosition.left = wall.rect.right

            if pygame.Rect(self.rect.x, newPosition.y, self.rect.width, self.rect.height).colliderect(wall.rect):

                if newPosition.y > self.rect.y:

                    newPosition.bottom = wall.rect.top
                
                else:

                    newPosition.top = wall.rect.bottom

        self.UpdatePosition(newPosition.topleft)

    def HandleEvents(self, event, mousePosition, keys):

        if event.type == pygame.MOUSEBUTTONDOWN:

            self.Fire(mousePosition)

    def Fire(self, targerPosition):

        time = pygame.time.get_ticks() / 1000
        fireRate = 1

        if not hasattr(self, "lastFireTime"):

            self.lastFireTime = 0

        if time - self.lastFireTime > fireRate:

            self.game.bullets.append(Bullet(self.rect.topleft, targerPosition))

            self.lastFireTime = time

    def Rotate(self, mousePosition, deltaTime):

        return
    
        angle = math.atan2(mousePosition[1] - self.rect.centery, mousePosition[0] - self.rect.centerx)
        angle = math.degrees(angle)  # Convert radians to degrees
        self.surface = pygame.transform.rotate(self.originalImage, -angle)
        self.rect = self.surface.get_rect(center=self.rect.center)

    def UpdatePosition(self, position):

        self.rect.topleft = position
        self.nameText.rect.center = (self.rect.centerx, self.rect.top - 15)
    
    def Draw(self, surface: pygame.Surface):
        
        self.camera.Draw(surface, self.surface, self.rect)
        self.camera.Draw(surface, self.nameText["Normal"], self.nameText.rect)

        if self.game.developMode:
            
            self.camera.Draw(surface, self.collisionSurface, self.rect)

class Zombie():

    def __init__(self) -> None:
        pass

class Players(list[Player]):

    def __init__(self) -> None:
        
        super().__init__()

    def Add(self, playerID, playerName, playerSize=TILE_SIZE, playerPosition=(0, 0), playerColor=Red, game=None):
        
        player = Player(playerID, playerName, playerSize, playerPosition, playerColor, game)
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

        self.bullets = Bullets()

        super().__init__(WINDOW_TITLE, WINDOW_SIZE, {"mainMenu" : CustomBlue}, developMode=DEVELOP_MODE)
        
        self.AddObject("mainMenu", "title", Text(("CENTER", 250), self.rect, self.title, 60, color=Red))
        self.AddObject("mainMenu", "menu", MainMenu())
        
        self.StartClient()
        self.OpenTab("mainMenu")

    def StartClient(self) -> None:

        self.client = Client(self)
        self.client.Start()
        
        self.CreateMap()
        self.CreateCamera()
        self.CreatePlayers()

    def Start(self):
        
        if self.client.isConnected:

            self.OpenTab("game")
            self.CreateMainPlayer()

    def GetData(self, data) -> None:

        if data:

            if data['command'] == "!PLAYERS":

                for playerID, playerName in data['value']:

                    self.players.Add(playerID, playerName, game=self)

                self["mainMenu"]["menu"].playerCountText.UpdateText("Normal", str(len(self.players)) + " Players are Online")

            elif data['command'] == "!PLAYER_ID":
                
                self.player = self.players.Add(data['value'], self["mainMenu"]["menu"].playerNameEntry.text, TILE_SIZE, self.map.spawnPoints[1], Yellow, self)

            elif data['command'] == "!NEW_PLAYER":
                
                self.players.Add(*data['value'], game=self)

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

        self.camera = Camera(self.rect.size, self.map)

    def CreateMap(self) -> None:

        self.map = TileMap()
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
                self.player.Rotate(self.mousePosition, self.deltaTime)
                self.camera.Follow(self.player.rect)
                self.client.SendData({'command' : "!PLAYER_RECT", 'value' : [self.player.ID, pygame.Rect(self.player.rect.x - self.map.rect.x, self.player.rect.y - self.map.rect.y, self.player.rect.w, self.player.rect.h)]})

        super().Draw()

    def Exit(self) -> None:

        self.client.DisconnectFromServer()
        return super().Exit()
            