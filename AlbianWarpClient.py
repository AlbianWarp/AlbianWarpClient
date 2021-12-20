#!/usr/bin/env python3

import sys
import os
from distutils.dir_util import copy_tree
import ssl
import time
import json
import logging
import requests
import threading
import configparser
import zipfile

from urllib3 import PoolManager
from requests.adapters import HTTPAdapter

from util import retry
from CaosEvolution.GameVariables import *
from CaosEvolution.Agent import AgentBuilder, enumAgents
from CaosEvolution import (
    CI,
    WorldName,
    add_user_to_contact_list,
    delete_creature_by_moniker,
)

from ws4py.client.threadedclient import WebSocketClient

logger = logging.getLogger("AW")
logger.setLevel("INFO")


# TODO: logger does not work reliable with the current multithreading approach, investigate and replace all the
# TODO: ugly print('') Statements with logger.info, logger.debug and so on...
# TODO: This whole mess with multiple Threads doing different things... must be simplified massively!
# TODO: Split this whole freaking beast up into modules!


def read_config():
    config = configparser.ConfigParser()
    config["DEFAULT"] = {
        "username": "",
        "password": "",
        "websocket_url": "wss://gameserver.albianwarp.com/ws",
        "url": "https://gameserver.albianwarp.com",
        "my_creatures_directory": r"C:\Users\%s\Documents\Creatures\Docking Station\My Creatures"
        % os.getlogin(),
        "ds_directory": r"C:\GOG Games\Creatures Exodus\Docking Station",
        "github_game_modification_update_url": r"https://gameserver.albianwarp.com/game_modifications_latest.json",
        "disable_bootstrap_auto_update": "false",
        "disable_initial_checks": "false",
    }
    f = os.path.join(os.getenv("HOME", ""), ".albianwarp", "albianwarp.cfg")
    if not os.path.isfile(f):
        f = "albianwarp.cfg"  # fallback to the old way based on the CWD of the terminal it's run from ^^'
    if not os.path.isfile(f):
        print(f"Missing config file {f}")
        sys.exit(1)
    config.read(f)
    if not "albianwarp" in config:
        print(f"Config file is corrupted!: {f}")
        sys.exit(1)
    return config["albianwarp"]


class MyAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False, **kwargs):
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_version=ssl.PROTOCOL_TLSv1_2,
        )


s = requests.Session()
s.mount("https://", MyAdapter())
cfg = read_config()
ws = None
auth_token = None
run = True
latest_release = {}

contact_list = []


def sleep_while_run(seconds):
    for second in range(seconds):
        if not run:
            break
        time.sleep(1)


def consumer(message, websocket):
    try:
        data = json.loads(str(message))
        if "ping" in data:
            websocket.send(json.dumps({"pong": f"{data['ping']}"}))
        if "aw_sender" in data:
            print("received a RTDMA")
            try:
                if AgentBuilder(1, 1, 35756, data).inject().Success:
                    print(f"DEBUG: INJECTED incoming RTDMA: {data}")
            except Exception as e:
                print(f"ERROR: {e}")
    except Exception as e:
        print(message)
        print(f"NOT JSON! {e}")


class AwSocketClient(WebSocketClient):
    def opened(self):
        self.send(json.dumps({"auth": auth_token}))
        print("Opened WebSocket")

    def closed(self, code, reason=None):
        print("Closed WebSocket", code, reason)

    def received_message(self, m):
        consumer(m, self)
        if len(m) == 175:
            self.close(reason="Bye bye")


def socket_handler():
    print("DEBUG: socket_handler thread started")
    global run
    global ws
    while run:
        try:
            ws = AwSocketClient(cfg["websocket_url"])
            ws.connect()
            ws.run_forever()
        except Exception as e:
            run = False
            raise e
    run = False
    print("DEBUG: socket_handler thread ended")


def download_latest_game_modifications():
    global s
    global cfg
    global latest_release
    latest_release = s.get(cfg["github_game_modification_update_url"]).json()
    print(
        f"Latest available GameModification Version is \"{latest_release['tag_name']}\""
    )
    bootstrap_download_dir = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "bootstrap_downloads"
    )
    if not os.path.exists(bootstrap_download_dir):
        os.makedirs(bootstrap_download_dir)
    if not os.path.isfile(
        os.path.join(bootstrap_download_dir, f"{latest_release['tag_name']}.zip")
    ):
        print(
            'downloading AlbianWarpGameModifications Version "%s"'
            % latest_release["tag_name"]
        )
        r = requests.get(latest_release["zipball_url"], stream=True)
        with open(
            os.path.join(bootstrap_download_dir, f"{latest_release['tag_name']}.zip"),
            "wb",
        ) as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
    else:
        print(
            'AlbianWarpGameModifications version "%s" already downloaded'
            % latest_release["tag_name"]
        )
    if not os.path.exists(
        os.path.join(bootstrap_download_dir, latest_release["tag_name"])
    ):
        with zipfile.ZipFile(
            os.path.join(bootstrap_download_dir, f"{latest_release['tag_name']}.zip"),
            "r",
        ) as z:
            print(
                'Extracting Bootstrap from Zipfile "%s.zip"'
                % latest_release["tag_name"]
            )
            files_to_extract = [
                file
                for file in z.namelist()
                if file.startswith(f"{z.namelist()[0]}Bootstrap/")
            ]
            z.extractall(
                os.path.join(bootstrap_download_dir, latest_release["tag_name"]),
                members=files_to_extract,
            )
            print(
                'Copying/installing files for Version "%s"!'
                % latest_release["tag_name"]
            )
            copy_tree(
                os.path.join(
                    bootstrap_download_dir,
                    latest_release["tag_name"],
                    z.namelist()[0],
                    "Bootstrap/",
                ),
                os.path.join(cfg["ds_directory"], "Bootstrap/"),
            )
            print(
                "Bootstrap was just updated, please ensure the modifications in your world are active."
            )
            print(
                "Please restart the Game and AlbianWarp Client and create a new World :)"
            )


def main():
    global s
    if cfg["disable_bootstrap_auto_update"].lower() != "true":
        download_latest_game_modifications()
    else:
        print(
            "Bootstrap updating is disabled via configuration. Did not try to download latest Bootstrap Version!"
        )
    if cfg["disable_initial_checks"].lower() != "true":
        initial_checks()
    else:
        print("Initial checks are disabled via configuration, and therefore skipped.")
    verify_login_credentials()
    print("going online...")
    CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1004 next")
    game_user_of_this_world.Value = cfg["username"]
    game_status.Value = "online"
    game_aw_status.Value = "online"
    print("running...")
    print(
        CI.ExecuteCaos(
            "enum 1 2 14 mesg writ targ 1005 mesg writ targ 500 next"
        ).Content
    )
    socket_handler_thread = threading.Thread(target=socket_handler)
    socket_handler_thread.daemon = True
    socket_handler_thread.start()
    # creatures download handling
    creature_download_handler_thread = threading.Thread(
        target=creature_download_handler
    )
    creature_download_handler_thread.daemon = True
    creature_download_handler_thread.start()
    # creatures upload handling
    creature_upload_handler_thread = threading.Thread(target=creature_upload_handler)
    creature_upload_handler_thread.daemon = True
    creature_upload_handler_thread.start()
    # dma receive handling
    dma_receive_handler_thread = threading.Thread(target=dma_receive_handler)
    dma_receive_handler_thread.daemon = True
    dma_receive_handler_thread.start()
    # dma send handling
    dma_send_handler_thread = threading.Thread(target=dma_send_handler)
    dma_send_handler_thread.daemon = True
    dma_send_handler_thread.start()
    # contactlist handling
    contactlist_handler_thread = threading.Thread(target=contactlist_handler)
    contactlist_handler_thread.daemon = True
    contactlist_handler_thread.start()
    # rtdma send Handler
    rtdma_send_handler_thread = threading.Thread(target=rtdma_send_handler)
    rtdma_send_handler_thread.daemon = True
    rtdma_send_handler_thread.start()
    while run:
        dbg_out = CI.ExecuteCaos("DBG: POLL").Content.strip("\x00")
        if dbg_out != "":
            print("DBG: OUTS:")
            print(dbg_out)
        time.sleep(1)
    time.sleep(2)
    input("Press Enter to Exit...")


def initial_checks():
    server_version = "beta baboon"
    print(f"DEBUG: My Creatures directory: \"{cfg['my_creatures_directory']}\"")
    print("DEBUG: Checking Bootstrap version...")
    if eame_aw_mod_version == "":
        print("ERROR: Game modifications are not Installed! :(")
        exit(1)
    elif eame_aw_mod_version not in [latest_release["tag_name"], "dev", "alpha alpaca"]:
        print(
            'ERROR: Wrong modification version found! Expected "%s" found "%s" instead'
            % (latest_release["tag_name"], eame_aw_mod_version)
        )
        exit(1)
    print("DEBUG: Checking server version...")
    actual_version = s.get(f"{cfg['url']}/version").text
    if actual_version != server_version:
        print(
            "ERROR: Server and Client Version mismatch, are you running the latest/correct client version?"
        )
        print(
            'ERROR: Server Version does not match! Expected "%s", found "%s"'
            % (server_version, actual_version)
        )
        exit(1)


def verify_login_credentials():
    global auth_token
    auth_test = s.post(
        f"{cfg['url']}/auth",
        json={"username": cfg["username"], "password": cfg["password"]},
    )
    while auth_test.status_code != 200:
        cfg["username"] = input("Please enter your username: ")
        cfg["password"] = input("Please enter your password: ")
        auth_test = s.post(
            f"{cfg['url']}/auth",
            json={"username": cfg["username"], "password": cfg["password"]},
        )
        if auth_test.status_code != 200:
            print("Wrong username or password, please try again!")
    auth_token = auth_test.json()["token"]
    print(auth_token)


@retry(Exception)
def send_creature(agent):
    tmp = agent.dict
    print(f"DETECTED SCA: {agent.unid}")
    print(f"DEBUG: Processing  {tmp}")
    if tmp["creature_name"] != "":
        creature_file = os.path.join(
            cfg["my_creatures_directory"],
            f"{tmp['creature_name']}_{tmp['moniker'].replace('-', '_')}.ds.creature",
        )
    else:
        creature_file = os.path.join(
            cfg["my_creatures_directory"],
            f"{tmp['moniker'].replace('-', '_')}.ds.creature",
        )
    if os.path.isfile(creature_file):
        print(f'DEBUG: Found creature to warp at "{creature_file}"')
        with open(creature_file, "rb") as f:
            files = {"file": f}
            values = {
                "recipient": tmp["aw_recipient"],
                "creature_name": tmp["creature_name"],
            }
            result = s.post(
                f"{cfg['url']}/creature",
                files=files,
                data=values,
                headers={"token": auth_token},
            )
        if result.status_code != 200:
            print(
                "ERROR: uploading creature %s to %s FAILED! Status Code: %s"
                % (tmp["moniker"], tmp["aw_recipient"], result.status_code)
            )
        else:
            print(f"uploaded creature {tmp['moniker']} to {tmp['aw_recipient']}")
        print(delete_creature_by_moniker(tmp["moniker"]))
        time.sleep(1)
        if not os.path.isfile(creature_file):
            print(f'Deleted creature file "{creature_file}" after succesfull upload')
        else:
            print(
                'COULD NOT delete creature file "%s" after successful upload!'
                % creature_file
            )
    else:
        print(f"ERROR: Could not find {creature_file}")
    agent.Kill()


@retry(Exception)
def download_creatures():
    # print("DEBUG: requesting available creatures")
    available_creatures = s.get(f"{cfg['url']}/creature", headers={"token": auth_token})
    if available_creatures.status_code == 200:
        for creature in available_creatures.json()["creatures"]:
            print(f"found creature {creature['filename']}")
            result = s.get(
                f"{cfg['url']}/creature/{creature['id']}",
                headers={"token": auth_token},
            )
            if result.status_code == 200:
                with open(
                    os.path.join(cfg["my_creatures_directory"], creature["filename"]),
                    "wb",
                ) as file:
                    file.write(result.content)
            else:
                raise Exception(
                    f"Creature upload Failed! Status Code: {result.status_code}"
                )
            s.delete(
                f"{cfg['url']}/creature/{creature['id']}",
                headers={"token": auth_token},
            )
    else:
        print(
            "ERROR: could not request available creatures. Status Code: %s"
            % available_creatures.status_code
        )


def creature_download_handler():
    global run
    print("DEBUG: creature_download_handler thread started")
    while run:
        try:
            download_creatures()
        except Exception as e:
            print(f"ERROR: {e}")
            run = False
            raise e
        sleep_while_run(50)
    print("DEBUG: creature_download_handler thread ended")


def creature_upload_handler():
    global run
    print("DEBUG: creature_upload_handler thread started")
    while run:
        try:
            if WorldName != "Startup":
                game_aw_online_indicator.Value = 1
                game_user_of_this_world.Value = cfg["username"]
                for agent in enumAgents(1, 1, 35760):
                    CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1004 next")
                    send_creature(agent)
                    CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1005 next")
        except Exception as e:
            print(f"ERROR: {e}")
            run = False
            raise e
        sleep_while_run(5)
    print("DEBUG: creature_upload_handler thread ended")


@retry(Exception)
def send_dma(agent):
    tmp = agent.dict
    print(f"DETECTED outgoing DMA: {agent.unid}")
    print(f"DEBUG: Processing {tmp}")
    result = s.post(f"{cfg['url']}/message", headers={"token": auth_token}, json=tmp)
    if result.status_code == 200:
        print(f"SENT DMA ({agent.unid})")
    else:
        print(f"Could not send DMA, Status Code: {result.status_code}")
    agent.Kill()


def dma_send_handler():
    global run
    print("DEBUG: dma_send_hanlder thread started")
    while run:
        try:
            if WorldName != "Startup":
                game_aw_online_indicator.Value = 1
                game_user_of_this_world.Value = cfg["username"]
                for agent in enumAgents(1, 1, 35753):
                    CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1004 next")
                    send_dma(agent)
                    CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1005 next")
        except Exception as e:
            print(f"ERROR: {e}")
            run = False
            raise e
        sleep_while_run(5)
    print("DEBUG: dma_send_handler thread ended")


@retry(Exception)
def receive_dmas():
    # print("DEBUG: requesting available DMA's")
    available_messages = s.get(f"{cfg['url']}/message", headers={"token": auth_token})
    if available_messages.status_code == 200:
        for message_id in available_messages.json()["messages"]:
            message = s.get(
                f"{cfg['url']}/message/{message_id}",
                headers={"token": auth_token},
            ).json()
            CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1004 next")
            try:
                if AgentBuilder(1, 1, 35754, message).inject().Success:
                    print(f"INJECTED incoming DMA: {message}")
            except Exception as e:
                print(f"ERROR: {e}")
            finally:
                if (
                    not s.delete(
                        f"{cfg['url']}/message/{message_id}",
                        headers={"token": auth_token},
                    ).status_code
                    == 200
                ):
                    print(f"ERROR: could not delete message {message}")
            CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1005 next")


def dma_receive_handler():
    global run
    print("DEBUG: dma_receive_handler thread started")
    while run:
        if WorldName != "Startup":
            game_aw_online_indicator.Value = 1
            game_user_of_this_world.Value = cfg["username"]
            try:
                receive_dmas()
            except Exception as e:
                print(e)
                run = False
                raise e
        sleep_while_run(10)
    print("DEBUG: dma_receive_handler thread ended")


@retry(Exception)
def update_contact_list():
    users = s.get(f"{cfg['url']}/who_is_online", headers={"token": auth_token})
    online_users = users.json()
    for user in online_users:
        add_user_to_contact_list(user)
    contact_list = (
        CI.ExecuteCaos(
            """
    sets va00 ""
    loop
      sets va00 gamn va00
      setv va01 sins va00 1 "_contact"
      doif va01 ne -1
        outs "|" outs va00
      endi
    untl va00 eq ""
    """
        )
        .Content.strip("\x00")
        .replace("|!friend_contact|!net: ruso_contact|", "")
        .replace("_contact", "")
        .split("|")
    )
    for contact in contact_list:
        if contact not in online_users:
            status = "offline"
        else:
            status = "online"
        CI.ExecuteCaos(f'sets game "{contact}_status" "{status}"')


def contactlist_handler():
    print("DEBUG: contactlist_handler thread started")
    global run
    while run:
        try:
            update_contact_list()
        except Exception as e:
            print(f"ERROR: {e}")
            run = False
            raise e
        sleep_while_run(10)
    print("DEBUG: contactlist_handler thread ended")


@retry(Exception)
def send_rtdma(agent):
    tmp = agent.dict
    print(f"DETECTED outgoing RTDMA: {agent.unid}")
    print(f"DEBUG: Processing {tmp}")
    ws.send(json.dumps(tmp))
    print(f"SENT RTDMA ({agent.unid})")
    agent.Kill()


def rtdma_send_handler():
    global run
    print("DEBUG: rtdma_send_handler thread started")
    while run:
        try:
            if WorldName != "Startup":
                game_aw_online_indicator.Value = 1
                game_user_of_this_world.Value = cfg["username"]
                for agent in enumAgents(1, 1, 35755):
                    CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1004 next")
                    send_rtdma(agent)
                    CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1005 next")
        except Exception as e:
            print(f"ERROR: {e}")
            run = False
            raise e
        sleep_while_run(1)
    print("DEBUG: rtdma_send_handler thread ended")


if __name__ == "__main__":
    main()
