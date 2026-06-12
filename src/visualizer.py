"""
AFFICHAGE DES RESULTATS
Ce module affiche:
- la stratégie et le temps total de course (simulation & réel)
- l'évolution des temps au tour fonction du nombre de tours pour le cas simulé et le cas réel.
- animation 3D du circuit.
"""

import matplotlib.pyplot as plt
import numpy as np

class TelemetryVisualizer:
    @staticmethod
    def plot_race_strategy(lap_times, pitstop_events, selected_driver,
        historical_data=None, historical_pit_stops=None, year=None, optimal_lap_times=None,
                           optimal_pit_events=None):
        """
        Génère un graphique Matplotlib montrant l'évolution des temps au tour simulés,
        marque visuellement l'emplacement de l'arrêt au stand, superpose les données réelles
        ainsi que la stratégie IA, avec un axe Y calculé dynamiquement de façon simplifiée.
        """
        fig, ax = plt.subplots(figsize=(10, 5))

        # Initialisation des tours
        total_laps = len(lap_times)
        tours = list(range(1, total_laps + 1))

        # =======================================================
        # CALCUL DYNAMIQUE DE L'AXE Y (Simple)
        # =======================================================
        min_y = min(lap_times)
        max_y = max(lap_times)

        # On ajuste avec les données réelles (en ignorant les drapeaux rouges > 200 secondes)
        if historical_data is not None and not historical_data.empty:
            temps_valides = historical_data['LapTimeSeconds'][historical_data['LapTimeSeconds'] < 200]

            if not temps_valides.empty:
                min_y = min(min_y, temps_valides.min())
                max_y = max(max_y, temps_valides.max())

        # Application directe avec une petite marge esthétique
        ax.set_ylim(min_y - 2, max_y + 5)
        # =======================================================

        # 1. Tracé de la simulation manuelle
        ax.plot(tours, lap_times, label="Simulation du rythme", color="#1E90FF", linewidth=2)

        # 2. Marquage des arrêts aux stands simulés
        for pit_lap, pit_time in pitstop_events.items():
            ax.axvline(x=pit_lap, color="#FF4500", linestyle="--", alpha=0.8, label=f"BOX Simulé (Tour {pit_lap})")
            ax.text(pit_lap, ax.get_ylim()[0] + 0.3, 'BOX SIM', color="#FF4500", weight='bold', fontsize=9, ha='center')

        # 3. Tracé des données réelles
        if historical_data is not None and not historical_data.empty:
            ax.plot(
                historical_data['LapNumber'],
                historical_data['LapTimeSeconds'],
                label=f"Réel - {selected_driver} ({year})",
                color="#555555",
                linestyle="-.",
                linewidth=1.5,
                alpha=0.7
            )

            # Ajout des repères visuels pour les arrêts aux stands réels
            if historical_pit_stops:
                for i, pit in enumerate(historical_pit_stops):
                    label_pit = "BOX Réel" if i == 0 else ""
                    ax.axvline(x=pit, color="#555555", linestyle=":", alpha=0.7, label=label_pit)
                    ax.text(pit, ax.get_ylim()[0] + 0.3, 'BOX RÉEL', color="#555555", weight='bold', fontsize=8,
                            ha='center')

        # 4. Tracé de la stratégie optimale
        if optimal_lap_times is not None:
            laps_ia = list(range(1, len(optimal_lap_times) + 1))
            ax.plot(laps_ia, optimal_lap_times, label="Stratégie Optimale", color="#8A2BE2", linestyle="--", linewidth=2.5)

            if optimal_pit_events is not None:
                for pit_lap, pit_time in optimal_pit_events.items():
                    if 0 < pit_lap <= len(optimal_lap_times):
                        ax.plot(pit_lap, optimal_lap_times[pit_lap - 1], marker="*", color="#8A2BE2", markersize=12, linestyle="None")

        # 5. Configuration et mise en page: titre, axes, grille
        ax.set_title("Analyse du Rythme de Course et Dégradation des Pneumatiques", fontsize=12, pad=15)
        ax.set_xlabel("Numéro du Tour", fontsize=10)
        ax.set_xlim(0, total_laps + 2)
        ax.set_ylabel("Temps au Tour (secondes)", fontsize=10)
        ax.grid(True, linestyle=":", alpha=0.6)

        # Nettoyage de la légende pour éviter les doublons d'étiquettes
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(), loc="upper right", fontsize=9)

        plt.tight_layout()

        return fig



    @staticmethod
    def plot_circuit_layout(telemetry):
        """
        Génère un graphique représentant le tracé en 2D du circuit
        avec un code couleur basé sur la vitesse du pilote.
        """
        import numpy as np
        from matplotlib.collections import LineCollection

        # Extraire les coordonnées X, Y et la vitesse
        x = telemetry['X'].values
        y = telemetry['Y'].values
        vitesse = telemetry['Speed'].values

        # Préparation des segments de ligne pour appliquer un dégradé de couleur
        points = np.array([x, y]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)

        fig, ax = plt.subplots(figsize=(8, 8))

        # Création du LineCollection avec la palette 'RdYlGn' (Rouge = Lent, Vert = Rapide)
        norm = plt.Normalize(vitesse.min(), vitesse.max())
        lc = LineCollection(segments, cmap='RdYlGn', norm=norm, linewidth=4)
        lc.set_array(vitesse)

        # Ajout de la ligne au graphique
        line = ax.add_collection(lc)

        # Ajout d'une barre de couleur pour la vitesse
        cbar = fig.colorbar(line, ax=ax, orientation='horizontal', pad=0.05)
        cbar.set_label('Vitesse instantanée (km/h)', fontsize=10)

        # Ajuster les axes pour éviter les déformations géométriques du circuit
        ax.axis('equal')
        ax.set_axis_off()  # Masquer les axes X et Y inutiles pour un circuit

        ax.set_title("🗺️ Tracé géométrique du circuit et zones de vitesse", fontsize=12, pad=10)
        plt.tight_layout()

        return fig

    @staticmethod
    def plot_live_frame(telemetry, current_index):
        """
        Génère une frame unique pour l'animation live.
        Affiche le circuit gris et un point brillant pour la voiture.
        """
        x = telemetry['X'].values
        y = telemetry['Y'].values

        fig, ax = plt.subplots(figsize=(6, 6))

        # 1. Dessiner le circuit complet en arrière-plan (gris)
        ax.plot(x, y, color='#D3D3D3', linewidth=3, zorder=1)

        # 2. Dessiner la position actuelle de la voiture (point rouge brillant)
        if current_index < len(x):
            ax.scatter(x[current_index], y[current_index], color='#FF4500', s=150, edgecolors='black', zorder=2,
                       label="Votre Pilote")

        # Ajustements esthétiques
        ax.axis('equal')
        ax.set_axis_off()
        plt.tight_layout()

        return fig

    @staticmethod
    def plot_cumulative_gap(lap_times, pitstop_events, selected_driver, historical_data=None, year=None):
        """
        Génère un graphique d'écarts cumulés par rapport à un rythme de référence.
        Permet de visualiser les gains/pertes de temps, les arrêts et les écarts Simu vs Réel.
        """
        fig, ax = plt.subplots(figsize=(10, 4.5)) # Création de la figure

        total_laps = len(lap_times)
        tours = list(range(1, total_laps + 1))

        # 1. Définition du rythme de référence basé sur la simulation
        # On retire les tours avec arrêt
        clean_sim_times = [t for i, t in enumerate(lap_times) if (i + 1) not in pitstop_events]
        # On calcule la médiane des tours de simulation hors arrêts
        reference_lap_time = np.median(clean_sim_times) if clean_sim_times else np.median(lap_times)

        # 2. Calcul des écarts cumulés pour la simulation
        sim_gaps = np.cumsum([t - reference_lap_time for t in lap_times])
        ax.plot(tours, sim_gaps, label="Simulation (Écart cumulé)", color="#1E90FF", linewidth=2.5)

        # Marquage des arrêts simulés
        for pit_lap in pitstop_events.keys():
            if pit_lap <= len(sim_gaps):
                y_pos = sim_gaps[pit_lap - 1]
                ax.plot(pit_lap, y_pos, marker='o', color="#FF4500", markersize=8)
                ax.text(pit_lap, y_pos + (max(sim_gaps) * 0.05), 'BOX SIM', color="#FF4500", weight='bold', fontsize=8,
                        ha='center')

        # 3. Calcul des écarts cumulés pour les résultats réels
        if historical_data is not None and not historical_data.empty:
            df_real = historical_data.sort_values('LapNumber').copy()

            # On calcule l'écart par rapport à la même référence que la simulation
            df_real['GapToRef'] = df_real['LapTimeSeconds'] - reference_lap_time
            df_real['CumulativeGap'] = df_real['GapToRef'].cumsum()

            ax.plot(
                df_real['LapNumber'],
                df_real['CumulativeGap'],
                label=f"Réel - {selected_driver} ({year})",
                color="#555555",
                linestyle="-.",
                linewidth=1.5,
                alpha=0.8
            )

            # Marquage des arrêts réels (changement de Stint) & affichage en légende
            if 'Stint' in df_real.columns:
                real_pits = df_real.drop_duplicates(subset=['Stint'], keep='last')
                real_pits = real_pits[real_pits['LapNumber'] < total_laps]

                legend_added = False
                for _, row in real_pits.iterrows():
                    # On n'affiche le label dans la légende que pour la toute première croix rencontrée
                    lbl = "Arrêt au stand Réel (FastF1)" if not legend_added else ""
                    ax.plot(
                        row['LapNumber'],
                        row['CumulativeGap'],
                        marker='x',
                        color="#555555",
                        markersize=8,
                        markeredgewidth=2,  
                        label=lbl
                    )
                    legend_added = True

        # 4. Habillage du graphique
        ax.set_title(f"Graphique des Écarts Cumulés - {selected_driver}", fontsize=11, pad=10)
        ax.set_xlabel("Numéro du Tour", fontsize=10)
        ax.set_ylabel("Temps cumulé vs référence (s)\n⬅️ Plus rapide (Gain)  |  Plus lent (Perte) ➡️", fontsize=9)

        # Inverser l'axe Y est la norme des ingénieurs F1 : vers le bas = gain de temps
        ax.invert_yaxis()
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(loc="upper left", fontsize=9)

        plt.tight_layout()
        return fig