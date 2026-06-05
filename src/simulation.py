import random


class RaceSimulation:
    def __init__(self, total_laps, track_base_time, tyre_config, track_config, track_factor=1.0):
        """
        Initialise le moteur de simulation de course.
        """
        self.total_laps = total_laps
        self.track_base_time = track_base_time
        self.tyre_config = tyre_config
        self.track_config = track_config
        self.track_factor = track_factor

        # Constante d'ingénierie : gain de temps par tour dû à la consommation d'essence (allègement)
        # En moyenne en F1, une voiture gagne environ 0.06 seconde par tour en s'allégeant.
        self.fuel_gain_per_lap = 0.06

    def simulate_pitstop(self):
        """
        Calcule la durée de l'arrêt au stand en combinant le temps de perte fixe
        dans la pitlane et un tirage probabiliste (stochastique) pour l'erreur humaine.
        """
        base_loss = self.track_config.get('pitstop_loss_seconds', 22.0)

        # Modélisation des aléas du stand (Loi de probabilité personnalisée)
        tirage = random.random()

        if tirage < 0.85:
            # 85% de chance : Arrêt optimal et réussi
            random_delay = random.uniform(2.2, 2.8)
        elif tirage < 0.96:
            # 11% de chance : Léger contretemps (ex: écrou récalcitrant)
            random_delay = random.uniform(4.0, 6.0)
        else:
            # 4% de chance : Problème majeur (ex: crevaison lente, aileron à changer)
            random_delay = random.uniform(10.0, 15.0)

        return base_loss + random_delay

    def run_strategy(self, starting_tyre, pit_stops):
        """
        Exécute la simulation de la course tour par tour selon la stratégie choisie.
        pit_stops est un dictionnaire. Ex: {15: 'HARD'} signifie arrêt au tour 15 pour mettre des HARD.
        """
        current_tyre = starting_tyre.upper()
        tyre_age = 0
        total_race_time = 0
        lap_times = []
        pitstop_events = {}  # Pour stocker le temps perdu et le tour où cela est arrivé

        # Récupération des coefficients de dégradation depuis le YAML
        penalty_coeff = self.tyre_config.get(f'{current_tyre.lower()}_base_penalty', 0.05)

        for lap in range(1, self.total_laps + 1):
            # 1. Effet de l'essence : la voiture s'allège et devient plus rapide
            fuel_effect = self.fuel_gain_per_lap * lap

            # 2. Effet des pneus : la pénalité augmente de façon non linéaire avec l'âge de la gomme
            tyre_effect = penalty_coeff * (tyre_age ** 1.5) * self.track_factor

            # 3. Calcul du temps au tour net (sans incident)
            lap_time = self.track_base_time - fuel_effect + tyre_effect

            # 4. Gestion de l'événement d'arrêt au stand
            if lap in pit_stops:
                pit_time = self.simulate_pitstop()
                lap_time += pit_time

                # Enregistrement de l'événement pour les graphiques futurs
                pitstop_events[lap] = pit_time

                # Changement de pneu et réinitialisation de l'âge
                current_tyre = pit_stops[lap].upper()
                penalty_coeff = self.tyre_config.get(f'{current_tyre.lower()}_base_penalty', 0.05)
                tyre_age = 0

            # Accumulation du temps et passage au tour suivant
            total_race_time += lap_time
            lap_times.append(lap_time)
            tyre_age += 1

        return {
            "total_race_time": total_race_time,
            "lap_times": lap_times,
            "pitstop_events": pitstop_events
        }

    def is_strategy_valid(self, starting_tyre, pit_stops):
        """
        Vérifie si la stratégie respecte le règlement (au moins deux composés différents).
        Retourne True si valide, False sinon.
        """
        composes_utilises = {starting_tyre.upper()}

        # Ajouter tous les pneus chaussés lors des arrêts aux stands
        for lap, tyre in pit_stops.items():
            composes_utilises.add(tyre.upper())

        # La stratégie est valide si le nombre de composés uniques est de 2 ou plus
        return len(composes_utilises) >= 2