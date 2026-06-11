"""
APPLICATION PRINCIPALE
Ce module:- définit l'interface utilisateur Streamlit,
          - récupère les choix de stratégie de l'utilisateur,
          - calcule et affiche les résultats et graphiques de la simulation.
"""

import streamlit as st
import matplotlib.pyplot as plt
import time
import fastf1
from src.data_loader import F1DataLoader
from src.simulation import RaceSimulation
from src.visualizer import TelemetryVisualizer
from src.regression_engine import RegressionEngine

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
    defaults = {"year": 2025, "gp": "Monaco", "event": "Q", "total_laps": 50}
    track_params = {"pitstop_loss_seconds": 22.0, "base_lap_time_seconds": 85.0}
    data_loader = F1DataLoader()

    # Initialisation du moteur de régression/lecture pluri-annuel par pilote
    @st.cache_resource
    def init_regression_engine():
        return RegressionEngine()

    try:
        regression_engine = init_regression_engine()
    except Exception as e:
        st.error(f"❌ Erreur au chargement des coefficients pilotes : {e}")
        st.stop()


    # 2. Barre latérale : Paramètres de la simulation
    st.sidebar.header("🕹️ Configuration de la course")
    st.sidebar.subheader("🌍 Sélection du Grand Prix et du Pilote")

    # Récupération des circuits disponibles directement depuis la structure du JSON
    available_events = list(regression_engine.coefficients_db.keys())
    if available_events:
        selected_event = st.sidebar.selectbox("Sélectionnez le circuit :", available_events)
    else:
        st.sidebar.error("Aucun circuit trouvé dans la base de données de coefficients.")
        selected_event = "Bahrain"

    # Sélection dynamique du pilote en fonction du circuit choisi
    if selected_event in regression_engine.coefficients_db:
        liste_pilotes = sorted(list(regression_engine.coefficients_db[selected_event].keys()))
    else:
        liste_pilotes = []

    selected_driver = st.sidebar.selectbox(
        "🏎️ Sélectionnez le pilote :",
        options=liste_pilotes,
        help="Les courbes d'usure et le rythme initial seront calqués sur l'historique de ce pilote."
    )

    # Sélection de la stratégie: arrêt au stand et pneumatiques
    st.sidebar.markdown("---")
    st.sidebar.subheader("📋 Paramètres de la Stratégie")

    # Détection automatique stricte et sans curseur du nombre de tours
    try:
        total_laps = data_loader.get_event_laps_count(defaults.get("year"), selected_event)
        st.sidebar.success(f"📏 Distance officielle : **{total_laps} tours**")
    except Exception:
        total_laps = int(defaults.get("total_laps", 50))
        st.sidebar.warning(f"Impossible de détecter les tours. Valeur par défaut forcée : {total_laps} tours")

    starting_tyre = st.sidebar.selectbox("Pneu de départ :", ["SOFT", "MEDIUM", "HARD"])

    # Gestion chronologique des arrêts multiples
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
        track_info = track_params
        try:
            track_base_time = data_loader.get_track_base_time(defaults.get("year"), selected_event)
        except Exception:
            track_base_time = track_info.get("base_lap_time_seconds", 85.0)
            st.warning("⚠️ Impossible de récupérer le temps de référence réel. Utilisation de la valeur par défaut.")

        try:
            # 1. Extraction chirurgicale des coefficients propres au couple Pilote/Circuit
            with st.spinner(f"Chargement de la signature d'usure de {selected_driver}..."):
                poly_coefficients = regression_engine.get_coefficients_for_driver(selected_event, selected_driver)

            if not poly_coefficients:
                st.error(f"Impossible de charger des données valides pour {selected_driver} à {selected_event}.")
            else:
                # 2. Instanciation du moteur de simulation avec le profil du pilote
                sim = RaceSimulation(
                    total_laps=total_laps,
                    track_base_time=track_base_time,
                    track_config=track_info,
                    poly_config=poly_coefficients
                )

                # Validation du règlement FIA
                if not sim.is_strategy_valid(starting_tyre, pit_stops):
                    st.error(
                        "🚨 Stratégie invalide selon le règlement de la FIA ! Vous devez utiliser au moins deux composés de pneus différents.")
                else:
                    with st.spinner(f"Modélisation physique de la course de {selected_driver}..."):
                        results = sim.run_strategy(starting_tyre, pit_stops)
                        st.session_state.results = results
                        st.session_state.sim_calculee = True
                        st.success(f"Simulation terminée avec succès pour {selected_driver} au {selected_event}!")

        except FileNotFoundError as fnf_err:
            st.error(f"🚨 {fnf_err}")
        except Exception as sim_err:
            st.error(f"Une erreur est survenue pendant la simulation : {sim_err}")

    # --------------------------------------------------------------------------------------------------------
    # 4. Affichage des résultats et rendus graphiques

    # Initialisation des variables historiques par défaut
    historical_data = None
    historical_pit_stops = None
    recent_year = None

    # Récupération dynamique des données historiques avec gestion des erreurs
    try:
        with st.spinner("🔄 Recherche et chargement des données historiques réelles (FastF1)..."):
            recent_year = data_loader.find_most_recent_year(selected_event, selected_driver)
            if recent_year:
                historical_data, historical_pit_stops = data_loader.get_historical_driver_data(
                    recent_year, selected_event, selected_driver
                )
            else:
                st.info(f"ℹ️ Aucun historique récent (depuis 2018) trouvé pour {selected_driver} ayant fini ce GP.")
    except Exception as e:
        st.warning(f"⚠️ Impossible de superposer les données réelles : {e}")

    # 1. Affichage des stratégies & temps total de course (simulation & historique)

    if st.session_state.sim_calculee and st.session_state.results:
        res = st.session_state.results

        # LIGNE 1 : LA SIMULATION
        st.markdown(f"### Simulation de {selected_driver} au {selected_event}")

        col1, col2, col3 = st.columns(3)

        with col1:
            # Temps total de course
            readable_time = format_race_time(res['total_race_time'])
            st.metric(
                label="Temps de course total",
                value=readable_time
            )

        with col2:
            # Arrêts au stand: nombre d'arrêts & numéro de tour
            sim_pit_laps = list(res['pitstop_events'].keys())
            sim_count = len(sim_pit_laps)
            if sim_count > 0:
                sim_laps_str = ", ".join(str(int(lap)) for lap in sim_pit_laps)
                sim_value = f"{sim_count} (Tour{'s' if sim_count > 1 else ''} {sim_laps_str})"
            else:
                sim_value = "0"

            st.metric(
                label="Arrêts au stand",
                value=sim_value
            )

        with col3:
            # Choix des pneumatiques
            sim_compounds = [starting_tyre] + list(pit_stops.values())
            sim_strategy = " - ".join([str(c).strip().title() for c in sim_compounds])

            st.metric(
                label="Choix des pneumatiques",
                value=sim_strategy
            )


        # LIGNE 2 : LE RÉEL / HISTORIQUE (Affiché uniquement si les données existent)
        if 'historical_data' in locals() and historical_data is not None and not historical_data.empty:
            st.markdown("---")  # Petite ligne fine de séparation visuelle
            st.markdown(f"### Résultats réels de {selected_driver} au {selected_event} de {recent_year}")

            col4, col5, col6 = st.columns(3)

            with col4:
                # Temps total de course - réel
                real_total_seconds = historical_data['LapTimeSeconds'].sum()
                readable_real_time = format_race_time(real_total_seconds)
                st.metric(
                    label="Temps de course total",
                    value=readable_real_time
                )

            with col5:
                # Arrêts au stand réels
                if 'historical_pit_stops' in locals() and historical_pit_stops is not None:
                    real_count = len(historical_pit_stops)
                    if real_count > 0:
                        real_laps_str = ", ".join(str(int(lap)) for lap in historical_pit_stops)
                        real_value = f"{real_count} (Tour{'s' if real_count > 1 else ''} {real_laps_str})"
                    else:
                        real_value = "0"
                else:
                    real_value = "Non disponible"

                st.metric(
                    label="Arrêts au stand",
                    value=real_value
                )

            with col6:
                # Choix de pneumatiques - réel
                if 'historical_data' in locals() and historical_data is not None and not historical_data.empty:
                    if 'Compound' in historical_data.columns:
                        # NETTOYAGE STRICT : On supprime les vrais NaN ET les textes "nan" / "unknown"
                        df_tires = historical_data.dropna(subset=['Compound'])
                        df_tires = df_tires[~df_tires['Compound'].astype(str).str.lower().str.strip().isin(
                            ['nan', 'none', 'unknown', ''])]

                        if not df_tires.empty:
                            if 'Stint' in df_tires.columns:
                                # On prend le premier pneu VALIDE pour chaque relais (Stint)
                                stints_sequence = df_tires.sort_values('LapNumber').drop_duplicates(subset=['Stint'])[
                                    'Compound'].tolist()
                            else:
                                # Sécurité alternative si la colonne 'Stint' venait à manquer
                                raw_compounds = df_tires.sort_values('LapNumber')['Compound'].tolist()
                                stints_sequence = [raw_compounds[0]] if raw_compounds else []
                                for c in raw_compounds[1:]:
                                    if c != stints_sequence[-1]:
                                        stints_sequence.append(c)

                            real_strategy = " - ".join([str(c).strip().title() for c in stints_sequence])
                        else:
                            real_strategy = "Non disponible"
                    else:
                        real_strategy = "Non disponible"
                else:
                    real_strategy = "Non disponible"

                st.metric(
                    label="Choix des pneumatiques",
                    value=real_strategy
                )


        # 2. Tracé de la courbe de performance
        st.subheader(f"📊 Analyse des performances au tour de {selected_driver} au {selected_event}")

        fig_laps = TelemetryVisualizer.plot_race_strategy(
            lap_times=res["lap_times"],
            pitstop_events=res["pitstop_events"],
            selected_driver=selected_driver,
            historical_data=historical_data,
            historical_pit_stops=historical_pit_stops,
            year=recent_year
        )

        st.pyplot(fig_laps)
        plt.close(fig_laps)

        st.markdown("---")

        # 3. Section Télémétrie Live Animée Spatialisée
        st.subheader("🏎️ Animation de la Télémétrie en temps réel")

        if st.button("🎬 Lancer l'animation sur le tracé"):
            try:
                with st.spinner("Téléchargement des données géométriques de la trajectoire F1..."):
                    session_reelle = data_loader.load_session_data(defaults.get("year"), selected_event, 'R')

                    # On essaie d'abord d'animer le tour le plus rapide spécifique du pilote sélectionné
                    laps_pilote = session_reelle.laps.pick_driver(selected_driver)
                    if not laps_pilote.empty:
                        lap_rapide = laps_pilote.pick_fastest()
                    else:
                        lap_rapide = session_reelle.laps.pick_fastest()

                    telemetry_reelle = lap_rapide.get_telemetry()

                    if telemetry_reelle.empty:
                        st.warning("Aucune donnée de télémétrie spatiale valide trouvée pour ce Grand Prix.")
                    else:
                        live_chart_slot = st.empty()
                        st.toast(f"Démarrage de la télémétrie pour {selected_driver}...", icon="🏎️")

                        total_points = len(telemetry_reelle)
                        nombre_frames_cible = 150
                        step = max(1, total_points // nombre_frames_cible)
                        delai_frame = 0.04

                        for i in range(0, total_points, step):
                            fig_live = TelemetryVisualizer.plot_live_frame(telemetry_reelle, i)
                            live_chart_slot.pyplot(fig_live)
                            plt.close(fig_live)
                            time.sleep(delai_frame)

                        st.success(f"{selected_driver} a franchi la ligne d'arrivée !")

            except Exception as e:
                st.warning(f"Impossible de générer la carte ou l'animation du circuit : {e}")
    else:
        st.info("Sélectionnez un pilote et configurez sa stratégie dans la barre latérale pour lancer les calculs.")


if __name__ == "__main__":
    main()