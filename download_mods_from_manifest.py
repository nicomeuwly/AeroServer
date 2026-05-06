#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys

try:
    import requests
    from packaging.version import Version, InvalidVersion
except ImportError as e:
    print(f"Missing dependency: {e}. Install with `pip install -r requirements.txt`.")
    sys.exit(1)

CURSEFORGE_API_URL = "https://api.curseforge.com/v1"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Télécharge les mods listés dans un manifest CurseForge vers un dossier mods."
    )
    parser.add_argument(
        "--manifest",
        default="manifest.json",
        help="Chemin du fichier manifest.json (défaut: manifest.json)",
    )
    parser.add_argument(
        "--mods-dir",
        default="mods",
        help="Dossier de destination pour les mods téléchargés (défaut: mods)",
    )
    parser.add_argument(
        "--api-key",
        help="Clé API CurseForge. Peut aussi être fournie via la variable d'environnement CURSEFORGE_API_KEY.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Forcer le re-téléchargement même si le fichier existe déjà.",
    )
    return parser.parse_args()


def load_manifest(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_file_info(api_key, project_id, file_id):
    url = f"{CURSEFORGE_API_URL}/mods/{project_id}/files/{file_id}"
    headers = {
        "x-api-key": api_key,
        "User-Agent": "CurseForgeManifestDownloader/1.0",
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()["data"]


def download_file(download_url, destination_path):
    with requests.get(download_url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        with open(destination_path, "wb") as out_file:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    out_file.write(chunk)


def download_neoforge_installer(manifest, force=False):
    minecraft = manifest.get("minecraft", {})
    mod_loaders = minecraft.get("modLoaders", [])
    neoforge_version = None
    for loader in mod_loaders:
        if loader.get("primary", False) and "neoforge" in loader.get("id", ""):
            neoforge_version = loader["id"].replace("neoforge-", "")
            break
    if not neoforge_version:
        print("Aucune version Neoforge trouvée dans le manifest.")
        return

    installer_name = f"neoforge-{neoforge_version}-installer.jar"
    installer_path = os.path.join(os.getcwd(), installer_name)
    if os.path.exists(installer_path) and not force:
        print(f"Installateur Neoforge déjà présent : {installer_name}")
        return

    url = f"https://maven.neoforged.net/releases/net/neoforged/neoforge/{neoforge_version}/neoforge-{neoforge_version}-installer.jar"
    print(f"Téléchargement de l'installateur Neoforge {neoforge_version}...", end=" ")
    try:
        download_file(url, installer_path)
        print("OK")
    except requests.RequestException as exc:
        print(f"Échec: {exc}")
        if os.path.exists(installer_path):
            os.remove(installer_path)


def main():
    args = parse_args()
    api_key = args.api_key or os.environ.get("CURSEFORGE_API_KEY")
    if not api_key:
        print("Erreur: une clé API CurseForge est requise. Définis CURSEFORGE_API_KEY ou utilise --api-key.")
        sys.exit(1)

    if not os.path.isfile(args.manifest):
        print(f"Erreur: impossible de trouver le manifest '{args.manifest}'.")
        sys.exit(1)

    manifest = load_manifest(args.manifest)
    files = manifest.get("files", [])
    if not files:
        print("Aucun fichier mod trouvé dans le manifest.")
        sys.exit(1)

    # Télécharger l'installateur Neoforge si nécessaire
    download_neoforge_installer(manifest, args.force)

    os.makedirs(args.mods_dir, exist_ok=True)

    for entry in files:
        project_id = entry.get("projectID")
        file_id = entry.get("fileID")
        if project_id is None or file_id is None:
            print("Fichier manifest ignoré: entrée manquante projectID/fileID.")
            continue

        try:
            file_info = get_file_info(api_key, project_id, file_id)
        except requests.HTTPError as exc:
            print(f"Erreur HTTP pour {project_id}/{file_id}: {exc}")
            continue
        except requests.RequestException as exc:
            print(f"Erreur réseau pour {project_id}/{file_id}: {exc}")
            continue

        download_url = file_info.get("downloadUrl")
        file_name = file_info.get("fileName")
        if not download_url or not file_name:
            print(f"Impossible de récupérer le lien de téléchargement pour {project_id}/{file_id}.")
            continue

        output_path = os.path.join(args.mods_dir, file_name)
        manifest_version = extract_version_from_filename(file_name)

        if os.path.exists(output_path) and not args.force:
            existing_version = extract_version_from_filename(os.path.basename(output_path))
            if existing_version and manifest_version:
                if manifest_version > existing_version:
                    print(f"Mise à jour de {file_name} (version {existing_version} → {manifest_version})...", end=" ")
                else:
                    print(f"Ignoré (version à jour): {file_name} (version {existing_version})")
                    continue
            elif existing_version is None or manifest_version is None:
                print(f"Ignoré (version non détectable): {file_name}")
                continue
            else:
                print(f"Ignoré (existe déjà): {file_name}")
                continue
        elif args.force:
            print(f"Forcé le téléchargement de {file_name}...", end=" ")
        else:
            print(f"Téléchargement de {file_name}...", end=" ")

        try:
            download_file(download_url, output_path)
            print("OK")
        except requests.RequestException as exc:
            print(f"Échec: {exc}")
            if os.path.exists(output_path):
                os.remove(output_path)

    print("Terminé.")


if __name__ == "__main__":
    main()
