import fastf1
import os


class F1DataLoader:
    def __init__(self, cache_dir="fastf1_cache"):
        # Créer le dossier de cache s'il n'existe pas déjà
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

        # Activer le cache
        fastf1.Cache.enable_cache(cache_dir)

    def load_session_data(self, year, gp, event_type):
        """Loads a specific F1 session (e.g., year=2025, gp='Monaco', event_type='Q')"""
        session = fastf1.get_session(year, gp, event_type)
        session.load()
        return session

    def get_driver_telemetry(self, session, driver_code):
        """Returns the telemetry dataframe for a specific driver"""
        lap = session.laps.pick_driver(driver_code).pick_fastest()
        telemetry = lap.get_telemetry()
        return telemetry