import socket
import struct
import pickle

def send_data(client_socket, data):
    serialized_data = pickle.dumps(data)
    data_length = len(serialized_data)
    packed_length = struct.pack('!I', data_length)
    client_socket.sendall(packed_length + serialized_data)

def receive_data(client_socket):
    packed_length = client_socket.recv(4)
    data_length = struct.unpack('!I', packed_length)[0]
    serialized_data = client_socket.recv(data_length)
    return pickle.loads(serialized_data)

# Set up the client socket
server_address = ('localhost', 12345)
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(server_address)

# Receive data from the server
received_data = receive_data(client_socket)
print('Received data from server:', received_data)

# Data to send from client to server
data_to_send = {'message': 'Hello from the client!', 'value': 123}
send_data(client_socket, data_to_send)

# Close the client socket
client_socket.close()