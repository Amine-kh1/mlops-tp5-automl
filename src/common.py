"""Utilitaires communs : mêmes données, même séparation, preuves traçables."""
import hashlib
import importlib.metadata
import json
import os
import platform
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from mlflow import MlflowClient
from sklearn.inspection import permutation_importance
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
FEATURES = ["montant", "anciennete", "freq_24h", "nuit"]


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def dataset():
    path = ROOT / "data/transactions.csv"
    df = pd.read_csv(path)
    X, y = df[FEATURES], df["fraude"]
    split = train_test_split(X, y, test_size=0.25, random_state=42)
    metadata = {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "rows": len(df), "frauds": int(y.sum()), "train_rows": len(split[0]),
        "test_rows": len(split[1]), "test_frauds": int(split[3].sum()),
        "features": FEATURES, "test_size": 0.25, "random_state": 42,
        "stratify": None,
    }
    REPORTS.mkdir(exist_ok=True)
    write_json(REPORTS / "dataset.json", metadata)
    return split


def versions():
    packages = ["flaml", "mlflow", "scikit-learn", "numpy", "pandas", "lightgbm", "xgboost", "skops", "cloudpickle"]
    return {"python": platform.python_version(), **{p: importlib.metadata.version(p) for p in packages}}


def save_and_register(model, Xte, yte, *, key, params, duration, run_name, serialization, extra=None, artifacts=()):
    pred = model.predict(Xte)
    metrics = {"f1": f1_score(yte, pred), "precision": precision_score(yte, pred), "recall": recall_score(yte, pred)}
    (ROOT / "models").mkdir(exist_ok=True)
    local_path = ROOT / f"models/model_{key}.pkl"
    joblib.dump(model, local_path)
    # Importance par permutation : définition commune aux deux familles de modèles.
    importance = permutation_importance(model, Xte, yte, scoring="f1", n_repeats=5, random_state=42, n_jobs=1)
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment("tp5-automl-deploiement")
    req = [f"{p}=={importlib.metadata.version(p)}" for p in ["scikit-learn", "numpy", "pandas", "cloudpickle", "skops"]]
    module = type(model).__module__.split(".")[0]
    if module in {"lightgbm", "xgboost"}:
        req.append(f"{module}=={importlib.metadata.version(module)}")
    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_params(params)
        duration_name = "duree_recherche_s" if key == "automl" else "duree_entrainement_s"
        mlflow.log_metrics({**metrics, duration_name: duration})
        mlflow.set_tags({"dataset_sha256": json.loads((REPORTS / "dataset.json").read_text(encoding="utf-8"))["sha256"], "split_seed": 42})
        for path in artifacts:
            mlflow.log_artifact(str(path))
        kwargs = {"skops_trusted_types": ["sklearn.tree._tree.Tree"]} if serialization == "skops" else {}
        info = mlflow.sklearn.log_model(
            model, name="model", input_example=Xte.head(3),
            registered_model_name=f"fraude-{key}", serialization_format=serialization,
            pip_requirements=req, **kwargs,
        )
        run_id = run.info.run_id
    result = {
        "name": f"fraude-{key}", "version": str(info.registered_model_version),
        "run_id": run_id, "model_uri": info.model_uri,
        "class": type(model).__name__, "module": module, "serialization": serialization,
        **metrics, "duration_s": duration, "size_bytes": local_path.stat().st_size,
        "confusion_matrix": confusion_matrix(yte, pred).tolist(),
        "permutation_importance": dict(zip(FEATURES, importance.importances_mean.tolist())),
        "permutation_std": dict(zip(FEATURES, importance.importances_std.tolist())),
        "params": params, "versions": versions(), **(extra or {}),
    }
    write_json(REPORTS / f"{key}_resultats.json", result)
    target = REPORTS / "preuves" / key
    target.mkdir(parents=True, exist_ok=True)
    artifact_dir = Path(mlflow.artifacts.download_artifacts(artifact_uri=info.model_uri))
    for name in ["MLmodel", "requirements.txt", "python_env.yaml", "input_example.json", "serving_input_example.json"]:
        source = artifact_dir / name
        if source.exists():
            (target / name).write_bytes(source.read_bytes())
    # Vérifier le rechargement du vrai paquet MLflow, pas seulement la copie joblib.
    restored = mlflow.sklearn.load_model(info.model_uri)
    assert np.array_equal(pred, restored.predict(Xte)), "Prédictions modifiées après sérialisation"
    result["packaged_predictions_identical"] = True
    write_json(REPORTS / f"{key}_resultats.json", result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result
