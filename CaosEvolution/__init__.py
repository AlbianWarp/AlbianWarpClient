import platform

if platform.system() == "Linux":
    from LinuxCaosInjector import CI
else:
    from .SharedMemoryCaosInjector import CI

@property
def WorldName():
    return CI.ExecuteCaos("outs wnam").Content.strip("\x00")

def add_user_to_contact_list(username):
    CI.ExecuteCaos('rtar 1 1 157 mesg wrt+ targ 1000 "%s" 0 0' % username)


def delete_creature_by_moniker(moniker):
    return CI.ExecuteCaos(
        'rtar 1 1 35700 mesg wrt+ targ 1337 "%s" 0 0' % moniker
    ).Content.strip("\x00")

def _ds_gui_online():
    CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1005 mesg writ targ 500 next")


def _ds_gui_offline():
    CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1005 mesg writ targ 501 next")
