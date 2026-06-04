import streamlit as st
from src.config_loader import ConfigLoader
from src.data_loader import F1DataLoader
from src.simulation import RaceSimulation
from src.visualizer import TelemetryVisualizer

st.title("F1 Strategy Analytics Simulator")

# Initialisation des composants
config = ConfigLoader()
data_loader = F1DataLoader()

