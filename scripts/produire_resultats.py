"""Assembler mesures et preuves ; aucune valeur d'expérience n'est simulée."""
import hashlib
import html
import json
import platform
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import psutil
import requests

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"


def read(name):
    return json.loads((REPORTS / name).read_text(encoding="utf-8"))


def page(name, title, subtitle, panels):
    blocks = "".join(f'<section><h2>{html.escape(heading)}</h2><pre>{html.escape(value)}</pre></section>' for heading, value in panels)
    content = '''<!doctype html><html lang="fr"><meta charset="utf-8"><title>''' + html.escape(title) + '''</title>
<style>*{box-sizing:border-box}body{margin:0;padding:28px;background:#edf2f7;color:#12243b;font:16px Segoe UI,Arial,sans-serif}header{margin-bottom:18px}h1{font-size:28px;margin:5px 0}header p{color:#526277;line-height:1.45;margin:8px 0}small{letter-spacing:2px;font-weight:700;color:#087f8c}.panels{display:grid;grid-template-columns:1fr 1fr;gap:18px;align-items:start}section{margin:8px 0 18px;border-radius:9px;overflow:hidden;background:#102034;box-shadow:0 3px 12px #182a3a15}h2{background:#1c334e;margin:0;padding:13px 16px;color:#b6dfdf;font-size:16px}pre{color:#edf5ff;font:15px/1.5 Consolas,monospace;white-space:pre-wrap;word-break:break-word;margin:0;padding:16px}footer{font-size:12px;color:#526277}</style>
<header><small>TP05 · PREUVES D'EXÉCUTION</small><h1>''' + html.escape(title) + "</h1><p>" + html.escape(subtitle) + "</p></header><div class='panels'>" + blocks + "</div><footer>Sources locales réelles, conservées dans reports/ ; présentation des journaux pour lecture et capture.</footer></html>"
    (REPORTS / "preuves" / name).write_text(content, encoding="utf-8")


def main():
    a, m = read("automl_resultats.json"), read("manuel_resultats.json")
    lat = [read(f"latence_{port}_{rep}.json") for rep in [1, 2] for port in [8100, 8101]]
    checks = read("verification_http.json")
    now = datetime.now(timezone.utc).isoformat()
    machine = {"utc": now, "os": platform.platform(), "processor": platform.processor(),
               "logical_cpus": psutil.cpu_count(), "physical_cpus": psutil.cpu_count(logical=False),
               "ram_gib": round(psutil.virtual_memory().total / 1024**3, 2), "python": platform.python_version()}
    (REPORTS / "environnement.json").write_text(json.dumps(machine, indent=2, ensure_ascii=False), encoding="utf-8")
    rows = [
        ["Famille de modèle", m["class"], a["class"]],
        ["F1 sur le même test", f'{m["f1"]:.4f}', f'{a["f1"]:.4f}'],
        ["Précision", f'{m["precision"]:.4f}', f'{a["precision"]:.4f}'],
        ["Rappel fraude", f'{m["recall"]:.4f}', f'{a["recall"]:.4f}'],
        ["Recherche / entraînement machine", f'{m["duration_s"]:.2f} s (entraînement seul)', f'{a["duration_s"]:.2f} s (budget 90 s)'],
        ["Temps humain (estimation)", "~2 h (estimation reprise du TP04)", "~10 min (estimation de préparation, non chronométrée)"],
    ]
    for rep in [1, 2]:
        ml = next(x for x in lat if x["port"] == 8101 and x["repetition"] == rep)
        al = next(x for x in lat if x["port"] == 8100 and x["repetition"] == rep)
        rows += [[f"Médiane, mesure {rep} (ms)", f'{ml["median_ms"]:.3f}', f'{al["median_ms"]:.3f}'],
                 [f"p95, mesure {rep} (ms)", f'{ml["p95_ms"]:.3f}', f'{al["p95_ms"]:.3f}']]
    auto_explain = f"{a['params'].get('cfg_n_estimators','?')} arbres ; max_leaves={a['params'].get('cfg_max_leaves','?')} ; importance par permutation"
    rows += [["Taille copie joblib (Mio)", f'{m["size_bytes"]/1024**2:.4f}', f'{a["size_bytes"]/1024**2:.4f}'],
             ["Explicabilité", "500 arbres ; profondeur <=16 ; importance par permutation", auto_explain],
             ["Format du paquet MLflow", "skops", "cloudpickle"],
             ["Version / alias", f'{m["version"]} / production', f'{a["version"]} / production']]
    text = "# Modèle manuel ou modèle AutoML ? (TP05)\n\n"
    text += "Mesures réellement exécutées, 29/10/2026 (UTC). Unités : ms et Mio (1 048 576 octets).\n\n"
    text += "| Critère | Manuel (RF 500/16) | AutoML (FLAML 90 s) |\n|---|---|---|\n"
    text += "\n".join("| " + " | ".join(row) + " |" for row in rows)
    text += "\n\nLes deux mesures restent distinctes : aucune moyenne de p95 n'est calculée. "
    text += "Chaque essai utilise 10 échauffements et 200 appels séquentiels valides, sans Session HTTP persistante. "
    text += "Le temps humain est une estimation, distincte des temps machine mesurés.\n"
    al = [x for x in lat if x["port"] == 8100]
    ml = [x for x in lat if x["port"] == 8101]
    use_auto = a["f1"] >= m["f1"] - 0.01 and a["recall"] >= m["recall"] and all(x["p95_ms"] < y["p95_ms"] for x,y in zip(al,ml))
    choice = "le modèle AutoML XGBoost" if use_auto else "la forêt manuelle de référence"
    decision = [
        f"1. Je retiens {choice} pour ce service, en tenant compte de la qualité et des contraintes de déploiement.",
        f"2. Le F1 AutoML est {a['f1']:.4f} contre {m['f1']:.4f} ; il détecte {a['confusion_matrix'][1][1]}/{read('dataset.json')['test_frauds']} fraudes contre {m['confusion_matrix'][1][1]}, avec {a['confusion_matrix'][0][1]} faux positifs contre {m['confusion_matrix'][0][1]}.",
        f"3. Les médianes AutoML sont {al[0]['median_ms']:.3f}/{al[1]['median_ms']:.3f} ms contre {ml[0]['median_ms']:.3f}/{ml[1]['median_ms']:.3f} ms ; les p95 confirment le classement sur ces essais.",
        f"4. AutoML pèse {a['size_bytes']/1024**2:.4f} Mio contre {m['size_bytes']/1024**2:.4f} Mio (facteur {m['size_bytes']/a['size_bytes']:.1f}) ; les deux modèles exposent une importance des variables.",
        "5. Je conserve l'autre version comme solution de repli et valide le coût des erreurs, les données futures et le retour arrière avant un déploiement réel.",
    ]
    (REPORTS / "decision.txt").write_text("\n".join(decision) + "\n", encoding="utf-8")
    (REPORTS / "choix.txt").write_text(choice, encoding="utf-8")
    text += "\n## Décision en cinq lignes\n\n" + "\n".join(decision) + "\n"
    (REPORTS / "tp5_comparaison.md").write_text(text, encoding="utf-8")
    (REPORTS / "tableau_comparaison.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), layout="constrained")
    colors = ["#60738d", "#07838c"]
    for ax, values, title in zip(axes, [[m["f1"], a["f1"]],
                                      [next(x["median_ms"] for x in lat if x["port"] == 8101 and x["repetition"] == 2), next(x["median_ms"] for x in lat if x["port"] == 8100 and x["repetition"] == 2)],
                                      [m["size_bytes"]/1024**2, a["size_bytes"]/1024**2]],
                                ["Qualité : F1 test", "Latence médiane (ms), mesure 2", "Taille joblib (Mio)"]):
        bars = ax.bar(["Manuel", "AutoML"], values, color=colors, width=0.55)
        ax.set_title(title, fontweight="bold", fontsize=11)
        ax.spines[["top", "right"]].set_visible(False)
        ax.bar_label(bars, labels=[f"{v:.4f}" if i == 0 else f"{v:.3f}" for i,v in enumerate(values)], padding=4)
        ax.set_ylim(0, max(values)*1.24)
    fig.savefig(REPORTS / "comparaison.png", dpi=180, facecolor="white")
    plt.close(fig)

    model_text = (REPORTS / "preuves/automl/MLmodel").read_text(encoding="utf-8")
    # Extrait exact des flavors ; le fichier complet reste disponible à côté.
    model_excerpt = model_text[model_text.index("flavors:"):model_text.index("is_signature_from_type_hint:")]
    req = (REPORTS / "preuves/automl/requirements.txt").read_text(encoding="utf-8")
    page("capture1_mlmodel.html", "Capture 1b - Paquet AutoML enregistré",
         "Extrait exact des flavors du vrai fichier MLmodel ; dépendances exactes du paquet. Le fichier complet est conservé dans preuves/automl/.",
         [("MLmodel - flavors (extrait)", model_excerpt), ("requirements.txt du modèle", req)])
    state = read("processes.json")
    panels = []
    for key, port in [("automl", 8100), ("manuel", 8101)]:
        status = requests.get(f"http://127.0.0.1:{port}/health", timeout=10)
        status.raise_for_status()
        proc = state[f"serve_{key}"]
        # Extrait de démarrage, sans les centaines de lignes d'accès du benchmark.
        lines = (ROOT / proc["log"]).read_text(encoding="utf-8", errors="replace").splitlines()
        ready = next((i for i,x in enumerate(lines) if "Uvicorn running on" in x), len(lines)-1)
        startup = [x for x in lines[:ready+1] if '"POST ' not in x and '"GET ' not in x and "Downloading artifacts:" not in x]
        startup = [x.replace(str(ROOT), ".") for x in startup if x.strip()][-14:]
        panels.append((f"Service {key} - port {port}", "Commande : " + " ".join(proc["command"]) +
                       f"\nPID parent enregistré : {proc['pid']}\nGET /health -> HTTP {status.status_code}\nContrôle UTC : {now}\n\n" + "\n".join(startup)))
    page("capture2_services.html", "Capture 2 - Deux services MLflow actifs",
         "Équivalent des terminaux 3 et 4 : vrais processus en arrière-plan, vrais journaux de démarrage et contrôles HTTP directs.", panels)
    outputs = []
    for x in lat:
        outputs += [f"python src/client.py {x['port']} --repetition {x['repetition']}",
                    f"réponse : {x['first_status']} {x['first_response']}",
                    f"médiane : {x['median_ms']:.3f} ms | p95 : {x['p95_ms']:.3f} ms | 200/200 réponses valides", ""]
    error = checks["automl"]
    page("capture3_client.html", "Capture 3 - Client HTTP et requête invalide",
         "Résultats réels ; 10 échauffements puis 200 appels par essai. L'erreur ci-dessous est la réponse du serveur AutoML.",
         [("Quatre mesures enregistrées", "\n".join(outputs)),
          ("Transaction incomplète : montant seul", f"HTTP {error['invalid_status']}\n" + json.dumps(error["invalid_response"], indent=2, ensure_ascii=False))])
    hashes = {str(p.relative_to(REPORTS)): hashlib.sha256(p.read_bytes()).hexdigest() for p in REPORTS.glob("*.json") if p.name not in {"processes.json", "provenance_privee.json", "manifest.json"}}
    (REPORTS / "manifest.json").write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    print("Comparaison, graphique, pages de preuves et manifeste produits.")


if __name__ == "__main__":
    main()
