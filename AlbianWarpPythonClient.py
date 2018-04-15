from CaosEvolution.GameVariables import *
from CaosEvolution.Agent import AgentBuilder, enumAgents
from CaosEvolution import CI, WorldName, add_user_to_contact_list
import requests
from requests.auth import HTTPBasicAuth
import logging
import os
import configparser
import asyncio
from socketIO_client import SocketIO, BaseNamespace
import threading


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


class AwNamespace(BaseNamespace):

    def on_connect(self):
        socketIO.emit('auth', {'token': auth_token})
        logging.info({'token': auth_token})

    def on_reconnect(self):
        socketIO.emit('auth', {'token': auth_token})
        logging.info({'token': auth_token})

    def on_disconnect(self):
        socketIO.emit('auth', {'token': auth_token})
        logging.info({'token': auth_token})

    def on_auth_acc(self, data):
        print(data)
        global socketio_sid
        socketio_sid = data['sid']
        print(socketio_sid)

    def on_rtdma(self, data):
        logging.info("recieved a RTDMA")
        try:
            if AgentBuilder(1, 1, 35754, data).inject().Success:
                logging.debug("INJECTED incoming RTDMA: %s" % data)
        except Exception as e:
            logging.error(e)
        print(data)


def socketio_worker():
    global socketIO
    logging.debug("run socketio_handler")
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
    loop = asyncio.get_event_loop()
    try:
        socketio_thread.start()
        asyncio.ensure_future(update_contact_list())
        asyncio.ensure_future(receive_direct_message_agents())
        asyncio.ensure_future(send_direct_message_agents())
        asyncio.ensure_future(receive_creatures())
        asyncio.ensure_future(send_creatures())
        asyncio.ensure_future(send_real_time_direct_message_agents())
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        print('EXIT!')
        loop.close()


def initial_checks():
    server_version = "alpha andromeda"
    bootstrap_version = "alpha alpaca"
    print('"My Creatures" directory: "%s"' % cfg['my_creatures_directory'])
    print("Checking Bootstrap version...")
    if eame_aw_mod_version == "":
        logging.error("Game modifications are not Installed! :(")
        exit(1)
    elif eame_aw_mod_version != bootstrap_version:
        logging.error(
            'Wrong modification version found! Expected "%s" found "%s" instead' % (
                bootstrap_version, eame_aw_mod_version))
        exit(1)

    print("Checking server version...")
    actual_version = requests.get("%s/version" % cfg['url']).text
    if actual_version != server_version:
        print("Server and Client Version mismatch, are you running the latest/correct client version?")
        logging.error('Server Version does not match! Expected "%s", found "%s"' % (server_version, actual_version))
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


async def send_creatures():
    while True:
        logging.debug("run send_creatures")
        game_aw_online_indicator.Value = 1
        if WorldName != "Startup":
            for agent in enumAgents(1, 1, 35760):
                CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1004 next")
                tmp = agent.dict
                logging.info("DETECTED SCA: %s" % agent.unid)
                logging.debug("Processing  %s" % tmp)
                creature_file = os.path.join(cfg['my_creatures_directory'],
                                             "%s.ds.creature" % tmp['moniker'].replace('-', '_'))
                if os.path.isfile(creature_file):
                    logging.debug('Found creature to warp at "%s"' % creature_file)
                    files = {'file': open(creature_file, 'rb')}
                    values = {'recipient': tmp['aw_recipient'], 'creature_name': tmp['creature_name']}
                    result = requests.post("%s/creature_upload" % cfg['url'], files=files, data=values,
                                           headers={'token': auth_token})
                    if result.status_code == 200:
                        logging.info("uploaded creature %s to %s" % (tmp['moniker'], tmp['aw_recipient']))
                    else:
                        logging.error("uploading creature %s to %s FAILED" % (tmp['moniker'], tmp['aw_recipient']))
                agent.Kill()
                CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1005 next")
        await asyncio.sleep(5)


async def receive_creatures():
    while True:
        logging.debug("run receive_creatures")
        if WorldName != "Startup":
            available_creatures = requests.get("%s/creatures" % cfg['url'],
                                               headers={'token': auth_token})
            for creature in available_creatures.json()['creatures']:
                logging.info("found creature %s" % creature['filename'])
                result = requests.get("%s/creature/%s" % (cfg['url'], creature['id']),
                                      headers={'token': auth_token})
                if result.status_code == 200:
                    with open(os.path.join(cfg['my_creatures_directory'], creature['filename']), 'wb') as file:
                        file.write(result.content)
                else:
                    raise Exception(len(result.content))
                requests.delete("%s/creature/%s" % (cfg['url'], creature['id']),
                                headers={'token': auth_token})
        await asyncio.sleep(50)


async def send_direct_message_agents():
    while True:
        logging.debug("run send_direct_message_agents")
        game_aw_online_indicator.Value = 1
        if WorldName != "Startup":
            for agent in enumAgents(1, 1, 35753):
                CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1004 next")
                tmp = agent.dict
                logging.info("DETECTED outgoing DMA: %s" % agent.unid)
                logging.debug("Processing %s" % tmp)
                result = requests.post("%s/messages" % cfg['url'],
                                       headers={'token': auth_token},
                                       json=tmp)
                if result.status_code == 200:
                    logging.info("SENT DMA (%s)" % agent.unid)
                    agent.Kill()
                CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1005 next")
        await asyncio.sleep(5)


async def send_real_time_direct_message_agents():
    while True:
        logging.debug("run send_real_time_direct_message_agents")
        game_aw_online_indicator.Value = 1
        if WorldName != "Startup":
            for agent in enumAgents(1, 1, 35755):
                CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1004 next")
                tmp = agent.dict
                logging.info("DETECTED outgoing RTDMA: %s" % agent.unid)
                logging.debug("Processing %s" % tmp)
                socketIO.emit('rtdma', tmp)
                logging.info("SENT RTDMA (%s)" % agent.unid)
                agent.Kill()
                CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1005 next")
        await asyncio.sleep(1)


async def receive_direct_message_agents():
    while True:
        logging.debug("run receive_direct_message_agents")
        if WorldName != "Startup":
            available_messages = requests.get("%s/messages" % cfg['url'],
                                              headers={'token': auth_token})
            for message_id in available_messages.json()['messages']:
                message = requests.get("%s/message/%s" % (cfg['url'], message_id),
                                       headers={'token': auth_token}).json()
                CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1004 next")
                try:
                    if AgentBuilder(1, 1, 35754, message).inject().Success:
                        print("INJECTED incoming DMA: %s" % message)
                except Exception as e:
                    logging.error(e)
                finally:
                    if not requests.delete("%s/message/%s" % (cfg['url'], message_id),
                                           headers={'token': auth_token}).status_code == 200:
                        logging.error("could not delete message %s" % message)
                CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1005 next")
        await asyncio.sleep(10)


async def update_contact_list():
    while True:
        logging.debug("run updateContactList")
        game_aw_online_indicator.Value = 1
        if WorldName != "Startup":
            users = requests.get("%s/users" % cfg['url'], headers={'token': auth_token})
            for user, status in users.json():
                logging.debug("%s is %s " % (user, status))
                add_user_to_contact_list(user)
                CI.ExecuteCaos('sets game "%s_status" "%s"' % (user, status))
        await asyncio.sleep(10)


if __name__ == '__main__':
    main()
