"""
MOTEUR DE RÉGRESSION : INTERFACE DES COEFFICIENTS
Ce module sert d'interface d'accès aux coefficients polynomiaux stockés localement au format JSON.
Il extrait les données de performance des pneus (Soft, Medium, Hard) pour un circuit donné.
"""

import os
import json
import streamlit as st


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
                "Veuillez exécuter le script 'generer_coefficients_professionnels.py' au préalable."
            )
        with open(self.json_path, "r") as f:
            return json.load(f)

    def get_coefficients_for_circuit(self, circuit_name):
        """
        Récupère les coefficients bruts (SOFT, MEDIUM, HARD) extraits des données
        pour un circuit spécifique.
        """
        coefficients = self.coefficients_db.get(circuit_name)

        if coefficients is None:
            # Sécurité (Ligne 39 corrigée) : On s'assure que le dictionnaire n'est pas vide avant le fallback
            db_keys = list(self.coefficients_db.keys())
            if not db_keys:
                raise ValueError("La base de données des coefficients JSON est vide.")

            premier_circuit = db_keys[0]
            coefficients = self.coefficients_db.get(premier_circuit)

            # Note : Idéalement, traitez cette alerte dans app.py avec st.warning()
            # plutôt qu'un print() invisible pour l'utilisateur de l'interface.
            st.warning("⚠️ Circuit '{circuit_name}' introuvable dans le JSON. Utilisation par défaut de : {premier_circuit}")

        return coefficients







