"""
GESTIONNAIRE DES DONNEES FastF1
Ce module centralise la récupération, le cache et le formatage des données
officielles de la Formule 1 (via l'API FastF1) ainsi que le chargement des
coefficients de performance.
"""

import fastf1
import os
import json
import streamlit as st


class F1DataLoader:
    def __init__(self, cache_dir="fastf1_cache"):
        # Créer le dossier de cache s'il n'existe pas déjà
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

        # Activer le cache
        fastf1.Cache.enable_cache(cache_dir)

    def load_session_data(self, year, gp, event_type='R'):
        """Loads a specific F1 race (e.g., year=2025, gp='Monaco').
        :param year: Année de la session choisie.
        :type year: int
        :param gp: Nom du circuit choisi.
        :type gp: str
        :param event_type: Type de session, par défaut 'R' pour Race.
        :type event_type: str
        :return: L'objet session de FastF1 contenant toutes les données chargées (tours, télémétrie, météo).
        :rtype: fastf1.core.Session
        """
        session = fastf1.get_session(year, gp, event_type)
        session.load()
        return session


    def get_driver_telemetry(self, session, driver_code):
        """
        Récupère la télémétrie du tour le plus rapide d'un pilote pour une session donnée.
        :param session: L'objet session FastF1 préalablement chargé.
        :type session: fastf1.core.Session
        :param driver_code: Le code du pilote (ex: 'VER', 'HAM', 'LEC').
        :type driver_code: str
        :return: Un DataFrame contenant les données de télémétrie (vitesse, RPM, X, Y, etc.).
        :rtype: fastf1.core.Telemetry
        """
        lap = session.laps.pick_driver(driver_code).pick_fastest()
        telemetry = lap.get_telemetry()
        return telemetry

    def get_event_laps_count(self, year, gp_name, event_type='R'):
        """
        Récupère le nombre total de tours pour un GP donné sans charger toute la télémétrie.
        :param year: Année de la saison de Formule 1.
        :type year: int
        :param gp_name: Nom du circuit ou du Grand Prix (ex: 'Bahrain', 'Spa').
        :type gp_name: str
        :param event_type: Type de session de l'événement, par défaut 'R' (Race).
        :type event_type: str, optional
        :return: Le nombre total de tours prévus ou complétés pour la course,
             ou une valeur par défaut de 50 en cas d'erreur.
        :rtype: int
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
        Récupère le meilleur temps au tour global de la course pour servir de base réaliste au moteur de simulation.
        :param year: Année de la saison de Formule 1.
        :type year: int
        :param gp_name: Nom du circuit ou du Grand Prix.
        :type gp_name: str
        :param event_type: Type de session de l'événement, par défaut 'R' (Race).
        :type event_type: str, optional
        :return: Le chrono absolu du meilleur tour de la session, exprimé en secondes.
        :rtype: float
        """

        session = fastf1.get_session(year, gp_name, event_type)
        session.load(laps=True, telemetry=False, weather=False, messages=False)

        # Récupérer le meilleur tour absolu de la course en secondes
        best_lap = session.laps.pick_fastest()
        base_time_seconds = best_lap['LapTime'].total_seconds()

        return base_time_seconds


    def load_multi_season_coefficients(self):
        """
        Charge  les coefficients pluri-annuels stockés à la racine du projet.
        :return: Un dictionnaire contenant la structure complète des coefficients par circuit, pilote et composé.
        :rtype: dict
        :raises FileNotFoundError: Si le fichier 'coefficients_pilotes_saisons.json' n'existe pas à l'emplacement attendu.
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
        :param selected_event: Le nom du Grand Prix à tester (ex: 'Monaco').
        :type selected_event: str
        :param selected_driver: Le code du pilote recherché (ex: 'LEC').
        :type selected_driver: str
        :param start_year: L'année de départ pour la recherche inversée, par défaut 2025.
        :type start_year: int, optional
        :return: L'année la plus récente trouvée où le pilote est classé,
                ou None si aucune occurrence valide n'existe entre 2019 et 2025.
        :rtype: int ou None
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
        :param year: Année de la saison.
        :type year: int
        :param selected_event: Nom du Grand Prix (ex: 'Monaco').
        :type selected_event: str
        :param selected_driver: Code du pilote (ex: 'HAM', 'LEC').
        :type selected_driver: str
        :return: Un tuple contenant :
             -  Un DataFrame nettoyé avec les colonnes ['LapNumber', 'LapTimeSeconds', 'Compound', 'Stint'].
             -  Une liste des numéros de tours où le pilote est rentré aux stands.
        :rtype: tuple[pandas.DataFrame, list[int]]
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


    @st.cache_data
    def _cached_historical_data(_data_loader, selected_event, selected_driver):
        """
        Télécharge et met en cache les données d'une course.
        Recherche l'année la plus récente disponible pour le pilote et l'événement
        donnés, puis extrait ses chronos ainsi que ses arrêts aux stands réels.

        :param _data_loader: L'instance du gestionnaire de données utilisé pour l'extraction.
        :type _data_loader: DataLoader
        :param selected_event: Nom du Grand Prix.
        :type selected_event: str
        :param selected_driver: Code du pilote recherché (ex: 'VER').
        :type selected_driver: str
        :return: Un tuple contenant :
             - Le DataFrame des chronos historiques (ou None si introuvable).
             - La liste des tours d'arrêts aux stands réels (ou None si introuvable).
             - L'année correspondante trouvée (ou None si introuvable).
        :rtype: tuple[pandas.DataFrame ou None, list[int] ou None, int ou None]
        """
        recent_year = _data_loader.find_most_recent_year(selected_event, selected_driver)
        if recent_year:
            hist_data, hist_pits = _data_loader.get_historical_driver_data(
                recent_year, selected_event, selected_driver
            )
            return hist_data, hist_pits, recent_year
        return None, None, None

    @st.cache_data
    def _cached_telemetry_data(_data_loader, year, selected_event, selected_driver):
        """
        Télécharge et met en cache la trajectoire spatiale pour l'animation.
        Récupère la télémétrie du tour le plus rapide du pilote sélectionné. Si le pilote
        n'a aucun tour enregistré dans la session, la télémétrie du meilleur tour absolu
        de la session est renvoyée par sécurité.

        :param _data_loader: L'instance du gestionnaire de données utilisé pour charger la session.
        :type _data_loader: DataLoader
        :param year: Année de la saison historique ciblée.
        :type year: int
        :param selected_event: Nom du Grand Prix.
        :type selected_event: str
        :param selected_driver: Code du pilote recherché (ex: 'LEC').
        :type selected_driver: str
        :return: Un DataFrame contenant la télémétrie complète (coordonnées X, Y, vitesse, etc.).
        :rtype: fastf1.core.Telemetry
        """
        session_reelle = _data_loader.load_session_data(year, selected_event, 'R')
        laps_pilote = session_reelle.laps.pick_driver(selected_driver)
        lap_rapide = laps_pilote.pick_fastest() if not laps_pilote.empty else session_reelle.laps.pick_fastest()
        return lap_rapide.get_telemetry()