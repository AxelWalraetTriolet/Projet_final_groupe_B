import matplotlib.pyplot as plt


class TelemetryVisualizer:
    @staticmethod
    def plot_race_strategy(lap_times, pitstop_events):
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