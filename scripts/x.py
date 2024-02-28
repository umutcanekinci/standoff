import threading

class a:

    def __init__(self) -> None:
        
        self.isRunning = True


def handle(a):

    while a.isRunning:

        print("a")

def start():

    A = a()
    thread = threading.Thread(target=handle, args=(A, ))
    thread.start()
    A.isRunning = False

start()