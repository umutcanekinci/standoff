import socket
import threading
import pickle
from server_settings import *
import struct

class Server:

    def Start(self):

        self.players = {} # {client : [playerID, playerName]}

        # Creating a server socket and providing the address family (socket.AF_INET) and type of connection (socket.SOCK_STREAM), i.e. using TCP connection.
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        print("[SERVER] => Server is started.")
        
        self.Bind()

    def Bind(self):

        try:

            # Binding the socket with the IP address and Port Number.
            self.server.bind(ADDR)

        except socket.error as error:

            print("[SERVER] => An error occured during connecting to server: " + str(error))

        else:

            print("[SERVER] => Server is binded.")
            
            self.Listen()
        
    def Listen(self):

        self.server.listen()
        print(f"[SERVER] => Server is listening on IP = {IP} at PORT = {PORT}")

        # running an infinite loop to accept continuous client requests.
        while True:

            # Making the server listen to new connections. when a new connection has detected codes will continue 
            clientSocket, addr = self.server.accept()
            print(f"[SERVER] => {addr[0]} is connected.")

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

        clientSockets = list(self.players.keys())

        for exception in exceptions:

            clientSockets.remove(exception)

        self.SendData(clientSockets, data)

    def HandleClient(self, clientSocket: socket.socket, addr):

        ip, port = addr
        connected = True

        try:

            while connected:
                
                data = self.RecieveData(clientSocket)

                if data:

                    if data['command'] == '!GET_PLAYERS': # new player entered to main menu

                        self.SendData([clientSocket], {'command' : "!PLAYERS", 'value' : list(self.players.values())})

                    if data['command'] == '!GET_PLAYER_ID': # new player came to game

                        playerID = len(self.players) + 1
                        playerName = data['value']

                        self.players[clientSocket] = [playerID, playerName]

                        #printing player count and player name
                        print(f"[SERVER] => {self.players[clientSocket][1]} ({ip}) is entered to game from PORT = {port}.")
                        print(f"[SERVER] => Player count is now {str(playerID)}.")
                        
                        self.SendData([clientSocket], {'command' : "!PLAYER_ID", 'value' : playerID})
                        self.SendDataToAllClients({'command' : "!NEW_PLAYER", 'value' : [playerID, playerName]}, [clientSocket])        
                        
                    elif data['command'] == '!PLAYER_RECT':

                        self.SendDataToAllClients(data, [clientSocket])
                        
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

        playerData = self.players[clientSocket]
        self.players.pop(clientSocket)

        print(f"[SERVER] => {playerData[1]} ({ip}) is dissconnected.")
        print(f"[SERVER] => Player count is now {str(len(self.players))}.")

        self.SendDataToAllClients({'command' : "!DISCONNECT", 'value' : playerData})
        
server = Server()
server.Start()