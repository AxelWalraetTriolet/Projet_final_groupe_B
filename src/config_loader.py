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

    def get_track_factor(self, track_name):
        """Retourne le coefficient multiplicateur d'usure pour un circuit (1.0 par défaut)"""
        factors = self.config.get('track_degradation_factors', {})
        return factors.get(track_name, 1.0)