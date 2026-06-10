import os
import json
import logging
import pandas as pd
import numpy as np
import fastf1
import matplotlib.pyplot as plt
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures

# Configuration du cache et des logs
logging.getLogger().setLevel(logging.WARNING)
CACHE_DIR = 'fastf1_cache'
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)
fastf1.Cache.enable_cache(CACHE_DIR)

# --- CONFIGURATION ---
ANNÉES_HISTORIQUES = [2022, 2023, 2024]
# Tu peux restreindre la liste des circuits pour tes premiers tests (ex: ['Japan'])
CIRCUITS_CIBLES = ['Bahrain', 'Saudi Arabia', 'Australia', 'Japan', 'Miami', 'Monaco', 'Canada', 'Spain', 'Austria',
                   'Great Britain', 'Hungary', 'Belgium', 'Netherlands', 'Italy', 'Azerbaijan', 'Singapore',
                   'United States', 'Mexico', 'Brazil', 'Las Vegas', 'Qatar', 'Abu Dhabi']
TRACK_EVOLUTION_PER_LAP = -0.035


# ---------------------

def extraire_donnees_brutes(circuit_name):
    """Télécharge et fusionne l'historique pluri-annuel en appliquant les filtres de base."""
    all_laps = []
    for year in ANNÉES_HISTORIQUES:
        try:
            print(f"   ↳ Téléchargement édition {year}...")
            session = fastf1.get_session(year, circuit_name, 'R')
            session.load(telemetry=False, weather=False)

            df_laps = session.laps.copy()
            df_laps['LapTimeSeconds'] = df_laps['LapTime'].dt.total_seconds()

            # Application de tes filtres stricts
            filtered = df_laps[df_laps['TrackStatus'] == '1']  # Piste verte
            filtered = filtered[(filtered['PitOutTime'].isna()) & (filtered['PitInTime'].isna())]  # Hors stands
            filtered = filtered[filtered['Compound'].isin(['SOFT', 'MEDIUM', 'HARD'])].dropna(
                subset=['LapTimeSeconds', 'TyreLife'])

            if not filtered.empty:
                best_lap_year = filtered['LapTimeSeconds'].min()
                filtered['LapTimePct'] = (filtered['LapTimeSeconds'] / best_lap_year) * 100.0
                all_laps.append(filtered[['Driver', 'Compound', 'TyreLife', 'LapNumber', 'LapTimePct']])

        except Exception as e:
            print(f"   ⚠️ Édition {year} non disponible : {e}")

    return pd.concat(all_laps, ignore_index=True) if all_laps else pd.DataFrame()


def calculer_et_tracer_pilote(df_driver, circuit_name, driver_name):
    """Calcule la régression isotonique par pneu pour un pilote et trace son graphique."""
    coefs_pilote = {}

    # Filtrage des 50% meilleurs tours par âge de pneu pour CE pilote
    top_50_laps = []
    for (compound, tyre_life), group in df_driver.groupby(['Compound', 'TyreLife']):
        seuil = group['LapTimePct'].quantile(0.50)
        top_50_laps.append(group[group['LapTimePct'] <= seuil])

    if not top_50_laps:
        return None

    df_frontiere = pd.concat(top_50_laps)

    # Initialisation du graphique du pilote
    plt.style.use('dark_background')
    fig, axes = plt.subplots(3, 1, figsize=(11, 12), sharex=True, sharey=True)

    config_pneus = [
        {'compound': 'SOFT', 'color': '#FF3333', 'ax': axes[0], 'degree': 2},
        {'compound': 'MEDIUM', 'color': '#FFCC00', 'ax': axes[1], 'degree': 1},
        {'compound': 'HARD', 'color': '#E0E0E0', 'ax': axes[2], 'degree': 1}
    ]

    a_au_moins_un_pneu = False

    for cfg in config_pneus:
        compound = cfg['compound']
        ax_sub = cfg['ax']
        df_target = df_frontiere[df_frontiere['Compound'] == compound]

        # Validation statistique : il faut assez de recul sur le pilote
        if len(df_target) >= 4 and len(df_target['TyreLife'].unique()) >= 2:
            a_au_moins_un_pneu = True
            X_age = df_target['TyreLife'].to_numpy()
            X_lap = df_target['LapNumber'].to_numpy()
            y = df_target['LapTimePct'].to_numpy()

            # Régression Isotonique pure
            iso = IsotonicRegression(increasing=True)
            y_iso = iso.fit_transform(X_age, y)

            # Conversion mathématique pour le simulateur
            if cfg['degree'] == 2 and len(np.unique(X_age)) > 2:
                poly = PolynomialFeatures(degree=2, include_bias=True)
                X_poly = poly.fit_transform(X_age.reshape(-1, 1))
                meta_model = LinearRegression(fit_intercept=True)
                meta_model.fit(X_poly[:, 1:], y_iso)
                b0, b1, b2 = float(meta_model.intercept_), float(meta_model.coef_[0]), float(meta_model.coef_[1])
            else:
                meta_model = LinearRegression(fit_intercept=True)
                meta_model.fit(X_age.reshape(-1, 1), y_iso)
                b0, b1, b2 = float(meta_model.intercept_), float(meta_model.coef_[0]), 0.0

            model_fuel = LinearRegression()
            model_fuel.fit(X_lap.reshape(-1, 1), y)
            b3 = float(model_fuel.coef_[0])

            start_lap_relais = df_target['LapNumber'].min()
            b0_corrige = b0 - (start_lap_relais * TRACK_EVOLUTION_PER_LAP)

            coefs_pilote[compound] = {
                'Beta_0_Intercept': round(b0_corrige, 4),
                'Beta_1_TyreLife': round(b1, 5),
                'Beta_2_TyreLife2': round(max(0.0, b2), 6),
                'Beta_3_LapNumber': round(b3, 5)
            }

            # Tracé des points et de la ligne isotonique
            ax_sub.scatter(X_age, y, color=cfg['color'], alpha=0.4, s=30, label=f"Tours {driver_name} (Top 50%)")
            ax_sub.plot(np.sort(X_age), np.sort(y_iso), color='#00FF00', linewidth=2.5, label="Ajustement Isotonique")
        else:
            coefs_pilote[compound] = None
            ax_sub.text(0.5, 0.5, "PAS ASSEZ DE TOURS POUR CE PILOTE", transform=ax_sub.transAxes, ha='center',
                        color='gray')

        ax_sub.set_title(f"Composé {compound}", fontsize=10, color=cfg['color'], loc='left')
        ax_sub.grid(True, linestyle=':', alpha=0.15)
        ax_sub.legend(loc='upper left', fontsize=9)

    axes[2].set_xlabel("Âge du pneu (Tours effectués)")
    fig.suptitle(f"Analyse Isotonique — {driver_name} à {circuit_name} (Multi-Saisons)", fontsize=13, fontweight='bold',
                 y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])

    if a_au_moins_un_pneu:
        dossier_sortie = f"graphiques_pilotes/{circuit_name.lower()}"
        os.makedirs(dossier_sortie, exist_ok=True)
        plt.savefig(f"{dossier_sortie}/{driver_name.lower()}.png", dpi=120)
    plt.close(fig)

    return coefs_pilote


def main():
    print("🚀 PIPELINE DE MODÉLISATION PAR PILOTE ET PAR CIRCUIT 🚀")
    base_finale = {}

    for circuit in CIRCUITS_CIBLES:
        print(f"\n🎬 Traitement du circuit : {circuit}")
        df_circuit = extraire_donnees_brutes(circuit)

        if not df_circuit.empty:
            base_finale[circuit] = {}
            pilotes_disponibles = df_circuit['Driver'].unique()
            print(f"   📊 {len(pilotes_disponibles)} pilotes détectés. Calcul des profiles individuels...")

            for driver in pilotes_disponibles:
                df_driver = df_circuit[df_circuit['Driver'] == driver]
                coefs = calculer_et_tracer_pilote(df_driver, circuit, driver)
                if coefs:
                    base_finale[circuit][driver] = coefs
            print(f"   ✅ Circuit {circuit} entièrement modélisé.")
        else:
            print(f"   ❌ Aucune donnée pour {circuit}.")

    with open('../coefficients_pilotes_saisons.json', 'w') as f:
        json.dump(base_finale, f, indent=4)
    print("\n🏁 PIPELINE TERMINÉ ! Base sauvegardée dans 'coefficients_pilotes_saisons.json'.")
    print("📁 Les graphiques de contrôle sont classés par dossier de circuit dans 'graphiques_pilotes/'.")


if __name__ == "__main__":
    main()