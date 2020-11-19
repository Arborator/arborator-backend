
import os


class KlangConfig:
    def __init__(self):
        self.BASEDIR = os.path.dirname(os.path.abspath(__file__))

    def set_path(self, env):
        self.path = os.path.join(self.BASEDIR, "data_" + env)