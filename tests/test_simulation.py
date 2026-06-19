import unittest
from unittest.mock import patch
from src.simulation import RaceSimulation


class TestRaceSimulation(unittest.TestCase):

    def setUp(self):
        """Configuration d'une simulation standard de course et de coefficients pour les tests."""
        self.total_laps = 50
        self.track_base_time = 80.0  # 1m 20s de base

        # Fausse configuration de circuit
        self.track_config = {
            "pitstop_loss_seconds": 22.0
        }

        # Faux coefficients polynomiaux calqués sur la structure attendue
        self.poly_config = {
            "SOFT": {"Beta_0_Intercept": 100.0, "Beta_1_TyreLife": 0.05, "Beta_2_TyreLife2": 0.002,
                     "Beta_3_LapNumber": -0.04},
            "MEDIUM": {"Beta_0_Intercept": 101.0, "Beta_1_TyreLife": 0.02, "Beta_2_TyreLife2": 0.0005,
                       "Beta_3_LapNumber": -0.04},
            "HARD": {"Beta_0_Intercept": 102.0, "Beta_1_TyreLife": 0.01, "Beta_2_TyreLife2": 0.0,
                     "Beta_3_LapNumber": -0.04}
        }

        self.sim = RaceSimulation(
            total_laps=self.total_laps,
            track_base_time=self.track_base_time,
            track_config=self.track_config,
            poly_config=self.poly_config
        )

    def test_is_strategy_valid_nominal(self):
        """Test unitaire : La stratégie doit être valide s'il y a au moins deux composés différents."""
        # SOFT au départ, puis passage en HARD au tour 15
        pit_stops = {15: "HARD"}
        self.assertTrue(self.sim.is_strategy_valid("SOFT", pit_stops))

    def test_is_strategy_valid_invalid(self):
        """Test unitaire : La stratégie doit être refusée si un seul composé est utilisé (infraction FIA)."""
        # SOFT au départ, et arrêt pour remettre des SOFT -> Non réglementaire
        pit_stops = {20: "SOFT"}
        self.assertFalse(self.sim.is_strategy_valid("SOFT", pit_stops))

    @patch('random.random', return_value=0.50)  # On force un tirage à 85% d'arrêt réussi
    @patch('random.uniform', return_value=2.5)  # On force un arrêt parfait de 2.5 secondes
    def test_simulate_pitstop_optimal(self, mock_uniform, mock_random):
        """Test stochastique contrôlé : Vérifie la perte de temps lors d'un arrêt parfait sans erreur."""
        total_loss = self.sim.simulate_pitstop()
        # Perte fixe pitlane (22.0) + temps mécanique (2.5) = 24.5 secondes
        self.assertEqual(total_loss, 24.5)

    @patch('random.random', return_value=0.99)  # On force un tirage dans les 4% de problème majeur
    @patch('random.uniform', return_value=12.0)  # On force un délai de 12 secondes
    def test_simulate_pitstop_major_issue(self, mock_uniform, mock_random):
        """Test stochastique contrôlé : Vérifie l'impact d'un problème majeur au stand."""
        total_loss = self.sim.simulate_pitstop()
        # Perte fixe pitlane (22.0) + problème majeur (12.0) = 34.0 secondes
        self.assertEqual(total_loss, 34.0)

    def test_run_strategy_value_error_missing_compound(self):
        """Test de sécurité : Le moteur doit lever une ValueError si un composé n'a pas de coefficients."""
        # On demande un composé 'WET' qui n'existe pas dans poly_config
        with self.assertRaises(ValueError):
            self.sim.run_strategy("WET", {})

    def test_run_strategy_lap_times_evolution(self):
        """Test de validation scientifique : Vérifie que le temps accumulé et la dégradation sont calculés."""
        pit_stops = {10: "MEDIUM"}
        results = self.sim.run_strategy("SOFT", pit_stops)

        # Vérification des structures de sortie
        self.assertIn("total_race_time", results)
        self.assertEqual(len(results["lap_times"]), self.total_laps)
        self.assertIn(10, results["pitstop_events"])

        # Vérification de la réinitialisation de l'âge de la gomme
        # Le tour 11 (premier tour du nouveau pneu) doit être plus rapide ou égal au tour 10 (pneu Soft usé + stand)
        self.assertGreater(results["lap_times"][9], results["lap_times"][10])


if __name__ == '__main__':
    unittest.main()