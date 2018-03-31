import sys
import clr
import logging

sys.path.append('.')
clr.AddReference('CAOS')
from CAOS import *


class CleanCaosInjector(CaosInjector):
    def __init__(self, game_name):
        logging.info('initializing CaosInjector')
        super().__init__(game_name)

    def ExecuteCaos(self, caos, action = "execute"):
        logging.debug('ExecuteCaos action: %s' % action)
        logging.debug(caos)


CI = CaosInjector('Docking Station')
