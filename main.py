import os
from settings import Settings
from interpreter import Interpreter


APPLICATION_ROOT = os.path.dirname(os.path.abspath(__file__))

runtime = Interpreter(Settings())
