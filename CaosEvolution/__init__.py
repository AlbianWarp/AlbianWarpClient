import sys
import clr

sys.path.append('.')
clr.AddReference('CAOS')
from CAOS import *

CI = CaosInjector('Docking Station')
