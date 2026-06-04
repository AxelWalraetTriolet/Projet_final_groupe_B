import matplotlib.pyplot as plt

class TelemetryVisualizer:
    @staticmethod
    def plot_strategy_comparison(lap_times_user, lap_times_real):
        """Generates a comparison chart of lap times over the race duration"""
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(lap_times_user, label="Votre Stratégie", color="blue")
        ax.plot(lap_times_real, label="Stratégie Réelle (FIA)", color="red", linestyle="--")
        ax.set_xlabel("Numéro du tour")
        ax.set_ylabel("Temps au tour (s)")
        ax.set_title("Comparaison des performances et dégradations")
        ax.legend()
        ax.grid(True)
        return fig