#!/bin/bash
set -euo pipefail

SERVER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SERVER_DIR"

log() { echo "[AeroServer] $*"; }

# ---------------------------------------------------------------------------
# Étape 1 — Installation (premier démarrage uniquement)
# run.sh est généré par l'installateur NeoForge ; son absence indique un
# premier démarrage.
# ---------------------------------------------------------------------------
if [ ! -f "run.sh" ]; then
    log "Premier démarrage détecté — installation en cours..."

    # Créer un environnement virtuel Python si nécessaire
    if [ ! -f ".venv/bin/python3" ]; then
        log "Création de l'environnement virtuel Python..."
        python3 -m venv .venv
        .venv/bin/pip install -q -r requirements.txt
    fi

    # Télécharger les mods et l'installateur NeoForge
    log "Téléchargement des mods..."
    .venv/bin/python3 download_mods_from_manifest.py

    # Lancer l'installateur NeoForge
    INSTALLER=$(ls neoforge-*-installer.jar 2>/dev/null | head -1)
    if [ -z "$INSTALLER" ]; then
        log "ERREUR : installateur NeoForge introuvable." >&2
        exit 1
    fi
    log "Installation de NeoForge ($INSTALLER)..."
    java -jar "$INSTALLER" --installServer
    log "Installation NeoForge terminée."
fi

# ---------------------------------------------------------------------------
# Étape 2 — Acceptation de l'EULA
# Si eula.txt n'existe pas ou contient eula=false, on lance le serveur une
# première fois pour le générer, puis on accepte automatiquement.
# ---------------------------------------------------------------------------
if ! grep -q "^eula=true" eula.txt 2>/dev/null; then
    log "Génération de eula.txt (premier lancement du serveur)..."
    bash run.sh || true

    if grep -q "^eula=false" eula.txt 2>/dev/null; then
        sed -i 's/^eula=false/eula=true/' eula.txt
    else
        printf "eula=true\n" >> eula.txt
    fi
    log "EULA acceptée."
fi

# ---------------------------------------------------------------------------
# Lancement du serveur
# ---------------------------------------------------------------------------
log "Démarrage du serveur..."
exec bash run.sh
