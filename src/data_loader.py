import fastf1
import os
import json


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

    def get_event_laps_count(self, year, gp_name, event_type='R'):
        """
        Récupère le nombre total de tours pour un GP donné
        sans charger toute la télémétrie lourde.
        """
        import fastf1
        try:
            # Charger uniquement l'objet session de la course ('R')
            session = fastf1.get_session(year, gp_name, event_type)
            # Charger les données de chronométrage très légères pour avoir la structure
            session.load(laps=True, telemetry=False, weather=False, messages=False)

            # Le nombre de tours correspond au numéro du dernier tour complété dans la session
            total_laps = int(session.laps['LapNumber'].max())
            return total_laps
        except Exception:
            # Valeur de secours par défaut si la session n'est pas encore disponible
            return 50

    def get_track_base_time(self, year, gp_name, event_type='R'):
        """
        Récupère le meilleur temps au tour global de la course
        pour servir de base réaliste au moteur de simulation.
        """
        import fastf1
        try:
            session = fastf1.get_session(year, gp_name, event_type)
            session.load(laps=True, telemetry=False, weather=False, messages=False)

            # Récupérer le meilleur tour absolu de la course en secondes
            best_lap = session.laps.pick_fastest()
            base_time_seconds = best_lap['LapTime'].total_seconds()

            return base_time_seconds
        except Exception:
            # Valeur de secours si les données ne sont pas disponibles (ex: Monaco par défaut)
            return 75.0

    def load_poly_coefficients(self):
        """
        Charge les coefficients polynomiaux de degré 2 depuis le fichier JSON
        situé à la racine du projet (au même niveau que app.py).
        """
        # 1. Trouve le chemin absolu du dossier où se trouve data_loader.py (src/)
        dossier_src = os.path.dirname(os.path.abspath(__file__))

        # 2. Remonte d'un niveau proprement pour arriver à la racine (Projet_final_groupe_B/)
        dossier_racine = os.path.dirname(dossier_src)

        # 3. Construit le chemin final vers le fichier JSON
        json_path = os.path.join(dossier_racine, "coefficients_simulateur_poly.json")

        if not os.path.exists(json_path):
            raise FileNotFoundError(
                f"Le fichier des coefficients est introuvable à l'emplacement requis : {json_path}\n"
                f"Assure-toi de placer 'coefficients_simulateur_poly.json' à la racine de ton projet."
            )

        with open(json_path, "r") as f:
            return json.load(f)