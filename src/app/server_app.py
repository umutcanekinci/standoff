"""Server GUI (Layer 3): a Tkinter window that drives a GameServer.

This is the only place that knows about tkinter. It owns no sockets and no game
rules — it starts/stops a GameServer, shows its status log, and lets an operator
broadcast a raw command. All transport and lobby logic lives below it in
net.game_server / net.transport / net.protocol.
"""

import threading
from tkinter import Tk, Label, Text, Button, Frame, Entry, BOTH, END
from ctypes import windll

from util.constants import SERVER_TITLE, SERVER_SIZE, SERVER_ADDR
from net.game_server import GameServer

# Window-chrome helpers (borderless drag + taskbar registration)
GWL_EXSTYLE = -20
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080


def set_appwindow(root):
    hwnd = windll.user32.GetParent(root.winfo_id())
    style = windll.user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
    style = style & ~WS_EX_TOOLWINDOW
    style = style | WS_EX_APPWINDOW
    windll.user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, style)
    # re-assert the new window style
    root.withdraw()
    root.after(10, root.deiconify)


class Grip:
    """Makes a window dragable."""

    def __init__(self, parent, disable=None, releasecmd=None):
        self.parent = parent
        self.root = parent.winfo_toplevel()

        self.disable = disable

        if isinstance(disable, str):
            self.disable = disable.lower()

        self.release_cmd = releasecmd

        self.parent.bind("<Button-1>", self.relative_position)
        self.parent.bind("<ButtonRelease-1>", self.drag_unbind)

    def relative_position(self, event):
        cx, cy = self.parent.winfo_pointerxy()
        geo = self.root.geometry().split("+")
        self.ori_x, self.ori_y = int(geo[1]), int(geo[2])
        self.rel_x = cx - self.ori_x
        self.rel_y = cy - self.ori_y

        self.parent.bind("<Motion>", self.drag_wid)

    def drag_wid(self, event):
        cx, cy = self.parent.winfo_pointerxy()
        d = self.disable
        x = cx - self.rel_x
        y = cy - self.rel_y

        if d == "x":
            x = self.ori_x

        elif d == "y":
            y = self.ori_y

        self.root.geometry("+%i+%i" % (x, y))

    def drag_unbind(self, event):
        self.parent.unbind("<Motion>")

        if self.release_cmd is not None:
            self.release_cmd()


class Application(Tk):
    def __init__(self):
        super().__init__()

        # GUI is game-unaware beyond this: it hands the server a log callback and
        # then only calls serve()/close()/broadcast().
        self.server = GameServer(on_status=self.print_log)

        self.set_window_title(SERVER_TITLE)
        self.set_size(SERVER_SIZE)
        self.center_window()
        self.make_unresizable()
        self.make_borderless()
        self.show_in_task_bar()

        main_frame = Frame(bg="grey", width=self.width, height=self.height)
        main_frame.pack_propagate(0)
        main_frame.pack(fill=BOTH, expand=1)

        top_frame = Frame(main_frame, bg="#505050")
        top_frame.place(x=0, y=0, anchor="nw", width=self.width, height=40)
        Grip(top_frame)

        Label(
            top_frame,
            bg="#505050",
            fg="white",
            font=("Comic Sans MS", 15),
            text=SERVER_TITLE,
        ).pack()

        Button(top_frame, text="X", bg="#FF6666", fg="white", command=self.exit).place(
            x=self.width - 75, y=0, anchor="nw", width=75, height=40
        )

        Label(main_frame, text="Command Log", font=("Comic Sans MS", 13)).place(
            x=20, y=60, anchor="nw"
        )

        self.command_log = Text(
            main_frame, bg="white", fg="green", font=("Comic Sans MS", 12)
        )
        self.command_log.config(state="disabled")
        self.command_log.place(
            x=20, y=110, anchor="nw", width=self.width - 160, height=self.height - 250
        )

        self.start_button = Button(
            main_frame,
            bg="orange",
            fg="white",
            font=("Comic Sans MS", 12),
            text="START",
            command=self.start_server,
        )
        self.start_button.place(
            x=self.width - 120, y=110, anchor="nw", width=100, height=50
        )

        self.restart_button = Button(
            main_frame,
            bg="orange",
            fg="white",
            font=("Comic Sans MS", 12),
            text="RESTART",
            command=self.restart_server,
        )
        self.restart_button.place(
            x=self.width - 120, y=170, anchor="nw", width=100, height=50
        )

        self.close_button = Button(
            main_frame,
            bg="orange",
            fg="white",
            font=("Comic Sans MS", 12),
            text="CLOSE",
            command=self.close_server,
        )
        self.close_button.place(
            x=self.width - 120, y=230, anchor="nw", width=100, height=50
        )

        Label(main_frame, text="Command Entry", font=("Comic Sans MS", 13)).place(
            x=20, y=self.height - 120, anchor="nw"
        )

        self.command_entry = Entry(main_frame)
        self.command_entry.place(
            x=20, y=self.height - 70, anchor="nw", width=self.width - 160, height=50
        )

        self.send_button = Button(
            main_frame,
            bg="orange",
            fg="white",
            font=("Comic Sans MS", 12),
            text="SEND",
            command=self.send_command,
        )
        self.send_button.place(
            x=self.width - 120, y=self.height - 70, anchor="nw", width=100, height=50
        )

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
        self.geometry("{}x{}+{}+{}".format(width, height, x, y))
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
            # serve() blocks in its accept loop, so run it off the GUI thread.
            threading.Thread(
                target=self.server.serve, args=(SERVER_ADDR,), daemon=True
            ).start()

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
        self.server.broadcast(command, value)

    def restart_server(self):
        self.close_server()
        self.start_server()

    def close_server(self):
        self.server.close()

        self.start_button["state"] = "normal"
        self.restart_button["state"] = "disabled"
        self.close_button["state"] = "disabled"
        self.send_button["state"] = "disabled"

    def print_log(self, text):
        self.command_log.config(state="normal")
        self.command_log.insert(END, "[SERVER] => " + text + "\n")
        self.command_log.config(state="disabled")
        self.command_log.yview(END)


if __name__ == "__main__":
    Application().start()
