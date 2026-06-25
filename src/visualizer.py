"""
AFFICHAGE DES RESULTATS
=======================

Ce module permet d'afficher:

- un temps formaté en h/min/s
- l'évolution des temps au tour fonction du nombre de tours pour le cas simulé et le cas réel
- l'écart au tour par rapport à un tour de référence de la simulation et comparaison avec le cas réel
- une animation 3D du circuit.
"""

import matplotlib.pyplot as plt
import numpy as np

class Visualizer:

    @staticmethod
    def format_race_time(total_seconds):
        """
        Convertit un temps en secondes en une chaîne lisible : heures, minutes et secondes.

        :param total_seconds : temps en secondes
        :type total_seconds: float
        :return: le temps formaté en h/min/s
        :rtype: str
        """
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = total_seconds % 60

        if hours > 0:
            return f"{hours} h {minutes} min {seconds:.3f} s"
        else:
            return f"{minutes} min {seconds:.3f} s"

    @staticmethod
    def plot_race_strategy(lap_times, pitstop_events, selected_driver,
        historical_data=None, historical_pit_stops=None, year=None, optimal_lap_times=None,
                           optimal_pit_events=None):
        """
        Génère un graphique Matplotlib montrant l'évolution des temps au tour simulés,
        marque visuellement l'emplacement de l'arrêt au stand, superpose les données réelles
        ainsi que la stratégie IA, avec un axe Y calculé dynamiquement de façon simplifiée.

        :param lap_times: Liste des temps au tour simulés en secondes.
        :type lap_times: list[float]
        :param pitstop_events: Dictionnaire associant le numéro du tour de l'arrêt à ses détails.
        :type pitstop_events: dict[int, str]
        :param selected_driver: Code du pilote analysé (ex: 'VER', 'HAM').
        :type selected_driver: str
        :param historical_data: Données historiques de FastF1 contenant les chronos réels, optionnel
        :type historical_data: pandas.DataFrame, optional
        :param historical_pit_stops: Liste des numéros de tours des arrêts au stand réels, optionnel
        :type historical_pit_stops: list[int], optional
        :param year: Année de la course sélectionnée finie (pas de DNF) la plus récente, optionnel.
        :type year: int, optional
        :param optimal_lap_times: Liste des temps au tour de la stratégie optimale calculée par l'IA, optionnel.
        :type optimal_lap_times: list[float], optional
        :param optimal_pit_events: Événements d'arrêts aux stands de la stratégie IA, optionnel.
        :type optimal_pit_events: dict[int, str], optional
        :return: La figure Matplotlib contenant le graphique comparatif généré.
        :rtype: matplotlib.figure.Figure
        """
        fig, ax = plt.subplots(figsize=(10, 5))

        # Initialisation des tours
        total_laps = len(lap_times)
        tours = list(range(1, total_laps + 1))

        # Calcul dynamique de l'axe y
        min_y = min(lap_times)
        max_y = max(lap_times)

        # Ajustement de l'axe y avec les données réelles (en ignorant les drapeaux rouges > 200 secondes)
        if historical_data is not None and not historical_data.empty:
            temps_valides = historical_data['LapTimeSeconds'][historical_data['LapTimeSeconds'] < 200]

            if not temps_valides.empty:
                min_y = min(min_y, temps_valides.min())
                max_y = max(max_y, temps_valides.max())

        # Application directe avec une petite marge
        ax.set_ylim(min_y - 2, max_y + 5)

        # 1. Tracé des résultats de la simulation
        ax.plot(tours, lap_times, label="Simulation du rythme", color="#1E90FF", linewidth=2)

        # 2. Marquage des arrêts aux stands de la simulation
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
        Génère un graphique représentant le tracé en 2D du circuit avec un code couleur basé sur la vitesse du pilote.

        :param telemetry: Données de télémétrie FastF1 (coordonnées X, Y et Speed)
        :type telemetry: pandas.DataFrame
        :return: La figure Matplotlib affichant la carte du tracé avec son dégradé de vitesse
        :rtype: matplotlib.figure.Figure
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
        Affiche le circuit complet dont le trait change de couleur selon la vitesse,
        et un point brillant pour la position actuelle de la voiture.

        :param telemetry: Données de télémétrie FastF1 (coordonnées 'X', 'Y' et 'Speed')
        :type telemetry: pandas.DataFrame
        :param current_index: l'indice actuel dans le tableau de télémétrie représentant la position de la voiture
        :type current_index: int
        :return: La figure Matplotlib représentant l'état de l'animation à l'instant ciblé
        :rtype: matplotlib.figure.Figure
        """
        # Importations locales nécessaires pour cette méthode
        from matplotlib.collections import LineCollection
        import matplotlib.colors as mcolors
        import numpy as np

        # 1. Extraction des données nécessaires
        x = telemetry['X'].values
        y = telemetry['Y'].values
        vitesse = telemetry['Speed'].values
        total_points = len(x)

        fig, ax = plt.subplots(figsize=(6, 6))

        # 1. Dessiner le circuit avec le degradé de vitesse

        # Création des paires de points pour les segments : [[x1, y1], [x2, y2]], etc.
        points = np.array([x, y]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)

        # Définition de la palette de couleurs (Colormap) avec 'RdYlGn' : Rouge = Lent, Jaune = Moyen, Vert = Rapide
        cmap = plt.get_cmap('RdYlGn')

        # Normalisation : associer la vitesse minimale au rouge et la maximale au vert
        # On définit des limites fixes (ex: 30 à 340 km/h) pour que les couleurs restent
        # cohérentes d'une course à l'autre, quel que soit le pilote.
        vmin = 30
        vmax = 340
        norm = plt.Normalize(vmin=vmin, vmax=vmax)

        lc = LineCollection(segments, cmap=cmap, norm=norm, zorder=1) # Création de la collection de lignes avec le dégradé de couleur
        lc.set_array(vitesse) # Attribution des valeurs de vitesse à chaque segment pour déterminer sa couleur
        lc.set_linewidth(5) # Définition de l'épaisseur du trait du circuit
        ax.add_collection(lc) # Ajout du circuit coloré au graphique

        # 2. Dessiner la voiture et la vitesse instantanée en km/h
        if 0 <= current_index < total_points:
            # Récupération de la position et de la vitesse actuelle
            cur_x = x[current_index]
            cur_y = y[current_index]
            cur_speed = vitesse[current_index]

            # Dessiner la voiture : un point brillant avec un contour net
            ax.scatter(cur_x, cur_y, color='#FF4500', s=180, edgecolors='black',
                       linewidth=2, zorder=3, label="Votre Pilote")

            # Afficher la vitesse en texte numérique à côté de la voiture
            # On ajoute un fond blanc semi-transparent pour la lisibilité
            ax.text(cur_x + (np.max(x) - np.min(x)) * 0.05, cur_y, f"{int(cur_speed)} km/h",
                    color='#FF4500', fontsize=16, weight='bold', va='center',
                    bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='round,pad=0.3'),
                    zorder=4)


        # 3. Ajout de la barre de couleur en légende
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])  # Nécessaire pour Matplotlib
        cbar = fig.colorbar(sm, ax=ax, orientation='horizontal', pad=0.03, aspect=40)
        cbar.set_label('Vitesse (km/h)', fontsize=10)
        cbar.ax.tick_params(labelsize=8)

        # Ajustements esthétiques finaux
        ax.axis('equal')  # Éviter que le circuit ne soit déformé géométriquement
        ax.set_axis_off()  # Masquer les axes X,Y inutiles
        ax.set_title("Télémétrie Live : Vitesse sur le tracé", fontsize=11, pad=10, weight='bold')
        plt.tight_layout()

        return fig

    @staticmethod
    def plot_cumulative_gap(lap_times, pitstop_events, selected_driver, historical_data=None, year=None):
        """
        Génère un graphique d'écarts cumulés par rapport à un rythme de référence de la simulation.
        Permet de visualiser les gains/pertes de temps, les arrêts et les écarts Simu vs Réel.

        :param lap_times: Liste des temps au tour simulés en secondes.
        :type lap_times: list[float]
        :param pitstop_events: Dictionnaire contenant les tours des arrêts au stand simulés en clés.
        :type pitstop_events: dict[int, str]
        :param selected_driver: Nom ou trigramme du pilote sélectionné (ex: 'LEC', 'HAM').
        :type selected_driver: str
        :param historical_data: Données de course réelles issues de FastF1, optionnel.
        :type historical_data: pandas.DataFrame, optional
        :param year: Année de la saison de référence pour les données historiques, optionnel.
        :type year: int, optional
        :return: La figure Matplotlib contenant le graphique des écarts cumulés généré.
        :rtype: matplotlib.figure.Figure
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