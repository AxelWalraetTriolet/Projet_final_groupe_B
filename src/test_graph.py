import os
import logging
import fastf1
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Configuration des logs et du cache FastF1
logging.getLogger().setLevel(logging.WARNING)
cache_dir = 'fastf1_cache'
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)
fastf1.Cache.enable_cache(cache_dir)

# --- CONFIGURATION DU GRAND PRIX À ANALYSER ---
ANNEE = 2024
CIRCUIT = 'Abu Dhabi'  # Modifie le circuit si tu veux (ex: 'Japan', 'Monza')
# ----------------------------------------------

print(f"📥 Téléchargement et extraction des données pour {CIRCUIT} {ANNEE}...")

try:
    session = fastf1.get_session(ANNEE, CIRCUIT, 'R')
    session.load(telemetry=False, weather=False)

    laps = session.laps.copy()
    laps['LapTimeSeconds'] = laps['LapTime'].dt.total_seconds()

    # Nettoyage F1 standard pour isoler les tours représentatifs
    filtered_laps = laps.pick_quicklaps()
    filtered_laps = filtered_laps[
        (filtered_laps['PitOutTime'].isna()) &
        (filtered_laps['PitInTime'].isna()) &
        (filtered_laps['TrackStatus'] == '1') &
        (filtered_laps['Compound'].isin(['SOFT', 'MEDIUM', 'HARD']))
        ]

    # Normalisation locale (% du meilleur tour absolu)
    best_lap = filtered_laps['LapTimeSeconds'].min()
    filtered_laps['LapTimePct'] = (filtered_laps['LapTimeSeconds'] / best_lap) * 100.0

    print("📊 Génération des sous-graphiques comparatifs...")

    # 2. Configuration de la grille Matplotlib (Mode F1 Dark, 3 lignes, 1 colonne)
    plt.style.use('dark_background')
    fig, axes = plt.subplots(3, 1, figsize=(12, 14), sharex=True, sharey=True)

    config_pneus = [
        {'compound': 'SOFT', 'color': '#FF3333', 'ax': axes[0]},
        {'compound': 'MEDIUM', 'color': '#FFCC00', 'ax': axes[1]},
        {'compound': 'HARD', 'color': '#E0E0E0', 'ax': axes[2]}
    ]

    # Bornes communes pour une comparaison visuelle équitable
    y_min = filtered_laps['LapTimePct'].min() - 0.5
    y_max = filtered_laps['LapTimePct'].quantile(0.97) + 1.0

    # 3. Boucle de traçage par sous-graphique
    for pneu in config_pneus:
        df_sub = filtered_laps[filtered_laps['Compound'] == pneu['compound']]
        ax_sub = pneu['ax']

        # Nuage de points des pilotes
        sns.scatterplot(
            data=df_sub,
            x='TyreLife',
            y='LapTimePct',
            color=pneu['color'],
            alpha=0.5,
            s=35,
            edgecolor='none',
            ax=ax_sub,
            label=f"Tours réels en {pneu['compound']} ({len(df_sub)} tours)"
        )

        # Habillage de chaque sous-graphique
        ax_sub.set_title(f"Composé {pneu['compound']}", fontsize=12, fontweight='bold', color=pneu['color'], loc='left')
        ax_sub.grid(True, linestyle=':', alpha=0.25, color='gray')
        ax_sub.legend(loc='upper left', facecolor='#1A1A1A', edgecolor='gray')
        ax_sub.set_ylabel("Temps au tour (% du meilleur tour)", fontsize=10)
        ax_sub.set_ylim(y_min, y_max)

    # Axe des abscisses commun tout en bas
    axes[2].set_xlabel("Âge du pneu (Nombre de tours du relais)", fontsize=11, labelpad=10)

    # Titre global de la fenêtre
    fig.suptitle(f"Analyse comparative de la dégradation par composé - {CIRCUIT} {ANNEE}",
                 fontsize=15, fontweight='bold', y=0.98)

    plt.tight_layout(rect=[0, 0, 1, 0.96])

    # Sauvegarde et rendu
    nom_fichier = f"analyse_relais_{CIRCUIT.lower()}_{ANNEE}.png"
    plt.savefig(nom_fichier, dpi=300)
    print(f"✅ Graphique en 3 volets sauvegardé sous : '{nom_fichier}'")
    plt.show()

except Exception as e:
    print(f"❌ Une erreur est survenue : {e}")