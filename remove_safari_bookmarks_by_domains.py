#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script : remove_safari_bookmarks_by_domains.py
But :   Supprimer des signets Safari dont le domaine correspond à une liste.
Compat : Safari 26.1 (macOS Sonoma) et versions proches
"""

import argparse
import plistlib
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime
import sys

# --- Constantes chemins (utilisateur courant) ---
BOOKMARKS_PATH = Path.home() / "Library/Safari/Bookmarks.plist"

# --- Utilitaires domaine ------------------------------------------------------
def hostname(url: str) -> str:
    """Retourne le hostname (sans port) à partir d'une URL. None si non parsable."""
    try:
        h = urlparse(url).hostname
        return (h or "").lower()
    except Exception:
        return ""

def matches_domain(host: str, targets: list[str]) -> bool:
    """
    Retourne True si host correspond à l'un des domaines cibles.
    - Correspondances par suffixe (ex: *.example.com -> example.com)
    - Comparaison insensible à la casse
    """
    host = (host or "").lower().strip(".")
    if not host:
        return False

    for d in targets:
        d = d.lower().lstrip(".")
        if not d:
            continue
        if host == d or host.endswith("." + d):
            return True
    return False

# --- Filtrage récursif --------------------------------------------------------
def filter_children(children: list, targets: list[str], ignore_folders: set[str], dry_run: bool):
    """
    Parcourt récursivement la hiérarchie 'Children' et filtre les bookmarks.
    Retourne (nouveaux_enfants, nb_suppr)
    """
    new_children = []
    deleted = 0

    for item in children or []:
        # Dossiers (listes)
        if "Children" in item:
            title = item.get("Title") or item.get("URIDictionary", {}).get("title") or ""
            # Si on doit ignorer ce dossier, on le recopie tel quel
            if title in ignore_folders:
                new_children.append(item)
                continue

            filtered_kids, del_count = filter_children(item.get("Children", []), targets, ignore_folders, dry_run)
            # On met à jour uniquement si pas dry-run
            if not dry_run:
                item["Children"] = filtered_kids
            deleted += del_count
            new_children.append(item)
            continue

        # Feuilles (URL)
        url = item.get("URLString")
        if url:
            host = hostname(url)
            if matches_domain(host, targets):
                title = item.get("URIDictionary", {}).get("title") or item.get("Title") or url
                print(f"➡️  Match domaine → suppression : {title} ({url})")
                deleted += 1
                # En dry-run, on NE supprime pas réellement (on garde l'item)
                if dry_run:
                    new_children.append(item)
                # sinon on saute l'append → l'élément est supprimé
                continue

        # Aucun match → conserver
        new_children.append(item)

    return new_children, deleted

# --- Sauvegarde ---------------------------------------------------------------
def backup_bookmarks(bookmarks_path: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = bookmarks_path.with_name(f"Bookmarks.backup.{ts}.plist")
    backup_path.write_bytes(bookmarks_path.read_bytes())
    return backup_path

# --- Main ---------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Supprimer des signets Safari correspondant à une liste de domaines."
    )
    parser.add_argument(
        "-d", "--domain", action="append", required=True,
        help="Domaine à supprimer (peut être répété : -d facebook.com -d twitter.com)."
    )
    parser.add_argument(
        "--ignore-folder", action="append", default=[],
        help="Nom exact d'un dossier de signets à ignorer (peut être répété)."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Simule la suppression sans modifier le fichier."
    )
    parser.add_argument(
        "--bookmarks-path", default=str(BOOKMARKS_PATH),
        help=f"Chemin du Bookmarks.plist (défaut : {BOOKMARKS_PATH})."
    )

    args = parser.parse_args()
    path = Path(args.bookmarks_path).expanduser()

    # Vérifs de base
    if not path.exists():
        print(f"❌ Fichier introuvable : {path}")
        print("Astuce : Vérifie le chemin et ferme Safari avant de lancer le script.")
        sys.exit(1)

    # Charger le plist
    try:
        with open(path, "rb") as f:
            data = plistlib.load(f)
    except Exception as e:
        print(f"❌ Impossible de lire le plist : {e}")
        sys.exit(1)

    # Liste des domaines cibles
    targets = [d.strip() for d in args.domain if d.strip()]
    if not targets:
        print("❌ Aucun domaine valide fourni.")
        sys.exit(1)

    ignore_folders = set(args.ignore_folder or [])

    print("ℹ️  Configuration :")
    print(f"   - Fichier : {path}")
    print(f"   - Dry-run : {args.dry_run}")
    print(f"   - Domaines : {', '.join(targets)}")
    if ignore_folders:
        print(f"   - Dossiers ignorés : {', '.join(ignore_folders)}")
    print("⚠️  Assure-toi que Safari est FERMÉ (et idéalement la synchro iCloud Safari désactivée temporairement).")

    # Sauvegarde avant modification (pas nécessaire en dry-run, mais utile)
    backup_path = backup_bookmarks(path)
    print(f"💾 Sauvegarde créée : {backup_path}")

    # Filtrer
    children = data.get("Children", [])
    new_children, deleted = filter_children(children, targets, ignore_folders, args.dry_run)

    if args.dry_run:
        print(f"\n✅ Dry-run terminé : {deleted} signet(s) seraient supprimé(s). Aucune modification écrite.")
        print("   Supprime --dry-run pour appliquer réellement les changements.")
        return

    # Appliquer et sauvegarder
    data["Children"] = new_children
    try:
        with open(path, "wb") as f:
            plistlib.dump(data, f)
        print(f"\n✅ Terminé : {deleted} signet(s) supprimé(s).")
        print("   Relance Safari (et re-active iCloud si tu l’avais coupé).")
    except Exception as e:
        print(f"❌ Erreur d'écriture du plist, restauration de la sauvegarde… ({e})")
        backup_bytes = backup_path.read_bytes()
        path.write_bytes(backup_bytes)
        print("↩️  Fichier original restauré.")
        sys.exit(1)

if __name__ == "__main__":
    main()