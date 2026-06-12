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
        fastf1.Cache.enable_cache(cache_dir)

    def load_session_data(self, year, gp, event_type='R'):
        """Loads a specific F1 race (e.g., year=2025, gp='Monaco')."""
        session = fastf1.get_session(year, gp, event_type)
        session.load()
        return session


    def get_driver_telemetry(self, session, driver_code):
        lap = session.laps.pick_driver(driver_code).pick_fastest()
        telemetry = lap.get_telemetry()
        return telemetry

    def get_event_laps_count(self, year, gp_name, event_type='R'):
        """
        Récupère le nombre total de tours pour un GP donné
        sans charger toute la télémétrie.
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
        Charge  les coefficients pluri-annuels
        stockés à la racine du projet.
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        json_path = os.path.join(base_dir, "coefficients_pilotes_saisons.json")

        if not os.path.exists(json_path):
            raise FileNotFoundError(
                "Le fichier 'coefficients_pilotes_saisons.json' est introuvable. "
                "Exécute d'abord le script 'generer_coefficients_professionnels.py' pour le créer."
            )

        with open(json_path, "r") as f:
            return json.load(f)


    def find_most_recent_year(self, selected_event, selected_driver, start_year=2025):
        """
        Parcourt les années à l'envers pour trouver l'année la plus récente
        où le pilote a croisé le drapeau à damier (classé / a fini la course).
        """
        # On remonte dans le temps jusqu'à 2018
        for year in range(start_year, 2018, -1):
            try:
                # Chargement ultra-léger juste pour vérifier les résultats, sans la télémétrie
                session = fastf1.get_session(year, selected_event, 'R')
                session.load(laps=False, telemetry=False, weather=False, messages=False)

                results = session.results
                # On cherche le pilote par son abréviation (ex: HAM) ou son nom
                driver_row = results[
                    (results['Abbreviation'] == selected_driver) |
                    (results['LastName'].str.lower() == selected_driver.lower())
                    ]

                if not driver_row.empty:
                    status = driver_row.iloc[0]['Status']
                    # Si le statut contient 'Finished' ou '+1 Lap', '+2 Laps', le pilote a fini la course
                    if 'Finished' in status or 'Lap' in status:
                        return year
            except Exception:
                # Si le GP n'a pas eu lieu cette année-là ou erreur, on passe à l'année précédente
                continue

        return None

    def get_historical_driver_data(self, year, selected_event, selected_driver):
        """
        Récupère les temps au tour et les tours de passage par les stands
        pour un pilote, un circuit et une année donnée.
        """
        session = fastf1.get_session(year, selected_event, 'R')
        session.load(telemetry=False, weather=False)  # On ne charge que les laps pour aller vite

        # Filtrer pour n'avoir que les tours du pilote sélectionné
        driver_laps = session.laps.pick_driver(selected_driver)

        # 1. Extraction des temps au tour (convertis en secondes pour le graphique)
        driver_laps['LapTimeSeconds'] = driver_laps['LapTime'].dt.total_seconds()

        # Nettoyage rapide pour enlever les tours sans chrono (ex: drapeau rouge)
        lap_data = driver_laps[['LapNumber', 'LapTimeSeconds', 'Compound','Stint']].dropna(subset=['LapTimeSeconds'])

        # 2. Extraction des tours où il y a eu un arrêt au stand
        # Dans fastf1, PitInTime n'est pas nul sur le tour où le pilote entre aux stands
        pit_stops = driver_laps[driver_laps['PitInTime'].notna()]['LapNumber'].tolist()

        return lap_data, pit_stops