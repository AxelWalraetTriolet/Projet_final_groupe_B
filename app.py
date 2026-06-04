import streamlit as st
from src.config_loader import ConfigLoader
from src.data_loader import F1DataLoader


def main():
    st.title("F1 Strategy Simulator - Test Initial")
    st.write("Validation du chargement de la configuration et des données")

    # 1. Test du ConfigLoader
    st.subheader("1. Test de la configuration (YAML)")
    try:
        config = ConfigLoader()
        defaults = config.get_simulation_defaults()
        tyre_params = config.get_tyre_parameters()

        st.success("Fichier config.yaml chargé avec succès !")
        st.json({
            "Paramètres par défaut": defaults,
            "Pénalités pneus": tyre_params
        })
    except Exception as e:
        st.error(f"Erreur lors du chargement du fichier YAML : {e}")
        return

    # 2. Test du F1DataLoader (FastF1)
    st.subheader("2. Test de l'API FastF1")
    st.write("Téléchargement des données en cours... (Cela peut prendre du temps au premier lancement)")

    try:
        data_loader = F1DataLoader()

        # On utilise les variables chargées depuis le YAML
        year = defaults.get('year', 2025)
        gp = defaults.get('gp', 'Monaco')
        event_type = defaults.get('event', 'Q')

        # Tentative de chargement de la session
        session = data_loader.load_session_data(year, gp, event_type)
        st.success(f"Session {year} - {gp} GP ({event_type}) chargée avec succès depuis FastF1 !")

        # Affichage des pilotes disponibles pour valider la structure de données
        drivers = session.laps['Driver'].unique()
        st.write("Pilotes détectés dans cette session :", list(drivers))

    except Exception as e:
        st.error(f"Erreur lors de la communication avec FastF1 : {e}")


if __name__ == "__main__":
    main()