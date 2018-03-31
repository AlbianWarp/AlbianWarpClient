import sys
import clr
import logging
logging.basicConfig(level=logging.DEBUG)
sys.path.append('.')
clr.AddReference('CAOS')
from CAOS import *


class CleanCaosInjector(CaosInjector):
    def __init__(self, game_name):
        logging.info('initializing CaosInjector')
        super().__init__(game_name)

    def ExecuteCaos(self, caos, action="execute"):
        logging.debug('ExecuteCaos action: %s' % action)
        logging.debug(caos)
        result = super().ExecuteCaos(caos, action=action)
        logging.debug(result.Content)
        return result


CI = CleanCaosInjector('Docking Station')
