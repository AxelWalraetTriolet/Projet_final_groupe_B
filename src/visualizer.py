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