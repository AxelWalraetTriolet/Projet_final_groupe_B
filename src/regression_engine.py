import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures


class RegressionEngine:
    @staticmethod
    def calculate_live_coefficients(session_reelle):
        """
        Calcule la dégradation des pneus via une Régression Isotonique sur les 20%
        des tours les plus rapides, puis extrait les coefficients stables pour le simulateur.
        """
        laps = session_reelle.laps.copy()
        if 'LapTime' not in laps.columns or 'TyreLife' not in laps.columns:
            raise ValueError("Données de télémétrie insuffisantes pour ce Grand Prix.")

        laps['LapTimeSeconds'] = laps['LapTime'].dt.total_seconds()

        # 1. Nettoyage de la session
        filtered = laps.pick_quicklaps()
        filtered = filtered[
            (filtered['PitOutTime'].isna()) &
            (filtered['PitInTime'].isna()) &
            (filtered['TrackStatus'] == '1') &
            (filtered['Compound'].isin(['SOFT', 'MEDIUM', 'HARD']))
            ]

        if filtered.empty:
            raise ValueError("Aucune donnée de course exploitable après nettoyage.")

        # Normalisation locale (% du meilleur tour absolu)
        best_lap_absolute = filtered['LapTimeSeconds'].min()
        filtered['LapTimePct'] = (filtered['LapTimeSeconds'] / best_lap_absolute) * 100.0

        # Extraction de la frontière inférieure (les 20% les plus rapides par âge de pneu)
        frontiere_inferieure = []
        for (compound, tyre_life), group in filtered.groupby(['Compound', 'TyreLife']):
            if len(group) >= 1:
                seuil = group['LapTimePct'].quantile(0.20)
                frontiere_inferieure.append(group[group['LapTimePct'] <= seuil])

        df_frontiere = pd.concat(frontiere_inferieure) if frontiere_inferieure else filtered

        # CORRECTION : On initialise TOUS les composés avec des dictionnaires par défaut stables
        # pour éviter l'erreur 'NoneType' si un pneu n'a pas roulé.
        coefficients_optimaux = {
            'SOFT': {'Beta_0_Intercept': 104.7, 'Beta_1_TyreLife': 0.015, 'Beta_2_TyreLife2': 0.0095,
                     'Beta_3_LapNumber': -0.04},
            'MEDIUM': {'Beta_0_Intercept': 105.4, 'Beta_1_TyreLife': 0.035, 'Beta_2_TyreLife2': 0.0,
                       'Beta_3_LapNumber': -0.04},
            'HARD': {'Beta_0_Intercept': 106.5, 'Beta_1_TyreLife': 0.014, 'Beta_2_TyreLife2': 0.0,
                     'Beta_3_LapNumber': -0.04}
        }

        TRACK_EVOLUTION_PER_LAP = -0.035

        # --- 2. APPLICATION DE LA RÉGRESSION ISOTONIQUE ---
        for compound in ['SOFT', 'MEDIUM', 'HARD']:
            df_target = df_frontiere[df_frontiere['Compound'] == compound]

            # Si le pneu a suffisamment roulé en piste, on écrase les valeurs par défaut par les vraies stats
            if len(df_target) >= 5 and len(df_target['TyreLife'].unique()) >= 3:
                X_age = df_target['TyreLife'].to_numpy()
                X_lap = df_target['LapNumber'].to_numpy()
                y = df_target['LapTimePct'].to_numpy()

                # Étape A : Régression isotonique sur l'âge du pneu (contrainte croissante)
                iso = IsotonicRegression(increasing=True)
                y_iso = iso.fit_transform(X_age, y)

                # Étape B : Extraction des coefficients mathématiques équivalents
                if compound == 'SOFT':
                    poly = PolynomialFeatures(degree=2, include_bias=True)
                    X_poly = poly.fit_transform(X_age.reshape(-1, 1))

                    meta_model = LinearRegression(fit_intercept=True)
                    meta_model.fit(X_poly[:, 1:], y_iso)

                    b0 = float(meta_model.intercept_)
                    b1 = float(meta_model.coef_[0])
                    b2 = float(meta_model.coef_[1])
                else:
                    meta_model = LinearRegression(fit_intercept=True)
                    meta_model.fit(X_age.reshape(-1, 1), y_iso)

                    b0 = float(meta_model.intercept_)
                    b1 = float(meta_model.coef_[0])
                    b2 = 0.0

                # Ajustement de l'effet carburant moyen (tendance globale LapNumber)
                model_fuel = LinearRegression()
                model_fuel.fit(X_lap.reshape(-1, 1), y)
                b3 = float(model_fuel.coef_[0])

                # Correction de l'intercept avec le gommage de la piste
                start_lap_relais = df_target['LapNumber'].min()
                b0_corrige = b0 - (start_lap_relais * TRACK_EVOLUTION_PER_LAP)

                # Sauvegarde des calculs réels dans le dictionnaire déjà existant
                coefficients_optimaux[compound] = {
                    'Beta_0_Intercept': b0_corrige,
                    'Beta_1_TyreLife': b1,
                    'Beta_2_TyreLife2': max(0.0, b2),
                    'Beta_3_LapNumber': b3
                }

        # --- 3. SÉCURISATION ET VERROUILLAGE DES HIÉRARCHIES PHYSIQUES ---
        # On extrait l'intercept pivot du Medium (qu'il soit issu des calculs ou par défaut)
        med_b0 = coefficients_optimaux['MEDIUM']['Beta_0_Intercept']
        med_b1 = max(0.01, coefficients_optimaux['MEDIUM']['Beta_1_TyreLife'])

        # Recalage strict et dynamique de la performance initiale (SOFT < MEDIUM < HARD)
        coefficients_optimaux['SOFT']['Beta_0_Intercept'] = round(med_b0 - 0.80, 4)
        coefficients_optimaux['MEDIUM']['Beta_0_Intercept'] = round(med_b0, 4)
        coefficients_optimaux['HARD']['Beta_0_Intercept'] = round(med_b0 + 1.05, 4)

        # Ajustement des pentes d'usures finales
        coefficients_optimaux['SOFT']['Beta_2_TyreLife2'] = max(0.0085,
                                                                coefficients_optimaux['SOFT']['Beta_2_TyreLife2'])
        coefficients_optimaux['SOFT']['Beta_1_TyreLife'] = round(med_b1 * 0.4, 5)
        coefficients_optimaux['MEDIUM']['Beta_1_TyreLife'] = round(med_b1, 5)
        coefficients_optimaux['HARD']['Beta_1_TyreLife'] = round(med_b1 * 0.40, 5)

        # Nettoyage final des structures numériques
        for c in ['SOFT', 'MEDIUM', 'HARD']:
            coefficients_optimaux[c]['Beta_0_Intercept'] = round(coefficients_optimaux[c]['Beta_0_Intercept'], 4)
            coefficients_optimaux[c]['Beta_2_TyreLife2'] = round(coefficients_optimaux[c]['Beta_2_TyreLife2'], 6)
            coefficients_optimaux[c]['Beta_3_LapNumber'] = round(coefficients_optimaux[c]['Beta_3_LapNumber'], 5)

        return coefficients_optimaux