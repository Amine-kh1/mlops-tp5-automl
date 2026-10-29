"""Rapport PDF reproductible à partir des mesures et des captures réelles."""
import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "reports"
OUT = ROOT / "output/pdf/Khabot_Amine_5IASD_G1.pdf"
NAVY = colors.HexColor("#12243b")
TEAL = colors.HexColor("#087f8c")
GRAY = colors.HexColor("#526277")
LIGHT = colors.HexColor("#edf3f7")
WIDTH = A4[0] - 92


def read(name):
    return json.loads((R / name).read_text(encoding="utf-8"))


def main():
    pdfmetrics.registerFont(TTFont("ArialTP5", "C:/Windows/Fonts/arial.ttf"))
    pdfmetrics.registerFont(TTFont("ArialTP5-Bold", "C:/Windows/Fonts/arialbd.ttf"))
    pdfmetrics.registerFontFamily("ArialTP5", normal="ArialTP5", bold="ArialTP5-Bold", italic="ArialTP5", boldItalic="ArialTP5-Bold")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("TextTP5", fontName="ArialTP5", fontSize=10, leading=14.3, textColor=NAVY, spaceAfter=9))
    styles.add(ParagraphStyle("SmallTP5", parent=styles["TextTP5"], fontSize=8.2, leading=11, textColor=GRAY, spaceAfter=6))
    styles.add(ParagraphStyle("TitleTP5", parent=styles["TextTP5"], fontName="ArialTP5-Bold", fontSize=28, leading=33, spaceAfter=17))
    styles.add(ParagraphStyle("HeadingTP5", parent=styles["TextTP5"], fontName="ArialTP5-Bold", fontSize=19, leading=24, spaceBefore=3, spaceAfter=13))
    styles.add(ParagraphStyle("SubTP5", parent=styles["TextTP5"], fontName="ArialTP5-Bold", fontSize=11.5, leading=16, textColor=TEAL, spaceBefore=7, spaceAfter=7))
    styles.add(ParagraphStyle("CellTP5", parent=styles["TextTP5"], fontSize=8.4, leading=11, spaceAfter=0))
    story = []
    md = []

    def p(text, style="TextTP5"):
        story.append(Paragraph(text, styles[style]))

    def paragraph(text):
        p(escape(text))

    def h(text):
        p(escape(text), "HeadingTP5")

    def sub(text):
        p(escape(text), "SubTP5")

    def table(rows, widths=None, header=True):
        cells = [[Paragraph(escape(str(c)), styles["CellTP5"]) for c in row] for row in rows]
        t = Table(cells, colWidths=widths, hAlign="LEFT", repeatRows=1 if header else 0)
        commands = [("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0),(-1,-1),8),
                    ("RIGHTPADDING", (0,0),(-1,-1),8), ("TOPPADDING", (0,0),(-1,-1),7),
                    ("BOTTOMPADDING",(0,0),(-1,-1),7), ("LINEBELOW",(0,0),(-1,0),1,TEAL),
                    ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,LIGHT])]
        if header:
            commands += [("BACKGROUND",(0,0),(-1,0),LIGHT)]
        t.setStyle(TableStyle(commands))
        story.append(t)
        story.append(Spacer(1,10))

    def image(name, max_height):
        path = R / name
        img = Image(str(path))
        ratio = min(WIDTH / img.imageWidth, max_height / img.imageHeight)
        img.drawWidth, img.drawHeight = img.imageWidth * ratio, img.imageHeight * ratio
        img.hAlign = "LEFT"
        story.append(img)
        story.append(Spacer(1,9))

    a, m = read("automl_resultats.json"), read("manuel_resultats.json")
    data, env = read("dataset.json"), read("environnement.json")
    checks = read("verification_http.json")
    lat = [read(f"latence_{port}_{rep}.json") for rep in [1,2] for port in [8100,8101]]
    decision = [s for s in (R / "decision.txt").read_text(encoding="utf-8").splitlines() if s.strip()]
    choice = (R / "choix.txt").read_text(encoding="utf-8").strip()
    repo = read("github.json")["html_url"]
    questions = [
        ("Question 1 - Le choix de production",
         f"Je retiens {choice}. Le F1 vaut {a['f1']:.4f} pour AutoML et {m['f1']:.4f} pour la forêt manuelle ; les rappels valent respectivement {a['recall']:.4f} et {m['recall']:.4f}. "
         "En fraude, le coût des faux négatifs et le nombre de vérifications humaines importent autant que le F1. La décision tient aussi compte du p95 HTTP, de la taille du modèle, de la traçabilité des réglages et de la facilité de retour arrière. "
         "Ces résultats reposent sur un seul jeu de test synthétique : ils ne prouvent pas une supériorité statistique sur des transactions futures. Avant une vraie mise en production, il faut confirmer le seuil métier, tester hors période et surveiller dérive et erreurs."),
        ("Question 2 - Le coût d'un point de terminaison cloud",
         "Page officielle Google Cloud consultée le 29/10/2026 [1]. Pour AutoML tabulaire, la tarification de l'inférence renvoie à celle des modèles personnalisés. Hypothèse explicite : région Iowa (us-central1), une machine n1-standard-2, tarif à la demande de 0,1095 USD par heure, sans GPU ni remise, une réplique conservée 24 h/24. "
         "Pour 30 jours : 1 × 24 × 30 × 0,1095 = 78,84 USD. Pour une convention de 730 h : 79,94 USD. Ce calcul porte sur le calcul de service seul ; stockage, transferts et taxes éventuels sont exclus. Même sans requête, la réplique prête à servir reste facturée. Il faut retirer le modèle déployé pour arrêter ce poste de coût. Aucune ressource cloud n'a été créée pour ce TP."),
        ("Question 3 - Latence locale et latence cloud",
         f"Les médianes AutoML locales sont {lat[0]['median_ms']:.3f} et {lat[2]['median_ms']:.3f} ms ; celles du modèle manuel sont {lat[1]['median_ms']:.3f} et {lat[3]['median_ms']:.3f} ms. "
         "Ces mesures traversent la boucle locale 127.0.0.1. Un appel cloud ajoute généralement le trajet réseau aller-retour, TLS, l'authentification, les passerelles et une éventuelle file d'attente ; un démarrage ou une montée en charge peut aussi ajouter du délai. "
         "Un serveur distant plus puissant peut réduire le temps de calcul, sans garantir une meilleure latence totale. Aucune latence cloud n'a été mesurée : l'écart cloud/local n'est donc pas chiffré."),
        ("Question 4 - Le moteur change de version",
         "Un nouvel entraînement avec le même budget et la même graine peut sélectionner une autre famille, d'autres hyperparamètres ou un autre prétraitement après une mise à jour du moteur AutoML. Les scores, formats et dépendances peuvent alors évoluer. Cela n'implique pas que tout modèle déjà déployé change immédiatement : il faut distinguer le modèle figé, un réentraînement et une mise à jour du runtime de service. "
         "Je conserve la version exportée, les versions de dépendances, les données et la signature, puis je compare une nouvelle version à des tests de référence. La promotion se fait après validation et avec une version de retour disponible."),
        ("Question 5 - Réversibilité",
         "Je conserve les données, leur schéma, le prétraitement, le découpage, les réglages, les métriques et les dépendances, puis je teste réellement une exécution hors fournisseur. La documentation actuelle permet l'export des modèles AutoML tabulaires de classification/régression vers Cloud Storage et leur service Docker ailleurs [2]. Elle précise que l'explicabilité Vertex n'est pas disponible avec ces modèles exportés. "
         "Il faut donc archiver le modèle et son runtime, vérifier des prédictions de référence et maintenir un contrat HTTP stable. Si un export ou une fonction reste propriétaire, une solution de repli consiste à réentraîner un modèle libre sur les mêmes données. Ici, les objets sous-jacents, le paquet MLflow et les dépendances épinglées rendent cette sortie vérifiable."),
        ("Question 6 - skops ou cloudpickle",
         f"La recherche a retenu {a['class']}. L'énoncé impose cloudpickle pour exporter des familles tierces que skops ne couvre pas nécessairement, alors que la forêt scikit-learn manuelle est enregistrée en skops. "
         "Pickle, joblib et cloudpickle peuvent exécuter du code lors du chargement ; cloudpickle ne garantit pas non plus la compatibilité future des environnements [3]. Skops permet une inspection et une liste de types approuvés, sans dispenser de vérifier la provenance. "
         "Dans ce TP, les fichiers sont produits par nos propres scripts, le registre et les services sont limités à 127.0.0.1, et aucune source de modèle inconnue n'est chargée. L'autorisation MLflow de désérialiser est limitée à ces processus. En production, contrôle d'accès, intégrité des artéfacts et environnement isolé restent nécessaires."),
    ]

    # 1. Présentation et protocole
    p("EMSI  /  DÉPLOIEMENT D'IA  /  2026-2027", "SmallTP5")
    story.append(Spacer(1,20))
    p("TP05<br/>Du modèle AutoML<br/>au service HTTP", "TitleTP5")
    p("Amine KHABOT  ·  5IASD  ·  Groupe G1", "SubTP5")
    paragraph("Exécution et consultation des sources : 29 octobre 2026 (UTC).")
    paragraph("Objectif : comparer un modèle trouvé automatiquement et la référence du TP2 sur la qualité, la latence HTTP, la taille et l'explicabilité, après un déploiement dans le même environnement.")
    table([["Chaîne réalisée", "Résultat vérifié"],
           ["FLAML, budget 90 s", f"{a['class']} ; F1 test {a['f1']:.4f}"],
           ["Référence manuelle", f"RandomForest 500/16 ; F1 test {m['f1']:.4f}"],
           ["Registre et promotion", f"fraude-automl v{a['version']} et fraude-manuel v{m['version']} ; alias production"],
           ["Service et tests", "Ports 8100 / 8101 ; 800 appels mesurés valides ; signature rejetant les colonnes absentes"]], [170,WIDTH-170])
    sub("Données et comparaison équitable")
    paragraph(f"Le générateur original du TP04 produit {data['rows']} lignes, dont {data['frauds']} fraudes ({data['frauds']/data['rows']:.2%}). Les deux modèles partagent les {data['train_rows']} lignes d'apprentissage et les {data['test_rows']} lignes de test ({data['test_frauds']} fraudes), avec test_size=0,25 et random_state=42, sans stratification, comme dans le TP.")
    paragraph("Le test ne participe pas à la recherche FLAML. Les prédictions restent identiques après export, après rechargement du paquet MLflow, puis via HTTP sur l'intégralité du test. Le plan B scikit-learn n'a pas été utilisé. Le parcours cloud facultatif n'a pas été exécuté.")
    publication = read("statut_publication.json") if (R / "statut_publication.json").exists() else {}
    label = "Dépôt public" if publication.get("code_pushed") else "Dépôt public cible"
    p(label+' : <link href="'+repo+'" color="#087f8c">'+repo+'</link>', "SmallTP5")
    if not publication.get("code_pushed", False):
        p("Statut de remise : dépôt créé ; publication du code en attente d'autorisation spécifique. Rapport et projet finalisés localement. Courriel préparé, non envoyé.", "SmallTP5")
    story.append(PageBreak())

    # 2. Tableau et décision
    h("Comparer et décider")
    shortrows = [["Critère", "Manuel (RF 500/16)", "AutoML (FLAML 90 s)"],
                 ["Famille", m["class"], a["class"]],
                 ["F1 / précision / rappel", f"{m['f1']:.4f} / {m['precision']:.4f} / {m['recall']:.4f}", f"{a['f1']:.4f} / {a['precision']:.4f} / {a['recall']:.4f}"],
                 ["Temps machine", f"{m['duration_s']:.2f} s (entraînement)", f"{a['duration_s']:.2f} s (recherche)"],
                 ["Temps humain estimé", "~2 h (repris du TP04)", "~10 min de préparation"],
                 ["Médiane / p95, essai 1 (ms)", f"{lat[1]['median_ms']:.3f} / {lat[1]['p95_ms']:.3f}", f"{lat[0]['median_ms']:.3f} / {lat[0]['p95_ms']:.3f}"],
                 ["Médiane / p95, essai 2 (ms)", f"{lat[3]['median_ms']:.3f} / {lat[3]['p95_ms']:.3f}", f"{lat[2]['median_ms']:.3f} / {lat[2]['p95_ms']:.3f}"],
                 ["Taille joblib (Mio)", f"{m['size_bytes']/1024**2:.4f}", f"{a['size_bytes']/1024**2:.4f}"],
                 ["Explicabilité", "500 arbres, profondeur <=16 ; permutation", f"{a['params'].get('cfg_n_estimators','?')} arbres, max_leaves={a['params'].get('cfg_max_leaves','?')} ; permutation"],
                 ["Sérialisation MLflow", "skops", "cloudpickle"]]
    table(shortrows,[145,(WIDTH-145)/2,(WIDTH-145)/2])
    p("Mio = 1 048 576 octets. Temps humains : estimations, non chronométrées. Tailles des copies joblib sans compression ; la taille du paquet MLflow complet est différente.", "SmallTP5")
    sub("Décision en cinq lignes")
    for line in decision:
        p(escape(line), "SmallTP5")
    image("comparaison.png", 155)
    story.append(PageBreak())

    # 3. Registre / MLmodel
    h("Capture 1 - Recherche et paquet MLflow")
    paragraph(f"Run automl-90s : famille {a['params']['famille']}, budget 90 secondes, deux threads. Les paramètres cfg_* enregistrent les réglages gagnants. F1 FLAML = F1 export = {a['f1']:.4f}, et toutes les prédictions du test coïncident.")
    p(f"Le fit dure {a['duration_s']:.2f} s avec le réentraînement final. La durée courte du run MLflow correspond à la journalisation, démarrée après l'apprentissage ; la métrique duree_recherche_s mesure le fit complet.", "SmallTP5")
    image("captures/capture1_run.jpg", 270)
    p("1a. Capture de l'interface MLflow du run réellement exécuté.", "SmallTP5")
    image("captures/capture1_parametres.jpg", 270)
    p("1a (suite). Paramètres famille et cfg_* du même run, après défilement de la vue.", "SmallTP5")
    story.append(PageBreak())
    h("Capture 1 - Le modèle exporté")
    paragraph("Le paquet exporté contient le modèle XGBoost sous-jacent, sans la recherche FLAML. Les dépendances comprennent explicitement xgboost. Le fichier MLmodel décrit la sérialisation cloudpickle ainsi que les flavors sklearn et python_function.")
    image("captures/capture1_mlmodel.jpg", 430)
    p("1b. Extrait exact des flavors du fichier MLmodel et requirements.txt du paquet réel. Les fichiers complets sont conservés dans reports/preuves/automl/.", "SmallTP5")
    sub("Contrôles de portabilité")
    paragraph("L'export reproduit les prédictions FLAML sur les 1 250 lignes de test. Le paquet rechargé avec mlflow.sklearn.load_model reproduit ensuite ces prédictions. Le modèle manuel est soumis au même contrôle, avec un paquet skops. Le hash des données et les versions des dépendances sont conservés avec les résultats.")
    story.append(PageBreak())

    # 4. Services
    h("Capture 2 - Promotion et services actifs")
    paragraph("Les deux versions ont reçu l'alias production. Les processus de service ont été lancés en arrière-plan pour conserver leurs journaux. La capture présente ces journaux réels et les contrôles directs /health ; elle constitue l'équivalent documenté des terminaux 3 et 4.")
    image("captures/capture2_services.jpg", 455)
    table([["Modèle", "URI de démarrage", "Service"],
           ["AutoML", "models:/fraude-automl@production", "127.0.0.1:8100"],
           ["Manuel", "models:/fraude-manuel@production", "127.0.0.1:8101"]], [80,290,WIDTH-370])
    paragraph("L'alias est résolu au chargement. Modifier l'alias dans le registre ne recharge pas automatiquement un serveur MLflow déjà actif : il faut redémarrer ou redéployer ce service après une promotion ou un retour arrière. L'URL du client conserve son port et son chemin /invocations.")
    story.append(PageBreak())

    # 5. Client
    h("Capture 3 - Appels client et signature")
    paragraph("La transaction témoin est montant=8500, anciennete=3, freq_24h=9, nuit=1. Chaque essai comporte 10 échauffements puis 200 requêtes unitaires séquentielles, sans Session HTTP persistante. Chaque statut et chaque réponse sont contrôlés ; le p95 utilise la méthode exclusive de statistics.quantiles.")
    image("captures/capture3_client.jpg", 450)
    sub("Contrôle supplémentaire de bout en bout")
    paragraph(f"Un batch de {data['test_rows']} transactions de test envoyé à chaque service reproduit exactement le F1 local : {checks['automl']['http_f1']:.4f} sur 8100 et {checks['manuel']['http_f1']:.4f} sur 8101. Les deux services renvoient HTTP 400 pour une requête avec montant seul et citent anciennete, freq_24h et nuit parmi les colonnes absentes.")
    paragraph("La latence observée inclut transport HTTP local, décodage JSON, validation de signature et prédiction. La transaction unique répétée ne représente ni un trafic concurrent, ni toutes les transactions possibles ; les deux répétitions restent présentées séparément.")
    story.append(PageBreak())

    # 6 et 7. Réponses
    for page_no, subset in enumerate([questions[:3],questions[3:]], start=1):
        h(f"Réponses aux questions ({page_no}/2)")
        for title, text in subset:
            sub(title)
            paragraph(text)
            md += ["## " + title, "", text, ""]
        story.append(PageBreak())

    # 8. Traçabilité et sources
    h("Reproductibilité et traçabilité")
    paragraph(f"Environnement : {env['os']}, Python {env['python']}, {env['physical_cpus']} cœurs physiques / {env['logical_cpus']} processeurs logiques, {env['ram_gib']} Gio de RAM. FLAML utilise n_jobs=2. Les dépendances exactes sont conservées dans requirements-lock.txt ; pip check ne signale aucun conflit.")
    table([["Élément", "Identifiant ou preuve"],
           ["Run AutoML", a["run_id"]], ["Run manuel",m["run_id"]],
           ["SHA-256 du CSV",data["sha256"]],
           ["Preuves", "reports/*_resultats.json ; latence_*.json ; verification_http.json ; preuves/ ; captures/"],
           ["Historique Git", "Au moins cinq commits ; données, modèles, base et environnement exclus de Git"]],[110,WIDTH-110])
    paragraph("La commande scripts/tout_executer.ps1 reconstruit la chaîne. Les services ont été arrêtés après les mesures et les captures. Le registre et les artéfacts restent disponibles localement ; les scripts permettent de les recréer. Les graphiques et pages de preuves sont calculés à partir des fichiers JSON et journaux réels, sans valeur simulée.")
    sub("Sources officielles, consultées le 29/10/2026")
    sources = [
        ("[1] Google Cloud - Vertex AI / Gemini platform, tarification AutoML tabulaire et inférence N1", "https://cloud.google.com/vertex-ai/pricing"),
        ("[2] Google Cloud - Export AutoML tabular models", "https://docs.cloud.google.com/gemini-enterprise-agent-platform/machine-learning/export/export-model-tabular"),
        ("[3] scikit-learn - Model persistence", "https://scikit-learn.org/stable/model_persistence.html"),
        ("[4] MLflow - Model Registry Workflows", "https://mlflow.org/docs/latest/ml/model-registry/workflow"),
        ("[5] MLflow - sklearn, formats et types approuvés", "https://www.mlflow.org/docs/latest/api_reference/_modules/mlflow/sklearn.html"),
    ]
    for label,url in sources:
        p(escape(label)+'<br/><link href="'+url+'" color="#087f8c">'+escape(url)+'</link>', "SmallTP5")
        md += [f"- {label} : {url}"]
    p("Note de lecture : la page Google Cloud consultée affiche le nom Gemini platform ; l'URL historique Vertex AI de l'énoncé reste le point d'accès utilisé. L'estimation est un exemple tarifaire documenté, sans déploiement cloud.", "SmallTP5")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(OUT), pagesize=A4, rightMargin=46, leftMargin=46,
                            topMargin=46, bottomMargin=47, title="TP05 - AutoML : créer et déployer un modèle",
                            author="Amine KHABOT", subject="5IASD - Groupe G1 - Déploiement d'IA")

    def chrome(canvas, document):
        canvas.setStrokeColor(TEAL)
        canvas.setLineWidth(2)
        canvas.line(46,A4[1]-29,A4[0]-46,A4[1]-29)
        canvas.setFont("ArialTP5",8)
        canvas.setFillColor(GRAY)
        canvas.drawString(46,27,"Amine KHABOT  |  5IASD G1  |  TP05  |  29/10/2026")
        canvas.drawRightString(A4[0]-46,27,str(document.page))

    doc.build(story,onFirstPage=chrome,onLaterPages=chrome)
    report_md = "# TP05 - Créer et déployer un modèle AutoML\n\nAmine KHABOT - 5IASD - G1 - 29/10/2026 (UTC)\n\n"
    report_md += f"Dépôt : {repo}\n\n" + (R / "tp5_comparaison.md").read_text(encoding="utf-8") + "\n\n"
    report_md += "\n".join(md) + "\n\n"
    report_md += "Captures : captures/capture1_run.jpg, capture1_mlmodel.jpg, capture2_services.jpg, capture3_client.jpg. Les captures 1b, 2 et 3 présentent des journaux/fichiers réels dans une mise en page de lecture, et non des fenêtres de terminal.\n"
    (R / "rapport_tp5.md").write_text(report_md,encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
