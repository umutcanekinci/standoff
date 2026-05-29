from util.constants import *
import threading
import pickle
import struct  # Import the struct module for packing/unpacking data

class Client:

    def __init__(self, game):

        self.isConnected = False
        self.game = game

    def Start(self):

        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.recieveThread = threading.Thread(target=self.ConnectToServer)
        self.recieveThread.start()        
        
    def ConnectToServer(self):

        self.game.DebugLog("[CLIENT] => Connecting to server.")

        try:

            self.client.connect(CLIENT_ADDR)

        except (ConnectionRefusedError, OSError) as e:

            self.game.DebugLog("[CLIENT] => An error occured while connecting to the server.")
            return

        self.isConnected = True

        self.game.DebugLog("[CLIENT] => Connected to server.")
        
        self.RecieveData()
        
    def RecvAll(self, length):

        # TCP recv can return fewer bytes than requested; loop until we have all of them.
        data = bytearray()

        while len(data) < length:

            packet = self.client.recv(length - len(data))

            if not packet:

                return None

            data.extend(packet)

        return bytes(data)

    def RecieveData(self):

        while self.isConnected:

            try:

                packedLength = self.RecvAll(HEADER)

                if not packedLength:

                    self.isConnected = False
                    break

                dataLength = struct.unpack('!I', packedLength)[0]
                serializedData = self.RecvAll(dataLength)

                if not serializedData:

                    self.isConnected = False
                    break

                self.game.GetData(pickle.loads(serializedData))

            except(socket.error, ConnectionResetError, struct.error):

                self.isConnected = False
                break

    def SendData(self, command, value=None):

        dataToSend = {'command': command, 'value': value}

        if self.isConnected:
            
            serializedData = pickle.dumps(dataToSend)
            dataLength = len(serializedData)
            packedLength = struct.pack('!I', dataLength)
            self.client.sendall(packedLength + serializedData)

    def DisconnectFromServer(self):
        
        self.isConnected = False

        if hasattr(self, 'client'):

            self.client.close()