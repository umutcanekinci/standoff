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
        self.roomList = {} # id : playerList
        self.players = {} # playerId : player

        # Creating a server socket and providing the address family (socket.AF_INET) and type of connection (socket.SOCK_STREAM), i.e. using TCP connection.
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        print(SERVER_PREFIX+"Server is started.")
        
        self.Bind()

    def Bind(self):

        try:

            # Binding the socket with the IP address and Port Number.
            self.server.bind(SERVER_ADDR)

        except socket.error as error:

            print(SERVER_PREFIX+"An error occured during connecting to server: " + str(error))

        else:

            print(SERVER_PREFIX+"Server is binded.")
            
            self.Listen()
        
    def Listen(self):

        self.server.listen()
        print(f"{SERVER_PREFIX}Server is listening on IP = {SERVER_IP} at PORT = {SERVER_PORT}")
        playerID, self.roomID = 0, 0

        # running an infinite loop to accept continuous client requests.
        while True:

            # Making the server listen to new connections. when a new connection has detected codes will continue 
            clientSocket, address = self.server.accept()
            playerID += 1

            self.clientSockets[playerID] = clientSocket
            player = PlayerInfo(playerID, address)
            self.players[playerID] = player

            print(f"{SERVER_PREFIX}{player.IP} is connected from PORT = {player.PORT}.")
            print(f"{SERVER_PREFIX}Player count is now {str(len(self.players))}.")

            self.SendData(list(self.players.values()), "!SET_PLAYER_COUNT", len(self.players))

            # starting a new thread
            thread = threading.Thread(target=self.HandleClient, args=(clientSocket, player))
            thread.start()

    def RecieveData(self, clientSocket, player):

        try:

            packedLength = clientSocket.recv(HEADER)
            dataLength = struct.unpack('!I', packedLength)[0]
            serializedData = clientSocket.recv(dataLength)
            return pickle.loads(serializedData)

        except (socket.error, ConnectionResetError):

            self.DisconnectClient(player)

    def SendData(self, playerList, command, value=None, exceptions=[]):
        
        dataToSend = {'command': command, 'value': value}

        if not hasattr(playerList, '__iter__'):

            playerList = [playerList]

        for exception in exceptions:

            playerList.remove(exception)

        for player in playerList:

            try:

                serializedData = pickle.dumps(dataToSend)
                dataLength = len(serializedData)
                packedLength = struct.pack('!I', dataLength)
                self.clientSockets[player.ID].sendall(packedLength + serializedData)

            except (socket.error, ConnectionResetError):

                self.DisconnectClient(player.ID)
                continue

    def CreateRoom(self):

        self.roomID += 1
        self.roomList[self.roomID] = Room(self.roomID, 100)

    def HandleClient(self, clientSocket: socket.socket, player):

        connected = True

        try:

            while connected:
                
                data = self.RecieveData(clientSocket, player)

                if data:

                    command = data['command']
                    value = data['value'] if 'value' in data else None

                    if command == '!SET_PLAYER':
                        
                        playerName, characterName = value
                        player.SetName(playerName)
                        player.SetCharacterName(characterName)
                        print(f"{SERVER_PREFIX}{player.name} ({player.ID}) is entered to lobby.")
                        
                    elif command == '!JOIN_ROOM':

                        roomID = value

                        if len(self.roomList) > 0 and roomID in self.roomList.keys():
                            
                            player.JoinRoom(self.roomList[roomID])
                            print(f"{SERVER_PREFIX}{player.name} ({player.ID}) is joined a room {roomID}.")

                            for roomMate in player.room:

                                self.SendData(roomMate, "!SET_ROOM", roomMate)

                        else:

                            self.SendData(player, "!SET_ROOM", False)

                    elif command == '!CREATE_ROOM':

                        self.CreateRoom()
                        player.JoinRoom(self.roomList[self.roomID])
                        self.SendData(player, "!SET_ROOM", player)
                        print(f"{SERVER_PREFIX}{player.name} ({player.ID}) is created a room {self.roomID}.")

                    elif command == '!START_GAME':
                        
                        self.SendData(player.room, '!START_GAME')

                    elif command == '!SET_PLAYER_RECT':

                        for roomMate in player.room:
                                
                            self.SendData(roomMate, command, value)

                    elif command == '!DISCONNECT':
    
                        connected = False
                        self.DisconnectClient(player)

                else:

                    connected = False
        
        except(socket.error, ConnectionResetError):
            
            connected = False
            self.DisconnectClient(player)
        
        finally:

            clientSocket.close()

    def DisconnectClient(self, player: PlayerInfo):
        
        self.clientSockets.pop(player.ID)
        
        if player.room:
            
            if len(player.room) == 1:

                self.roomList.pop(player.room.ID)
            
            else:

                player.room.remove(player)

        print(f"{SERVER_PREFIX}{player.name} ({player.IP}) is dissconnected.")
        self.players.pop(player.ID)
        print(f"{SERVER_PREFIX}Player count is now {str(len(self.players))}.")

        self.SendData(list(self.players.values()), "!DISCONNECT", player.ID)
        
server = Server()
server.Start()