import streamlit as st
from src.config_loader import ConfigLoader
from src.data_loader import F1DataLoader
from src.simulation import RaceSimulation
from src.visualizer import TelemetryVisualizer


def main():
    st.set_page_config(page_title="F1 Strategy Simulator", layout="wide")

    st.title("🏎️ F1 Strategy Simulator")
    st.markdown("---")

    # Initialisation de la mémoire de session
    if "sim_calculee" not in st.session_state:
        st.session_state.sim_calculee = False
    if "results" not in st.session_state:
        st.session_state.results = None

    # 1. Chargement des composants de base
    config = ConfigLoader()
    defaults = config.get_simulation_defaults()
    tyre_params = config.get_tyre_parameters()
    track_params = config.get_track_parameters()
    data_loader = F1DataLoader()

    # 2. Barre latérale : Paramètres de la simulation
    st.sidebar.header("🕹️ Configuration de la course")

    st.sidebar.subheader("🌍 Sélection du Grand Prix")

    # Choix de l'année
    selected_year = st.sidebar.number_input(
        "Année du Grand Prix :",
        min_value=2020,
        max_value=2026,
        value=int(defaults.get('year', 2025))
    )

    # Liste des circuits standard pour éviter un chargement infini au démarrage
    # L'utilisateur peut taper le nom de n'importe quel autre GP (ex: "Spa", "Monza", "Bahrain")
    selected_gp = st.sidebar.selectbox(
        "Choisir le circuit :",
        ["Monaco", "Monza", "Spa", "Silverstone", "Bahrain", "Australia", "Suzuka", "Austin"]
    )

    # --- INTERROGATION AUTOMATIQUE DE FASTF1 ---
    with st.sidebar.spinner("Analyse du circuit via FastF1..."):
        total_laps = data_loader.get_event_laps_count(selected_year, selected_gp)
        # On extrait dynamiquement le vrai chrono de référence du circuit
        track_base_time = data_loader.get_track_base_time(selected_year, selected_gp)

    # Calcul des minutes/secondes pour l'affichage informatif
    base_min = int(track_base_time // 60)
    base_sec = track_base_time % 60

    st.sidebar.markdown(f"**🏎️ Distance détectée :** {total_laps} tours")
    st.sidebar.markdown(f"**⏱️ Chrono de référence :** {base_min}m {base_sec:.2f}s")
    st.sidebar.markdown("---")

    # --- REPRISE DES OPTIONS DE STRATÉGIE ---
    st.sidebar.subheader("Stratégie Pneumatique")
    starting_tyre = st.sidebar.selectbox(
        "Pneu de départ :",
        ["SOFT", "MEDIUM", "HARD"],
        index=1
    )

    nb_stops = st.sidebar.radio("Nombre d'arrêts prévus :", [1, 2], horizontal=True)

    # INITIALISATION DU DICTIONNAIRE VIDE (Obligatoire pour éviter les UnboundLocalError)
    pit_stops = {}

    if nb_stops == 1:
        pit_lap = st.sidebar.slider(
            "Tour de l'arrêt au stand :",
            min_value=1,
            max_value=total_laps - 1,
            value=25
        )
        next_tyre = st.sidebar.selectbox(
            "Pneu pour le deuxième relais :",
            ["SOFT", "MEDIUM", "HARD"],
            index=2
        )
        # On remplit le dictionnaire pour 1 arrêt
        pit_stops[pit_lap] = next_tyre

    elif nb_stops == 2:
        st.sidebar.markdown("---")
        st.sidebar.write("**Premier arrêt**")
        pit_lap_1 = st.sidebar.slider(
            "Tour du 1er arrêt :",
            min_value=1,
            max_value=total_laps - 2,
            value=20
        )
        next_tyre_1 = st.sidebar.selectbox(
            "Pneu pour le relais 2 :",
            ["SOFT", "MEDIUM", "HARD"],
            index=1,
            key="tyre_1"
        )
        # On ajoute le premier arrêt
        pit_stops[pit_lap_1] = next_tyre_1

        st.sidebar.markdown("---")
        st.sidebar.write("**Deuxième arrêt**")
        pit_lap_2 = st.sidebar.slider(
            "Tour du 2e arrêt :",
            min_value=pit_lap_1 + 1,
            max_value=total_laps - 1,
            value=50
        )
        next_tyre_2 = st.sidebar.selectbox(
            "Pneu pour le relais 3 :",
            ["SOFT", "MEDIUM", "HARD"],
            index=2,
            key="tyre_2"
        )
        # On ajoute le deuxième arrêt
        pit_stops[pit_lap_2] = next_tyre_2

    # 3. Zone principale : Exécution du simulateur
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("📋 Résumé de votre plan")
        st.write(f"**Distance totale :** {total_laps} tours")
        st.write(f"**Relais 1 :** Départ en pneu `{starting_tyre}`")

        if nb_stops == 1:
            st.write(f"**Arrêt prévu :** Tour {pit_lap} (Perte estimée : ~{track_params.get('pitstop_loss_seconds')}s)")
            st.write(f"**Relais 2 :** Fin de course en `{next_tyre}`")
        else:
            st.write(f"**Arrêt 1 prévu :** Tour {pit_lap_1} (Pneu : `{next_tyre_1}` intermediate)")
            st.write(f"**Arrêt 2 prévu :** Tour {pit_lap_2} (Pneu : `{next_tyre_2}` final)")

        st.markdown("---")
        # Bouton pour déclencher les calculs
        launch_sim = st.button("🚀 Lancer la simulation de stratégie", type="primary")

    with col2:
        st.subheader("📊 Résultats du moteur de calcul")

        # 1. Gestion du clic sur le bouton de calcul
        if launch_sim:
            track_factor = config.get_track_factor(selected_gp)
            sim_engine = RaceSimulation(total_laps, track_base_time, tyre_params, track_params, track_factor)

            if not sim_engine.is_strategy_valid(starting_tyre, pit_stops):
                st.error(
                    "🚨 **Stratégie non conforme au règlement de la FIA !** Vous devez obligatoirement utiliser au moins deux types de pneus différents.")
                st.session_state.sim_calculee = False
            else:
                st.session_state.results = sim_engine.run_strategy(starting_tyre, pit_stops)
                st.session_state.sim_calculee = True
                st.success("Simulation complétée avec succès !")

        # 2. Affichage des résultats basé sur la mémoire de session
        if st.session_state.sim_calculee and st.session_state.results is not None:
            results = st.session_state.results  # Récupération des données sauvegardées

            # Affichage des métriques globales
            total_minutes = int(results["total_race_time"] // 60)
            total_seconds = results["total_race_time"] % 60

            st.metric(
                label="Temps total de course simulé",
                value=f"{total_minutes} min {total_seconds:.2f} s"
            )

            # --- AFFICHAGE DYNAMIQUE DES ARRÊTS ---
            st.markdown("### ⏱️ Détails des arrêts aux stands")
            for lap, pit_time in results["pitstop_events"].items():
                pneu_choisi = pit_stops[lap]
                st.info(f"🏁 **Tour {lap} :** Passage par les stands pour chausser les pneus `{pneu_choisi}`. "
                        f"Temps total perdu : **{pit_time:.3f} secondes**.")

            # Aperçu des chronos
            st.markdown("**Aperçu des chronos calculés (Tours 1 à 5) :**")
            laps_preview = {f"Tour {i + 1}": f"{time:.3f} s" for i, time in enumerate(results["lap_times"][:5])}
            st.json(laps_preview)

            # Graphique d'analyse des relais
            st.markdown("### 📈 Graphique d'analyse des relais")
            fig = TelemetryVisualizer.plot_race_strategy(results["lap_times"], results["pitstop_events"])
            st.pyplot(fig)

            # Carte du circuit fixe et Animation Live
            st.markdown("### 🗺️ Carte du circuit et analyse télémétrique")
            try:
                with st.spinner("Génération du tracé de la piste en cours..."):
                    # Récupération des données géométriques réelles via le sélecteur dynamique
                    session_circuit = data_loader.load_session_data(selected_year, selected_gp, defaults.get('event'))
                    premier_pilote = session_circuit.laps['Driver'].unique()[0]
                    telemetry_reelle = data_loader.get_driver_telemetry(session_circuit, premier_pilote)

                    # Rendu de la carte fixe
                    fig_circuit = TelemetryVisualizer.plot_circuit_layout(telemetry_reelle)
                    st.pyplot(fig_circuit)

                    # Séparateur pour la section Live Animation
                    st.markdown("---")
                    st.markdown("### 🎬 Simulation en direct (Live Tracking)")

                    if st.button("🏁 Démarrer le replay de la course", type="secondary"):
                        import time
                        import matplotlib.pyplot as plt

                        live_chart_slot = st.empty()
                        st.toast("Démarrage de la télémétrie live...", icon="🏎️")

                        total_points = len(telemetry_reelle)

                        # --- AJUSTEMENT DYNAMIQUE DU RYTHME ---
                        # On cible environ 150 frames au total pour une belle animation fluide
                        nombre_frames_cible = 150

                        # Calcul du pas idéal (minimum 1 pour ne pas diviser par zéro)
                        step = max(1, total_points // nombre_frames_cible)

                        # Temps de pause par frame (ajustable : 0.04s pour ~25 images par seconde)
                        delai_frame = 0.04

                        # Boucle d'animation avec les paramètres adaptés
                        for i in range(0, total_points, step):
                            fig_live = TelemetryVisualizer.plot_live_frame(telemetry_reelle, i)
                            live_chart_slot.pyplot(fig_live)
                            plt.close(fig_live)
                            time.sleep(delai_frame)

                        st.success("Le pilote a franchi la ligne d'arrivée !")

            except Exception as e:
                st.warning(f"Impossible de générer la carte ou l'animation du circuit : {e}")
        else:
            # Message affiché par défaut si aucun calcul n'a encore été lancé
            st.info("Cliquez sur le bouton pour générer les calculs de dégradation et d'arrêts.")


if __name__ == "__main__":
    main()