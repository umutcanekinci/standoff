from util.constants import *
import threading
import pickle
import struct  # Import the struct module for packing/unpacking data


class Client:
    def __init__(self, game):
        self.is_connected = False
        self.game = game

    def start(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.recieve_thread = threading.Thread(target=self.connect_to_server)
        self.recieve_thread.start()

    def connect_to_server(self):
        self.game.debug_log("[CLIENT] => Connecting to server.")

        try:
            self.client.connect(CLIENT_ADDR)

        except (ConnectionRefusedError, OSError) as e:
            self.game.debug_log(
                "[CLIENT] => An error occured while connecting to the server."
            )
            return

        self.is_connected = True

        self.game.debug_log("[CLIENT] => Connected to server.")

        self.recieve_data()

    def recv_all(self, length):
        # TCP recv can return fewer bytes than requested; loop until we have all of them.
        data = bytearray()

        while len(data) < length:
            packet = self.client.recv(length - len(data))

            if not packet:
                return None

            data.extend(packet)

        return bytes(data)

    def recieve_data(self):
        while self.is_connected:
            try:
                packed_length = self.recv_all(HEADER)

                if not packed_length:
                    self.is_connected = False
                    break

                data_length = struct.unpack("!I", packed_length)[0]
                serialized_data = self.recv_all(data_length)

                if not serialized_data:
                    self.is_connected = False
                    break

                self.game.get_data(pickle.loads(serialized_data))

            except (socket.error, ConnectionResetError, struct.error):
                self.is_connected = False
                break

    def send_data(self, command, value=None):
        data_to_send = {"command": command, "value": value}

        if self.is_connected:
            serialized_data = pickle.dumps(data_to_send)
            data_length = len(serialized_data)
            packed_length = struct.pack("!I", data_length)
            self.client.sendall(packed_length + serialized_data)

    def disconnect_from_server(self):
        self.is_connected = False

        if hasattr(self, "client"):
            self.client.close()
