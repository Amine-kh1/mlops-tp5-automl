"""Préparer une archive de remise et un brouillon .eml, sans aucun envoi."""
import json
import subprocess
import zipfile
from email.message import EmailMessage
from email.policy import SMTP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "livrables"


def main():
    DEST.mkdir(exist_ok=True)
    pdf = ROOT / "output/pdf/Khabot_Amine_5IASD_G1.pdf"
    if not pdf.is_file():
        raise FileNotFoundError("Produire et vérifier le rapport PDF avant de préparer la remise.")
    repo = json.loads((ROOT / "reports/github.json").read_text(encoding="utf-8"))["html_url"]
    publication = json.loads((ROOT / "reports/statut_publication.json").read_text(encoding="utf-8"))
    statut = "Code publié sur GitHub." if publication.get("code_pushed") else "Dépôt créé ; publication du code en attente."
    message = EmailMessage(policy=SMTP)
    message["To"] = "h.naciri@emsi.ma"
    message["From"] = "amine.khabot@gmail.com"
    message["Subject"] = "Khabot Amine_5IASD_G1"
    message["X-Unsent"] = "1"
    message.set_content(
        "Bonjour Madame,\n\n"
        "Veuillez trouver ci-joint mon rapport du TP05 : créer et déployer un modèle AutoML.\n"
        f"Le dépôt GitHub public contenant le code et les mesures est disponible ici :\n{repo}\n\n"
        "Cordialement,\nAmine KHABOT\n5IASD - Groupe G1\n"
    )
    message.add_attachment(pdf.read_bytes(), maintype="application", subtype="pdf", filename=pdf.name)
    draft = DEST / "Remise_TP05_Khabot_Amine_5IASD_G1.eml"
    draft.write_bytes(bytes(message))
    bundle = DEST / "mlops-tp5-automl.bundle"
    subprocess.run(["git", "bundle", "create", str(bundle), "--all"], cwd=ROOT, check=True)
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    archive = DEST / "TP05_Khabot_Amine_5IASD_G1.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in tracked:
            if rel:
                z.write(ROOT / rel, "projet/" + rel)
        z.write(pdf, pdf.name)
        z.write(bundle, bundle.name)
        z.writestr("LIRE_AVANT_REMISE.txt",
            f"Rapport : {pdf.name}\nDépôt public cible : {repo}\n"
            f"{statut}\n"
            "Le code et les preuves sont dans projet/ ; l'historique Git est dans le bundle.\n"
            "Le courriel .eml fourni séparément est un brouillon local avec le rapport joint.\n"
            "Aucun e-mail n'a été envoyé automatiquement.\n"
            "Parcours cloud facultatif non exécuté ; aucun coût cloud engagé.\n")
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert pdf.name in z.namelist()
    print(f"Archive vérifiée : {archive}")
    print(f"Brouillon local avec pièce jointe (non envoyé) : {draft}")


if __name__ == "__main__":
    main()
