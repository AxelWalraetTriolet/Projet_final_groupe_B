import streamlit as st
import matplotlib.pyplot as plt
import time
import fastf1
from src.config_loader import ConfigLoader
from src.data_loader import F1DataLoader
from src.simulation import RaceSimulation
from src.visualizer import TelemetryVisualizer


def format_race_time(total_seconds):
    """
    Convertit un temps en secondes en une chaîne lisible : heures, minutes et secondes.
    """
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = total_seconds % 60

    if hours > 0:
        return f"{hours} h {minutes} min {seconds:.3f} s"
    else:
        return f"{minutes} min {seconds:.3f} s"


def main():
    st.set_page_config(page_title="F1 Strategy Simulator", layout="wide")

    st.title("🏎️ F1 Strategy Simulator")
    st.markdown("---")

    # Initialisation de la mémoire de session pour Streamlit
    if "sim_calculee" not in st.session_state:
        st.session_state.sim_calculee = False
    if "results" not in st.session_state:
        st.session_state.results = None

    # 1. Chargement des composants de configuration et de données
    config = ConfigLoader()
    defaults = config.get_simulation_defaults()
    track_params = config.get_track_parameters()
    data_loader = F1DataLoader()

    # Année figée par défaut (2024)
    CURRENT_YEAR = 2024

    # 2. Barre latérale : Paramètres de la simulation
    st.sidebar.header("🕹️ Configuration de la course")
    st.sidebar.subheader("🌍 Sélection du Grand Prix")

    # Récupération du calendrier officiel via FastF1 pour l'année en cours
    try:
        schedule = fastf1.get_event_schedule(CURRENT_YEAR)
        available_events = schedule[schedule['EventFormat'] != 'testing']['EventName'].tolist()
        selected_event = st.sidebar.selectbox("Sélectionnez le circuit :", available_events)
    except Exception as e:
        st.sidebar.error(f"Erreur de chargement des circuits : {e}")
        selected_event = "Monaco"

    st.sidebar.markdown("---")
    st.sidebar.subheader("📋 Paramètres de la Stratégie")

    # Détection automatique stricte et sans curseur du nombre de tours
    try:
        total_laps = data_loader.get_event_laps_count(CURRENT_YEAR, selected_event)
        st.sidebar.success(f"📏 Distance officielle : **{total_laps} tours**")
    except Exception:
        total_laps = int(defaults.get("total_laps", 50))
        st.sidebar.warning(f"Impossible de détecter les tours. Valeur par défaut forcée : {total_laps} tours")

    starting_tyre = st.sidebar.selectbox("Pneu de départ :", ["SOFT", "MEDIUM", "HARD"])

    # Gestion dynamique et chronologique des arrêts multiples
    st.sidebar.markdown("---")
    st.sidebar.subheader("🛑 Gestion des Arrêts aux Stands")

    num_pits = st.sidebar.number_input("Nombre d'arrêts prévus :", min_value=1, max_value=3, value=1, step=1)

    pit_stops = {}
    last_pit_lap = 0  # Curseur pour mémoriser le tour du dernier arrêt validé

    for stop_idx in range(1, num_pits + 1):
        st.sidebar.markdown(f"**Arrêt n°{stop_idx}**")
        col_lap, col_tyre = st.sidebar.columns(2)

        with col_lap:
            # Sécurité temporelle : l'arrêt suivant est forcément plus tard que le précédent
            min_allowed_lap = last_pit_lap + 1
            max_allowed_lap = total_laps - (num_pits - stop_idx) - 1

            # Calcul automatique du tour par défaut pour rester cohérent
            default_lap = min(max(int((total_laps / (num_pits + 1)) * stop_idx), min_allowed_lap), max_allowed_lap)

            p_lap = st.number_input(
                f"Tour de l'arrêt :",
                min_value=min_allowed_lap,
                max_value=total_laps - 1,
                value=default_lap,
                key=f"pit_lap_{stop_idx}"
            )
        with col_tyre:
            p_tyre = st.selectbox(
                f"Nouveau pneu :",
                ["SOFT", "MEDIUM", "HARD"],
                index=1 if stop_idx == 1 else 0,
                key=f"pit_tyre_{stop_idx}"
            )

        # Mise à jour du dictionnaire et déplacement du curseur chronologique
        pit_stops[p_lap] = p_tyre
        last_pit_lap = p_lap

    # 3. Zone principale d'affichage et d'exécution des calculs
    st.header("⚡ Simulation et Résultats")

    if st.sidebar.button("🏎️ Lancer la simulation de stratégie", type="primary"):
        track_key = selected_event.lower().replace(" ", "_")
        track_info = track_params.get(track_key, {})
        track_base_time = track_info.get("base_lap_time_seconds", 85.0)

        try:
            # Chargement des coefficients polynomiaux d2 via le data_loader
            with st.spinner("Chargement des coefficients Scikit-Learn..."):
                poly_coefficients = data_loader.load_poly_coefficients()

            # Instanciation du moteur avec injection directe des paramètres
            sim = RaceSimulation(
                total_laps=total_laps,
                track_base_time=track_base_time,
                track_config=track_info,
                poly_config=poly_coefficients
            )

            # Validation de la règle des deux composés minimum (FIA)
            if not sim.is_strategy_valid(starting_tyre, pit_stops):
                st.error(
                    "🚨 Stratégie invalide selon le règlement de la FIA ! Vous devez utiliser au moins deux composés de pneus différents pendant la course.")
            else:
                with st.spinner("Modélisation polynomiale de l'usure des gommes en cours..."):
                    results = sim.run_strategy(starting_tyre, pit_stops)

                    st.session_state.results = results
                    st.session_state.sim_calculee = True
                    st.success("Simulation terminée avec succès !")

        except FileNotFoundError as fnf_err:
            st.error(f"🚨 {fnf_err}")
        except Exception as sim_err:
            st.error(f"Une erreur est survenue pendant la simulation : {sim_err}")

    # 4. Affichage des résultats et rendus graphiques
    if st.session_state.sim_calculee and st.session_state.results:
        res = st.session_state.results

        col1, col2 = st.columns(2)
        with col1:
            # --- MODIFICATION ICI : Formatage du temps de course lisible ---
            readable_time = format_race_time(res['total_race_time'])
            st.metric(
                label="Temps de course total simulé",
                value=readable_time
            )
        with col2:
            st.metric(
                label="Nombre d'arrêts effectués",
                value=f"{len(res['pitstop_events'])}"
            )

        # Tracé de la courbe de performance
        st.subheader("📊 Analyse des performances au tour")
        fig_laps = TelemetryVisualizer.plot_race_strategy(res["lap_times"], res["pitstop_events"])
        st.pyplot(fig_laps)
        plt.close(fig_laps)

        st.markdown("---")

        # Section Télémétrie Live Animée Spatialisée
        st.subheader("🏎️ Animation de la Télémétrie en temps réel")

        if st.button("🎬 Lancer l'animation sur le tracé"):
            try:
                with st.spinner("Téléchargement des données géométriques de la trajectoire F1..."):
                    session_reelle = data_loader.load_session_data(CURRENT_YEAR, selected_event, 'R')

                    lap_rapide = session_reelle.laps.pick_fastest()
                    telemetry_reelle = lap_rapide.get_telemetry()

                    if telemetry_reelle.empty:
                        st.warning("Aucune donnée de télémétrie spatiale valide trouvée pour ce Grand Prix.")
                    else:
                        live_chart_slot = st.empty()
                        st.toast("Démarrage de la télémétrie live...", icon="🏎️")

                        total_points = len(telemetry_reelle)
                        nombre_frames_cible = 150
                        step = max(1, total_points // nombre_frames_cible)
                        delai_frame = 0.04

                        for i in range(0, total_points, step):
                            fig_live = TelemetryVisualizer.plot_live_frame(telemetry_reelle, i)
                            live_chart_slot.pyplot(fig_live)
                            plt.close(fig_live)
                            time.sleep(delai_frame)

                        st.success("Le pilote a franchi la ligne d'arrivée !")

            except Exception as e:
                st.warning(f"Impossible de générer la carte ou l'animation du circuit : {e}")
    else:
        st.info("Cliquez sur le bouton pour générer les calculs de dégradation et d'arrêts.")


if __name__ == "__main__":
    main()