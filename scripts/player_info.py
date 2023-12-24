from settings import *

class PlayerInfo():

    def __init__(self, ID=1, address=(0, 0), name="", characterName="") -> None:
        
        self.ID = ID
        self.adress = self.IP, self.PORT = address
        self.size = 1
        self.SetName(name)
        self.SetCharacterName(characterName)

        self.room = None

    def SetName(self, name: str):

        self.name = name

    def SetCharacterName(self, name: str):

        self.characterName = name

    def JoinRoom(self, room, isRuler):
        
        self.isReady = isRuler
        self.isRuler = isRuler
        self.room = room
        room.append(self)
        self.baseNumber = len(self.room)
        self.basePoint = self.room.basePoints[self.baseNumber]

    def LeaveRoom(self):

        self.room.remove(self)
        self.room = None

class MobInfo:

    def __init__(self, ID, room, targetBase, position, targetPlayer=None) -> None:

        self.ID, self.room, self.targetBase, self.position, self.size, self.targetPlayer = ID, room, targetBase, position, 1, targetPlayer
    