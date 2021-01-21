import sys
import clr
import logging
sys.path.append('.')
clr.AddReference('CAOS')
from CAOS import *
from threading import Lock
import platform
import socket
import os

class LoggingCaosInjector(CaosInjector):

    lock = Lock()

    def __init__(self, game_name):
        super().__init__(game_name)

    def ExecuteCaos(self, caos, action="execute"):
        self.lock.acquire()
        result = super().ExecuteCaos(caos, action=action)
        self.lock.release()
        return result

class LinuxCaosInjector(object):

    lock = Lock()
    host = "localhost"
    port = int(os.popen('cat ~/.creaturesengine/port').read())


    def ExecuteCaos(self, caos):
        self.lock.acquire()
        s = socket.socket()
        s.connect((self.host, self.port))
        s.sendall((caos + " outs \":thisworked\"\r\nrscr\r\n").encode())
        s.shutdown(socket.SHUT_WR)

        res = ""

        while True:
            data = s.recv(1024)
            if not data:
                break
            res += data.decode()
        s.close
        
        self.lock.release()

        success = res.endswith(":thisworked")
        content = res[:-len(":thisworked")] if success else res

        mesg = lambda: None
        mesg.Content = content
        mesg.Success = success
        return mesg


CI = LoggingCaosInjector('Docking Station')

# Here's where we hijack the caos injector if it's linux
if (platform.system() == "Linux"):
    CI = LinuxCaosInjector()
    print("Oh, you're on linux. Hello linux friend!")


@property
def WorldName():
    return CI.ExecuteCaos('outs wnam').Content.strip('\x00')


def add_user_to_contact_list(username):
    CI.ExecuteCaos('rtar 1 1 157 mesg wrt+ targ 1000 "%s" 0 0' % username)


def delete_creature_by_moniker(moniker):
    return CI.ExecuteCaos('rtar 1 1 35700 mesg wrt+ targ 1337 "%s" 0 0' % moniker).Content.strip('\x00')


def _ds_gui_online():
    CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1005 mesg writ targ 500 next")


def _ds_gui_offline():
    CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1005 mesg writ targ 501 next")
