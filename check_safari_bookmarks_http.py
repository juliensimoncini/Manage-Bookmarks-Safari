#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script : check_safari_bookmarks_http.py
But    : Tester les URL des signets Safari et détecter les 404 / erreurs.
Compat : Safari 26.1 (macOS Sonoma)
"""

import argparse
import csv
from pathlib import Path
import plistlib
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import ssl
import sys
from datetime import datetime

# --- Constantes chemins (utilisateur courant) ---
BOOKMARKS_PATH = Path.home() / "Library/Safari/Bookmarks.plist"

# ---------- UTILS ----------
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


# ---------- RECURSIVE WALK ----------
def walk(children, path_stack, out_rows):
    for item in children or []:
        # Dossier
        if "Children" in item:
            title = item.get("Title") or item.get("URIDictionary", {}).get("title") or ""
            path_stack.append(title or "Sans titre")
            walk(item.get("Children", []), path_stack, out_rows)
            path_stack.pop()
            continue

        # Signet URL
        url = item.get("URLString")
        if url:
            title = item.get("URIDictionary", {}).get("title") or item.get("Title") or url

            folder_path = "/".join([p for p in path_stack if p])
            full_path = folder_path + " / " + title if folder_path else title

            row = {
                "path": folder_path,
                "full_path": full_path,
                "title": title,
                "url": url,
                "domain": hostname(url),
            }
            out_rows.append(row)


# ---------- LOAD BOOKMARKS ----------
def load_bookmarks(path: Path):
    with open(path, "rb") as f:
        return plistlib.load(f)


# ---------- URL CHECK ----------
def check_url(url: str, timeout: int = 10):
    if not is_http_url(url):
        return None, "Non-HTTP"

    req = Request(url, headers={
        "User-Agent": "SafariBookmarkChecker/1.0"
    })
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


# ---------- CSV EXPORT ----------
def write_csv(rows, path: Path):
    fields = ["full_path", "path", "title", "url", "domain", "status", "error"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)


# ---------- MAIN ----------
def main():
    parser = argparse.ArgumentParser(description="Tester les signets Safari et détecter les liens cassés.")
    parser.add_argument("--bookmarks-path", default=str(BOOKMARKS_PATH))
    parser.add_argument("--folder", help='Chemin dossier (ex: "Barre de favoris/Dev")')
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument("--output-csv")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    plist_path = Path(args.bookmarks_path).expanduser()

    try:
        data = load_bookmarks(plist_path)
    except PermissionError:
        print("❌ Autorisation refusée. Active l’Accès complet au disque pour Terminal.")
        sys.exit(1)

    # Collecte de tous les signets
    all_rows = []
    walk(data.get("Children", []), [], all_rows)

    # Filtrage dossier
    target = args.folder.strip() if args.folder else None
    rows = [r for r in all_rows if not target or r["path"].startswith(target)]

    if args.limit:
        rows = rows[:args.limit]

    print(f"🔎 Signets à tester : {len(rows)}")
    if target:
        print(f"📁 Filtre dossier : {target}")

    results = []

    for idx, r in enumerate(rows, start=1):
        print(f"[{idx}/{len(rows)}] {r['full_path']}")
        print(f"   URL → {r['url']}")

        status, error = check_url(r["url"], timeout=args.timeout)

        # Texte du statut
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
        print()  # saut de ligne

        results.append({
            "full_path": r["full_path"],
            "path": r["path"],
            "title": r["title"],
            "url": r["url"],
            "domain": r["domain"],
            "status": status if status else "",
            "error": error or "",
        })

    if args.output_csv:
        write_csv(results, Path(args.output_csv).expanduser())
        print(f"\n📄 Export CSV : {args.output_csv}")

    # Résumé final
    broken = [r for r in results if (not r["status"]) or int(r["status"]) >= 400]

    print("\n📊 Résumé :")
    print(f"   Total : {len(results)}")
    print(f"   Liens cassés : {len(broken)}\n")

    for b in broken[:15]:
        print(f" - {b['status']} | {b['full_path']} | {b['url']}")

if __name__ == "__main__":
    main()