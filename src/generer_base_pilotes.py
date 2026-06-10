import os
import json
import logging
import pandas as pd
import numpy as np
import fastf1
from sklearn.linear_model import LinearRegression, HuberRegressor
from sklearn.preprocessing import SplineTransformer
from sklearn.pipeline import make_pipeline

# Mutisme complet des logs FastF1 et Matplotlib
logging.getLogger('fastf1').setLevel(logging.CRITICAL)
logging.getLogger('matplotlib').setLevel(logging.CRITICAL)

CACHE_DIR = 'fastf1_cache'
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)
fastf1.Cache.enable_cache(CACHE_DIR)

ANNÉES_HISTORIQUES = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
ANNEE_CALENDRIER_CIBLE = 2024  # Année pivot pour récupérer la liste de tous les circuits
TRACK_EVOLUTION_PER_LAP = -0.035


# -------------------------------

def recuperer_tous_les_circuits():
    """Extrait dynamiquement tous les noms de circuits officiels de la saison via FastF1."""
    try:
        schedule = fastf1.get_event_schedule(ANNEE_CALENDRIER_CIBLE)
        # On filtre les séances d'essais (testing) pour ne garder que les vrais Grands Prix
        circuits = schedule[schedule['EventFormat'] != 'testing']['EventName'].tolist()
        return circuits
    except Exception as e:
        # Repli de sécurité minimal si l'API FastF1 est inaccessible au démarrage
        return ['Bahrain', 'Saudi Arabia', 'Australia', 'Japan', 'Monaco', 'Great Britain', 'Italy', 'Abu Dhabi']


def extraire_donnees_brutes_vectorisees(circuit_name):
    """Télécharge et fusionne l'historique pluri-annuel de manière parallélisée par bloc Pandas."""
    all_laps = []
    for year in ANNÉES_HISTORIQUES:
        try:
            session = fastf1.get_session(year, circuit_name, 'R')
            session.load(telemetry=False, weather=False)
            df_laps = session.laps.copy()

            # Vectorisation des conversions temporelles
            df_laps['LapTimeSeconds'] = df_laps['LapTime'].dt.total_seconds()

            # Filtrage vectoriel direct (booléen)
            mask = (
                    (df_laps['TrackStatus'] == '1') &
                    (df_laps['PitOutTime'].isna()) &
                    (df_laps['PitInTime'].isna()) &
                    (df_laps['Compound'].isin(['SOFT', 'MEDIUM', 'HARD']))
            )
            filtered = df_laps[mask].dropna(subset=['LapTimeSeconds', 'TyreLife'])

            if not filtered.empty:
                # Normalisation vectorielle par rapport au minimum de l'année
                filtered['LapTimePct'] = (filtered['LapTimeSeconds'] / filtered['LapTimeSeconds'].min()) * 100.0
                all_laps.append(filtered[['Driver', 'Compound', 'TyreLife', 'LapNumber', 'LapTimePct']])
        except Exception:
            pass

    if not all_laps:
        return pd.DataFrame()

    df_global = pd.concat(all_laps, ignore_index=True)

    # Calcul vectorisé de la frontière inférieure (quantile 50%)
    seuil_mediane = df_global.groupby(['Driver', 'Compound', 'TyreLife'])['LapTimePct'].transform('quantile', 0.50)
    return df_global[df_global['LapTimePct'] <= seuil_mediane]


def ajuster_spline_morceaux(df_target):
    """ Ajuste une régression par spline cubique (par morceaux) et extrait des coefficients équivalents. """
    X_age = df_target['TyreLife'].to_numpy().reshape(-1, 1)
    X_lap = df_target['LapNumber'].to_numpy().reshape(-1, 1)
    y = df_target['LapTimePct'].to_numpy()

    # Configuration des Splines par morceaux : 3 nœuds, HuberRegressor robuste au bruit
    model_spline = make_pipeline(
        SplineTransformer(n_knots=3, degree=3, extrapolation="linear"),
        HuberRegressor(max_iter=1000)
    )
    model_spline.fit(X_age, y)

    # Projection de la spline lissée sur une approximation polynomiale d2 équivalente
    tours_simules = np.arange(1, 45).reshape(-1, 1)
    y_pred_smooth = model_spline.predict(tours_simules)

    A = np.hstack([np.ones_like(tours_simules), tours_simules, tours_simules ** 2])
    coefficients_poly, _, _, _ = np.linalg.lstsq(A, y_pred_smooth, rcond=None)

    # Effet carburant vectorisé
    fuel_model = LinearRegression().fit(X_lap, y)
    b3 = float(fuel_model.coef_[0])

    start_lap = df_target['LapNumber'].min()
    b0_corrige = float(coefficients_poly[0]) - (start_lap * TRACK_EVOLUTION_PER_LAP)

    return {
        'Beta_0_Intercept': round(b0_corrige, 4),
        'Beta_1_TyreLife': round(float(coefficients_poly[1]), 5),
        'Beta_2_TyreLife2': round(max(0.0, float(coefficients_poly[2])), 6),
        'Beta_3_LapNumber': round(b3, 5)
    }


def main():
    base_finale = {}

    # Récupération dynamique de la liste complète des circuits de l'année
    liste_circuits_officiels = recuperer_tous_les_circuits()

    for circuit in liste_circuits_officiels:
        df_frontiere = extraire_donnees_brutes_vectorisees(circuit)

        if df_frontiere.empty:
            continue

        base_finale[circuit] = {}

        # Groupement vectorisé par Pilote et Composé
        grouped = df_frontiere.groupby(['Driver', 'Compound'])

        for (driver, compound), group in grouped:
            if len(group) >= 6 and len(group['TyreLife'].unique()) >= 3:
                if driver not in base_finale[circuit]:
                    base_finale[circuit][driver] = {'SOFT': None, 'MEDIUM': None, 'HARD': None}

                base_finale[circuit][driver][compound] = ajuster_spline_morceaux(group)

    # Exportation directe du fichier JSON épuré à la racine
    with open('../coefficients_pilotes_saisons.json', 'w', encoding='utf-8') as f:
        json.dump(base_finale, f, indent=4)


if __name__ == "__main__":
    main()