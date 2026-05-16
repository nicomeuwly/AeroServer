# AeroServer

Serveur Minecraft 1.21.1 moddé avec NeoForge 21.1.228.
Basé sur le mod `Create` et l'addon `Create Aeronautics`, accompagnés de nombreux mods complémentaires.

## Contenu du dépôt

| Fichier | Rôle |
|---|---|
| `manifest.json` | Liste des mods CurseForge (`projectID` + `fileID`) |
| `download_mods_from_manifest.py` | Script de téléchargement automatique des mods |
| `requirements.txt` | Dépendances Python |
| `.env` | Variables d'environnement locales (clé API CurseForge) |
| `run.bat` / `run.sh` | Scripts de démarrage du serveur (générés par l'installateur NeoForge) |
| `start.sh` | Script de démarrage Linux avec setup automatique au premier lancement |
| `stop.sh` | Script d'arrêt propre (sauvegarde du monde avant extinction) |
| `aeroserver.service` | Service systemd pour démarrage/arrêt automatique sur Linux |

---

## Prérequis

- Python 3.10+
- Java 21+
- Une clé API CurseForge — [obtenir une clé](https://console.curseforge.com/)

---

## Installation Windows

1. Créer et activer un environnement virtuel Python :
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Installer les dépendances :
   ```powershell
   pip install -r requirements.txt
   ```

3. Créer le fichier `.env` à la racine du projet :
   ```env
   CURSEFORGE_API_KEY=ta_clé_api
   ```

4. Télécharger les mods et l'installateur NeoForge :
   ```powershell
   python download_mods_from_manifest.py
   ```

5. Lancer l'installateur NeoForge généré :
   ```powershell
   java -jar neoforge-21.1.228-installer.jar --installServer
   ```

6. Démarrer le serveur :
   ```powershell
   .\run.bat
   ```

---

## Script de téléchargement des mods

Le script interroge l'API CurseForge en **une seule requête batch** pour tous les mods, puis les télécharge en **parallèle**.

```powershell
python download_mods_from_manifest.py [options]
```

| Option | Description | Défaut |
|---|---|---|
| `--manifest` | Chemin du fichier manifest | `manifest.json` |
| `--mods-dir` | Dossier de destination des mods | `mods` |
| `--api-key` | Clé API CurseForge (prioritaire sur `.env`) | — |
| `--workers N` | Nombre de téléchargements parallèles | `4` |
| `--force` | Re-télécharger tous les mods même s'ils existent | — |

Comportement automatique :
- Les mods déjà présents sont ignorés.
- Les anciennes versions d'un mod mis à jour sont supprimées.
- Les mods sans URL de téléchargement dans l'API utilisent un fallback CDN.
- Les fichiers sont écrits de façon atomique (via `.tmp`) pour éviter la corruption en cas d'interruption.

---

## Déploiement Linux (serveur dédié)

### 1. Préparer le serveur

```bash
# Créer l'utilisateur dédié
sudo useradd -r -m -d /opt/aeroserver -s /bin/bash minecraft

# Cloner le dépôt
sudo git clone <url-du-dépôt> /opt/aeroserver
sudo chown -R minecraft:minecraft /opt/aeroserver

# Rendre les scripts exécutables
sudo chmod +x /opt/aeroserver/start.sh /opt/aeroserver/stop.sh
```

### 2. Configurer la clé API

```bash
echo "CURSEFORGE_API_KEY=ta_clé_api" | sudo tee /opt/aeroserver/.env
```

### 3. Installer le service systemd

```bash
sudo cp /opt/aeroserver/aeroserver.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now aeroserver
```

Le service gère automatiquement :

- **Premier démarrage** : création du venv Python, téléchargement des mods, installation de NeoForge, acceptation de l'EULA, puis lancement du serveur.
- **Démarrages suivants** : lancement direct via `run.sh`.
- **Boot Linux** : le serveur démarre automatiquement avec le système.
- **Extinction Linux** : la commande `stop` est envoyée au serveur via un pipe, ce qui déclenche la sauvegarde du monde avant l'arrêt. Timeout de 90 secondes avant SIGKILL.

### Commandes utiles

```bash
sudo systemctl start aeroserver     # démarrer
sudo systemctl stop aeroserver      # arrêter proprement (sauvegarde monde)
sudo systemctl restart aeroserver   # redémarrer
sudo systemctl status aeroserver    # état du service
journalctl -u aeroserver -f         # logs en direct
```

---

## Mettre à jour les mods

Pour mettre à jour les `fileID` dans `manifest.json` puis synchroniser les mods :

```bash
# Linux (service arrêté)
sudo systemctl stop aeroserver
sudo -u minecraft .venv/bin/python3 download_mods_from_manifest.py
sudo systemctl start aeroserver
```

```powershell
# Windows
python download_mods_from_manifest.py
```

---

## Fichiers exclus de Git

Le `.gitignore` exclut les fichiers générés lors de l'installation et de l'exécution :

- `libraries/` — librairies NeoForge
- `mods/` — fichiers `.jar` téléchargés
- `logs/` — journaux du serveur
- `world/` — données de la map
- `neoforge-*-installer.jar` — installateur téléchargé
- `.server_stdin` — FIFO utilisé pour l'arrêt propre
- `usercache.json`, `ops.json`, `whitelist.json`, etc.
