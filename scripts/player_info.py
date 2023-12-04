
class PlayerInfo():

    def __init__(self, ID, state="menu") -> None:
        
        self.ID = ID
        self.name = ""
        self.team = None
        self.state = state

    def EnterLobby(self, name):
        
        self.name = name
        
        print(f"[SERVER] => {self.name} ({self.ID}) is entered to lobby.")

    def JoinTeam(self, team):
        
        self.state = "team"
        self.team = team
        team.append(self)

        print(f"[SERVER] => {self.name} ({self.ID}) is joined to team {team.ID}.")