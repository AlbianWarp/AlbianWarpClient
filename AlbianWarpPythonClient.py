from CaosEvolution.GameVariables import *
from CaosEvolution.Agent import AgentBuilder, enumAgents
from CaosEvolution import CI, WorldName, add_user_to_contact_list, delete_creature_by_moniker
from decorators import retry
import requests
from requests.auth import HTTPBasicAuth
import logging
import os
import configparser
from socketIO_client import SocketIO, BaseNamespace
import threading
import time

logger = logging.getLogger('AW')
logger.setLevel("INFO")
# TODO: logger does not work reliable with the current multithreading approach, investigate and replace all the
# TODO: ugly print('') Statements with logger.info, logger.debug and so on...

def read_config():
    config = configparser.ConfigParser()
    config['DEFAULT'] = {
        'username': '',
        'password': '',
        'url': 'https://alpha.albianwarp.com',
        'port': 443,
        'my_creatures_directory': r"C:\Users\%s\Documents\Creatures\Docking Station\My Creatures" % os.getlogin()
    }
    config.read('albianwarp.cfg')
    return config['albianwarp']


cfg = read_config()
socketIO = None
socketio_sid = None
auth_token = None
run = True

def sleep_while_run(seconds):
    for second in range(seconds):
        if not run:
            break
        time.sleep(1)

class AwNamespace(BaseNamespace):

    def on_connect(self):
        socketIO.emit('auth', {'token': auth_token})
        print({'token': auth_token})

    def on_reconnect(self):
        socketIO.emit('auth', {'token': auth_token})
        print({'token': auth_token})

    def on_disconnect(self):
        socketIO.emit('auth', {'token': auth_token})
        print({'token': auth_token})

    def on_auth_acc(self, data):
        global socketio_sid
        socketio_sid = data['sid']

    def on_rtdma(self, data):
        print("recieved a RTDMA")
        try:
            if AgentBuilder(1, 1, 35754, data).inject().Success:
                print("DEBUG: INJECTED incoming RTDMA: %s" % data)
        except Exception as e:
            print("ERROR: %s" % e)
        print(data)


def socketio_worker():
    global socketIO
    print("DEBUG: soketio_handler thread started")
    socketIO = SocketIO(cfg['url'], cfg['port'], Namespace=AwNamespace)
    socketIO.emit('auth', {'token': auth_token})
    socketIO.wait()


def main():
    initial_checks()
    verify_login_credentials()
    print("going online...")
    CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1004 next")
    game_user_of_this_world.Value = cfg['username']
    game_status.Value = "online"
    game_aw_status.Value = "online"
    print("running...")
    print(CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1005 mesg writ targ 500 next").Content)
    socketio_thread = threading.Thread(target=socketio_worker)
    socketio_thread.daemon = True
    socketio_thread.start()
    # creatures download handling
    creature_download_handler_thread = threading.Thread(target=creature_download_handler)
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
    # rtdma send handling
    rtdma_send_handler_thread = threading.Thread(target=rtdma_send_handler)
    rtdma_send_handler_thread.daemon = True
    rtdma_send_handler_thread.start()
    while run:
        dbg_out = CI.ExecuteCaos("DBG: POLL").Content.strip('\x00')
        if dbg_out != "":
            print("DBG: OUTS:")
            print(dbg_out)
        time.sleep(1)


def initial_checks():
    server_version = "alpha andromeda"
    bootstrap_version = "alpha alpaca"
    print('My Creatures directory: "%s"' % cfg['my_creatures_directory'])
    print("DEBUG: Checking Bootstrap version...")
    if eame_aw_mod_version == "":
        print("ERROR: Game modifications are not Installed! :(")
        exit(1)
    elif eame_aw_mod_version != bootstrap_version:
        print('ERROR: Wrong modification version found! Expected "%s" found "%s" instead' % (
                bootstrap_version, eame_aw_mod_version))
        exit(1)

    print("Checking server version...")
    actual_version = requests.get("%s/version" % cfg['url']).text
    if actual_version != server_version:
        print("ERROR: Server and Client Version mismatch, are you running the latest/correct client version?")
        print('ERROR: Server Version does not match! Expected "%s", found "%s"' % (server_version, actual_version))
        exit(1)


def verify_login_credentials():
    global auth_token
    auth_test = requests.get("%s/login" % cfg['url'], auth=HTTPBasicAuth(cfg['username'], cfg['password']))
    while auth_test.status_code != 200:
        cfg['username'] = input('Please enter your username: ')
        cfg['password'] = input('Please enter your password: ')
        auth_test = requests.get("%s/login" % cfg['url'], auth=HTTPBasicAuth(cfg['username'], cfg['password']))
        if auth_test.status_code != 200:
            print('Wrong username or password, please try again!')
    auth_token = auth_test.json()['token']
    print(auth_token)


@retry(Exception)
def send_creature(agent):
    tmp = agent.dict
    print("DETECTED SCA: %s" % agent.unid)
    print("DEBUG: Processing  %s" % tmp)
    if tmp['creature_name'] != "":
        creature_file = os.path.join(
            cfg['my_creatures_directory'],
            "%s_%s.ds.creature" % (tmp['creature_name'], tmp['moniker'].replace('-', '_'))
        )
    else:
        creature_file = os.path.join(
            cfg['my_creatures_directory'],
            "%s.ds.creature" % tmp['moniker'].replace('-', '_')
        )
    if os.path.isfile(creature_file):
        print('DEBUG: Found creature to warp at "%s"' % creature_file)
        with open(creature_file, 'rb') as f:
            files = {'file': f}
            values = {'recipient': tmp['aw_recipient'], 'creature_name': tmp['creature_name']}
            result = requests.post("%s/creature_upload" % cfg['url'], files=files, data=values,
                                   headers={'token': auth_token})
        if result.status_code == 200:
            print("uploaded creature %s to %s" % (tmp['moniker'], tmp['aw_recipient']))
            time.sleep(5)
            print(delete_creature_by_moniker(tmp['moniker']))
            if not os.path.isfile(creature_file):
                print('Deleted creature file "%s" after succesfull upload' % creature_file)
            else:
                print('COULD NOT delete creature file "%s" after succesfull upload, probably already deleted!' % creature_file)
        else:
            print("ERROR: uploading creature %s to %s FAILED! Status Code: %s" % (
            tmp['moniker'], tmp['aw_recipient'], result.status_code))
    else:
        print("ERROR: Could not find %s" % creature_file)
    agent.Kill()


@retry(Exception)
def download_creatures():
    print("DEBUG: requesting available creatures")
    available_creatures = requests.get("%s/creatures" % cfg['url'],
                                       headers={'token': auth_token})
    if available_creatures.status_code == 200:
        for creature in available_creatures.json()['creatures']:
            print("found creature %s" % creature['filename'])
            result = requests.get("%s/creature/%s" % (cfg['url'], creature['id']),
                                  headers={'token': auth_token})
            if result.status_code == 200:
                with open(os.path.join(cfg['my_creatures_directory'], creature['filename']), 'wb') as file:
                    file.write(result.content)
            else:
                raise Exception("Creature upload Failed! Status Code: %s" % result.status_code)
            requests.delete("%s/creature/%s" % (cfg['url'], creature['id']),
                            headers={'token': auth_token})
    else:
        print("ERROR: could not request available creatures. Status Code: %s" % available_creatures.status_code)


def creature_download_handler():
    global run
    print("DEBUG: creature_download_handler thread started")
    while run:
        try:
            download_creatures()
        except Exception as e:
            print("ERROR: %s" % e)
            run = False
        sleep_while_run(50)
    print("DEBUG: creature_download_handler thread ended")


def creature_upload_handler():
    global run
    print("DEBUG: creature_upload_handler thread started")
    while run:
        try:
            game_aw_online_indicator.Value = 1
            if WorldName != "Startup":
                for agent in enumAgents(1, 1, 35760):
                    CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1004 next")
                    send_creature(agent)
                    CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1005 next")
        except Exception as e:
            print("ERROR: %s" % e)
            run = False
        sleep_while_run(8)
    print("DEBUG: creature_upload_handler thread ended")


@retry(Exception)
def send_dma(agent):
    tmp = agent.dict
    print("DETECTED outgoing DMA: %s" % agent.unid)
    print("DEBUG: Processing %s" % tmp)
    result = requests.post("%s/messages" % cfg['url'],
                           headers={'token': auth_token},
                           json=tmp)
    if result.status_code == 200:
        print("SENT DMA (%s)" % agent.unid)
        agent.Kill()


def dma_send_handler():
    global run
    print("DEBUG: dma_send_hanlder thread started")
    while run:
        try:
            game_aw_online_indicator.Value = 1
            if WorldName != "Startup":
                for agent in enumAgents(1, 1, 35753):
                    CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1004 next")
                    send_dma(agent)
                    CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1005 next")
        except Exception as e:
            print("ERROR: %s" % e)
            run = False
        sleep_while_run(5)
    print("DEBUG: dma_send_handler thread ended")


@retry(Exception)
def receive_dmas():
    print("DEBUG: requesting available DMA's")
    available_messages = requests.get("%s/messages" % cfg['url'], headers={'token': auth_token})
    if available_messages.status_code == 200:
        for message_id in available_messages.json()['messages']:
            message = requests.get("%s/message/%s" % (cfg['url'], message_id), headers={'token': auth_token}).json()
            CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1004 next")
            try:
                if AgentBuilder(1, 1, 35754, message).inject().Success:
                    print("INJECTED incoming DMA: %s" % message)
            except Exception as e:
                print("ERROR: %s" % e)
            finally:
                if not requests.delete("%s/message/%s" % (cfg['url'], message_id),
                                       headers={'token': auth_token}).status_code == 200:
                    print("ERROR: could not delete message %s" % message)
            CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1005 next")


def dma_receive_handler():
    global run
    print("DEBUG: dma_receive_handler thread started")
    while run:
        if WorldName != "Startup":
            try:
                receive_dmas()
            except Exception as e:
                print(e)
                run = False
        sleep_while_run(9)
    print("DEBUG: dma_receive_handler thread ended")

retry(Exception)
def send_rtdma(agent):
    tmp = agent.dict
    print("DETECTED outgoing RTDMA: %s" % agent.unid)
    print("DEBUG: Processing %s" % tmp)
    socketIO.emit('rtdma', tmp)
    print("SENT RTDMA (%s)" % agent.unid)
    agent.Kill()


def rtdma_send_handler():
    global run
    print("DEBUG: rtdma_send_handler thread started")
    while run:
        try:
            game_aw_online_indicator.Value = 1
            if WorldName != "Startup":
                for agent in enumAgents(1, 1, 35755):
                    CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1004 next")
                    send_rtdma(agent)
                    CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1005 next")
        except Exception as e:
            print("ERROR: %s" % e)
            run = False
        sleep_while_run(2)
    print("DEBUG: rtdma_send_handler thread ended")

@retry(Exception)
def update_contact_list():
    users = requests.get("%s/users" % cfg['url'], headers={'token': auth_token})
    for user, status in users.json():
        #print("DEBUG: %s is %s " % (user, status))
        add_user_to_contact_list(user)
        CI.ExecuteCaos('sets game "%s_status" "%s"' % (user, status))


def contactlist_handler():
    print("DEBUG: contactlist_handler thread started")
    global run
    while run:
        try:
            update_contact_list()
        except Exception as e:
            print("ERROR: %s" % e)
            run = False
        sleep_while_run(5)
    print("DEBUG: contactlist_handler thread ended")

if __name__ == '__main__':
    main()
