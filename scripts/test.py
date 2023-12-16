from settings import *



def foo():
    
    global WINDOW_HEIGHT
    WINDOW_HEIGHT = 10

def prin(msg=None):

    msg = WINDOW_HEIGHT if not msg else msg

    print(msg)

foo()
prin()
