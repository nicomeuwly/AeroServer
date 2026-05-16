#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    from dotenv import load_dotenv
    from tqdm import tqdm
except ImportError as e:
    print(f"Missing dependency: {e}. Install with `pip install -r requirements.txt`.")
    sys.exit(1)

load_dotenv()

CURSEFORGE_API_URL = "https://api.curseforge.com/v1"
BATCH_SIZE = 50
CHUNK_SIZE = 65_536


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Télécharge les mods listés dans un manifest CurseForge vers un dossier mods."
    )
    parser.add_argument("--manifest", default="manifest.json", help="Chemin du manifest (défaut: manifest.json)")
    parser.add_argument("--mods-dir", default="mods", help="Dossier de destination (défaut: mods)")
    parser.add_argument("--api-key", help="Clé API CurseForge (ou variable CURSEFORGE_API_KEY)")
    parser.add_argument("--force", action="store_true", help="Forcer le re-téléchargement")
    parser.add_argument(
        "--workers", type=int, default=4, metavar="N", help="Téléchargements parallèles (défaut: 4)"
    )
    return parser.parse_args()


def make_session(api_key: str) -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "x-api-key": api_key,
        "User-Agent": "CurseForgeManifestDownloader/1.0",
    })
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def load_manifest(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fetch_files_info(session: requests.Session, file_ids: list[int]) -> dict[int, dict]:
    """Récupère les infos de plusieurs fichiers via l'endpoint batch de CurseForge."""
    result: dict[int, dict] = {}
    for i in range(0, len(file_ids), BATCH_SIZE):
        batch = file_ids[i : i + BATCH_SIZE]
        resp = session.post(f"{CURSEFORGE_API_URL}/mods/files", json={"fileIds": batch}, timeout=30)
        resp.raise_for_status()
        for item in resp.json()["data"]:
            result[item["id"]] = item
    return result


def build_cdn_url(file_id: int, file_name: str) -> str:
    s = str(file_id)
    return f"https://mediafilez.forgecdn.net/files/{s[:4]}/{int(s[4:])}/{file_name}"


def find_old_versions(mods_dir: Path, new_filename: str) -> list[Path]:
    match = re.search(r"-\d+(?:\.\d+)*", new_filename)
    if not match:
        return []
    prefix = new_filename[: match.start()]
    return [
        p
        for p in mods_dir.iterdir()
        if p.name != new_filename and p.name.startswith(prefix) and p.suffix == ".jar"
    ]


def download_file(session: requests.Session, url: str, dest: Path) -> None:
    """Téléchargement atomique : écrit dans un .tmp puis renomme."""
    tmp = dest.with_suffix(".tmp")
    try:
        with session.get(url, stream=True, timeout=60) as resp:
            resp.raise_for_status()
            with open(tmp, "wb") as f:
                for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
        tmp.rename(dest)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise


def download_neoforge_installer(
    session: requests.Session, manifest: dict, dest_dir: Path, force: bool
) -> None:
    loaders = manifest.get("minecraft", {}).get("modLoaders", [])
    version = next(
        (
            loader["id"].replace("neoforge-", "")
            for loader in loaders
            if loader.get("primary") and "neoforge" in loader.get("id", "")
        ),
        None,
    )
    if not version:
        print("Aucune version Neoforge trouvée dans le manifest.")
        return

    name = f"neoforge-{version}-installer.jar"
    dest = dest_dir / name
    if dest.exists() and not force:
        print(f"Installateur Neoforge déjà présent : {name}")
        return

    url = f"https://maven.neoforged.net/releases/net/neoforged/neoforge/{version}/{name}"
    print(f"Téléchargement de l'installateur Neoforge {version}...", end=" ", flush=True)
    try:
        download_file(session, url, dest)
        print("OK")
    except requests.RequestException as exc:
        print(f"Échec : {exc}")


def process_mod(
    session: requests.Session, file_info: dict, mods_dir: Path, force: bool
) -> str:
    file_id: int = file_info["id"]
    file_name: str = file_info.get("fileName", "")
    if not file_name:
        return f"[ERREUR] Nom de fichier manquant pour fileID {file_id}"

    url = file_info.get("downloadUrl") or build_cdn_url(file_id, file_name)
    dest = mods_dir / file_name

    if dest.exists() and not force:
        return f"Ignoré : {file_name}"

    try:
        download_file(session, url, dest)
        old = find_old_versions(mods_dir, file_name)
        for p in old:
            p.unlink()
        removed = "".join(f"\n  Supprimé : {p.name}" for p in old)
        return f"OK : {file_name}{removed}"
    except requests.RequestException as exc:
        return f"[ERREUR] {file_name} : {exc}"


def main() -> None:
    args = parse_args()
    api_key = args.api_key or os.environ.get("CURSEFORGE_API_KEY")
    if not api_key:
        print("Erreur : CURSEFORGE_API_KEY manquant. Définis la variable ou utilise --api-key.")
        sys.exit(1)

    manifest_path = Path(args.manifest)
    if not manifest_path.is_file():
        print(f"Erreur : manifest introuvable : {manifest_path}")
        sys.exit(1)

    manifest = load_manifest(manifest_path)
    entries = [e for e in manifest.get("files", []) if "fileID" in e]
    if not entries:
        print("Aucun mod trouvé dans le manifest.")
        sys.exit(1)

    session = make_session(api_key)
    mods_dir = Path(args.mods_dir)
    mods_dir.mkdir(parents=True, exist_ok=True)

    download_neoforge_installer(session, manifest, Path.cwd(), args.force)

    file_ids = [e["fileID"] for e in entries]
    print(f"Récupération des informations pour {len(file_ids)} mods...", flush=True)
    try:
        files_info = fetch_files_info(session, file_ids)
    except requests.RequestException as exc:
        print(f"Erreur API : {exc}")
        sys.exit(1)

    missing = [fid for fid in file_ids if fid not in files_info]
    if missing:
        print(f"Avertissement : {len(missing)} fileID(s) absents de la réponse API.")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(process_mod, session, files_info[fid], mods_dir, args.force): fid
            for fid in file_ids
            if fid in files_info
        }
        with tqdm(total=len(futures), unit="mod", desc="Mods") as bar:
            for future in as_completed(futures):
                tqdm.write(future.result())
                bar.update(1)

    print("Terminé.")


if __name__ == "__main__":
    main()
