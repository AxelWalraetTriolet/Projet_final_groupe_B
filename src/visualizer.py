"""
AFFICHAGE DES RESULTATS
Ce module affiche l'évolution des temps au tour fonction du nombre de tours pour le cas simulé et le cas réel.
Il affiche également une animation 3D du circuit.
"""

import matplotlib.pyplot as plt

class TelemetryVisualizer:
    @staticmethod


    def plot_race_strategy(lap_times, pitstop_events, selected_driver, historical_data=None, historical_pit_stops=None,
                           year=None):
        """
        Génère un graphique Matplotlib montrant l'évolution des temps au tour simulés,
        marque visuellement l'emplacement de l'arrêt au stand, et superpose les données réelles.
        """
        fig, ax = plt.subplots(figsize=(10, 5))

        # Initialisation des tours et du plafond visuel sur l'axe y
        total_laps = len(lap_times)
        tours = list(range(1, total_laps + 1))

        if historical_data is not None and not historical_data.empty:
            median_time = historical_data['LapTimeSeconds'].median()
            upper_limit = median_time + 6
        else:
            upper_limit = max(lap_times) + 2

        # Fixation des limites de l'axe Y pour éviter les débordements
        ax.set_ylim(min(lap_times) - 1.5, upper_limit)

        ax.plot(tours, lap_times, label="Simulation du rythme", color="#1E90FF", linewidth=2)

        # Marquage des arrêts aux stands simulés
        for pit_lap, pit_time in pitstop_events.items():
            ax.axvline(x=pit_lap, color="#FF4500", linestyle="--", alpha=0.8, label=f"BOX Simulé (Tour {pit_lap})")
            ax.text(pit_lap, ax.get_ylim()[0] + 0.3, 'BOX SIM', color="#FF4500", weight='bold', fontsize=9, ha='center')

        # Tracé des données réelles (si disponibles)
            if historical_data is not None:
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
                    # Le texte 'BOX RÉEL' est placé en bas du graphique pour éviter les collisions
                    ax.text(pit , ax.get_ylim()[0] + 0.3, 'BOX RÉEL', color="#555555", weight='bold', fontsize=8, ha='center')

        # 4. Configuration et mise en page: titre, axes, grille
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





    #def plot_race_strategy(lap_times, pitstop_events):
        """
        Génère un graphique Matplotlib montrant l'évolution des temps au tour
        et marque visuellement l'emplacement de l'arrêt au stand.
        """
        # Création de la figure
        fig, ax = plt.subplots(figsize=(10, 5))

        # Tracé de la courbe des temps au tour
        total_laps = len(lap_times)
        tours = list(range(1, total_laps + 1))

        ax.plot(tours, lap_times, label="Évolution du rythme de course", color="#1E90FF", linewidth=2)

        # Ajout des repères visuels pour les arrêts aux stands
        for pit_lap, pit_time in pitstop_events.items():
            # Ligne verticale pointillée au tour du pitstop
            ax.axvline(x=pit_lap, color="#FF4500", linestyle="--", alpha=0.8,
                       label=f"Arrêt au stand (Tour {pit_lap})")

            # Petite annotation textuelle sur le graphique
            ax.text(pit_lap + 1, max(lap_times) - 0.5, 'BOX', color="#FF4500", weight='bold')

        # Configuration des axes et titres
        ax.set_title("📊 Analyse du Rythme de Course et Dégradation des Pneumatiques", fontsize=12, pad=15)
        ax.set_xlabel("Numéro du Tour", fontsize=10)
        ax.set_ylabel("Temps au Tour (secondes)", fontsize=10)

        # Personnalisation de la grille pour une meilleure lisibilité
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(loc="upper right")

        # Ajustement des marges
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