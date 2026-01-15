import os

class GrewConfig:
    def __init__(self):
        self.server = None

    def set_url(self, env):
        if env == "prod":
            self.server = "http://arborator-prod.grew.fr"
        elif env == "preprod":
            self.server = os.getenv('EXTERNAL_PREPROD_SERVER_URL', "https://arborator-preprod.grew.fr")
        else:  # if env is dev or test
            self.server = os.getenv('EXTERNAL_SERVER_URL', "http://localhost:8222")