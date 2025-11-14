#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script : prune_broken_safari_bookmarks.py
But    : Tester les signets Safari et SUPPRIMER ceux dont l'URL ne répond pas
         ou renvoie un statut HTTP >= 300.

Compat : Safari 26.1 (macOS Sonoma et proches)
ATTENTION : Safari doit être FERMÉ et iCloud Safari idéalement désactivé
pendant l'exécution.
"""

import argparse
import plistlib
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import ssl
from datetime import datetime
import sys
import time

# --- Constantes chemins (utilisateur courant) ---
BOOKMARKS_PATH = Path.home() / "Library/Safari/Bookmarks.plist"

# ---------- UTILITAIRES URL ----------

def is_http_url(url: str) -> bool:
    try:
        p = urlparse(url)
        return p.scheme in ("http", "https")
    except Exception:
        return False


def hostname(url: str) -> str:
    try:
        h = urlparse(url).hostname or ""
        return h.lower()
    except Exception:
        return ""


def check_url(url: str, timeout: int = 10):
    """
    Teste une URL.
    Retourne (status_code, error_message).
    - status_code : int (200, 404, 500, ...) ou None si pas de réponse
    - error_message : str ou None
    """
    if not is_http_url(url):
        return None, "Non-HTTP"

    req = Request(
        url,
        headers={"User-Agent": "SafariBookmarkPruner/1.0"},
    )
    ctx = ssl.create_default_context()

    try:
        with urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.getcode(), None
    except HTTPError as e:
        return e.code, None
    except URLError as e:
        return None, f"URLError: {e.reason}"
    except Exception as e:
        return None, f"Error: {e}"


# ---------- BACKUP ----------

def backup_bookmarks(path: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = path.with_name(f"Bookmarks.backup.{ts}.plist")
    backup_path.write_bytes(path.read_bytes())
    return backup_path


# ---------- FILTRAGE RECURSIF + SUPPRESSION ----------

def prune_children(children, path_stack, folder_filter, timeout, dry_run, min_status, stats):
    """
    Parcours récursif de la hiérarchie de signets.
    Retourne une nouvelle liste Children filtrée.

    - folder_filter : str ou None, chemin type "Barre de favoris/Dev"
    - stats : dict pour compter ce qui se passe
    """
    new_children = []

    for item in children or []:
        # Dossier
        if "Children" in item:
            title = item.get("Title") or item.get("URIDictionary", {}).get("title") or ""
            path_stack.append(title or "Sans titre")

            folder_path = "/".join([p for p in path_stack if p])

            # On descend toujours récursivement, mais on n'applique la
            # condition de suppression que si le chemin commence par folder_filter
            filtered_kids = prune_children(
                item.get("Children", []),
                path_stack,
                folder_filter,
                timeout,
                dry_run,
                min_status,
                stats,
            )

            # On met à jour les enfants
            item["Children"] = filtered_kids
            new_children.append(item)

            path_stack.pop()
            continue

        # Signet URL
        url = item.get("URLString")
        if not url:
            new_children.append(item)
            continue

        title = item.get("URIDictionary", {}).get("title") or item.get("Title") or url
        folder_path = "/".join([p for p in path_stack if p])
        full_path = folder_path + " / " + title if folder_path else title

        # Si un filtre de dossier est défini et que le chemin ne matche pas, on ne supprime pas
        if folder_filter and not folder_path.startswith(folder_filter):
            new_children.append(item)
            continue

        stats["total_tested"] += 1

        print(f"[{stats['total_tested']}] {full_path}")
        print(f"   URL → {url}")

        status, error = check_url(url, timeout=timeout)

        # Décision de suppression : statut None (pas de réponse) ou >= min_status
        to_delete = False

        if status is None:
            to_delete = True
            reason = error or "Aucune réponse"
        elif status >= min_status:
            to_delete = True
            reason = f"Statut HTTP {status}"
        else:
            reason = f"Statut HTTP {status}"

        if status is not None:
            if 200 <= status < 300:
                status_text = f"{status} (OK)"
            elif 300 <= status < 400:
                status_text = f"{status} (Redirection)"
            elif 400 <= status < 500:
                status_text = f"{status} (Erreur client)"
            else:
                status_text = f"{status} (Erreur serveur)"
        else:
            status_text = "Aucune réponse"

        print(f"   Statut → {status_text}" + (f" | {error}" if error else ""))
        if to_delete:
            stats["total_broken"] += 1
            print(f"   🔥 Marqué pour suppression ({reason})")
            if dry_run:
                # En dry-run on NE supprime pas réellement, on garde dans la liste
                new_children.append(item)
            else:
                stats["total_deleted"] += 1
                # on ne fait pas append → suppression
        else:
            print("   ✅ Conservé")
            new_children.append(item)

        print()
        # Petite pause optionnelle si tu veux éviter d'agresser les serveurs
        # time.sleep(0.1)

    return new_children


# ---------- MAIN ----------

def main():
    parser = argparse.ArgumentParser(
        description="Supprimer les signets Safari dont l'URL ne répond pas ou renvoie un statut >= 300."
    )
    parser.add_argument(
        "--bookmarks-path",
        default=str(BOOKMARKS_PATH),
        help=f"Chemin du Bookmarks.plist (défaut : {BOOKMARKS_PATH})",
    )
    parser.add_argument(
        "--folder",
        help='Limiter aux signets d\'un dossier (chemin complet, ex: "Barre de favoris/Dev").',
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Timeout HTTP en secondes (défaut : 10).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simuler sans rien supprimer.",
    )
    parser.add_argument(
        "--min-status",
        type=int,
        default=300,
        help="Seuil de statut HTTP à partir duquel on supprime (défaut : 300).",
    )

    args = parser.parse_args()

    plist_path = Path(args.bookmarks_path).expanduser()
    if not plist_path.exists():
        print(f"❌ Fichier introuvable : {plist_path}")
        sys.exit(1)

    print("⚠️ Assure-toi que Safari est FERMÉ et qu'iCloud Safari est désactivé le temps du script.")
    print(f"📄 Fichier : {plist_path}")
    print(f"📁 Dossier filtré : {args.folder or 'Aucun (tous les signets)'}")
    print(f"🕒 Timeout : {args.timeout}s")
    print(f"🔪 Suppression si statut >= {args.min_status} ou aucune réponse")
    print(f"🧪 Dry-run : {args.dry_run}")
    print()

    # Sauvegarde AVANT toute modif (même en dry-run, ça ne fait pas de mal)
    backup_path = backup_bookmarks(plist_path)
    print(f"💾 Sauvegarde créée : {backup_path}\n")

    try:
        with open(plist_path, "rb") as f:
            data = plistlib.load(f)
    except PermissionError:
        print("❌ Permission refusée. Active l'Accès complet au disque pour Terminal / python3.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Impossible de lire le plist : {e}")
        sys.exit(1)

    stats = {
        "total_tested": 0,
        "total_broken": 0,
        "total_deleted": 0,
    }

    children = data.get("Children", [])
    folder_filter = args.folder.strip() if args.folder else None

    new_children = prune_children(
        children=children,
        path_stack=[],
        folder_filter=folder_filter,
        timeout=args.timeout,
        dry_run=args.dry_run,
        min_status=args.min_status,
        stats=stats,
    )

    print("📊 Récapitulatif :")
    print(f"   Signets testés       : {stats['total_tested']}")
    print(f"   Signets cassés       : {stats['total_broken']}")
    if args.dry_run:
        print(f"   Signets supprimés    : 0 (dry-run)")
    else:
        print(f"   Signets supprimés    : {stats['total_deleted']}")
    print(f"   Sauvegarde disponible: {backup_path}")
    print()

    if args.dry_run:
        print("✅ Dry-run terminé. Relance sans --dry-run pour appliquer la suppression.")
        return

    # Écriture du plist mis à jour
    data["Children"] = new_children
    try:
        with open(plist_path, "wb") as f:
            plistlib.dump(data, f)
        print("✅ Fichier Bookmarks.plist mis à jour.")
    except Exception as e:
        print(f"❌ Erreur d'écriture du plist : {e}")
        print("↩️ Restauration de la sauvegarde...")
        plist_path.write_bytes(backup_path.read_bytes())
        print("✅ Restauration effectuée.")
        sys.exit(1)


if __name__ == "__main__":
    main()