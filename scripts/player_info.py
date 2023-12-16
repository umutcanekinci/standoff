class PlayerInfo():

    def __init__(self, ID=1, address=(0, 0), name="", characterName="", state="menu") -> None:
        
        self.ID = ID
        self.adress = self.IP, self.PORT = address

        self.SetName(name)
        self.SetCharacterName(characterName)

        self.team = None
        self.room = None
        self.state = state

    def SetName(self, name):

        self.name = name

    def SetCharacterName(self, name):

        self.characterName = name

    def JoinRoom(self, room):
        
        self.state = "room"
        self.room = room
        room.append(self)