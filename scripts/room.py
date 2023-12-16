from player_info import PlayerInfo

class Room(list[PlayerInfo]):

    def __init__(self, ID, size):

        super().__init__()

        self.ID = ID
        self.size = size

class Team(list[PlayerInfo]):

    def __init__(self, ID, size):

        super().__init__()

        self.ID = ID
        self.size = size