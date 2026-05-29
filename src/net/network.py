import socket, threading, pickle, struct
from util.constants import HEADER, CLIENT_PORT as PORT

class Network:

    def __init__(self, onRecieveData) -> None:

        self.playerID = 0
        self.players = {}
        self.isConnected = False

        self.onRecieveData = onRecieveData

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.status = '[CLIENT] => Socket has been created'

    def Connect(self, ip, port=PORT) -> int:

        try:

            self.server = socket.gethostbyname(socket.gethostname())
            self.port = port
            self.address = (self.server, self.port)

            self.socket.connect(self.address)
            self.status += '\n' + '[CLIENT] => Connected to Server with IP: ' + self.server + ' and Port: ' + str(port)

        except socket.error as e:

            self.status += '\n' + 'Failed to Connect to Server with IP: ' + self.server + ' and Port: ' + str(port) + ' => ' + str(e)
            return 0

        else:

            threading.Thread(target=self.__RecieveFromServer, args=(self.socket,)).start()
            return 1

    def Host(self, port=PORT) -> int:

        self.server = socket.gethostbyname(socket.gethostname())
        self.port = port
        self.address = (self.server, self.port)

        self.players[self.playerID] = self.server

        try:

            self.Bind()
            self.Listen()

            return 1

        except:

            return 0

    def Bind(self) -> None:

        try:

            self.socket.bind(self.address)

        except:

            self.status += '\n' + 'Failed to Bind to IP: ' + self.server + ' and Port: ' + str(self.port)

        else:

            self.status += '\n' + 'Binded to IP: ' + self.server + ' and Port: ' + str(self.port)

    def Listen(self) -> None:

        try:

            self.socket.listen()
            self.status += '\n' + 'Server is Listening on IP: ' + self.server + ' and Port: ' + str(self.port)
            self.isConnected = True

        except:

            self.status += '\n' + 'Failed to Listen on IP: ' + self.server + ' and Port: ' + str(self.port)

        else:

            threading.Thread(target=self.__Accept).start()

    def __Accept(self) -> None:

        while self.isConnected:

            try:

                socket, address = self.socket.accept()

                playerID = len(self.players)
                self.players[playerID] = address

                self.status += '\n' + 'Connected to IP: ' + address[0] + ' and Port: ' + str(address[1]) + ' as Player ' + str(playerID)
                self.status += '\n' + 'Player count is ' + str(len(self.players))

                self.Send(socket, '!SET_PLAYER', ('Player name', 'Character Name'))

            except:

                self.status += '\n' + 'Failed to Accept Connection'

            else:

                threading.Thread(target=self.__HandleClient, args=(socket, playerID,)).start()

    def __HandleClient(self, socket: socket.socket, playerID) -> None:

        while self.isConnected:

            try:

                data = self.__RecieveFromClient(socket, playerID)

                if data:

                    command = data['command']
                    value = data['value'] if 'value' in data else None

                    if command == '!SET_PLAYER':

                        print(f"Player {value} is entered to lobby.")

                    elif command == '!DISCONNECT':

                        self.DisconnectClient(playerID)
                        break

                    """
                    if command == '!SET_PLAYER':

                        playerName, characterName = value
                        player.SetName(playerName)
                        player.SetCharacterName(characterName)
                        self.PrintLog(f"{player.name} ({player.ID}) is entered to lobby.")

                    elif command == '!JOIN_ROOM':

                        roomID = value

                        if len(self.roomList) > 0 and roomID in self.roomList.keys() and self.roomList[roomID].size > len(self.roomList[roomID]):

                            player.JoinRoom(self.roomList[roomID], False)
                            self.PrintLog(f"{player.name} ({player.ID}) is joined a room {roomID}.")

                            for roomMate in player.room:

                                self.SendData(roomMate, "!UPDATE_ROOM", roomMate)

                        else:

                            self.SendData(player, "!UPDATE_ROOM", False)

                    elif command == '!LEAVE_ROOM':

                        self.LeaveRoom(player)

                    elif command == '!GET_READY':

                            player.isReady = True

                            for roomMate in player.room:

                                self.SendData(roomMate, "!UPDATE_ROOM", roomMate)

                    elif command == '!GET_UNREADY':

                            player.isReady = False

                            for roomMate in player.room:

                                self.SendData(roomMate, "!UPDATE_ROOM", roomMate)

                    elif command == '!START_GAME':

                        self.SendData(player.room, command)

                        thread = threading.Thread(target= self.HandleRoom, args=(player.room, ))
                        thread.start()

                    elif command == '!SHOOT':

                        self.SendData(player.room, command, value)

                    elif command == '!UPDATE_PLAYER':

                        for roomMate in player.room:

                            self.SendData(roomMate, command, value)

                    """



                else:

                    break

            except:

                self.DisconnectClient(playerID)
                break

            finally:

                socket.close()


    # player name
    # character name
    # player ıd



    def __Recieve(self, socket) -> dict | None:

        try:

            packedLength = socket.recv(HEADER)
            dataLength = struct.unpack('!I', packedLength)[0]
            serializedData = socket.recv(dataLength)
            return pickle.loads(serializedData)

        except (socket.error, ConnectionResetError) as e:

            self.status += '\n' + 'Failed to Recieve Data' + ' => ' + str(e)
            return None

    def __RecieveFromClient(self, socket, player) -> dict | None:

        data = self.__Recieve(socket)

        if data: return data

        self.DisconnectClient(player)
        return None

    def __RecieveFromServer(self, socket) -> None:

        while self.isConnected:

            data = self.__Recieve(socket)

            if data:

                self.onRecieveData(data)

            else:

                self.Close()
                break

    def Send(self, socket, command, value=None) -> None:

        try:

            dataToSend = {'command': command, 'value': value}

            if self.isConnected:

                serializedData = pickle.dumps(dataToSend)
                dataLength = len(serializedData)
                packedLength = struct.pack('!I', dataLength)
                socket.sendall(packedLength + serializedData)

        except socket.error as e:

            self.status += '\n' + 'Failed to Send Data' + ' => ' + str(e)

    def SendList(self, playerList, command, value=None, exceptions=[]) -> None:

        if not hasattr(playerList, '__iter__'): playerList = [playerList]
        for exception in exceptions: playerList.remove(exception)
        for player in playerList:

            self.SendData(player, command, value)

    def DisconnectClient(self, player) -> None:

        self.players.pop(player)
        self.Send(player, {'command': '!DISCONNECT'})
        self.status += '\n' + 'Player ' + str(player) + ' has disconnected'
        self.status += '\n' + 'Player count is ' + str(len(self.players))

    def Close(self) -> None:

        self.isConnected = False
        self.socket.close()

    def __del__(self) -> None:

        self.Close()
