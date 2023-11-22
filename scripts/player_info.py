
class PlayerInfo():

    def __init__(self, ID, state="menu") -> None:
        
        self.ID = ID
        self.name = ""
        self.room = None
        self.state = state

    def EnterLobby(self, name):
        
        self.name = name
        
        print(f"[SERVER] => {self.name} ({self.ID}) is entered to lobby.")

    def JoinRoom(self, room):
        
        self.state = "room"
        self.room = room
        room.append(self)

        print(f"[SERVER] => {self.name} ({self.ID}) is joined to room {room.ID}.")