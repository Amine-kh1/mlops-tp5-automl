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
