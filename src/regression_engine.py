import os
import json


class RegressionEngine:
    def __init__(self):
        """
        Initialise le moteur en chargeant la base de données de coefficients
        pluri-annuels générée par le script d'analyse.
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.json_path = os.path.join(base_dir, "coefficients_multi_saisons.json")
        self.coefficients_db = self._load_database()

    def _load_database(self):
        """Charge le fichier JSON multi-saisons."""
        if not os.path.exists(self.json_path):
            raise FileNotFoundError(
                f"Le fichier '{self.json_path}' est introuvable. "
                "Veuillez exécuter le script 'generer_base_brute_et_graphiques.py' au préalable."
            )
        with open(self.json_path, "r") as f:
            return json.load(f)

    def get_coefficients_for_circuit(self, circuit_name):
        """
        Récupère les coefficients bruts (SOFT, MEDIUM, HARD) extraits des données
        pour un circuit spécifique.
        """
        # Sécurité pour correspondre au format du fichier JSON (ex: 'Bahrain', 'Japan')
        coefficients = self.coefficients_db.get(circuit_name)

        if coefficients is None:
            # Fallback de secours sur le premier circuit disponible si le nom est mal orthographié
            premier_circuit = list(self.coefficients_db.keys())[0]
            coefficients = self.coefficients_db.get(premier_circuit)
            print(
                f"⚠️ Circuit '{circuit_name}' introuvable dans le JSON. Utilisation par défaut de : {premier_circuit}")

        return coefficients