import socket, threading, pickle, struct
from util.constants import HEADER, CLIENT_PORT as PORT

class Network:

    def __init__(self, on_recieve_data) -> None:

        self.player_id = 0
        self.players = {}
        self.is_connected = False

        self.on_recieve_data = on_recieve_data

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.status = '[CLIENT] => Socket has been created'

    def connect(self, ip, port=PORT) -> int:

        try:

            self.server = socket.gethostbyname(socket.gethostname())
            self.port = port
            self.address = (self.server, self.port)

            self.socket.connect(self.address)
            self.status += '\n' + '[CLIENT] => Connected to Server with IP: ' + self.server + ' and Port: ' + str(port)

        except socket.error as e:

            self.status += '\n' + 'Failed to connect to Server with IP: ' + self.server + ' and Port: ' + str(port) + ' => ' + str(e)
            return 0

        else:

            threading.Thread(target=self.__recieve_from_server, args=(self.socket,)).start()
            return 1

    def host(self, port=PORT) -> int:

        self.server = socket.gethostbyname(socket.gethostname())
        self.port = port
        self.address = (self.server, self.port)

        self.players[self.player_id] = self.server

        try:

            self.bind()
            self.listen()

            return 1

        except:

            return 0

    def bind(self) -> None:

        try:

            self.socket.bind(self.address)

        except:

            self.status += '\n' + 'Failed to bind to IP: ' + self.server + ' and Port: ' + str(self.port)

        else:

            self.status += '\n' + 'Binded to IP: ' + self.server + ' and Port: ' + str(self.port)

    def listen(self) -> None:

        try:

            self.socket.listen()
            self.status += '\n' + 'Server is Listening on IP: ' + self.server + ' and Port: ' + str(self.port)
            self.is_connected = True

        except:

            self.status += '\n' + 'Failed to listen on IP: ' + self.server + ' and Port: ' + str(self.port)

        else:

            threading.Thread(target=self.__accept).start()

    def __accept(self) -> None:

        while self.is_connected:

            try:

                socket, address = self.socket.accept()

                player_id = len(self.players)
                self.players[player_id] = address

                self.status += '\n' + 'Connected to IP: ' + address[0] + ' and Port: ' + str(address[1]) + ' as Player ' + str(player_id)
                self.status += '\n' + 'Player count is ' + str(len(self.players))

                self.send(socket, '!SET_PLAYER', ('Player name', 'Character Name'))

            except:

                self.status += '\n' + 'Failed to Accept Connection'

            else:

                threading.Thread(target=self.__handle_client, args=(socket, player_id,)).start()

    def __handle_client(self, socket: socket.socket, player_id) -> None:

        while self.is_connected:

            try:

                data = self.__recieve_from_client(socket, player_id)

                if data:

                    command = data['command']
                    value = data['value'] if 'value' in data else None

                    if command == '!SET_PLAYER':

                        print(f"Player {value} is entered to lobby.")

                    elif command == '!DISCONNECT':

                        self.disconnect_client(player_id)
                        break

                    """
                    if command == '!SET_PLAYER':

                        player_name, character_name = value
                        player.set_name(player_name)
                        player.set_character_name(character_name)
                        self.print_log(f"{player.name} ({player.id}) is entered to lobby.")

                    elif command == '!JOIN_ROOM':

                        room_id = value

                        if len(self.room_list) > 0 and room_id in self.room_list.keys() and self.room_list[room_id].size > len(self.room_list[room_id]):

                            player.join_room(self.room_list[room_id], False)
                            self.print_log(f"{player.name} ({player.id}) is joined a room {room_id}.")

                            for room_mate in player.room:

                                self.send_data(room_mate, "!UPDATE_ROOM", room_mate)

                        else:

                            self.send_data(player, "!UPDATE_ROOM", False)

                    elif command == '!LEAVE_ROOM':

                        self.leave_room(player)

                    elif command == '!GET_READY':

                            player.is_ready = True

                            for room_mate in player.room:

                                self.send_data(room_mate, "!UPDATE_ROOM", room_mate)

                    elif command == '!GET_UNREADY':

                            player.is_ready = False

                            for room_mate in player.room:

                                self.send_data(room_mate, "!UPDATE_ROOM", room_mate)

                    elif command == '!START_GAME':

                        self.send_data(player.room, command)

                        thread = threading.Thread(target= self.handle_room, args=(player.room, ))
                        thread.start()

                    elif command == '!SHOOT':

                        self.send_data(player.room, command, value)

                    elif command == '!UPDATE_PLAYER':

                        for room_mate in player.room:

                            self.send_data(room_mate, command, value)

                    """



                else:

                    break

            except:

                self.disconnect_client(player_id)
                break

            finally:

                socket.close()


    # player name
    # character name
    # player ıd



    def __recieve(self, socket) -> dict | None:

        try:

            packed_length = socket.recv(HEADER)
            data_length = struct.unpack('!I', packed_length)[0]
            serialized_data = socket.recv(data_length)
            return pickle.loads(serialized_data)

        except (socket.error, ConnectionResetError) as e:

            self.status += '\n' + 'Failed to Recieve Data' + ' => ' + str(e)
            return None

    def __recieve_from_client(self, socket, player) -> dict | None:

        data = self.__recieve(socket)

        if data: return data

        self.disconnect_client(player)
        return None

    def __recieve_from_server(self, socket) -> None:

        while self.is_connected:

            data = self.__recieve(socket)

            if data:

                self.on_recieve_data(data)

            else:

                self.close()
                break

    def send(self, socket, command, value=None) -> None:

        try:

            data_to_send = {'command': command, 'value': value}

            if self.is_connected:

                serialized_data = pickle.dumps(data_to_send)
                data_length = len(serialized_data)
                packed_length = struct.pack('!I', data_length)
                socket.sendall(packed_length + serialized_data)

        except socket.error as e:

            self.status += '\n' + 'Failed to send Data' + ' => ' + str(e)

    def send_list(self, player_list, command, value=None, exceptions=[]) -> None:

        if not hasattr(player_list, '__iter__'): player_list = [player_list]
        for exception in exceptions: player_list.remove(exception)
        for player in player_list:

            self.send_data(player, command, value)

    def disconnect_client(self, player) -> None:

        self.players.pop(player)
        self.send(player, {'command': '!DISCONNECT'})
        self.status += '\n' + 'Player ' + str(player) + ' has disconnected'
        self.status += '\n' + 'Player count is ' + str(len(self.players))

    def close(self) -> None:

        self.is_connected = False
        self.socket.close()

    def __del__(self) -> None:

        self.close()
