import sys
import clr
import logging
sys.path.append('.')
clr.AddReference('CAOS')
from CAOS import *
from threading import Lock

class LoggingCaosInjector(CaosInjector):

    lock = Lock()

    def __init__(self, game_name):
        super().__init__(game_name)

    def ExecuteCaos(self, caos, action="execute"):
        self.lock.acquire()
        result = super().ExecuteCaos(caos, action=action)
        self.lock.release()
        return result


CI = LoggingCaosInjector('Docking Station')


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
