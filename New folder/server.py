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

# Set up the server socket
server_address = ('localhost', 12345)
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(server_address)
server_socket.listen(1)

print('Server is listening for connections...')

# Accept a connection from a client
client_socket, addr = server_socket.accept()
print('Connection from', addr)

# Data to send from server to client
data_to_send = {'message': 'Hello from the server!', 'value': 42}
send_data(client_socket, data_to_send)

# Receive data from the client
received_data = receive_data(client_socket)
print('Received data from client:', received_data)

# Close the connection and server socket
client_socket.close()
server_socket.close()