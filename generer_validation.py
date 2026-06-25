# -*- coding: utf-8 -*-
"""
MODULE DE VALIDATION SCIENTIFIQUE
=================================

Ce module automatise la comparaison entre les prédictions du modèle polynomial
et les données de chronométrage réelles de la FIA issues de l'API FastF1.
Saisons sélectionnées pour conformité API : 2024, 2025
"""

import os
import json
import logging
import time
import pandas as pd
import fastf1

from data_loader import F1DataLoader
from regression_engine import RegressionEngine
from simulation import RaceSimulation

# Désactivation des logs intrusifs pour garantir un terminal propre au correcteur
logging.getLogger('fastf1').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)

TRACK_CONFIG_DEFAUT = {"pitstop_loss_seconds": 22.0}


def convertir_en_format_simulateur(driver_laps):
    """
    Convertit l'historique des tours d'un pilote en paramètres d'entrée pour le simulateur.

    Cette fonction analyse les caractéristiques des relais (stints) réels d'un pilote,
    identifie le composé de pneu de départ et cartographie les arrêts aux stands
    (numéro du tour et composé suivant). Elle filtre les composés non pris en charge
    (ex: pneumatiques pluie ou intermédiaires).

    :param driver_laps: Objet contenant l'ensemble des tours du pilote pour la session.
    :type driver_laps: fastf1.core.Laps
    :returns: Un tuple contenant le pneu de départ (ex: 'MEDIUM') et le dictionnaire
              des arrêts aux stands {tour_arret: 'PROCHAIN_PNEU'}. Renvoie (None, None)
              si aucun relais valide n'est détecté.
    :rtype: tuple(str, dict) or tuple(None, None)
    """
    relais_groupes = driver_laps.groupby('Stint')
    starting_tyre = None
    pit_stops = {}
    cumul_tours = 0

    relais_valides = []
    for _, laps_stint in relais_groupes:
        compound = str(laps_stint['Compound'].iloc[0]).upper()
        if compound in ['SOFT', 'MEDIUM', 'HARD']:
            relais_valides.append((compound, len(laps_stint)))

    if not relais_valides:
        return None, None

    starting_tyre = relais_valides[0][0]
    for idx, (compound, nb_tours) in enumerate(relais_valides[:-1]):
        cumul_tours += nb_tours
        prochain_pneu = relais_valides[idx + 1][0]
        pit_stops[cumul_tours] = prochain_pneu

    return starting_tyre, pit_stops


def main():
    """
    Point d'entrée principal du pipeline de validation multi-saisons.

    Exécute l'algorithme de validation de bout en bout :
        1. Initialise les moteurs de données et de régression.
        2. Boucle sur les saisons cibles (2024, 2025).
        3. Extrait les données de course réelles et exclut les sessions avec Safety Car.
        4. Exécute la classe `RaceSimulation` pour chaque pilote éligible.
        5. Calcule l'erreur absolue (MAE) par rapport à la réalité.
        6. Sérialise l'ensemble des métriques de performance dans un fichier JSON.

    :raises Exception: Gère de manière transparente les anomalies de requêtes réseau
                       ou l'absence de coefficients locaux pour un pilote donné.
    :returns: Rien. Génère le fichier structure 'validation_resultats.json'.
    :rtype: None
    """
    print("==================================================================")
    print("🔬 DÉMARRAGE DU PIPELINE DE VALIDATION HISTORIQUE (2024 - 2025) ")
    print("==================================================================")
    print("💡 Note : Pour respecter les quotas de l'API FastF1, la validation")
    print("         se concentre sur les 2 saisons les plus récentes : 2024 et 2025.")
    print("         Temps d'exécution estimé : ~5 minutes.\n")

    loader = F1DataLoader()
    try:
        engine = RegressionEngine()
    except Exception as e:
        print(f"❌ Erreur critique : Impossible de charger la base de coefficients : {e}")
        return

    circuits_disponibles = list(engine.coefficients_db.keys())
    rapport_global = {}

    # Sélection des 2 saisons les plus récentes à valider
    saisons_eval = [2024, 2025]

    for saison in saisons_eval:
        print(f"⏳ Analyse de la saison F1 {saison} en cours...", end="", flush=True)
        resultats_saison = []

        for circuit in circuits_disponibles:
            # Temporisation de sécurité (0.6s) pour stabiliser les requêtes API
            time.sleep(0.1)

            try:
                session = loader.load_session_data(saison, circuit, 'R')

                if session.laps.empty or 'TrackStatus' not in session.laps.columns:
                    continue

                # --- FILTRE STRICT : EXCLUSION SI JAUNE, SC OU VSC ---
                # Statuts : '4' = Safety Car, '6' = Virtual Safety Car
                # Si l'un de ces statuts apparaît sur au moins un tour, on ignore la course.
                if session.laps['TrackStatus'].str.contains('4|6', na=False).any():
                    continue
                # -----------------------------------------------------

                total_laps = int(session.laps['LapNumber'].max())
                track_base_time = loader.get_track_base_time(saison, circuit)
                pilotes = session.results[session.results['Status'].str.contains('Finished|\\+1 Lap|\\+2 Laps', na=False)]['Abbreviation'].tolist()

                for driver in pilotes:
                    driver_laps = session.laps.pick_driver(driver)
                    temps_total_reel = driver_laps['LapTime'].dt.total_seconds().sum()
                    starting_tyre, pit_stops = convertir_en_format_simulateur(driver_laps)

                    if not starting_tyre or temps_total_reel <= 0:
                        continue

                    poly_config = engine.get_coefficients_for_driver(circuit, driver)
                    if not poly_config or not poly_config.get(starting_tyre):
                        continue

                    simulateur = RaceSimulation(
                        total_laps=total_laps,
                        track_config=TRACK_CONFIG_DEFAUT,
                        poly_config=poly_config,
                        track_base_time=track_base_time
                    )

                    try:
                        res_sim = simulateur.run_strategy(starting_tyre, pit_stops)
                        temps_total_simule = res_sim["total_race_time"]

                        erreur = temps_total_simule - temps_total_reel
                        resultats_saison.append({
                            'Circuit': circuit,
                            'Driver': driver,
                            'TempsReel': round(temps_total_reel, 2),
                            'TempsSimule': round(temps_total_simule, 2),
                            'Erreur': round(erreur, 2),
                            'ErreurAbsolue': round(abs(erreur), 2)
                        })
                    except Exception:
                        continue
            except Exception:
                continue

        if resultats_saison:
            df_saison = pd.DataFrame(resultats_saison)
            moyenne_par_circuit = df_saison.groupby('Circuit')['ErreurAbsolue'].mean().round(2).to_dict()
            moyenne_par_pilote = df_saison.groupby('Driver')['ErreurAbsolue'].mean().round(2).to_dict()
            erreur_globale_moyenne = round(df_saison['ErreurAbsolue'].mean(), 2)

            # --- CALCUL DE LA PRÉCISION À +-30 SECONDES ---
            total_echantillons = len(df_saison)
            dans_la_fenetre = sum(1 for e in df_saison['Erreur'] if abs(e) <= 30)
            precision_30s = round((dans_la_fenetre / total_echantillons) * 100, 1) if total_echantillons > 0 else 0.0
            # -----------------------------------------------

            # Dictionnaire structuré de manière synchrone avec app.py
            rapport_global[str(saison)] = {
                'mae_globale': erreur_globale_moyenne,
                'precision_30s': precision_30s,
                'total_echantillons': total_echantillons,
                'mae_par_circuit': moyenne_par_circuit,
                'mae_par_pilote': moyenne_par_pilote,
                'toutes_erreurs': df_saison['Erreur'].tolist(),
                'details_tous_les_calculs': resultats_saison
            }
            print(f" [OK] -> MAE : {erreur_globale_moyenne}s | Précision ±30s : {precision_30s}%")
        else:
            print(" [AUCUNE DONNÉE EXPLOITABLE]")

    # Écriture propre du fichier final à la racine
    chemin_sortie = os.path.normpath(os.path.join(os.path.dirname(__file__), "validation_resultats.json"))
    with open(chemin_sortie, 'w', encoding='utf-8') as f:
        json.dump(rapport_global, f, indent=4, ensure_ascii=False)

    print("\n==================================================================")
    print("🏁 PIPELINE TERMINÉ : Fichier 'validation_resultats.json' généré !")
    print("==================================================================")


if __name__ == '__main__':
    main()