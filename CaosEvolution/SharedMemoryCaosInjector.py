import mmap
import time
import struct
import win32event
from threading import Lock


class CaosResult:
    def __init__(self, result_code: int, content: bytes, process_id: int):
        self.Content = content.decode("utf-8")
        self.ResultCode = result_code
        self.ProcessID = process_id
        self.Success = result_code == 0


class SharedMemoryCaosInjector:
    lock = Lock()
    shared_memory_size = 131072
    number_of_injections = 0

    def __init__(self, game_name: str = "DockingStation"):
        self.game_name = game_name

    def ExecuteCaos(self, caos: str, action="execute"):
        time.sleep(0.05)
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
        self.number_of_injections += 1
        self.lock.release()
        return CaosResult(
            result_code=result_code, content=result, process_id=process_id
        )


CI = SharedMemoryCaosInjector("Docking Station")
