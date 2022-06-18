import sys
import platform
import os
from threading import Lock
import time


class CaosResult:
    def __init__(self, result_code: int, content: str, process_id: int):
        self.Content = content.decode("utf-8")
        self.ResultCode = result_code
        self.ProcessID = process_id
        self.Success = result_code == 0


# LC2E and possibly Creatures Exodus!  (TODO: figure out if Exodus uses the same system (and the same ~/.creaturesengine/port) and include a check for Mac OS X or better yet, just make the other one check for Windows and make this the "else:" XD )
if platform.system() == "Linux":
    import socket, json

    print("Oh, you're on linux. Hello linux friend!")

    f = os.path.join(os.getenv("HOME"), ".creaturesengine", "port")
    DefaultPort = 20001

    class CaosInjectionResponse(object):
        def __init__(self, content, success):
            self.Content = content
            self.Success = success

    class LinuxCaosInjector(object):

        lock = Lock()
        host = "localhost"

        def __init__(self, port):
            self.port = port

        def ExecuteCaos(self, caos):
            bargle = ":thisworked"

            self.lock.acquire()

            s = socket.socket()

            try:
                s.connect((self.host, self.port))
                s.sendall((caos + ' outs "' + bargle + '"\r\nrscr\r\n').encode())
                s.shutdown(socket.SHUT_WR)

                res = ""

                while True:
                    data = s.recv(1024)
                    if not data:
                        break
                    res += data.decode()
            finally:
                try:
                    s.close()
                finally:
                    self.lock.release()

            success = res.endswith(bargle)
            content = res[: -len(bargle)] if success else res

            return CaosInjectionResponse(content, success)

    def tryPort(port):
        try:
            i = LinuxCaosInjector(port)
            r = i.ExecuteCaos(
                "setv va00 9  mulv va00 va00  outv va00"
            )  # Square of 9 == 81  :>
        except ConnectionRefusedError:
            return False

        return r.Success and r.Content == "81"

    ParseError = object()

    if os.path.isfile(f):
        h = open(f, "r")
        try:
            p = h.read()
        finally:
            h.close()

        try:
            standardPort = int(p.strip())
        except ValueError:
            print(
                "Found standard port file at "
                + f
                + " but couldn't parse it as an integer!  It contained: "
                + repr(p)
            )
            standardPort = ParseError
    else:
        standardPort = None
    #

    showHiddens = True  # Todo softcode this from a CLI argument!

    def readTLC2EInstances():
        def parse(f):
            h = open(f, "r")
            try:
                return json.load(h)
            finally:
                h.close()

        r = []
        sd = os.path.join(os.getenv("HOME"), ".tlc2e")
        for d in [os.path.join(sd, "running"), os.path.join(sd, "running-manual")]:
            if os.path.isdir(d):
                r.extend(
                    map(
                        lambda n: parse(os.path.join(d, n)),
                        filter(lambda n: n.lower().endswith(".json"), os.listdir(d)),
                    )
                )
        return r

    #

    tlc2es = readTLC2EInstances()

    tlc2esWithPorts = filter(
        lambda t: t.get("e6b02a88-7311-4a27-bbb7-d8f3a2d4e353") != None
        and t["e6b02a88-7311-4a27-bbb7-d8f3a2d4e353"].get("caosInjectionType") == "tcp"
        and t["e6b02a88-7311-4a27-bbb7-d8f3a2d4e353"].get("caosInjectionPort") != None,
        tlc2es,
    )

    if not showHiddens:
        tlc2esWithPorts = filter(
            lambda t: not (
                t.get("e6b02a88-7311-4a27-bbb7-d8f3a2d4e353") != None
                and t["e6b02a88-7311-4a27-bbb7-d8f3a2d4e353"].get("hidden") == True
            ),
            tlc2esWithPorts,
        )

    # construct the menu :3

    Default = object()

    def formatTLC2EInstance(t):
        d = t["e6b02a88-7311-4a27-bbb7-d8f3a2d4e353"]
        port = d["caosInjectionPort"]
        hidden = d.get("hidden")

        if hidden == None:
            hidden = False

        hasExtraInfo = t.get("2424f4d5-4888-421d-bd19-ba3d4067598d") != None

        if hasExtraInfo:
            e = t["2424f4d5-4888-421d-bd19-ba3d4067598d"]

            name = e.get("name")
            worldnames = e.get("worldnames")
            creator = e.get("creator")
        else:
            name = None
            worldnames = None
            hidden = None
            creator = Default

        r = ""

        if name != None:
            r += name + " (a "

        if hidden:
            r += "HIDDEN "

        if creator != Default:
            r += "User-made" if creator == None else creator
            r += " "

        r += "TLC2E Engine on port " + str(port)

        if worldnames != None:
            worldnames = list(filter(lambda n: n != "Startup", worldnames))

            if len(worldnames) == 0:
                r += " (with no worlds)"
            elif len(worldnames) == 1:
                r += " (with only the one world: " + worldnames[0] + ")"
            else:
                r += " (with worlds: " + (", ".join(worldnames)) + ")"

        if name != None:
            r += ")"

        return r

    #

    menu = []

    if tryPort(DefaultPort):
        menu.append((DefaultPort, "Engine on Default Port"))
    if standardPort != None and standardPort != ParseError and tryPort(DefaultPort):
        menu.append((standardPort, "Engine on Standard Port"))

    menu.extend(
        sorted(
            map(
                lambda t: (
                    t["e6b02a88-7311-4a27-bbb7-d8f3a2d4e353"]["caosInjectionPort"],
                    formatTLC2EInstance(t),
                ),
                tlc2esWithPorts,
            ),
            key=lambda a: a[1],
        )
    )

    if len(menu) == 0:
        if standardPort != None:
            if standardPort == ParseError:
                print()
                print(
                    "Uh oh, we need for this file to contain the TCP port number of the engine to inject CAOS through (an integer, not "
                    + repr(p)
                    + "): "
                    + f
                )
                print(
                    "We also tried TLC2E and the default port "
                    + str(DefaultPort)
                    + ", but couldn't find an engine on either!"
                )
                print(
                    "So I have no idea which engine to connect to if one is even running :["
                )
                sys.exit(33)
            else:
                print()
                print(
                    "We tried TLC2E, the port "
                    + str(standardPort)
                    + " explicitly given by "
                    + f
                    + " and the default port "
                    + str(DefaultPort)
                    + ", but couldn't find an engine on any of them!"
                )
                print(
                    "So it looks like an engine isn't running, and if it is, then I don't know which one to connect to! :P"
                )
                sys.exit(34)
        else:
            print()
            print(
                "Uh oh, we need either TLC2E or this file to find the TCP loopback port to inject CAOS into the engine through: "
                + f
            )
            print(
                "We also tried the default port "
                + str(DefaultPort)
                + ", but couldn't find an engine on it!"
            )
            print(
                "So I have no idea which engine to connect to if one is even running :["
            )
            sys.exit(32)

    elif len(menu) == 1:
        print("Using the only engine we found without menu prompt: " + menu[0][1])
        port = menu[0][0]

    else:
        print("We've found multiple engines to connect to!")
        print("Please choose one from the menu below :)")

        for i in range(len(menu)):
            print("\t" + str(i) + " - " + menu[i][1])

        while True:
            sys.stdout.write("> ")
            sys.stdout.flush()
            a = sys.stdin.readline().strip()

            try:
                ai = int(a)
            except ValueError:
                ai = None

            if ai == None:
                print(
                    "  I'm sorry I didn't understand "
                    + repr(a)
                    + ".  Please enter an integer ^^'"
                )
            else:
                if ai < 0 or ai >= len(menu):
                    print("  I'm sorry, please enter an integer on the menu ^^'")
                else:
                    port = menu[ai][0]
                    print(
                        "Excellent!  Using engine at port "
                        + str(port)
                        + ": "
                        + menu[ai][1]
                        + "  :D"
                    )
                    break

    CI = LinuxCaosInjector(port)

# The windows one!
else:
    import mmap
    import struct
    import win32event

    class SharedMemoryCaosInjector:

        lock = Lock()

        shared_memory_size = 131072

        def __init__(self, game_name: str = "DockingStation"):
            self.game_name = game_name

        def ExecuteCaos(self, caos: str, action="execute"):
            time.sleep(0.01)
            self.lock.acquire()
            hMutex = win32event.OpenMutex(0x1F0001, False, self.game_name + "_mutex")
            win32event.WaitForSingleObject(hMutex, win32event.INFINITE)
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
            win32event.WaitForSingleObject(result_event_handler, win32event.INFINITE)
            shared_memory.seek(0)
            _, process_id, result_code, result_length, _, _ = struct.unpack(
                "4sIIIII", shared_memory.read(24)
            )
            result = shared_memory.read(result_length)
            shared_memory.seek(24)
            shared_memory.write(b"\x00" * (result_length + len(caos) + 9))
            win32event.ReleaseMutex(hMutex)
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
