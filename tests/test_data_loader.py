import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
from src.data_loader import F1DataLoader


class TestF1DataLoader(unittest.TestCase):

    def setUp(self):
        """Initialisation exécutée avant chaque méthode de test."""
        # On isole le cache dans un dossier temporaire pour ne pas polluer le vrai cache
        self.data_loader = F1DataLoader(cache_dir="fastf1_cache_test")

    def test_get_event_laps_count_success(self):
        """Test unitaire : Vérifie l'extraction correcte du nombre de tours quand FastF1 répond."""
        # On crée une fausse session et de faux laps sous forme de dictionnaire/DataFrame
        mock_session = MagicMock()
        mock_laps = pd.DataFrame({'LapNumber': [1, 2, 3, 56]})
        mock_session.laps = mock_laps

        # On intercepte l'appel à fastf1.get_session pour lui faire renvoyer notre faux objet
        with patch('fastf1.get_session', return_value=mock_session) as mock_get:
            laps_count = self.data_loader.get_event_laps_count(2024, "Japan")

            # Vérifications (Assertions)
            self.assertEqual(laps_count, 56)
            mock_get.assert_called_once_with(2024, "Japan", 'R')

    def test_get_event_laps_count_fallback(self):
        """Test de robustesse : Vérifie le repli sur la valeur 50 en cas de plantage réseau API."""
        # On simule une levée d'exception (connexion perdue) lors de l'appel à FastF1
        with patch('fastf1.get_session', side_effect=Exception("Connexion API échouée")):
            laps_count = self.data_loader.get_event_laps_count(2024, "Suzuka")

            # Le système doit encaisser l'erreur et renvoyer la valeur par défaut
            self.assertEqual(laps_count, 50)

    def test_get_track_base_time(self):
        """Test de validation scientifique : Vérifie le calcul du meilleur tour absolu en secondes."""
        mock_session = MagicMock()

        # Simulation de l'objet timedelta renvoyé par FastF1 pour un chrono (ex: 1m 24s 500)
        mock_timedelta = MagicMock()
        mock_timedelta.total_seconds.return_value = 84.500

        # On injecte ce faux chrono dans le dictionnaire du meilleur tour
        mock_best_lap = {'LapTime': mock_timedelta}
        mock_session.laps.pick_fastest.return_value = mock_best_lap

        with patch('fastf1.get_session', return_value=mock_session):
            base_time = self.data_loader.get_track_base_time(2024, "Japan")
            self.assertEqual(base_time, 84.500)

    @patch('os.path.exists')
    def test_load_multi_season_coefficients_missing_file(self, mock_exists):
        """Test de sécurité : Le chargeur doit lever une exception explicite si le JSON est absent."""
        # On force os.path.exists à répondre False (le fichier n'existe pas)
        mock_exists.return_value = False

        # On vérifie que la bonne exception (FileNotFoundError) est bien levée
        with self.assertRaises(FileNotFoundError):
            self.data_loader.load_multi_season_coefficients()


if __name__ == '__main__':
    unittest.main()