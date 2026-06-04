import streamlit as st
from src.config_loader import ConfigLoader
from src.data_loader import F1DataLoader
from src.simulation import RaceSimulation
from src.visualizer import TelemetryVisualizer


def main():
    st.set_page_config(page_title="F1 Strategy Simulator", layout="wide")

    st.title("🏎️ F1 Strategy Analytics Simulator")
    st.markdown("---")

    # 1. Chargement des composants de base
    config = ConfigLoader()
    defaults = config.get_simulation_defaults()
    tyre_params = config.get_tyre_parameters()
    track_params = config.get_track_parameters()
    data_loader = F1DataLoader()

    # 2. Barre latérale : Paramètres de la simulation
    st.sidebar.header("🕹️ Configuration de la course")

    total_laps = 78
    track_base_time = 75.0

    st.sidebar.subheader("Stratégie Pneumatique")
    starting_tyre = st.sidebar.selectbox(
        "Pneu de départ :",
        ["SOFT", "MEDIUM", "HARD"],
        index=1
    )

    # Choix du nombre d'arrêts
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

        if launch_sim:
            # Initialisation du moteur de simulation
            sim_engine = RaceSimulation(total_laps, track_base_time, tyre_params, track_params)

            # Validation du règlement
            if not sim_engine.is_strategy_valid(starting_tyre, pit_stops):
                st.error(
                    "🚨 **Stratégie non conforme au règlement de la FIA !** Vous devez obligatoirement utiliser au moins deux types de pneus différents pendant la course (ex: SOFT puis HARD).")
            else:
                # Si la stratégie est valide, on exécute les calculs
                results = sim_engine.run_strategy(starting_tyre, pit_stops)

                # Affichage des métriques globales
                total_minutes = int(results["total_race_time"] // 60)
                total_seconds = results["total_race_time"] % 60

                st.success("Simulation complétée avec succès (Stratégie conforme) !")

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

                # Carte du circuit
                st.markdown("### 🗺️ Carte du circuit et analyse télémétrique")
                try:
                    with st.spinner("Génération de la carte du circuit..."):
                        session = data_loader.load_session_data(defaults.get('year'), defaults.get('gp'),
                                                                defaults.get('event'))
                        premier_pilote = session.laps['Driver'].unique()[0]
                        telemetry_reelle = data_loader.get_driver_telemetry(session, premier_pilote)
                        fig_circuit = TelemetryVisualizer.plot_circuit_layout(telemetry_reelle)
                        st.pyplot(fig_circuit)
                except Exception as e:
                    st.warning(f"Impossible de générer la carte du circuit : {e}")
        else:
            st.info("Cliquez sur le bouton pour générer les calculs de dégradation et d'arrêts.")


if __name__ == "__main__":
    main()