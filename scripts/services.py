"""Gestion des seuls processus MLflow de ce projet (sans fenêtres de terminal)."""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import psutil
import requests

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
PIDFILE = REPORTS / "processes.json"


def read_state():
    return json.loads(PIDFILE.read_text(encoding="utf-8")) if PIDFILE.exists() else {}


def start(key, port, arguments, health):
    state = read_state()
    if key in state and psutil.pid_exists(state[key]["pid"]):
        raise RuntimeError(f"{key} possède déjà un processus enregistré ; vérifier avant de relancer")
    try:
        requests.get(f"http://127.0.0.1:{port}", timeout=1)
    except requests.ConnectionError:
        pass
    else:
        raise RuntimeError(f"Port {port} déjà occupé : aucun processus tiers ne sera arrêté")
    env = {**os.environ, "MLFLOW_TRACKING_URI": "http://127.0.0.1:5000", "PYTHONIOENCODING": "utf-8",
           "MLFLOW_ALLOW_PICKLE_DESERIALIZATION": "true", "MLFLOW_DISABLE_AGENT_HINT": "1",
           "PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", ""),
           "VIRTUAL_ENV": str(Path(sys.executable).parent.parent)}
    log = REPORTS / f"{key}.log"
    with log.open("w", encoding="utf-8") as stream:
        process = subprocess.Popen([sys.executable, "-m", "mlflow", *arguments], cwd=ROOT, env=env,
                                   stdout=stream, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    state[key] = {"pid": process.pid, "create_time": psutil.Process(process.pid).create_time(),
                  "port": port, "command": ["python", "-m", "mlflow", *arguments], "log": str(log.relative_to(ROOT))}
    PIDFILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    for _ in range(90):
        if process.poll() is not None:
            raise RuntimeError(log.read_text(encoding="utf-8", errors="replace")[-12000:])
        try:
            r = requests.get(f"http://127.0.0.1:{port}{health}", timeout=2)
            if r.status_code == 200:
                print(f"{key} : PID {process.pid}, port {port}, santé HTTP 200", flush=True)
                return
        except requests.RequestException:
            pass
        time.sleep(1)
    raise TimeoutError(f"{key} pas prêt ; consulter {log}")


def stop(keys):
    state = read_state()
    for key in keys:
        record = state.get(key)
        if not record:
            continue
        try:
            parent = psutil.Process(record["pid"])
            if abs(parent.create_time() - record["create_time"]) > 0.01:
                raise RuntimeError("PID réutilisé : arrêt refusé")
            processes = parent.children(recursive=True) + [parent]
            for process in reversed(processes):
                try:
                    process.terminate()
                except psutil.NoSuchProcess:
                    pass
            _, alive = psutil.wait_procs(processes, timeout=5)
            for process in alive:
                process.kill()
            print(f"{key} : arrêté")
        except psutil.NoSuchProcess:
            pass
        state.pop(key, None)
    PIDFILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["tracking", "automl", "manuel", "stop-serving", "stop-all", "status"])
    action = parser.parse_args().action
    REPORTS.mkdir(exist_ok=True)
    if action == "tracking":
        start("server", 5000, ["server", "--host", "127.0.0.1", "--port", "5000", "--backend-store-uri", "sqlite:///mlflow.db", "--artifacts-destination", str(ROOT / "mlartifacts"), "--workers", "1"], "/health")
    elif action in {"automl", "manuel"}:
        port = 8100 if action == "automl" else 8101
        start(f"serve_{action}", port, ["models", "serve", "-m", f"models:/fraude-{action}@production", "--host", "127.0.0.1", "-p", str(port), "--env-manager", "local", "--workers", "1"], "/health")
    elif action == "stop-serving":
        stop(["serve_automl", "serve_manuel"])
    elif action == "stop-all":
        stop(["serve_automl", "serve_manuel", "server"])
    else:
        print(json.dumps(read_state(), indent=2))


if __name__ == "__main__":
    main()
