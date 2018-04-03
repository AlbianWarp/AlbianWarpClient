from CaosEvolution.GameVariables import *
from CaosEvolution.Agent import AgentBuilder, enumAgents
from CaosEvolution import CI
import requests
from requests.auth import HTTPBasicAuth
import time
import configparser
import logging
import os

config = configparser.ConfigParser()
config.read('albianwarp.cfg')

username = config.get('albianwarp', "username", fallback="")
password = config.get('albianwarp', "password", fallback="")
url = config.get('albianwarp', "url", fallback="http://192.168.0.29:5000")
my_creatures_directory = config.get("albianwarp", "my_creatures_directory",
                   fallback=r"C:\Users\%s\Documents\Creatures\Docking Station\My Creatures" % os.getlogin())
server_version = "alpha alpaca"
mod_version = "alpha alpaca"
print('"My Creatures" directory: "%s"' % my_creatures_directory)

print("Checking for game modification version...")
if eame_aw_mod_version == "":
    logging.error("Game modifications are not Installed! :(")
    exit(1)
elif eame_aw_mod_version != mod_version:
    logging.error("Wrong modification version found! Expected %s found %s instead" % (mod_version, eame_aw_mod_version))
    exit(1)

print("Server version check...")
actual_version = requests.get("%s/version" % url).text
if actual_version != server_version:
    print("Server and Client Version mismatch, are you running the latest/correct client version?")
    logging.error('Server Version does not match! Expected "%s", found "%s"' % (server_version, actual_version))
    exit(1)
auth_test = requests.get("%s/messages" % url, auth=HTTPBasicAuth(username, password))
while auth_test.status_code != 200:
    username = input('Please enter your username: ')
    password = input('Please enter your password: ')
    auth_test = requests.get("%s/messages" % url, auth=HTTPBasicAuth(username, password))
    if auth_test.status_code != 200:
        print('Wrong username or password, please try again!')
print("going online...")
CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1004 next")
game_user_of_this_world.Value = username
game_status.Value = "online"
game_aw_status.Value = "online"
print("running...")
print(CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1005 mesg writ targ 500 next").Content)
while True:
    game_aw_online_indicator.Value = 1
    available_messages = requests.get("%s/messages" % url, auth=HTTPBasicAuth(username, password))
    for message_id in available_messages.json()['messages']:
        message = requests.get("%s/message/%s" % (url, message_id), auth=HTTPBasicAuth(username, password)).json()
        CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1004 next")
        try:
            if AgentBuilder(1, 1, 35754, message).inject().Success:
                print("INJECTED incoming DMA: %s" % message)
        except Exception as e:
            logging.error(e)
        finally:
            if not requests.delete("%s/message/%s" % (url, message_id),
                                   auth=HTTPBasicAuth(username, password)).status_code == 200:
                logging.error("could not delete message %s" % message)
        CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1005 next")
    # Parse direct message agents
    for agent in enumAgents(1, 1, 35753):
        print("DETECTED outgoing DMA: %s" % agent.unid)
        CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1004 next")
        tmp = agent.dict
        logging.info("Agent %s found: %s" % (agent.unid, tmp))
        result = requests.post("%s/messages" % url, auth=HTTPBasicAuth(username, password), json=tmp)
        if result.status_code == 200:
            print("SENT DMA (%s): %s" % (agent.unid, tmp))
            agent.Kill()
        CI.ExecuteCaos("enum 1 2 14 mesg writ targ 1005 next")
    # Parse send creature agents
    for agent in enumAgents(1, 1, 35760):
        tmp = agent.dict
        logging.debug("Processing %s" % tmp)
        logging.debug("DETECTED SCA: %s" % agent.unid)
        creature_file = os.path.join(my_creatures_directory,"%s.ds.creature" % tmp['moniker'].replace('-','_'))
        if os.path.isfile(creature_file):
            logging.debug('Found creature to warp at "%s"' % creature_file)
            files = {'file': open(creature_file, 'rb')}
            values = {'recipient': tmp['aw_recipient'], 'creature_name': tmp['creature_name']}
            result = requests.post("%s/creature_upload" % url, files=files, data=values, auth=HTTPBasicAuth(username, password))
            if result.status_code == 200:
                logging.info("uploaded creature %s to %s" % (tmp['moniker'], tmp['aw_recipient']))
            else:
                logging.error("uploading creature %s to %s FAILED" % (tmp['moniker'], tmp['aw_recipient']))
            agent.Kill()
    available_creatures = requests.get("%s/creatures" % url, auth=HTTPBasicAuth(username, password))
    for creature in available_creatures.json()['creatures']:
        logging.info("found creature %s" % creature['filename'])
        # download creature and save it in my creatures folder
    time.sleep(2)
