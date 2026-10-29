"""Contrôles HTTP : signature, batch test identique au test local, statuts."""
import json
import requests
from sklearn.metrics import f1_score
from common import REPORTS, dataset, write_json


def main():
    _, Xte, _, yte = dataset()
    checks = {}
    for port, key in [(8100, "automl"), (8101, "manuel")]:
        health = requests.get(f"http://127.0.0.1:{port}/health", timeout=10)
        health.raise_for_status()
        batch = requests.post(f"http://127.0.0.1:{port}/invocations", json={"dataframe_records": Xte.to_dict(orient="records")}, timeout=30)
        batch.raise_for_status()
        preds = batch.json()["predictions"]
        actual = f1_score(yte, preds)
        expected = json.loads((REPORTS / f"{key}_resultats.json").read_text(encoding="utf-8"))["f1"]
        assert actual == expected, (key, actual, expected)
        bad = requests.post(f"http://127.0.0.1:{port}/invocations", json={"dataframe_records": [{"montant": 8500.0}]}, timeout=10)
        assert bad.status_code == 400, (port, bad.status_code, bad.text)
        assert all(col in bad.text for col in ["anciennete", "freq_24h", "nuit"])
        checks[key] = {"port": port, "health_status": health.status_code, "batch_status": batch.status_code,
                       "batch_size": len(preds), "http_f1": actual, "http_matches_local_f1": True,
                       "invalid_status": bad.status_code, "invalid_response": bad.json()}
        print(f"port {port} : santé HTTP 200 ; batch {len(preds)} lignes F1={actual:.4f} ; requête invalide HTTP {bad.status_code}")
        print(bad.text)
    write_json(REPORTS / "verification_http.json", checks)


if __name__ == "__main__":
    main()
