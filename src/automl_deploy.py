"""Bloc A : véritable recherche FLAML, budget de 90 s, export et registre."""
import time
import numpy as np
from flaml import AutoML
from sklearn.metrics import f1_score
from common import ROOT, REPORTS, dataset, save_and_register


def main():
    Xtr, Xte, ytr, yte = dataset()
    automl = AutoML()
    start = time.perf_counter()
    automl.fit(Xtr, ytr, task="classification", metric="f1", time_budget=90,
               seed=42, n_jobs=2, verbose=0,
               log_file_name=str(REPORTS / "flaml_tp5.log"))
    duration = time.perf_counter() - start
    model = automl.model.estimator
    original, exported = automl.predict(Xte), model.predict(Xte)
    assert np.array_equal(original, exported), "Export FLAML non équivalent"
    print(f"famille : {automl.best_estimator} | classe : {type(model).__name__}")
    print(f"F1 FLAML : {f1_score(yte, original):.4f} | F1 export : {f1_score(yte, exported):.4f}")
    params = {"outil": "flaml", "budget_s": 90, "n_jobs": 2, "famille": automl.best_estimator,
              **{f"cfg_{k}": v for k, v in automl.best_config.items()}}
    save_and_register(model, Xte, yte, key="automl", params=params, duration=duration,
                      run_name="automl-90s", serialization="cloudpickle",
                      extra={"f1_flaml": f1_score(yte, original), "export_predictions_identical": True,
                             "best_validation_f1": 1 - automl.best_loss},
                      artifacts=[REPORTS / "flaml_tp5.log"])


if __name__ == "__main__":
    main()
