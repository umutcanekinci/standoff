from util.constants import *

class PlayerInfo():

    def __init__(self, ID=1, address=(0, 0), name="", characterName="") -> None:
        
        self.ID = ID
        self.address = self.IP, self.PORT = address
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
        # Take the first base point not already claimed by a room mate (len()-based
        # numbering breaks when a player leaves and another joins).
        used = {mate.baseNumber for mate in room if mate is not self and hasattr(mate, 'baseNumber')}
        self.baseNumber = next(number for number in room.basePoints if number not in used)
        self.basePoint = self.room.basePoints[self.baseNumber]

    def LeaveRoom(self):

        self.room.remove(self)
        self.room = None

class MobInfo:

    def __init__(self, ID, room, targetBase, position, targetPlayer=None) -> None:

        self.ID, self.room, self.targetBase, self.position, self.size, self.targetPlayer = ID, room, targetBase, position, 1, targetPlayer
    