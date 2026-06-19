import unittest
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from src.visualizer import Visualizer


class TestVisualizer(unittest.TestCase):

    def test_format_race_time_more_than_hour(self):
        """Test unitaire : Vérifie le formatage d'un temps supérieur à une heure."""
        # 1h = 3600s, 5min = 300s, 12.345s -> Total: 3912.345 secondes
        formatted = Visualizer.format_race_time(3912.345)
        self.assertEqual(formatted, "1 h 5 min 12.345 s")

    def test_format_race_time_less_than_hour(self):
        """Test unitaire : Vérifie le formatage d'un temps inférieur à une heure."""
        # 42min = 2520s, 7.001s -> Total: 2527.001 secondes
        formatted = Visualizer.format_race_time(2527.001)
        self.assertEqual(formatted, "42 min 7.001 s")

    def test_plot_race_strategy_returns_figure(self):
        """Test d'intégrité : Vérifie que le rendu de la stratégie génère bien une Figure Matplotlib valide."""
        lap_times = [85.0, 85.5, 86.0, 110.0, 84.0]  # Simule un petit relais avec arrêt
        pitstop_events = {4: 25.0}
        selected_driver = "VER"

        fig = Visualizer.plot_race_strategy(lap_times, pitstop_events, selected_driver)

        # Validation du type d'objet produit
        self.assertIsInstance(fig, plt.Figure)
        plt.close(fig)  # Libération de la mémoire RAM

    def test_plot_circuit_layout(self):
        """Test d'intégrité : Vérifie la génération de la carte 2D du circuit à partir de fausses coordonnées."""
        # Création d'un faux DataFrame de télémétrie spatiale avec Pandas
        mock_telemetry = pd.DataFrame({
            'X': np.sin(np.linspace(0, 2 * np.pi, 20)) * 1000,
            'Y': np.cos(np.linspace(0, 2 * np.pi, 20)) * 1000,
            'Speed': np.linspace(80, 300, 20)
        })

        fig = Visualizer.plot_circuit_layout(mock_telemetry)
        self.assertIsInstance(fig, plt.Figure)
        plt.close(fig)

    def test_plot_live_frame_valid_index(self):
        """Test d'intégrité : Vérifie le rendu d'une frame d'animation avec positionnement de la voiture."""
        mock_telemetry = pd.DataFrame({
            'X': [10.0, 20.0, 30.0],
            'Y': [5.0, 10.0, 15.0],
            'Speed': [150.0, 220.0, 310.0]
        })

        # On teste le rendu au niveau du deuxième échantillon (index 1)
        fig = Visualizer.plot_live_frame(mock_telemetry, current_index=1)
        self.assertIsInstance(fig, plt.Figure)
        plt.close(fig)

    def test_plot_cumulative_gap(self):
        """Test de validation scientifique : Vérifie la génération du graphique des écarts cumulés."""
        lap_times = [85.0, 85.2, 85.4, 85.6]
        pitstop_events = {}

        # Simulation de données réelles pour comparer
        mock_historical = pd.DataFrame({
            'LapNumber': [1, 2, 3, 4],
            'LapTimeSeconds': [85.1, 85.3, 85.2, 85.5],
            'Stint': [1, 1, 1, 1]
        })

        fig = Visualizer.plot_cumulative_gap(lap_times, pitstop_events, "LEC", mock_historical, year=2024)
        self.assertIsInstance(fig, plt.Figure)
        plt.close(fig)


if __name__ == '__main__':
    unittest.main()