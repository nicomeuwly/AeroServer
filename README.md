# AeroServer

Serveur Minecraft 1.21.1 moddé avec Neoforge.
Ce projet est basé sur le mod `Create` et l'addon `Create Aeronautics`, plus plusieurs autres mods en lien de près ou de loin.

## Contenu

- `manifest.json` : liste des mods CurseForge avec `projectID` et `fileID`
- `download_mods_from_manifest.py` : script qui télécharge automatiquement les mods à partir du manifest
- `requirements.txt` : dépendances Python nécessaires
- `.env` : variables d'environnement locales (clé CurseForge)
- `run.bat` / `run.sh` : scripts de démarrage du serveur

## Installation

1. Installer Python 3.x
2. Créer et activer un environnement virtuel Python :
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Installer les dépendances :
   ```powershell
   python -m pip install -r requirements.txt
   ```
4. Ouvrir `.env` et remplacer `VOTRE_CLE_API` par votre clé API CurseForge :
   ```env
   CURSEFORGE_API_KEY=VOTRE_CLE_API
   ```

## Télécharger les mods

Le script utilise `manifest.json` pour récupérer les mods listés sur CurseForge.

```powershell
python download_mods_from_manifest.py
```

Le script compare automatiquement les versions des mods existants :
- Si un mod existe déjà avec une version identique ou supérieure, il est ignoré.
- Si la version du manifest est plus récente, le mod est mis à jour.
- Utilise `--force` pour forcer le re-téléchargement de tous les mods :

```powershell
python download_mods_from_manifest.py --force
```

## Démarrer le serveur

- Sous Windows : `run.bat`
- Sous Linux/macOS : `run.sh`

## Fichiers ignorés par Git

Le fichier `.gitignore` exclut les fichiers générés par l'installateur et l'exécution du serveur, notamment :

- `libraries/`
- `mods/`
- `logs/`
- `world/`
- fichiers de configuration locaux générés (`eula.txt`, `usercache.json`, `ops.json`, etc.)

## Remarques

- `manifest.json` est le fichier principal pour l'installation automatique des mods.
- Si tu veux recréer le serveur depuis zéro, importe `manifest.json` dans un launcher CurseForge/Prism Launcher ou utilise le script Python.
