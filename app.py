"""
APPLICATION PRINCIPALE
Ce module : - définit l'interface utilisateur Streamlit avec page d'accueil,
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

    # --- AJOUT DU CSS POUR REDIMENSIONNER LES METRICS ---
    st.markdown(
        """
        <style>
        /* Force les titres des metrics à aller à la ligne au lieu de mettre ... */
        [data-testid="stMetricLabel"] {
            word-wrap: break-word;
            white-space: normal;
        }
        /* Rend la taille des valeurs dynamique selon l'espace disponible */
        [data-testid="stMetricValue"] {
            word-wrap: break-word;
            white-space: normal;
            font-size: clamp(1.2rem, 2vw, 1.8rem) !important; 
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    # ----------------------------------------------------

    # Initialisation de la mémoire de session pour Streamlit
    if "validated" not in st.session_state:
        st.session_state.validated = False
    if "sim_calculee" not in st.session_state:
        st.session_state.sim_calculee = False
    if "results" not in st.session_state:
        st.session_state.results = None
    if "home_event" not in st.session_state:
        st.session_state.home_event = None
    if "home_driver" not in st.session_state:
        st.session_state.home_driver = None
    if "optimal_strategy" not in st.session_state:
        st.session_state.optimal_strategy = None

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

    available_events = list(regression_engine.coefficients_db.keys())

    # ========================================================================================================
    # PAGE D'ACCUEIL (SI NON VALIDÉ)
    # ========================================================================================================
    if not st.session_state.validated:
        st.title("🏎️ Bienvenue sur l'interface d'analyse de stratégie F1")
        st.markdown("---")
        st.markdown("### 🌍 Configuration initiale de l'analyse")

        col_init_event, col_init_driver = st.columns(2)

        with col_init_event:
            if available_events:
                default_event = st.selectbox("Sélectionnez le circuit à analyser :", available_events, key="init_event")
            else:
                st.error("Aucun circuit trouvé dans la base de données.")
                default_event = "Bahrain"

        with col_init_driver:
            if default_event in regression_engine.coefficients_db:
                liste_pilotes_init = sorted(list(regression_engine.coefficients_db[default_event].keys()))
            else:
                liste_pilotes_init = []

            st.selectbox("Sélectionnez le pilote à analyser :", options=liste_pilotes_init, key="init_driver")

        st.markdown("##")
        if st.button("🚀 Valider et ouvrir l'interface d'analyse", type="primary"):
            st.session_state.home_event = st.session_state.init_event
            st.session_state.home_driver = st.session_state.init_driver
            st.session_state.validated = True
            st.sidebar.empty()  # Force le rafraîchissement de la sidebar
            st.rerun()

    # ========================================================================================================
    # INTERFACE D'ANALYSE PRINCIPALE (SI VALIDÉ)
    # ========================================================================================================
    else:
        # Témoin d'activité tout en haut de la page
        st.info(
            f"📊 **Analyse active :** Simulation de la course de **{st.session_state.home_driver}** au **{st.session_state.home_event}**")

        # Bouton Revenir à l'accueil tout en haut de la barre latérale
        if st.sidebar.button("🏠 Revenir à l'accueil"):
            st.session_state.validated = False
            st.session_state.sim_calculee = False
            st.rerun()

        st.title("🏎️ Simulateur de course F1")
        st.markdown("---")

        # 2. Barre latérale : Paramètres de la simulation
        st.sidebar.header("🕹️ Configuration de la course")
        st.sidebar.subheader("🌍 Sélection du Grand Prix et du Pilote")

        try:
            event_index = available_events.index(st.session_state.home_event)
        except ValueError:
            event_index = 0

        selected_event = st.sidebar.selectbox(
            "Sélectionnez le circuit :",
            available_events,
            index=event_index
        )

        if selected_event != st.session_state.home_event:
            st.session_state.home_event = selected_event
            st.session_state.sim_calculee = False
            st.session_state.optimal_strategy = None
            if "toggle_ia" in st.session_state: del st.session_state["toggle_ia"]
            st.rerun()

        if selected_event in regression_engine.coefficients_db:
            liste_pilotes = sorted(list(regression_engine.coefficients_db[selected_event].keys()))
        else:
            liste_pilotes = []

        try:
            driver_index = liste_pilotes.index(st.session_state.home_driver)
        except ValueError:
            driver_index = 0

        selected_driver = st.sidebar.selectbox(
            "🏎️ Sélectionnez le pilote :",
            options=liste_pilotes,
            index=driver_index,
            help="Les courbes d'usure et le rythme initial seront calqués sur l'historique de ce pilote."
        )

        if selected_driver != st.session_state.home_driver:
            st.session_state.home_driver = selected_driver
            st.session_state.sim_calculee = False
            st.session_state.optimal_strategy = None
            if "toggle_ia" in st.session_state: del st.session_state["toggle_ia"]
            st.rerun()

        st.sidebar.markdown("---")
        st.sidebar.subheader("📋 Paramètres de la Stratégie")

        try:
            total_laps = data_loader.get_event_laps_count(defaults.get("year"), selected_event)
            st.sidebar.success(f"📏 Distance officielle : **{total_laps} tours**")
        except Exception:
            total_laps = int(defaults.get("total_laps", 50))
            st.sidebar.warning(f"Impossible de détecter les tours. Valeur par défaut forcée : {total_laps} tours")

        starting_tyre = st.sidebar.selectbox("Pneu de départ :", ["SOFT", "MEDIUM", "HARD"])

        st.sidebar.markdown("---")
        st.sidebar.subheader("🛑 Gestion des Arrêts aux Stands")

        num_pits = st.sidebar.number_input("Nombre d'arrêts prévus :", min_value=1, max_value=3, value=1, step=1)

        pit_stops = {}
        last_pit_lap = 0

        for stop_idx in range(1, num_pits + 1):
            st.sidebar.markdown(f"**Arrêt n°{stop_idx}**")
            col_lap, col_tyre = st.sidebar.columns(2)

            with col_lap:
                min_allowed_lap = last_pit_lap + 1
                max_allowed_lap = total_laps - (num_pits - stop_idx) - 1
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
                st.warning(
                    "⚠️ Impossible de récupérer le temps de référence réel. Utilisation de la valeur par défaut.")

            try:
                with st.spinner(f"Chargement de la signature d'usure de {selected_driver}..."):
                    poly_coefficients = regression_engine.get_coefficients_for_driver(selected_event, selected_driver)

                if not poly_coefficients:
                    st.error(f"Impossible de charger des données valides pour {selected_driver} à {selected_event}.")
                else:
                    sim = RaceSimulation(
                        total_laps=total_laps,
                        track_base_time=track_base_time,
                        track_config=track_info,
                        poly_config=poly_coefficients
                    )

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
                st.error(f"Une erreur est survenue pendant la simulation : {sim_err}  \n Veuillez essayer une autre stratégie.")

        # 4. Affichage des résultats et rendus graphiques
        try:
            with st.spinner("🔄 Récupération des données historiques (FastF1)..."):
                historical_data, historical_pit_stops, recent_year = F1DataLoader._cached_historical_data(
                    data_loader, selected_event, selected_driver
                )
        except Exception as e:
            st.warning(f"⚠️ Impossible de superposer les données réelles : {e}")
            historical_data, historical_pit_stops, recent_year = None, None, None

        if st.session_state.sim_calculee and st.session_state.results:
            res = st.session_state.results

            # Création du système d'onglets
            tab_dashboard, tab_telemetry = st.tabs(["📊 Tableau de bord comparatif", "🏎️ Télémétrie & Animation Live"])

            # ==================================================================
            # ONGLET 1 : DONNÉES COMPARATIVES ET GRAPH_STRAT
            # ==================================================================
            with tab_dashboard:

                # --- 1. SECTION SIMULATION MANUELLE ---
                st.markdown(f"### Simulation manuelle de {selected_driver} au {selected_event}")
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric(label="Temps de course total", value=format_race_time(res['total_race_time']))

                with col2:
                    sim_pit_laps = list(res['pitstop_events'].keys())
                    sim_count = len(sim_pit_laps)
                    sim_value = f"{sim_count} (Tour{'s' if sim_count > 1 else ''} {', '.join(str(int(lap)) for lap in sim_pit_laps)})" if sim_count > 0 else "0"
                    st.metric(label="Arrêts au stand", value=sim_value)

                with col3:
                    sim_compounds = [starting_tyre] + list(pit_stops.values())
                    st.metric(label="Choix des pneumatiques",
                              value=" - ".join([str(c).strip().title() for c in sim_compounds]))

                # --- 2. SECTION HISTORIQUE RÉEL ---
                if 'historical_data' in locals() and historical_data is not None and not historical_data.empty:
                    st.markdown("---")
                    st.markdown(f"### Résultats réels de {selected_driver} au {selected_event} de {recent_year}")
                    col4, col5, col6 = st.columns(3)

                    with col4:
                        real_total_seconds = historical_data['LapTimeSeconds'].sum()
                        st.metric(label="Temps de course total", value=format_race_time(real_total_seconds))

                    with col5:
                        if 'historical_pit_stops' in locals() and historical_pit_stops is not None:
                            real_count = len(historical_pit_stops)
                            real_value = f"{real_count} (Tour{'s' if real_count > 1 else ''} {', '.join(str(int(lap)) for lap in historical_pit_stops)})" if real_count > 0 else "0"
                        else:
                            real_value = "Non disponible"
                        st.metric(label="Arrêts au stand", value=real_value)

                    with col6:
                        # Nettoyage et tri des données de pneumatiques
                        df_tires = historical_data.dropna(subset=['Compound']).sort_values('LapNumber')
                        df_tires = df_tires[~df_tires['Compound'].astype(str).str.lower().str.strip().isin(
                            ['nan', 'none', 'unknown', ''])]

                        if not df_tires.empty: #Vérification s'il y a eu un arrêt au stand = changement de pneu
                            stints_sequence = df_tires.drop_duplicates(subset=['Stint'])['Compound'].tolist()

                            real_strategy = " - ".join([str(c).strip().title() for c in stints_sequence])
                        else:
                            real_strategy = "Non disponible"

                        st.metric(label="Choix des pneumatiques", value=real_strategy)

                # --- 3. SECTION STRATEGIE OPTIMISÉE (Bouton Toggle) ---
                st.markdown("---")
                st.markdown("### 🤖 Assistant Stratégique")

                # Le bouton toggle
                afficher_ia = st.toggle("✨ Calculer et afficher la stratégie optimale", key="toggle_ia")

                # Initialisation des variables pour le graphique optimisé(vides par défaut)
                opt_lap_times = None
                opt_pit_events = None

                if afficher_ia:
                    # On calcule uniquement si ce n'est pas déjà dans la mémoire
                    if st.session_state.optimal_strategy is None:
                        with st.spinner("Analyse des stratégies en cours (1 à 2 arrêts)..."):
                            track_info = track_params
                            try:
                                track_base_time = data_loader.get_track_base_time(defaults.get("year"), selected_event)
                            except Exception:
                                track_base_time = track_info.get("base_lap_time_seconds", 85.0)

                            poly_coefficients = regression_engine.get_coefficients_for_driver(selected_event,
                                                                                              selected_driver)
                            sim_ia = RaceSimulation(total_laps, track_base_time, track_info, poly_coefficients)

                            # Appel de la fonction IA
                            st.session_state.optimal_strategy = sim_ia.find_optimal_stops_strategy()

                    # On récupère les résultats de l'IA et on prépare les variables pour le graphique final
                    opt_strat = st.session_state.optimal_strategy
                    if opt_strat:
                        opt_lap_times = opt_strat['results']["lap_times"]
                        opt_pit_events = opt_strat['results']["pitstop_events"]

                        st.success(f"✅ La meilleure stratégie trouvée est à **{opt_strat['type']}** !")
                        col_ia1, col_ia2, col_ia3 = st.columns(3)
                        with col_ia1:
                            st.metric(label="Temps de course estimé (optimal)",
                                      value=format_race_time(opt_strat['results']['total_race_time']))
                        with col_ia2:
                            ia_pit_laps = list(opt_strat['pit_stops'].keys())
                            ia_count = len(ia_pit_laps)
                            ia_value = f"{ia_count} (Tour{'s' if ia_count > 1 else ''} {', '.join(str(int(lap)) for lap in ia_pit_laps)})" if ia_count > 0 else "0"
                            st.metric(label="Arrêts optimaux", value=ia_value)
                        with col_ia3:
                            ia_compounds = [opt_strat['starting_tyre']] + list(opt_strat['pit_stops'].values())
                            st.metric(label="Pneumatiques idéaux",
                                      value=" - ".join([str(c).strip().title() for c in ia_compounds]))

                # --- 4. GRAPHIQUE COMPARATIF GLOBAL ---
                st.markdown("---")
                st.subheader(f"📊 Analyse des performances au tour comparées - {selected_driver}")

                # On envoie toutes les données à plot_race_strategy (les données IA seront nulles si le bouton est éteint)
                fig_laps = TelemetryVisualizer.plot_race_strategy(
                    lap_times=res["lap_times"],
                    pitstop_events=res["pitstop_events"],
                    selected_driver=selected_driver,
                    historical_data=historical_data,
                    historical_pit_stops=historical_pit_stops,
                    year=recent_year,
                    optimal_lap_times=opt_lap_times,
                    optimal_pit_events=opt_pit_events
                )
                st.pyplot(fig_laps)
                plt.close(fig_laps)

            # ==================================================================
            # ONGLET 2 : ANIMATION GÉOMÉTRIQUE EN TEMPS RÉEL
            # ==================================================================
            with tab_telemetry:
                st.subheader("🏎️ Animation de la Télémétrie en temps réel")

                if st.button("🎬 Lancer l'animation sur le tracé"):
                    try:
                        with st.spinner("Récupération de la trajectoire en cache..."):
                            telemetry_reelle = F1DataLoader._cached_telemetry_data(
                                data_loader, defaults.get("year"), selected_event, selected_driver
                            )

                            if telemetry_reelle.empty:
                                st.warning("Aucune donnée de télémétrie spatiale valide trouvée pour ce Grand Prix.")
                            else:
                                col_gauche, col_centre, col_droite = st.columns([1, 1, 1])

                                with col_centre:
                                    live_chart_slot = st.empty()

                                st.toast(f"Démarrage de la télémétrie pour {selected_driver}...", icon="🏎️")
                                total_points = len(telemetry_reelle)
                                nombre_frames_cible = 150
                                step = max(1, total_points // nombre_frames_cible)

                                for i in range(0, total_points, step):
                                    fig_live = TelemetryVisualizer.plot_live_frame(telemetry_reelle, i)
                                    live_chart_slot.pyplot(fig_live, use_container_width=True)
                                    plt.close(fig_live)
                                    time.sleep(0.04)
                                st.success(f"{selected_driver} a franchi la ligne d'arrivée !")
                    except Exception as e:
                        st.warning(f"Impossible de générer la carte ou l'animation du circuit : {e}")
        else:
            st.info("Utilisez les options de la barre latérale pour configurer la stratégie et lancer les calculs.")
if __name__ == "__main__":
    main()