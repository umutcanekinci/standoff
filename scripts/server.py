import socket
import threading
import pickle
from settings import *
import struct
from player_info import PlayerInfo
from team import Team

class Server:

    def Start(self):

        self.clientSockets = {} # id : clientSocket
        self.teamList = {} # id : playerList
        self.players = {} # playerId : player

        # Creating a server socket and providing the address family (socket.AF_INET) and type of connection (socket.SOCK_STREAM), i.e. using TCP connection.
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        print("[SERVER] => Server is started.")
        
        self.Bind()

    def Bind(self):

        try:

            # Binding the socket with the IP address and Port Number.
            self.server.bind(SERVER_ADDR)

        except socket.error as error:

            print("[SERVER] => An error occured during connecting to server: " + str(error))

        else:

            print("[SERVER] => Server is binded.")
            
            self.Listen()
        
    def Listen(self):

        self.server.listen()
        print(f"[SERVER] => Server is listening on IP = {SERVER_IP} at PORT = {SERVER_PORT}")
        playerID, self.teamID = 0, 0

        # running an infinite loop to accept continuous client requests.
        while True:

            # Making the server listen to new connections. when a new connection has detected codes will continue 
            clientSocket, addr = self.server.accept()
            playerID += 1

            self.clientSockets[playerID] = clientSocket
            self.players[playerID] = PlayerInfo(playerID)
            
            print(f"[SERVER] => {addr[0]} is connected from PORT = {addr[1]}.")
            print(f"[SERVER] => Player count is now {str(len(self.players))}.")

            self.SendData(clientSocket, {'command' : "!SET_PLAYER_ID", 'value' : self.players[playerID]})
            self.SendDataToAllClients({'command' : "!SET_PLAYER_COUNT", 'value' : str(len(self.players))})

            # starting a new thread
            thread = threading.Thread(target=self.HandleClient, args=(clientSocket, addr))
            thread.start()

    def RecieveData(self, clientSocket):

        try:

            packedLength = clientSocket.recv(HEADER)
            dataLength = struct.unpack('!I', packedLength)[0]
            serializedData = clientSocket.recv(dataLength)
            return pickle.loads(serializedData)

        except (socket.error, ConnectionResetError):

            self.DisconnectClient(clientSocket)

    def SendData(self, clientSockets, dataToSend):
        
        if type(clientSockets) == socket.socket:

            clientSockets = [clientSockets]

        for clientSocket in clientSockets:
            
            try:

                serializedData = pickle.dumps(dataToSend)
                dataLength = len(serializedData)
                packedLength = struct.pack('!I', dataLength)
                clientSocket.sendall(packedLength + serializedData)

            except (socket.error, ConnectionResetError):

                self.DisconnectClient(clientSocket)
                continue

    def SendDataToAllClients(self, data, exceptions=[]):

        clientSockets = list(self.clientSockets.values())

        for exception in exceptions:

            clientSockets.remove(exception)

        self.SendData(clientSockets, data)

    def CreateTeam(self):

        self.teamID += 1
        self.teamList[self.teamID] = Team(self.teamID, 100)

    def HandleClient(self, clientSocket: socket.socket, addr):

        ip, port = addr
        connected = True

        try:

            while connected:
                
                data = self.RecieveData(clientSocket)

                if data:

                    if data['command'] == '!ENTER_LOBBY': # a player entered to lobby

                        player = self.players[data['value'][0]]
                        player.EnterLobby(data['value'][1])

                    elif data['command'] == '!JOIN_ROOM':

                        playerID, teamID = data['value']

                        if len(self.teamList) > 0 and teamID in self.teamList.keys():

                            player = self.players[playerID]
                            player.JoinTeam(self.teamList[teamID])

                            for p in player.team:

                                self.SendData(self.clientSockets[p.ID], {'command' : "!JOIN_ROOM", 'value' : self.teamList[teamID]})

                        else:

                            self.SendData(clientSocket, {'command' : "!JOIN_ROOM", 'value' : False})

                    elif data['command'] == '!CREATE_ROOM':

                            player = self.players[data['value']]
                            self.CreateTeam()
                            player.JoinTeam(self.teamList[self.teamID])
                            self.SendData(clientSocket, {'command' : "!JOIN_ROOM", 'value' : self.teamList[self.teamID]})

                    elif data['command'] == '!START_GAME':

                        #teamID = data['value']
                        #team = self.teamList[teamID]
                        #team.StartGame()

                        self.SendData(self.clientSockets[playerID], {'command' : '!START_GAME'})

                    elif data['command'] == '!SET_PLAYER_RECT':

                        playerID = data['value'][0]

                        #playerInfo = self.players[playerID]
                        #team = playerInfo.team

                        for player in self.players.values(): #team:

                            if player.ID != playerID:
                                
                                self.SendData(self.clientSockets[player.ID], data)

                    elif data['command'] == '!DISCONNECT':

                        connected = False
                        self.DisconnectClient(clientSocket, ip)

                else:

                    connected = False
        
        except(socket.error, ConnectionResetError):
            
            connected = False
            self.DisconnectClient(clientSocket, ip)
        
        finally:

            clientSocket.close()

    def DisconnectClient(self, clientSocket, ip=""):
        
        playerID = list(self.clientSockets.keys())[list(self.clientSockets.values()).index(clientSocket)]
        self.clientSockets.pop(playerID)
        
        if self.players[playerID].state == "team":
            
            if len(self.players[playerID].team) == 1:

                self.teamList.pop(self.players[playerID].team.ID)
            
            else:

                self.players[playerID].team.remove(self.players[playerID])

        print(f"[SERVER] => {self.players[playerID].name} ({ip}) is dissconnected.")
        self.players.pop(playerID)
        print(f"[SERVER] => Player count is now {str(len(self.players))}.")

        self.SendDataToAllClients({'command' : "!DISCONNECT", 'value' : playerID})
        
server = Server()
server.Start()