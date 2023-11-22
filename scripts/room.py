from player_info import PlayerInfo

class Room(list[PlayerInfo]):

    def __init__(self, ID, maxPlayerInfoCount):

        super().__init__()

        self.ID = ID
        self.maxPlayerInfoCount = maxPlayerInfoCount
        self.isGameStarted = False

    def StartGame(self):

        self.isGameStarted = True