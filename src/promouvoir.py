"""Bloc C : attribuer l'alias production à la dernière version prête."""
import argparse
import mlflow
from mlflow import MlflowClient
from common import REPORTS, TRACKING_URI, write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("nom", choices=["fraude-automl", "fraude-manuel"])
    args = parser.parse_args()
    mlflow.set_tracking_uri(TRACKING_URI)
    client = MlflowClient()
    versions = [v for v in client.search_model_versions(f"name='{args.nom}'") if v.status == "READY"]
    if not versions:
        raise RuntimeError(f"Aucune version prête : {args.nom}")
    latest = max(versions, key=lambda v: int(v.version))
    client.set_registered_model_alias(args.nom, "production", latest.version)
    actual = client.get_model_version_by_alias(args.nom, "production")
    assert actual.version == latest.version
    write_json(REPORTS / f"alias_{args.nom}.json", {"name": args.nom, "alias": "production", "version": actual.version, "run_id": actual.run_id})
    print(f"{args.nom} : version {actual.version} promue (alias production)")


if __name__ == "__main__":
    main()
