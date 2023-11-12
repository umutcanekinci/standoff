import socket
import threading
import pickle
from settings import *
import struct

class Server:

    def Start(self):

        self.players = {}
        self.messages = ""

        # Creating a server socket and providing the address family (socket.AF_INET) and type of connection (socket.SOCK_STREAM), i.e. using TCP connection.
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        print("[SERVER] => Server is started.")
        
        self.Bind()

    def Bind(self):

        try:

            # Binding the socket with the IP address and Port Number.
            self.server.bind(ADDR)

        except socket.error as error:

            print("[SERVER] => An error occured during connecting to server: " + error)

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

    def RecieveMessage(self, clientSocket):

        packedLength = clientSocket.recv(HEADER)
        dataLength = struct.unpack('!I', packedLength)[0]
        serializedData = clientSocket.recv(dataLength)
        return pickle.loads(serializedData)

    def SendMessage(self, clientSockets, dataToSend):

        for clientSocket in clientSockets:
            
            serializedData = pickle.dumps(dataToSend)
            dataLength = len(serializedData)
            packedLength = struct.pack('!I', dataLength)
            clientSocket.sendall(packedLength + serializedData)

    def SendMessageToAllClients(self, message, exceptions=[]):

        clientSockets = list(self.players.keys())

        for exception in exceptions:

            clientSockets.remove(exception)

        self.SendMessage(clientSockets, message)

    def HandleClient(self, clientSocket: socket.socket, addr):

        ip, port = addr

        connected = True
        while connected:
            
            message = self.RecieveMessage(clientSocket)

            if message:

                if message['command'] == '!PLAYER_RECT':
                    
                    self.SendMessageToAllClients(message, [clientSocket])
                
                elif message['command'] == '!GET_PLAYER_ID':

                    playerID = len(self.players) + 1
                    self.players[clientSocket] = "Player " + str(playerID)

                    #printing player count and player name
                    print(f"[SERVER] => {self.players[clientSocket]} ({ip}) is entered to game from PORT = {port}.")
                    print(f"[SERVER] => Player count is now {str(playerID)}.")
                    
                    
                    self.SendMessageToAllClients({'command' : "!NEW_PLAYER", 'data' : playerID})
                    self.SendMessage([clientSocket], {'command' : "!PLAYER_IDs", 'data' : list(self.players.values())})
                    
                
                elif message['command'] == '!DISCONNECT':

                        print(f"[SERVER] => {self.players[clientSocket]} ({ip}) is dissconnected.")

                        self.SendMessageToAllClients({'command' : "!DISCONNECT", 'data' : self.players[clientSocket]})
                        self.players.pop(clientSocket)
                        
                        print(f"[SERVER] => Player count is now {str(len(self.players))}.")
                        connected = False

            else:

                connected = False

        clientSocket.close()

server = Server()
server.Start()