import numpy as np
import pandas as pd


# ============================================================
# 1. Paramètres
# ============================================================

rng = np.random.default_rng(7)  # Graine fixe pour reproduire les mêmes données
n = 5000                         # Nombre de transactions


# ============================================================
# 2. Génération des données
# ============================================================

# Montant des transactions
# Distribution log-normale : beaucoup de petits montants et quelques montants élevés
montant = np.round(
    rng.lognormal(6.2, 1.1, n),
    2
)

# Ancienneté du client en mois (0 à 119 mois)
anciennete = rng.integers(
    0,
    120,
    n
)

# Nombre de transactions sur 24 heures
freq = rng.poisson(
    3,
    n
) + 1

# Paiement effectué entre 00h et 05h
# 1 = paiement de nuit
# 0 = paiement normal
nuit = rng.binomial(
    1,
    0.18,
    n
)


# ============================================================
# 3. Calcul du score de fraude
# ============================================================

score = (
    2.2 * (np.log10(montant) - 3.0)
    - anciennete / 60
    + (freq - 3) / 3
    + nuit * 1.2
)


# ============================================================
# 4. Génération de l'étiquette de fraude
# ============================================================

# Ajout d'un bruit aléatoire pour rendre les données plus réalistes
fraude = (
    score + rng.normal(0, 0.35, n) > 0.6
).astype(int)


# ============================================================
# 5. Création du DataFrame
# ============================================================

df = pd.DataFrame({
    "montant": montant,
    "anciennete": anciennete,
    "freq_24h": freq,
    "nuit": nuit,
    "fraude": fraude
})


# ============================================================
# 6. Export du fichier CSV
# ============================================================

df.to_csv(
    "data/transactions.csv",
    index=False
)


# ============================================================
# 7. Affichage du résultat
# ============================================================

print(
    "data/transactions.csv écrit :",
    n,
    "lignes,",
    fraude.sum(),
    "fraudes"
)