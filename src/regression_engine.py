"""
MOTEUR DE RÉGRESSION : INTERFACE DES COEFFICIENTS
Ce module sert d'interface d'accès aux coefficients polynomiaux stockés localement au format JSON.
Il extrait les données de performance des pneus (Soft, Medium, Hard) pour un circuit donné.
"""

import os
import json


class RegressionEngine:
    def __init__(self):
        """
        Initialise le moteur en chargeant la base de données de coefficients
        pluri-annuels par pilote générée par le script d'analyse.
        """

        dossier_src = os.path.dirname(os.path.abspath(__file__))
        dossier_racine = os.path.dirname(dossier_src)

        # Construction du chemin vers le JSON
        self.json_path = os.path.normpath(os.path.join(dossier_racine, "coefficients_pilotes_saisons.json"))

        self.coefficients_db = self._load_database()

    def _load_database(self):
        """
        Charge le fichier JSON multi-saisons des pilotes depuis la racine.
        """
        if not os.path.exists(self.json_path):
            raise FileNotFoundError(
                f"Le fichier est introuvable.\n"
                f"Chemin testé par Python : '{self.json_path}'\n"
                f"Vérifie que le fichier est bien nommé exactement ainsi et placé dans ce dossier."
            )
        with open(self.json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_coefficients_for_driver(self, circuit_name, driver_name):
        """
        Récupère les coefficients bruts (SOFT, MEDIUM, HARD) extraits de la frontière
        inférieure des données de performance pour un pilote et un circuit spécifiques.

        :param circuit_name: Le nom du Grand Prix sélectionné.
        :type circuit_name: str
        :param driver_name: Le code du pilote sélectionné (ex: 'VER').
        :type driver_name: str
        :return: Un dictionnaire contenant les listes de coefficients polynomiaux par composé de pneu
        :rtype: dict[str, list[float]]
        """
        circuit_data = self.coefficients_db.get(circuit_name, {})

        if not circuit_data:
            premier_circuit = list(self.coefficients_db.keys())[0]
            circuit_data = self.coefficients_db.get(premier_circuit, {})
            print(f"⚠️ Circuit '{circuit_name}' absent du JSON. Utilisation par défaut du circuit : {premier_circuit}")

        driver_data = circuit_data.get(driver_name)

        if driver_data is None and circuit_data:
            premier_pilote = list(circuit_data.keys())[0]
            driver_data = circuit_data.get(premier_pilote)
            print(
                f"⚠️ Données pour {driver_name} absentes à {circuit_name}. Profil de {premier_pilote} appliqué par défaut.")

        return driver_data
