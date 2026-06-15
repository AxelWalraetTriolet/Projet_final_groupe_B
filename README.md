# Simulateur de stratégie de course F1 

## Description du projet
Développé dans le cadre du cours **MGA 802 - Introduction à la programmation avec Python**, ce projet consiste en un simulateur avancé d'aide à la décision dédié à la stratégie de course en Formule 1. 

L'application permet à un ingénieur de course virtuel de configurer une stratégie pneumatique personnalisée (choix des gommes, fenêtres d'arrêts aux stands) et d'en simuler l'impact sur le rythme de course. Le moteur de calcul intègre des modèles physiques de dégradation des pneumatiques, l'allègement progressif de la monoplace en carburant, ainsi qu'une modélisation stochastique (probabiliste) des aléas techniques lors des arrêts aux stands.  

La simulation est réalisée en supposant une course par temps sec, sans prendre en compte les incidents de course potentiels.

## Fonctionnalités 
* **Génération de modèle prédicitif de performance**: Détermination des coefficients par la méthode de régression par spline cubique robuste projetée sur un polynome d'ordre 2 à partir d'une moyenne des données *FastF1* de 2019 à 2025 après filtrage des anomalies de chronométrage et valeurs atypiques. Exportation des coefficients obtenus par pilote, course et type de pneumatiques dans un fichier .json
* **Moteur Physique & Stochastique :** Calcul dynamique du temps au tour indexé sur l'usure non linéaire des pneus et la consommation de carburant. Gestion des arrêts aux stands avec intégration d'une loi de probabilité à 3 scénarios pour simuler les erreurs humaines (arrêt optimal, léger contretemps ou problème technique majeur).
* **Validation des Règles FIA :** Algorithme de contrôle bloquant automatiquement les stratégies non conformes au règlement sportif (obligation d'utiliser au moins deux composés de pneus différents par course).
* **Protocole de Validation:** Pipeline de calcul automatisé comparant le temps global de course simulé au temps réel officiel de la FIA pour chaque pilote (données sans Safety Car). L'analyse est indexée sur 3 saisons clés (2019, 2024, 2025)s.
* **Pipeline de Données Réelles :** Connexion et gestion de cache local avec l'API `FastF1` pour extraire les données officielles de chronométrage et de télémétrie spatiale.
* **Analyses Graphiques (Visualisation) :** 
  * Tableau récapitulatif et comparatif du résultat de la simulation et des choix de stratégie. 
  * Courbe d'évolution du rythme de course et repérage visuel des arrêts.
  * Graphique d'écarts cumulés par rapport à un temps de référence.
  * Tracé géométrique en 2D du circuit généré par coordonnées GPS.
  * **Rapport de performance interactif** : Évolution de la MAE (*Mean Absolute Error*) inter-saisons, histogramme de distribution du biais du simulateur, précision par tracé et tableau de diagnostic des pires cas réels (faits de course, pénalités).
* **Interface Utilisateur :** Tableau de bord web interactif divisé en onglets complémentaires propulsé par `Streamlit`.


## Structure du Répertoire
* `app.py` : Point d'entrée de l'interface graphique Streamlit.
* `requirements.txt` : Liste des dépendances logicielles du projet.
* `coefficients_pilotes_saisons.json`: Base de données locale contenant les coefficients polynomiaux de dégradation ($\beta_0, \beta_1, \beta_2, \beta_3$) classés par circuit, par pilote et par composé pneumatique.
* `validation_resultats.json` : Base de données locale générée contenant les métriques de validation calculées (KPIs, erreurs par tracé, pires prédictions).
* `src/` : Bibliothèque centrale contenant les classes orientées objet (POO) du moteur :
  * `_init_.py`: Fichier d'initialisation du package python
  * `data_loader.py` : Extracteur et gestionnaire des données de télémétrie FastF1 avec gestion de cache.
  * `generer_base_pilotes.py`: Script de data-mining et d'ajustement mathématique (Scikit-Learn) pour générer le fichier JSON des coefficients.
  * `generer_validation.py` : Pipeline de calcul autonome qui compare les prédictions aux résultats réels pour quantifier la fiabilité du modèle.
  * `regression_engine.py`: Interface d'accès à la base de données JSON avec un système de repli (fallback) automatique si une entité est manquante. 
  * `simulation.py` : Coeur algorithmique de la simulation physique et stochastique.
  * `visualizer.py` : Générateur de rendus graphiques Matplotlib.

## Aperçu de l'interface

<div align="center">

**Première page** : Choix de la course et du pilote à analyser

| |
| :---: |
| <img width="1745" height="512" alt="image" src="https://github.com/user-attachments/assets/844fa1d7-ce83-48cc-8fa3-78525869e64a" />|

<br/>


**Deuxième page** : Choix de la stratégie de course (arrêts au stand et types de pneumatiques)

| |
| :---: |
| <img src="https://github.com/user-attachments/assets/9f1811b4-522d-44c2-983d-9021358c97b5" width="650" alt="Choix de la stratégie" /> |


<br/>

**Résultats** : Affichage des résultats et graphiques sur 3 onglets

| |
| :---: |
| <img src="https://github.com/user-attachments/assets/ccf11c61-65a5-40a7-a135-237ffaa9d973" width="650" alt="Affichage des graphiques" /> |

</div>

## Installation et Lancement

### 1. Cloner le projet et configurer l'environnement
Ouvrez votre terminal, placez-vous dans le dossier de votre choix, puis récupérez le projet :
```bash
# Cloner le dépôt
git clone https://github.com/AxelWalraetTriolet/Projet_final_groupe_B.git
cd Projet_final_groupe_B

# Créer un environnement virtuel (recommandé)
python -m venv .venv

# Activer l'environnement virtuel
# Sur Windows (Command Prompt) :
.venv\Scripts\activate
# Sur Windows (PowerShell) :
.venv\Scripts\Activate.ps1
# Sur Mac / Linux :
source .venv/bin/activate
```

### 2. Installer le projet et ses dépendances 
```
pip install -e .
```

### 3. Compiler et valider le modèle
```
cd src
python generer_base_pilotes.py
python generer_validation.py
cd ..
```

### 4. Lancer l'application localement
```
streamlit run app.py
```

## Limites actuelles
* **Gestion de la météo :** Simulation restreinte au temps sec (pas de gestion des pneus Intermédiaires/Pluie).
* **Incidents de course :** Absence de vagues de déploiement de la *Safety Car* ou de drapeaux rouges.
* **Trafic en piste :** Le modèle simule le rythme d'une monoplace seule en piste, sans l'effet du DRS ou de la perte d'appui derrière une autre voiture.
  
## Auteurs
Paul SERRA  
Naïs VIGROUX   
Axel WALRAET-TRIOLET
