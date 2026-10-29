$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$pythonTP5 = Join-Path (Get-Location) '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonTP5)) { python -m venv .venv }
& $pythonTP5 -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Installation impossible' }
$env:MLFLOW_TRACKING_URI = 'http://127.0.0.1:5000'
# Autorisé uniquement pour les modèles produits dans ce projet de confiance.
$env:MLFLOW_ALLOW_PICKLE_DESERIALIZATION = 'true'
$env:PYTHONIOENCODING = 'utf-8'
New-Item -ItemType Directory -Force data,models,reports,reports\preuves | Out-Null
function Invoke-TP5([string[]]$ArgumentsTP5) {
    & $pythonTP5 @ArgumentsTP5
    if ($LASTEXITCODE -ne 0) { throw "Échec : $ArgumentsTP5" }
}
try {
    Invoke-TP5 -ArgumentsTP5 @('donnees.py')
    Invoke-TP5 -ArgumentsTP5 @('scripts/services.py','tracking')
    Invoke-TP5 -ArgumentsTP5 @('src/automl_deploy.py')
    Invoke-TP5 -ArgumentsTP5 @('src/modele_manuel.py')
    Invoke-TP5 -ArgumentsTP5 @('src/promouvoir.py','fraude-automl')
    Invoke-TP5 -ArgumentsTP5 @('src/promouvoir.py','fraude-manuel')
    Invoke-TP5 -ArgumentsTP5 @('scripts/services.py','automl')
    Invoke-TP5 -ArgumentsTP5 @('scripts/services.py','manuel')
    Invoke-TP5 -ArgumentsTP5 @('src/client.py','8100','--repetition','1')
    Invoke-TP5 -ArgumentsTP5 @('src/client.py','8101','--repetition','1')
    Invoke-TP5 -ArgumentsTP5 @('src/client.py','8100','--repetition','2')
    Invoke-TP5 -ArgumentsTP5 @('src/client.py','8101','--repetition','2')
    Invoke-TP5 -ArgumentsTP5 @('src/verifier_services.py')
    Invoke-TP5 -ArgumentsTP5 @('scripts/produire_resultats.py')
} finally {
    & $pythonTP5 scripts/services.py stop-all
}
