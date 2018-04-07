from CaosEvolution.GameVariables import *
from CaosEvolution.Agent import AgentBuilder, enumAgents
from CaosEvolution import CI, WorldName, add_user_to_contact_list
import requests
from requests.auth import HTTPBasicAuth
import logging
import os
import configparser
import asyncio


def config():
    config = configparser.ConfigParser()
    config['DEFAULT'] = {
        'username': '',
        'password': '',
        'url': 'https://alpha.albianwarp.com',
        'my_creatures_directory': r"C:\Users\%s\Documents\Creatures\Docking Station\My Creatures" % os.getlogin()
    }
    config.read('albianwarp.cfg')
    return config['albianwarp']


cfg = config()


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
    loop = asyncio.get_event_loop()
    try:
        asyncio.ensure_future(updateContactList())
        asyncio.ensure_future(receive_direct_message_agents())
        asyncio.ensure_future(send_direct_message_agents())
        asyncio.ensure_future(receive_creatures())
        asyncio.ensure_future(send_creatures())
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        print('EXIT!')
        loop.close()


def initial_checks():
    server_version = "alpha alpaca"
    bootstrap_version = "alpha alpaca"
    print('"My Creatures" directory: "%s"' % cfg['my_creatures_directory'])
    print("Checking Bootstrap version...")
    if eame_aw_mod_version == "":
        logging.error("Game modifications are not Installed! :(")
        exit(1)
    elif eame_aw_mod_version != bootstrap_version:
        logging.error(
            'Wrong modification version found! Expected "%s" found "%s" instead' % (bootstrap_version, eame_aw_mod_version))
        exit(1)

    print("Checking server version...")
    actual_version = requests.get("%s/version" % cfg['url']).text
    if actual_version != server_version:
        print("Server and Client Version mismatch, are you running the latest/correct client version?")
        logging.error('Server Version does not match! Expected "%s", found "%s"' % (server_version, actual_version))
        exit(1)


def verify_login_credentials():
    auth_test = requests.get("%s/messages" % cfg['url'], auth=HTTPBasicAuth(cfg['username'], cfg['password']))
    while auth_test.status_code != 200:
        cfg['username'] = input('Please enter your username: ')
        cfg['password'] = input('Please enter your password: ')
        auth_test = requests.get("%s/messages" % cfg['url'], auth=HTTPBasicAuth(cfg['username'], cfg['password']))
        if auth_test.status_code != 200:
            print('Wrong username or password, please try again!')


async def send_creatures():
    while True:
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
                                           auth=HTTPBasicAuth(cfg['username'], cfg['password']))
                    if result.status_code == 200:
                        logging.info("uploaded creature %s to %s" % (tmp['moniker'], tmp['aw_recipient']))
                    else:
                        logging.error("uploading creature %s to %s FAILED" % (tmp['moniker'], tmp['aw_recipient']))
                agent.Kill()
                CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1005 next")
        await asyncio.sleep(5)


async def receive_creatures():
    while True:
        if WorldName != "Startup":
            available_creatures = requests.get("%s/creatures" % cfg['url'],
                                               auth=HTTPBasicAuth(cfg['username'], cfg['password']))
            for creature in available_creatures.json()['creatures']:
                logging.info("found creature %s" % creature['filename'])
                result = requests.get("%s/creature/%s" % (cfg['url'], creature['id']),
                                      auth=HTTPBasicAuth(cfg['username'], cfg['password']))
                if result.status_code == 200:
                    with open(os.path.join(cfg['my_creatures_directory'], creature['filename']), 'wb') as file:
                        file.write(result.content)
                else:
                    raise Exception(len(result.content))
                requests.delete("%s/creature/%s" % (cfg['url'], creature['id']),
                                auth=HTTPBasicAuth(cfg['username'], cfg['password']))
        await asyncio.sleep(50)


async def send_direct_message_agents():
    while True:
        game_aw_online_indicator.Value = 1
        if WorldName != "Startup":
            for agent in enumAgents(1, 1, 35753):
                CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1004 next")
                tmp = agent.dict
                logging.info("DETECTED outgoing DMA: %s" % agent.unid)
                logging.debug("Processing %s" % tmp)
                result = requests.post("%s/messages" % cfg['url'],
                                       auth=HTTPBasicAuth(cfg['username'], cfg['password']),
                                       json=tmp)
                if result.status_code == 200:
                    logging.info("SENT DMA (%s)" % (agent.unid))
                    agent.Kill()
                CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1005 next")
        await asyncio.sleep(5)


async def receive_direct_message_agents():
    while True:
        if WorldName != "Startup":
            available_messages = requests.get("%s/messages" % cfg['url'],
                                              auth=HTTPBasicAuth(cfg['username'], cfg['password']))
            for message_id in available_messages.json()['messages']:
                message = requests.get("%s/message/%s" % (cfg['url'], message_id),
                                       auth=HTTPBasicAuth(cfg['username'], cfg['password'])).json()
                CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1004 next")
                try:
                    if AgentBuilder(1, 1, 35754, message).inject().Success:
                        print("INJECTED incoming DMA: %s" % message)
                except Exception as e:
                    logging.error(e)
                finally:
                    if not requests.delete("%s/message/%s" % (cfg['url'], message_id),
                                           auth=HTTPBasicAuth(cfg['username'], cfg['password'])).status_code == 200:
                        logging.error("could not delete message %s" % message)
                CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1005 next")
        await asyncio.sleep(10)


async def updateContactList():
    while True:
        game_aw_online_indicator.Value = 1
        if WorldName != "Startup":
            users = requests.get("%s/users" % cfg['url'], auth=HTTPBasicAuth(cfg['username'], cfg['password']))
            for user in users.json():
                add_user_to_contact_list(user)
        await asyncio.sleep(60)


if __name__ == '__main__':
    main()
