import yaml

class ConfigLoader:
    def __init__(self, config_path="config.yaml"):
        self.config_path = config_path
        self.config = self.load_config()

    def load_config(self):
        with open(self.config_path, 'r') as file:
            return yaml.safe_load(file)

    def get_simulation_defaults(self):
        return self.config.get('simulation_defaults', {})

    def get_tyre_parameters(self):
        return self.config.get('tyre_degradation', {})

    def get_track_parameters(self):
        return self.config.get('track_parameters', {})