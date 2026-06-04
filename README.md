# F1 Strategy Simulator

## Description du projet
Développé dans le cadre du cours **MGA 802 - Introduction à la programmation avec Python**, ce projet consiste en un simulateur avancé d'aide à la décision dédié à la stratégie de course en Formule 1. 

L'application permet à un ingénieur de course virtuel de configurer une stratégie pneumatique personnalisée (choix des gommes, fenêtres d'arrêts aux stands) et d'en simuler l'impact sur le rythme de course. Le moteur de calcul intègre des modèles physiques de dégradation des pneumatiques, l'allègement progressif de la monoplace en carburant, ainsi qu'une modélisation stochastique (probabiliste) des aléas techniques lors des arrêts aux stands.

## Fonctionnalités actuelles
* **Moteur Physique & Stochastique :** Calcul dynamique du temps au tour indexé sur l'usure non linéaire des pneus et la consommation de carburant. Gestion des arrêts aux stands avec intégration d'une loi de probabilité pour simuler les erreurs humaines (écrou bloqué, etc.).
* **Validation des Règles FIA :** Algorithme de contrôle bloquant automatiquement les stratégies non conformes au règlement sportif (obligation d'utiliser au moins deux composés de pneus différents par course).
* **Pipeline de Données Réelles :** Connexion et gestion de cache local avec l'API `FastF1` pour extraire les données officielles de chronométrage et de télémétrie spatiale.
* **Analyses Graphiques (Visualisation) :** 
  * Courbe d'évolution du rythme de course et repérage visuel des arrêts.
  * Tracé géométrique en 2D du circuit généré par coordonnées GPS, enrichi d'un dégradé de couleurs représentant la vitesse instantanée.
* **Interface Utilisateur :** Tableau de bord web interactif propulsé par `Streamlit`.

## Structure du Répertoire
* `app.py` : Point d'entrée de l'interface graphique Streamlit.
* `config.yaml` : Fichier de configuration centralisant les constantes d'ingénierie (coefficients de dégradation, perte fixe dans les stands).
* `requirements.txt` : Liste des dépendances logicielles du projet.
* `src/` : Bibliothèque centrale contenant les classes orientées objet (POO) du moteur :
  * `config_loader.py` : Chargeur de configuration YAML.
  * `data_loader.py` : Extracteur et gestionnaire des données de télémétrie FastF1.
  * `simulation.py` : Coeur algorithmique de simulation physique et stochastique.
  * `visualizer.py` : Générateur de rendus graphiques Matplotlib.

## Installation et Lancement

### 1. Cloner le projet et configurer l'environnement
```
# Installer les dépendances requises
pip install -r requirements.txt
```

### 2. Lancer l'application localement
```
streamlit run app.py
```
