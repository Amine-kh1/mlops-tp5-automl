# TP05 - Créer et déployer un modèle AutoML

Amine KHABOT - 5IASD - Groupe G1 - EMSI, 2026-2027.

Le projet exécute la chaîne FLAML (90 secondes) -> registre MLflow -> alias
`production` -> services HTTP (8100 et 8101) -> client externe -> comparaison.
La référence est la forêt aléatoire du TP2 : 500 arbres, profondeur 16, graine 42.

## Installation et exécution (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python donnees.py
$env:MLFLOW_TRACKING_URI = 'http://127.0.0.1:5000'
$env:MLFLOW_ALLOW_PICKLE_DESERIALIZATION = 'true'
python scripts/services.py tracking
python src/automl_deploy.py
python src/modele_manuel.py
python src/promouvoir.py fraude-automl
python src/promouvoir.py fraude-manuel
python scripts/services.py automl
python scripts/services.py manuel
python src/client.py 8100 --repetition 1
python src/client.py 8101 --repetition 1
python src/client.py 8100 --repetition 2
python src/client.py 8101 --repetition 2
python src/verifier_services.py
python scripts/produire_resultats.py
python scripts/services.py stop-all
```

Ou lancer `& .\scripts\tout_executer.ps1` pour automatiser ces étapes.
Le serveur de suivi est accessible sur <http://127.0.0.1:5000> pendant son exécution.
Les processus sont lancés en arrière-plan, avec leurs journaux dans `reports/`.
La commande d'arrêt vérifie l'identité des processus créés par ce projet.

## Protocole

- Générateur original repris du TP04 : 5 000 transactions synthétiques, graine 7.
- Séparation identique : 75 % apprentissage / 25 % test, graine 42, sans stratification,
  conformément à l'énoncé. Le test est exclu de la recherche FLAML.
- FLAML dispose de 90 secondes et de deux threads. Le modèle sous-jacent est exporté.
- La référence manuelle utilise exactement les réglages 500/16.
- AutoML est enregistré en `cloudpickle`, manuel en `skops`.
- Les prédictions sont comparées avant/après export, après rechargement MLflow,
  puis sur les 1 250 transactions de test envoyées aux vrais services HTTP.
- Chaque mesure : une transaction témoin, 10 échauffements, 200 appels séquentiels
  `requests.post` sans Session persistante. Deux répétitions par service, dans l'ordre
  8100 / 8101 / 8100 / 8101. Chaque réponse est contrôlée.
- p95 : `statistics.quantiles(latences, n=20, method='exclusive')[18]`.
- Taille : copies joblib sans compression, en Mio (1 Mio = 1 048 576 octets).

Les latences incluent JSON, validation de signature, HTTP local et calcul.
Elles décrivent une requête unitaire répétée sur ce poste ; elles ne constituent
pas une charge concurrente ou une mesure réseau cloud.

## Fichiers à consulter

- `reports/tp5_comparaison.md` : comparaison et décision en cinq lignes.
- `reports/rapport_tp5.md` : réponses aux six questions, protocole et références.
- `reports/*_resultats.json`, `latence_*.json`, `verification_http.json` : mesures brutes.
- `reports/preuves/` : vrais fichiers MLmodel et dépendances issus du registre.
- `reports/captures/` : captures d'écran et extraits de journaux réels.
- `requirements-lock.txt` : environnement exact de l'exécution remise.

Les données, modèles binaires, base SQLite, artéfacts MLflow et environnement virtuel
sont exclus de Git. Ils se régénèrent avec les scripts. Une nouvelle exécution crée
de nouvelles versions ; les mesures peuvent varier avec le matériel et les versions.

Le parcours Vertex AI est facultatif et n'a pas été exécuté. L'étude tarifaire du
rapport est documentée et datée ; aucun résultat cloud n'est présenté comme mesuré.

## Régénérer le rapport et préparer la remise

Après l'exécution et la capture des preuves, `python scripts/rapport_pdf.py` produit
le rapport PDF dans `output/pdf/`. `python scripts/livrer.py` prépare l'archive,
le bundle de l'historique Git et un brouillon de courriel avec le rapport joint.
Ces scripts n'envoient aucun message et ne créent aucune ressource cloud.

Le rapport remis est nommé `Khabot_Amine_5IASD_G1.pdf`. Il contient les six réponses,
la comparaison, la décision et les captures. Les pages de preuves en HTML affichent
les sorties réelles pour faciliter leur lecture ; elles ne simulent pas des fenêtres
de terminal.
