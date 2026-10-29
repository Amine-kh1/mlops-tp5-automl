"""Bloc B : RandomForest du TP2, 500 arbres, profondeur maximale 16."""
import time
from sklearn.ensemble import RandomForestClassifier
from common import dataset, save_and_register


def main():
    Xtr, Xte, ytr, yte = dataset()
    start = time.perf_counter()
    model = RandomForestClassifier(n_estimators=500, max_depth=16, random_state=42).fit(Xtr, ytr)
    duration = time.perf_counter() - start
    save_and_register(model, Xte, yte, key="manuel", duration=duration,
                      params={"outil": "scikit-learn", "n_estimators": 500, "max_depth": 16, "random_state": 42},
                      run_name="manuel-rf-500-16", serialization="skops")


if __name__ == "__main__":
    main()
