import socket
import threading
import pickle
from settings import *
import struct
from player_info import PlayerInfo
from room import Room

class Server:

    def Start(self):

        self.clientSockets = {} # id : clientSocket
        self.gameList = {} # id : playerList
        self.roomList = {} # id : playerList
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
        playerID, self.roomID = 0, 0

        # running an infinite loop to accept continuous client requests.
        while True:

            # Making the server listen to new connections. when a new connection has detected codes will continue 
            clientSocket, addr = self.server.accept()
            playerID += 1

            self.clientSockets[playerID] = clientSocket
            self.players[playerID] = PlayerInfo(playerID)
            
            print(f"[SERVER] => {addr[0]} is connected from PORT = {addr[1]}.")
            print(f"[SERVER] => Player count is now {str(len(self.players))}.")

            self.SendData([clientSocket], {'command' : "!SET_PLAYER_ID", 'value' : playerID})
            self.SendDataToAllClients({'command' : "!SET_PLAYERS", 'value' : self.players})

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

    def OpenRoom(self):

        self.roomID += 1
        self.roomList[self.roomID] = Room(self.roomID, 100)

    def HandleClient(self, clientSocket: socket.socket, addr):

        ip, port = addr
        connected = True

        try:

            while connected:
                
                data = self.RecieveData(clientSocket)

                if data:

                    if data['command'] == '!ENTER_LOBBY': # a player entered to lobby

                        player = self.players[data['value'][0]]

                        if len(self.roomList) > 0:

                            player.EnterLobby(data['value'][1])
                            
                        else:

                            self.OpenRoom()
                            player.JoinRoom(self.roomList[self.roomID])
                            self.SendData([clientSocket], {'command' : "!JOIN_ROOM", 'value' : self.roomList[self.roomID]})

                    elif data['command'] == '!JOIN_ROOM':

                        playerID, roomID = data['value']

                        if len(self.roomList) > 0 and roomID in self.roomList.keys():

                            player = self.players[playerID]
                            player.JoinRoom(self.roomList[roomID])

                            for p in player.room:

                                self.SendData([self.clientSockets[p.ID]], {'command' : "!JOIN_ROOM", 'value' : self.roomList[roomID]})

                        else:

                            self.SendData([clientSocket], {'command' : "!JOIN_ROOM", 'value' : False})

                    elif data['command'] == '!CREATE_ROOM':

                            player = self.players[data['value']]
                            self.OpenRoom()
                            player.JoinRoom(self.roomList[self.roomID])
                            self.SendData([clientSocket], {'command' : "!JOIN_ROOM", 'value' : self.roomList[self.roomID]})

                    elif data['command'] == '!START_GAME':

                        roomID = data['value']
                        room = self.roomList[roomID]
                        room.StartGame()

                        self.SendData([self.clientSockets[player.ID] for player in room], {'command' : '!START_GAME'})

                    elif data['command'] == '!SET_PLAYER_RECT':

                        playerID = data['value']

                        for player in self.players[playerID].room:

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
        
        if self.players[playerID].state == "room":
            
            if len(self.players[playerID].room) == 1:

                self.roomList.pop(self.players[playerID].room.ID)
            
            else:

                self.players[playerID].room.remove(self.players[playerID])

        print(f"[SERVER] => {self.players[playerID].name} ({ip}) is dissconnected.")
        self.players.pop(playerID)
        print(f"[SERVER] => Player count is now {str(len(self.players))}.")

        self.SendDataToAllClients({'command' : "!DISCONNECT", 'value' : playerID})
        
server = Server()
server.Start()