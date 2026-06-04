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

    # 2. Barre latérale : Paramètres de la simulation
    st.sidebar.header("🕹️ Configuration de la course")

    # Paramètres fixes pour le test (Monaco - 78 tours)
    total_laps = 78
    track_base_time = 75.0  # Temps de base fictif en secondes (1m15s)

    st.sidebar.subheader("Stratégie Pneumatique")
    starting_tyre = st.sidebar.selectbox(
        "Pneu de départ :",
        ["SOFT", "MEDIUM", "HARD"],
        index=1  # MEDIUM par défaut
    )

    pit_lap = st.sidebar.slider(
        "Tour de l'arrêt au stand :",
        min_value=1,
        max_value=total_laps - 1,
        value=25
    )

    next_tyre = st.sidebar.selectbox(
        "Pneu pour le deuxième relais :",
        ["SOFT", "MEDIUM", "HARD"],
        index=2  # HARD par défaut
    )

    # Construction du dictionnaire d'arrêts pour le moteur de simulation
    pit_stops = {pit_lap: next_tyre}

    # 3. Zone principale : Exécution du simulateur
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("📋 Résumé de votre plan")
        st.write(f"**Distance totale :** {total_laps} tours")
        st.write(f"**Relais 1 :** Départ en pneu `{starting_tyre}`")
        st.write(f"**Arrêt prévu :** Tour {pit_lap} (Perte estimée : ~{track_params.get('pitstop_loss_seconds')}s)")
        st.write(f"**Relais 2 :** Chaussage du pneu `{next_tyre}` jusqu'à la fin")

        # Bouton pour déclencher les calculs
        launch_sim = st.button("🚀 Lancer la simulation de stratégie", type="primary")

    with col2:
        st.subheader("📊 Résultats du moteur de calcul")

        if launch_sim:
            # Initialisation du moteur de simulation
            sim_engine = RaceSimulation(total_laps, track_base_time, tyre_params, track_params)

            # --- AJOUT DE LA VALIDATION DU RÈGLEMENT ---
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

                # Détail de l'arrêt
                actual_pit_time = results["pitstop_events"][pit_lap]
                st.info(
                    f"⏱️ **Détail de l'arrêt au tour {pit_lap} :** Le passage par les stands a pris **{actual_pit_time:.3f} secondes**.")

                # Aperçu des chronos
                st.markdown("**Aperçu des chronos calculés (Tours 1 à 5) :**")
                laps_preview = {f"Tour {i + 1}": f"{time:.3f} s" for i, time in enumerate(results["lap_times"][:5])}
                st.json(laps_preview)

                # --- AJOUT DU GRAPHIQUE VISUEL ---
                st.markdown("### 📈 Graphique d'analyse des relais")

                # Génération de la figure via notre classe visualizer
                fig = TelemetryVisualizer.plot_race_strategy(results["lap_times"], results["pitstop_events"])

                # Affichage de la figure Matplotlib dans Streamlit
                st.pyplot(fig)
        else:
            st.info("Cliquez sur le bouton pour générer les calculs de dégradation et d'arrêts.")


if __name__ == "__main__":
    main()