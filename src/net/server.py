#region İmporting Packages

import socket
import threading
import time
import pickle
from util.constants import *
import struct
from net.player_info import PlayerInfo, MobInfo
from net.room import Room
from tkinter import Tk, Label, Text, Button, Frame, Entry, BOTH, END
from ctypes import windll

#endregion

class Server:

    def __init__(self, application) -> None:
        
        self.is_running = False
        self.application = application

    def print_log(self, text: str):

        self.application.print_log("[SERVER] => " + text + "\n")

    def start(self):

        self.is_running = True
        self.client_sockets = {} # id : client_socket
        self.room_list = {} # id : player_list
        self.players = {} # player_id : player
        self.mobs = {}

        # Creating a server socket and providing the address family (socket.AF_INET) and type of connection (socket.SOCK_STREAM), i.e. using TCP connection.
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        self.print_log("Server is started.")
        
        self.bind()

    def bind(self):

        try:

            # Binding the socket with the IP address and Port Number.
            self.server.bind(SERVER_ADDR)

        except socket.error as error:

            self.print_log("An error occured during connecting to server: " + str(error))

        else:

            self.print_log("Server is binded.")
            self.listen()

    def listen(self):

        self.server.listen()
        self.print_log(f"Server is listening on IP = {SERVER_IP} at PORT = {SERVER_PORT}")
        player_id, self.room_id = 0, 0

        # running an infinite loop to accept continuous client requests.
        while self.is_running:

            # Making the server listen to new connections. when a new connection has detected codes will continue 
            try:

                client_socket, address = self.server.accept()

                player_id += 1

                self.client_sockets[player_id] = client_socket
                player = PlayerInfo(player_id, address)
                self.players[player_id] = player

                self.print_log(f"{player.IP} is connected from PORT = {player.PORT}.")
                self.print_log(f"Player count is now {str(len(self.players))}.")

                self.send_data(list(self.players.values()), "!SET_PLAYER_COUNT", len(self.players))
                self.send_data(player, "!UPDATE_ROOM", player)

                # starting a new thread
                thread = threading.Thread(target=self.handle_client, args=(client_socket, player))
                thread.start()

            except socket.error as e:
            
                if self.is_running:

                    self.print_log(f"Error accepting client connection: {e}")

    def recv_all(self, client_socket, length):

        # TCP recv can return fewer bytes than requested; loop until we have all of them.
        data = bytearray()

        while len(data) < length:

            packet = client_socket.recv(length - len(data))

            if not packet:

                return None

            data.extend(packet)

        return bytes(data)

    def recieve_data(self, client_socket, player):

        try:

            packed_length = self.recv_all(client_socket, HEADER)

            if not packed_length:

                self.disconnect_client(player)
                return None

            data_length = struct.unpack('!I', packed_length)[0]
            serialized_data = self.recv_all(client_socket, data_length)

            if not serialized_data:

                self.disconnect_client(player)
                return None

            return pickle.loads(serialized_data)

        except (socket.error, ConnectionResetError, struct.error):

            self.disconnect_client(player)

    def send_data(self, player_list, command, value=None, exceptions=None):

        data_to_send = {'command': command, 'value': value}

        if not hasattr(player_list, '__iter__'):

            player_list = [player_list]

        # Copy so we never mutate the caller's list (e.g. a Room), and avoid a mutable default.
        player_list = [player for player in player_list if player not in (exceptions or [])]

        for player in player_list:

            try:

                serialized_data = pickle.dumps(data_to_send)
                data_length = len(serialized_data)
                packed_length = struct.pack('!I', data_length)
                self.client_sockets[player.id].sendall(packed_length + serialized_data)

            except (socket.error, ConnectionResetError):

                self.disconnect_client(player)
                continue

    def create_room(self, map_name, base_points):

        self.room_id += 1
        self.room_list[self.room_id] = Room(self.room_id, map_name, base_points)

    def leave_room(self, player):
 
        room = player.room
        
        if room:
            
            player.leave_room()
            self.print_log(f"{player.name} ({player.IP}) is leaved Room {room.id}.")
            self.print_log(f"Player count in Room {room.id} is now {str(len(room))}.")

            if len(room) == 0:

                self.room_list.pop(room.id)
                self.print_log(f"Room {room.id} is deleted.")

            else:

                room[0].is_ruler = True

                for room_mate in room:

                    self.send_data(room_mate, "!UPDATE_ROOM", room_mate)

            self.send_data(player, "!LEAVE_ROOM", player)
     
    def spawn_mob(self, room, mob):

        if hasattr(self, 'mobs'):
            
            self.mobs[mob.id] = mob
            self.send_data(room, '!SPAWN', mob)

    def handle_room(self, room):

        while room.id in self.room_list:

            room.update(self.spawn_mob)
            time.sleep(0.01)

    def handle_client(self, client_socket: socket.socket, player: PlayerInfo):

        connected = True

        try:

            while connected:
                
                data = self.recieve_data(client_socket, player)

                if data:

                    command = data['command']
                    value = data['value'] if 'value' in data else None

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

                    elif command == '!CREATE_ROOM':

                        self.create_room(*value)
                        player.join_room(self.room_list[self.room_id], True)
                        self.send_data(player, "!UPDATE_ROOM", player)
                        self.print_log(f"{player.name} ({player.id}) is created a room {self.room_id}.")

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

                    elif command == '!DISCONNECT':
    
                        connected = False
                        self.disconnect_client(player)

                else:

                    connected = False
        
        except(socket.error, ConnectionResetError):
            
            connected = False
            self.disconnect_client(player)
        
        finally:

            client_socket.close()

    def disconnect_client(self, player: PlayerInfo):

        if player in self.players.values() and player.id in self.client_sockets.keys():

            if player.room:

                self.leave_room(player)
            
            self.send_data(list(self.players.values()), "!DISCONNECT", player.id)

            self.client_sockets.pop(player.id)
            self.players.pop(player.id)

            self.print_log(f"{player.name} ({player.IP}) is dissconnected.")
            self.print_log(f"Player count is now {str(len(self.players))}.")

    def close(self):

        self.print_log(f"Server is closing...")
                
        if hasattr(self, 'server'):

            for player in list(self.players.values()):

                self.disconnect_client(player)

            self.server.close()

        self.is_running = False

#region Tkinter

GWL_EXSTYLE = -20
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080

def set_appwindow(root):
    hwnd = windll.user32.GetParent(root.winfo_id())
    style = windll.user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
    style = style & ~WS_EX_TOOLWINDOW
    style = style | WS_EX_APPWINDOW
    res = windll.user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, style)
    # re-assert the new window style
    root.withdraw()
    root.after(10, root.deiconify)

class Grip:

    ''' Makes a window dragable. '''
    def __init__ (self, parent, disable=None, releasecmd=None):

        self.parent = parent
        self.root = parent.winfo_toplevel()

        self.disable = disable

        if type(disable) == 'str':

            self.disable = disable.lower()

        self.release_cmd = releasecmd

        self.parent.bind('<Button-1>', self.relative_position)
        self.parent.bind('<ButtonRelease-1>', self.drag_unbind)

    def relative_position (self, event):

        cx, cy = self.parent.winfo_pointerxy()
        geo = self.root.geometry().split("+")
        self.ori_x, self.ori_y = int(geo[1]), int(geo[2])
        self.rel_x = cx - self.ori_x
        self.rel_y = cy - self.ori_y

        self.parent.bind('<Motion>', self.drag_wid)

    def drag_wid (self, event):

        cx, cy = self.parent.winfo_pointerxy()
        d = self.disable
        x = cx - self.rel_x
        y = cy - self.rel_y

        if d == 'x':

            x = self.ori_x

        elif d == 'y':

            y = self.ori_y

        self.root.geometry('+%i+%i' % (x, y))

    def drag_unbind (self, event):

        self.parent.unbind('<Motion>')
        
        if self.release_cmd != None :

            self.release_cmd()

class Application(Tk):

    def __init__(self):

        super().__init__()

        self.server = Server(self)

        self.set_window_title(SERVER_TITLE)
        self.set_size(SERVER_SIZE)
        self.center_window()
        self.make_unresizable()
        self.make_borderless()
        self.show_in_task_bar()

        main_frame = Frame(bg="grey", width= self.width, height=self.height)
        main_frame.pack_propagate(0)
        main_frame.pack(fill=BOTH, expand=1)

        top_frame = Frame(main_frame, bg="#505050")
        top_frame.place(x=0, y=0, anchor="nw", width=self.width, height=40)
        Grip(top_frame)

        Label(top_frame, bg="#505050", fg='white', font=("Comic Sans MS", 15), text=SERVER_TITLE).pack()

        Button(top_frame, text="X", bg="#FF6666", fg="white", command=self.exit).place(x=self.width-75, y=0, anchor="nw", width=75, height=40)

        Label(main_frame, text="Command Log", font=("Comic Sans MS", 13)).place(x=20, y=60, anchor="nw")

        self.command_log = Text(main_frame, bg='white', fg='green', font=("Comic Sans MS", 12))
        self.command_log.config(state='disabled')
        self.command_log.place(x=20, y=110, anchor="nw", width=self.width - 160, height=self.height - 250)

        self.start_button = Button(main_frame, bg='orange', fg='white', font=("Comic Sans MS", 12), text='START', command=self.start_server)
        self.start_button.place(x=self.width - 120, y=110, anchor="nw", width=100, height=50)

        self.restart_button = Button(main_frame, bg='orange', fg='white', font=("Comic Sans MS", 12), text='RESTART', command=self.restart_server)
        self.restart_button.place(x=self.width - 120, y=170, anchor="nw", width=100, height=50)

        self.close_button = Button(main_frame, bg='orange', fg='white', font=("Comic Sans MS", 12), text='CLOSE', command=self.close_server)
        self.close_button.place(x=self.width - 120, y=230, anchor="nw", width=100, height=50)

        Label(main_frame, text="Command Entry", font=("Comic Sans MS", 13)).place(x=20, y=self.height - 120, anchor="nw")

        self.command_entry = Entry(main_frame)
        self.command_entry.place(x=20, y=self.height - 70, anchor="nw", width=self.width - 160, height=50)

        self.send_button = Button(main_frame, bg='orange', fg='white', font=("Comic Sans MS", 12), text='SEND', command=self.send_command)
        self.send_button.place(x=self.width - 120, y=self.height - 70, anchor="nw", width=100, height=50)

        self.start_button["state"] = "normal"
        self.restart_button["state"] = "disabled"
        self.close_button["state"] = "disabled"
        self.send_button["state"] = "disabled"

    def start(self):

        self.start_server()
        self.mainloop()

    def center_window(self):

        self.update_idletasks()
        width = self.winfo_width()
        frm_width = self.winfo_rootx() - self.winfo_x()
        win_width = width + 2 * frm_width
        height = self.winfo_height()
        titlebar_height = self.winfo_rooty() - self.winfo_y()
        win_height = height + titlebar_height + frm_width
        x = self.winfo_screenwidth() // 2 - win_width // 2
        y = self.winfo_screenheight() // 2 - win_height // 2
        self.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        self.deiconify()

    def show_in_task_bar(self):

        self.after(10, set_appwindow, self)

    def set_window_title(self, text: str):

        self.wm_title(text)

    def set_size(self, size):

        self.size = self.width, self.height = size
        self.geometry(str(self.width) + "x" + str(self.height))

    def make_unresizable(self):

        self.resizable(0, 0)

    def make_borderless(self):

        self.overrideredirect(True)

    def exit(self):

        self.close_server()
        self.destroy()

    def start_server(self):

        if not self.server.is_running:

            thread = threading.Thread(target=self.server.start)
            thread.start()

            self.start_button["state"] = "disabled"
            self.restart_button["state"] = "normal"
            self.close_button["state"] = "normal"
            self.send_button["state"] = "normal"

    def send_command(self):

        text = self.command_entry.get()
        parts = text.split()

        if not parts:

            return

        command = parts[0]
        value = parts[1] if len(parts) > 1 else None
        self.server.send_data(list(self.server.players.values()), command, value)

    def restart_server(self):

        self.close_server()
        self.start_server()

    def close_server(self):

        if hasattr(self, 'server'):

            self.server.close()

            self.start_button["state"] = "normal"
            self.restart_button["state"] = "disabled"
            self.close_button["state"] = "disabled"
            self.send_button["state"] = "disabled"

    def print_log(self, text):

        self.command_log.config(state='normal')
        self.command_log.insert(END, text)
        self.command_log.config(state='disabled')
        self.command_log.yview(END)


if __name__ == '__main__':

    app = Application()
    app.start()

#endregion
