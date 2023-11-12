import socket
from scripts.settings import *
import threading
import pickle
import struct  # Import the struct module for packing/unpacking data

class Client:

    def __init__(self, game):

        self.connected = False
        self.game = game

    def Start(self):

        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.ConnectToServer()
        
    def ConnectToServer(self):

        self.game.DebugLog("[CLIENT] => Connecting to server.")

        try:

            self.client.connect(ADDR)

        except ConnectionRefusedError as e:

            self.game.DebugLog("[CLIENT] => An error occured while connecting to the server.")
            return

        self.connected = True

        self.game.DebugLog("[CLIENT] => Connected to server.")
        self.SendMessage({'command' : '!GET_PLAYER_ID'})

        self.recieveThread = threading.Thread(target=self.RecieveMessage)
        self.recieveThread.start()
                
    def RecieveMessage(self):

        packedLength = self.client.recv(HEADER)
        dataLength = struct.unpack('!I', packedLength)[0]
        serializedData = self.client.recv(dataLength)
        self.game.GetMessage(pickle.loads(serializedData))

    def SendMessage(self, dataToSend):

        if self.connected:
            
            serializedData = pickle.dumps(dataToSend)
            dataLength = len(serializedData)
            packedLength = struct.pack('!I', dataLength)
            self.client.sendall(packedLength + serializedData)

    def DisconnectFromServer(self):

        self.SendMessage({'command' : "!DISCONNECT"})
        self.connected = False