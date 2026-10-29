# TP05 - Créer et déployer un modèle AutoML

Amine KHABOT - 5IASD - G1 - 29/10/2026 (UTC)

Dépôt : https://github.com/Amine-kh1/mlops-tp5-automl

# Modèle manuel ou modèle AutoML ? (TP05)

Mesures réellement exécutées, 29/10/2026 (UTC). Unités : ms et Mio (1 048 576 octets).

| Critère | Manuel (RF 500/16) | AutoML (FLAML 90 s) |
|---|---|---|
| Famille de modèle | RandomForestClassifier | XGBClassifier |
| F1 sur le même test | 0.8669 | 0.8614 |
| Précision | 0.8837 | 0.8647 |
| Rappel fraude | 0.8507 | 0.8582 |
| Recherche / entraînement machine | 2.38 s (entraînement seul) | 92.17 s (budget 90 s) |
| Temps humain (estimation) | ~2 h (estimation reprise du TP04) | ~10 min (estimation de préparation, non chronométrée) |
| Médiane, mesure 1 (ms) | 79.084 | 30.473 |
| p95, mesure 1 (ms) | 99.868 | 36.360 |
| Médiane, mesure 2 (ms) | 77.470 | 31.301 |
| p95, mesure 2 (ms) | 87.032 | 35.458 |
| Taille copie joblib (Mio) | 13.3735 | 0.2014 |
| Explicabilité | 500 arbres ; profondeur <=16 ; importance par permutation | 231 arbres ; max_leaves=4 ; importance par permutation |
| Format du paquet MLflow | skops | cloudpickle |
| Version / alias | 1 / production | 1 / production |

Les deux mesures restent distinctes : aucune moyenne de p95 n'est calculée. Chaque essai utilise 10 échauffements et 200 appels séquentiels valides, sans Session HTTP persistante. Le temps humain est une estimation, distincte des temps machine mesurés.

## Décision en cinq lignes

1. Je retiens le modèle AutoML XGBoost pour ce service, en tenant compte de la qualité et des contraintes de déploiement.
2. Le F1 AutoML est 0.8614 contre 0.8669 ; il détecte 115/134 fraudes contre 114, avec 18 faux positifs contre 15.
3. Les médianes AutoML sont 30.473/31.301 ms contre 79.084/77.470 ms ; les p95 confirment le classement sur ces essais.
4. AutoML pèse 0.2014 Mio contre 13.3735 Mio (facteur 66.4) ; les deux modèles exposent une importance des variables.
5. Je conserve l'autre version comme solution de repli et valide le coût des erreurs, les données futures et le retour arrière avant un déploiement réel.


## Question 1 - Le choix de production

Je retiens le modèle AutoML XGBoost. Le F1 vaut 0.8614 pour AutoML et 0.8669 pour la forêt manuelle ; les rappels valent respectivement 0.8582 et 0.8507. En fraude, le coût des faux négatifs et le nombre de vérifications humaines importent autant que le F1. La décision tient aussi compte du p95 HTTP, de la taille du modèle, de la traçabilité des réglages et de la facilité de retour arrière. Ces résultats reposent sur un seul jeu de test synthétique : ils ne prouvent pas une supériorité statistique sur des transactions futures. Avant une vraie mise en production, il faut confirmer le seuil métier, tester hors période et surveiller dérive et erreurs.

## Question 2 - Le coût d'un point de terminaison cloud

Page officielle Google Cloud consultée le 29/10/2026 [1]. Pour AutoML tabulaire, la tarification de l'inférence renvoie à celle des modèles personnalisés. Hypothèse explicite : région Iowa (us-central1), une machine n1-standard-2, tarif à la demande de 0,1095 USD par heure, sans GPU ni remise, une réplique conservée 24 h/24. Pour 30 jours : 1 × 24 × 30 × 0,1095 = 78,84 USD. Pour une convention de 730 h : 79,94 USD. Ce calcul porte sur le calcul de service seul ; stockage, transferts et taxes éventuels sont exclus. Même sans requête, la réplique prête à servir reste facturée. Il faut retirer le modèle déployé pour arrêter ce poste de coût. Aucune ressource cloud n'a été créée pour ce TP.

## Question 3 - Latence locale et latence cloud

Les médianes AutoML locales sont 30.473 et 31.301 ms ; celles du modèle manuel sont 79.084 et 77.470 ms. Ces mesures traversent la boucle locale 127.0.0.1. Un appel cloud ajoute généralement le trajet réseau aller-retour, TLS, l'authentification, les passerelles et une éventuelle file d'attente ; un démarrage ou une montée en charge peut aussi ajouter du délai. Un serveur distant plus puissant peut réduire le temps de calcul, sans garantir une meilleure latence totale. Aucune latence cloud n'a été mesurée : l'écart cloud/local n'est donc pas chiffré.

## Question 4 - Le moteur change de version

Un nouvel entraînement avec le même budget et la même graine peut sélectionner une autre famille, d'autres hyperparamètres ou un autre prétraitement après une mise à jour du moteur AutoML. Les scores, formats et dépendances peuvent alors évoluer. Cela n'implique pas que tout modèle déjà déployé change immédiatement : il faut distinguer le modèle figé, un réentraînement et une mise à jour du runtime de service. Je conserve la version exportée, les versions de dépendances, les données et la signature, puis je compare une nouvelle version à des tests de référence. La promotion se fait après validation et avec une version de retour disponible.

## Question 5 - Réversibilité

Je conserve les données, leur schéma, le prétraitement, le découpage, les réglages, les métriques et les dépendances, puis je teste réellement une exécution hors fournisseur. La documentation actuelle permet l'export des modèles AutoML tabulaires de classification/régression vers Cloud Storage et leur service Docker ailleurs [2]. Elle précise que l'explicabilité Vertex n'est pas disponible avec ces modèles exportés. Il faut donc archiver le modèle et son runtime, vérifier des prédictions de référence et maintenir un contrat HTTP stable. Si un export ou une fonction reste propriétaire, une solution de repli consiste à réentraîner un modèle libre sur les mêmes données. Ici, les objets sous-jacents, le paquet MLflow et les dépendances épinglées rendent cette sortie vérifiable.

## Question 6 - skops ou cloudpickle

La recherche a retenu XGBClassifier. L'énoncé impose cloudpickle pour exporter des familles tierces que skops ne couvre pas nécessairement, alors que la forêt scikit-learn manuelle est enregistrée en skops. Pickle, joblib et cloudpickle peuvent exécuter du code lors du chargement ; cloudpickle ne garantit pas non plus la compatibilité future des environnements [3]. Skops permet une inspection et une liste de types approuvés, sans dispenser de vérifier la provenance. Dans ce TP, les fichiers sont produits par nos propres scripts, le registre et les services sont limités à 127.0.0.1, et aucune source de modèle inconnue n'est chargée. L'autorisation MLflow de désérialiser est limitée à ces processus. En production, contrôle d'accès, intégrité des artéfacts et environnement isolé restent nécessaires.

- [1] Google Cloud - Vertex AI / Gemini platform, tarification AutoML tabulaire et inférence N1 : https://cloud.google.com/vertex-ai/pricing
- [2] Google Cloud - Export AutoML tabular models : https://docs.cloud.google.com/gemini-enterprise-agent-platform/machine-learning/export/export-model-tabular
- [3] scikit-learn - Model persistence : https://scikit-learn.org/stable/model_persistence.html
- [4] MLflow - Model Registry Workflows : https://mlflow.org/docs/latest/ml/model-registry/workflow
- [5] MLflow - sklearn, formats et types approuvés : https://www.mlflow.org/docs/latest/api_reference/_modules/mlflow/sklearn.html

Captures : captures/capture1_run.jpg, capture1_mlmodel.jpg, capture2_services.jpg, capture3_client.jpg. Les captures 1b, 2 et 3 présentent des journaux/fichiers réels dans une mise en page de lecture, et non des fenêtres de terminal.
