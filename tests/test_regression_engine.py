import unittest
from unittest.mock import patch, mock_open
from src.regression_engine import RegressionEngine


class TestRegressionEngine(unittest.TestCase):

    def setUp(self):
        """Données factices simulant la structure de coefficients_pilotes_saisons.json"""
        self.mock_db_content = {
            "Japan": {
                "VER": {
                    "SOFT": {"Beta_0_Intercept": 100.2, "Beta_1_TyreLife": 0.05, "Beta_2_TyreLife2": 0.001, "Beta_3_LapNumber": -0.03},
                    "MEDIUM": {"Beta_0_Intercept": 101.1, "Beta_1_TyreLife": 0.03, "Beta_2_TyreLife2": 0.0, "Beta_3_LapNumber": -0.03}
                },
                "HAM": {
                    "SOFT": {"Beta_0_Intercept": 100.5, "Beta_1_TyreLife": 0.04, "Beta_2_TyreLife2": 0.002, "Beta_3_LapNumber": -0.03}
                }
            },
            "Monaco": {
                "LEC": {
                    "SOFT": {"Beta_0_Intercept": 99.8, "Beta_1_TyreLife": 0.02, "Beta_2_TyreLife2": 0.0, "Beta_3_LapNumber": -0.02}
                }
            }
        }
        # Sérialisation en chaîne JSON pour simuler la lecture d'un fichier
        self.mock_json_str = json_str = __import__('json').dumps(self.mock_db_content)

    @patch('os.path.exists', return_value=True)
    def test_load_database_success(self, mock_exists):
        """Test unitaire : Vérifie que le JSON est correctement chargé et décodé si le fichier existe."""
        with patch('builtins.open', mock_open(read_data=self.mock_json_str)):
            engine = RegressionEngine()
            self.assertIn("Japan", engine.coefficients_db)
            self.assertEqual(engine.coefficients_db["Japan"]["VER"]["SOFT"]["Beta_0_Intercept"], 100.2)

    @patch('os.path.exists', return_value=False)
    def test_load_database_missing_file(self, mock_exists):
        """Test de sécurité : Doit lever une FileNotFoundError explicite si le fichier JSON n'existe pas."""
        with self.assertRaises(FileNotFoundError):
            RegressionEngine()

    @patch('os.path.exists', return_value=True)
    def test_get_coefficients_for_driver_nominal(self, mock_exists):
        """Test unitaire : Cas idéal où le circuit et le pilote demandés existent."""
        with patch('builtins.open', mock_open(read_data=self.mock_json_str)):
            engine = RegressionEngine()
            coefs = engine.get_coefficients_for_driver("Japan", "VER")
            self.assertIsNotNone(coefs)
            self.assertIn("SOFT", coefs)
            self.assertEqual(coefs["SOFT"]["Beta_1_TyreLife"], 0.05)

    @patch('os.path.exists', return_value=True)
    def test_get_coefficients_for_driver_fallback_driver(self, mock_exists):
        """Test de robustesse : Si le pilote est absent, appliquer le profil du premier pilote dispo sur ce GP."""
        with patch('builtins.open', mock_open(read_data=self.mock_json_str)):
            engine = RegressionEngine()
            # NOR n'existe pas au Japon dans notre mock, le moteur doit basculer sur VER
            coefs = engine.get_coefficients_for_driver("Japan", "NOR")
            self.assertIsNotNone(coefs)
            self.assertEqual(coefs["SOFT"]["Beta_0_Intercept"], 100.2)  # Profil de VER

    @patch('os.path.exists', return_value=True)
    def test_get_coefficients_for_driver_fallback_circuit(self, mock_exists):
        """Test de robustesse : Si le circuit est absent, basculer sur le premier circuit disponible."""
        with patch('builtins.open', mock_open(read_data=self.mock_json_str)):
            engine = RegressionEngine()
            # Monza n'existe pas dans notre mock, le moteur prend le premier circuit (Japan)
            # Et comme SAI n'y est pas, il prendra le premier pilote (VER)
            coefs = engine.get_coefficients_for_driver("Monza", "SAI")
            self.assertIsNotNone(coefs)
            self.assertEqual(coefs["SOFT"]["Beta_0_Intercept"], 100.2)  # Profil par défaut final (Japan -> VER)


if __name__ == '__main__':
    unittest.main()