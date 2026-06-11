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