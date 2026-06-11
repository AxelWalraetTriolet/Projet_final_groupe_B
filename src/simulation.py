"""
MOTEUR DE SIMULATION
Ce module simule le déroulement d'une course de F1 avec:
 - les modèles prédictifs de dégradation des pneus
 - des aléas pour l'arrêt aux stands
"""

import random

class RaceSimulation:

    def __init__(self, total_laps, track_base_time, track_config, poly_config):
        """Initialise le moteur de simulation de course."""
        self.total_laps = total_laps
        self.track_base_time = track_base_time
        self.track_config = track_config
        self.poly_config = poly_config

    def simulate_pitstop(self):
        """
        Calcule la durée de l'arrêt au stand en combinant le temps de perte fixe
        dans la pitlane et un tirage probabiliste (stochastique) pour l'erreur
        humaine.
        """
        base_loss = self.track_config.get("pitstop_loss_seconds", 22.0)

        # Modélisation des aléas du stand (Loi de probabilité stochastique)
        tirage = random.random()

        if tirage < 0.85:
            # 85% de chance : Arrêt optimal et réussi
            random_delay = random.uniform(2.2, 2.8)
        elif tirage < 0.96:
            # 11% de chance : Léger contretemps (ex: écrou récalcitrant)
            random_delay = random.uniform(4.0, 6.0)
        else:
            # 4% de chance : Problème majeur (ex: pistolet cassé, aileron changé)
            random_delay = random.uniform(10.0, 15.0)

        return base_loss + random_delay

    def run_strategy(self, starting_tyre, pit_stops):
        """
        Exécute la simulation de la course tour par tour selon la stratégie choisie.
        pit_stops est un dictionnaire. Ex: {15: 'HARD'} signifie arrêt au tour 15.
        """
        current_tyre = starting_tyre.upper()
        tyre_age = 0
        total_race_time = 0
        lap_times = []
        pitstop_events = {}
        coefs = self.poly_config.get(current_tyre)

        coefs = self.poly_config.get(current_tyre)
        if not coefs:
            raise ValueError(f"Le composé [{current_tyre}] n'est pas répertorié dans le fichier JSON des coefficients.")

        for lap in range(1, self.total_laps + 1):


            # --- APPLICATION DU MODÈLE SCIKIT-LEARN DEGRÉ 2 ---
            # La formule calcule un pourcentage théorique par rapport au meilleur tour
            pct_lap = (
                coefs["Beta_0_Intercept"]
                + (coefs["Beta_1_TyreLife"] * tyre_age)
                + (coefs["Beta_2_TyreLife2"] * (tyre_age**2))
                + (coefs["Beta_3_LapNumber"] * lap)
            )

            # Re-conversion mathématique du pourcentage en secondes réelles
            lap_time = (pct_lap / 100.0) * self.track_base_time

            # Gestion de l'événement d'arrêt au stand
            if lap in pit_stops:


                pit_time = self.simulate_pitstop()
                lap_time += pit_time

                # Enregistrement de l'événement pour la télémétrie finale
                pitstop_events[lap] = pit_time

                # Récupération des coefficients polynomiaux d2 pour le pneu actuel
                coefs = self.poly_config.get(current_tyre)
                if not coefs:
                    raise ValueError(
                        f"Le composé [{current_tyre}] n'est pas répertorié dans le fichier JSON des coefficients."
                    )

                # Changement de pneu et réinitialisation de l'âge de la gomme
                current_tyre = pit_stops[lap].upper()
                tyre_age = -1

            # Accumulation des données physiques
            total_race_time += lap_time
            lap_times.append(lap_time)
            tyre_age += 1

        return {
            "total_race_time": total_race_time,
            "lap_times": lap_times,
            "pitstop_events": pitstop_events,
        }

    def is_strategy_valid(self, starting_tyre, pit_stops):
        """
        Vérifie si la stratégie respecte la réglementation de la FIA (au moins deux composés différents obligatoires).
        """
        composes_utilises = {starting_tyre.upper()}

        for lap, tyre in pit_stops.items():
            composes_utilises.add(tyre.upper())

        return len(composes_utilises) >= 2

    def find_optimal_two_stops_strategy(self):
        """
        Trouve la meilleure stratégie à adopter pour une course et un pilote
        (choix du tour d'arrêts, du nombre d'arrêts et du type de pneu). Pour alléger le programme on ne prend
        en compte qu'au maximum deux arrêts.
        """
        best_time = float('inf')
        best_strategy = None

        composes = ['SOFT', 'MEDIUM', 'HARD']

        # Premier cas où il n'y a qu'un seul arrêt
        # On ne change pas les pneus au premier et au dernier tour.
        for tour_arret_1 in range(2, self.total_laps):
            for pneu_depart in composes: # Choix du pneu de départ
                for pneu_relais_2 in composes: #Boucle pour choisir le 2nd type de pneu

                    pit_stops = {tour_arret_1: pneu_relais_2}

                    if self.is_strategy_valid(pneu_depart, pit_stops):  # On vérifie qu'il y a bien 2 types de pneus

                        # Lancement de la simulation
                        result = self.run_strategy(pneu_depart, pit_stops)

                        # Sauvegarde si c'est le nouveau meilleur temps
                        if result['total_race_time'] < best_time:
                            best_time = result['total_race_time']
                            best_strategy = {
                                'type': '1 arrêt',
                                'starting_tyre': pneu_depart,
                                'pit_stops': pit_stops,
                                'results': result
                            }
        # Boucles pour choisir les tours d'arrêt (tour 1 < tour 2)
        # On ne change pas les pneus au premier, au dernier tour ou sur le même tour que le précédent changement
        # La nouvelle boucle fonctionne comme celle ci-dessus
        for tour_arret_1 in range(2, self.total_laps - 1):
            for tour_arret_2 in range(tour_arret_1 + 1, self.total_laps):

                for pneu_depart in composes:
                    for pneu_relais_2 in composes:
                        for pneu_relais_3 in composes:

                            pit_stops = {
                                tour_arret_1: pneu_relais_2,
                                tour_arret_2: pneu_relais_3
                            }

                            if self.is_strategy_valid(pneu_depart, pit_stops):

                                result = self.run_strategy(pneu_depart, pit_stops)

                                if result['total_race_time'] < best_time:
                                    best_time = result['total_race_time']
                                    best_strategy = {
                                        'starting_tyre': pneu_depart,
                                        'pit_stops': pit_stops,
                                        'results': result
                                    }

        return best_strategy