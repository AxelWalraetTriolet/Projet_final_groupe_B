"""
GESTIONNAIRE DES DONNEES FastF1
Ce module centralise la récupération, le cache et le formatage des données
officielles de la Formule 1 (via l'API FastF1) ainsi que le chargement des
coefficients de performance.
"""

import fastf1
import os
import json


class F1DataLoader:
    def __init__(self, cache_dir="fastf1_cache"):
        # Créer le dossier de cache s'il n'existe pas déjà
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

        # Activer le cache
        fastf1.cache.enable_cache(cache_dir)

    def load_session_data(self, year, gp, event_type='R'):
        """Loads a specific F1 race (e.g., year=2025, gp='Monaco')."""
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

        session = fastf1.get_session(year, gp_name, event_type)
        session.load(laps=True, telemetry=False, weather=False, messages=False)

        # Récupérer le meilleur tour absolu de la course en secondes
        best_lap = session.laps.pick_fastest()
        base_time_seconds = best_lap['LapTime'].total_seconds()

        return base_time_seconds


    def load_multi_season_coefficients(self):
        """
        Charge instantanément les coefficients pluri-annuels isotoniques
        stockés à la racine du projet.
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        json_path = os.path.join(base_dir, "coefficients_multi_saisons.json")

        if not os.path.exists(json_path):
            raise FileNotFoundError(
                "Le fichier 'coefficients_multi_saisons.json' est introuvable. "
                "Exécute d'abord le script 'generer_coefficients_professionnels.py' pour le créer."
            )

        with open(json_path, "r") as f:
            return json.load(f)