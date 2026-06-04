import random
import numpy as np


class RaceSimulation:
    def __init__(self, total_laps, track_base_time, tyre_config, track_config):
        self.total_laps = total_laps
        self.track_base_time = track_base_time
        self.tyre_config = tyre_config
        self.track_config = track_config

    def simulate_pitstop(self):
        """Simulates a pitstop duration with an element of probability"""
        base_loss = self.track_config.get('pitstop_loss_seconds', 22.0)

        # Exemple stochastique : 90% de chance d'un arrêt normal, 10% d'un problème
        if random.random() < 0.90:
            random_delay = random.uniform(2.2, 3.0)  # Arrêt réussi
        else:
            random_delay = random.uniform(5.0, 12.0)  # Problème au stand 

        return base_loss + random_delay

    def run_strategy(self, starting_tyre, pit_stops):
        """
        Runs the simulation.
        pit_stops is a dictionary like {15: 'HARD'} (stop at lap 15 for HARD tires)
        """
        current_tyre = starting_tyre
        tyre_age = 0
        total_race_time = 0
        lap_times = []

        for lap in range(1, self.total_laps + 1):
            # 1. Calcul du temps au tour de base + pénalité d'usure des pneus
            tyre_penalty = self.tyre_config.get(f'{current_tyre.lower()}_base_penalty', 0.1) * (tyre_age ** 1.5)
            lap_time = self.track_base_time + tyre_penalty

            # 2. Gestion de l'arrêt au stand
            if lap in pit_stops:
                pit_time = self.simulate_pitstop()
                lap_time += pit_time
                current_tyre = pit_stops[lap]
                tyre_age = 0  # Réinitialisation de l'âge du pneu

            total_race_time += lap_time
            lap_times.append(lap_time)
            tyre_age += 1

        return total_race_time, lap_times