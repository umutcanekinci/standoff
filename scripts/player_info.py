class PlayerInfo():

    def __init__(self, ID=1, address=(0, 0), name="", characterName="") -> None:
        
        self.ID = ID
        self.adress = self.IP, self.PORT = address

        self.SetName(name)
        self.SetCharacterName(characterName)

        self.room = None

    def SetName(self, name):

        self.name = name

    def SetCharacterName(self, name):

        self.characterName = name

    def JoinRoom(self, room):
        
        self.room = room
        room.append(self)
        self.spawnPoint = len(self.room)
        

class ZombieInfo:

    def __init__(self, ID, room, targetBase, spawnPoint) -> None:

        self.ID, self.room, self.targetBase, self.spawnPoint = ID, room, targetBase, spawnPoint
    