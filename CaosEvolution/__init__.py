import sys
from threading import Lock
import mmap
import win32event
import struct


class CaosResult:
    def __init__(self, result_code: int, content: str, process_id: int):
        self.Content = content.decode("utf-8")
        self.ResultCode = result_code
        self.ProcessID = process_id
        self.Success = result_code == 0


class SharedMemoryCaosInjector:

    lock = Lock()

    shared_memory_size = 131072

    def __init__(self, game_name: str = "DockingStation"):
        self.game_name = game_name

    def ExecuteCaos(self, caos: str, action="execute"):
        self.lock.acquire()
        hMutex = win32event.OpenMutex(0x1F0001, False, self.game_name + "_mutex")
        shared_memory = mmap.mmap(
            0, self.shared_memory_size, self.game_name + "_mem", mmap.ACCESS_WRITE
        )
        result_event_handler = win32event.OpenEvent(
            win32event.EVENT_ALL_ACCESS, False, self.game_name + "_result"
        )
        request_event_handler = win32event.OpenEvent(
            win32event.EVENT_ALL_ACCESS, False, self.game_name + "_request"
        )
        caos = bytes(caos, "latin-1")
        shared_memory.seek(24)
        shared_memory.write(b"execute\n" + caos + b"\n")
        win32event.SetEvent(request_event_handler)
        win32event.WaitForSingleObject(result_event_handler, 1000)
        shared_memory.seek(0)
        _, process_id, result_code, result_length, _, _ = struct.unpack(
            "4sIIIII", shared_memory.read(24)
        )
        result = shared_memory.read(result_length)
        shared_memory.seek(24)
        shared_memory.write(b"\x00" * (result_length + len(caos) + 9))
        hMutex.Close()
        self.lock.release()
        return CaosResult(
            result_code=result_code, content=result, process_id=process_id
        )


CI = SharedMemoryCaosInjector("Docking Station")


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
