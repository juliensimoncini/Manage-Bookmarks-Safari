#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script : list_safari_bookmarks.py
But    : Lister les signets Safari avec chemin de dossier, titre, URL
Compat : Safari 26.1 (macOS Sonoma) et proches

Fonctionnalités :
- Format de sortie : table (par défaut), csv, json, ndjson
- Filtrage par domaine (--domain) et recherche plein texte (--search)
- Export vers fichier (--output)
- Affiche uniquement les URL, pas les dossiers
"""

import argparse
import csv
import json
from pathlib import Path
import plistlib
from urllib.parse import urlparse
from datetime import datetime
import sys

# --- Constantes chemins (utilisateur courant) ---
BOOKMARKS_PATH = Path.home() / "Library/Safari/Bookmarks.plist"

def hostname(url: str) -> str:
    try:
        h = urlparse(url).hostname or ""
        return h.lower()
    except Exception:
        return ""

def matches_domain(host: str, targets: list[str]) -> bool:
    if not targets:
        return True
    host = (host or "").lower().strip(".")
    if not host:
        return False
    for d in targets:
        d = d.lower().lstrip(".")
        if host == d or host.endswith("." + d):
            return True
    return False

def contains_search(haystack: str, needles: list[str]) -> bool:
    if not needles:
        return True
    h = (haystack or "").lower()
    return all(n.lower() in h for n in needles)

def to_iso(dt):
    if isinstance(dt, datetime):
        # Les NSDate des plist deviennent des datetime avec plistlib
        return dt.isoformat()
    return ""

def walk(children, path_stack, out_rows):
    """
    Parcours récursif de la hiérarchie de signets.
    Accumule les entrées URL sous forme de dicts dans out_rows.
    """
    for item in children or []:
        # Dossier
        if "Children" in item:
            title = item.get("Title") or item.get("URIDictionary", {}).get("title") or ""
            path_stack.append(title or "Sans titre")
            walk(item.get("Children", []), path_stack, out_rows)
            path_stack.pop()
            continue

        # Feuille URL
        url = item.get("URLString")
        if url:
            title = item.get("URIDictionary", {}).get("title") or item.get("Title") or url
            row = {
                "path": "/".join([p for p in path_stack if p]),
                "title": title,
                "url": url,
                "domain": hostname(url),
                "added_at": to_iso(item.get("DateAdded")),
                "modified_at": to_iso(item.get("LastModified"))
            }
            out_rows.append(row)

def load_bookmarks(path: Path):
    with open(path, "rb") as f:
        return plistlib.load(f)

def print_table(rows):
    # Auto-width simple
    cols = ["path", "title", "url", "domain", "added_at"]
    widths = {c: len(c) for c in cols}
    for r in rows:
        for c in cols:
            widths[c] = max(widths[c], len(r.get(c, "") or ""))
    line = " | ".join(c.ljust(widths[c]) for c in cols)
    sep = "-+-".join("-" * widths[c] for c in cols)
    print(line)
    print(sep)
    for r in rows:
        print(" | ".join((r.get(c, "") or "").ljust(widths[c]) for c in cols))

def write_csv(rows, path):
    cols = ["path", "title", "url", "domain", "added_at", "modified_at"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)

def write_json(rows, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

def write_ndjson(rows, path):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def main():
    parser = argparse.ArgumentParser(description="Lister les signets Safari.")
    parser.add_argument("--bookmarks-path", default=str(BOOKMARKS_PATH),
                        help=f"Chemin du Bookmarks.plist (défaut: {BOOKMARKS_PATH})")
    parser.add_argument("--format", choices=["table", "csv", "json", "ndjson"], default="table",
                        help="Format de sortie.")
    parser.add_argument("-d", "--domain", action="append", default=[],
                        help="Filtrer par domaine (répétable : -d example.com -d x.com).")
    parser.add_argument("-s", "--search", action="append", default=[],
                        help="Filtrer par mots-clés (titre+URL, ET logique, répétable).")
    parser.add_argument("-o", "--output", help="Écrire la sortie dans un fichier.")
    args = parser.parse_args()

    plist_path = Path(args.bookmarks_path).expanduser()
    if not plist_path.exists():
        print(f"❌ Fichier introuvable : {plist_path}")
        sys.exit(1)

    try:
        data = load_bookmarks(plist_path)
    except Exception as e:
        print(f"❌ Impossible de lire le plist : {e}")
        sys.exit(1)

    rows = []
    walk(data.get("Children", []), [], rows)

    # Filtres
    filtered = []
    for r in rows:
        if not matches_domain(r["domain"], args.domain):
            continue
        if not contains_search((r["title"] or "") + " " + (r["url"] or ""), args.search):
            continue
        filtered.append(r)

    # Sort simple par chemin puis titre
    filtered.sort(key=lambda x: (x["path"].lower(), x["title"].lower()))

    # Sortie
    if args.output:
        out_path = Path(args.output).expanduser()
        if args.format == "csv":
            write_csv(filtered, out_path)
        elif args.format == "json":
            write_json(filtered, out_path)
        elif args.format == "ndjson":
            write_ndjson(filtered, out_path)
        else:
            # table vers fichier
            # On génère une table texte
            original_stdout = sys.stdout
            with open(out_path, "w", encoding="utf-8") as f:
                sys.stdout = f
                print_table(filtered)
                sys.stdout = original_stdout
        print(f"✅ Écrit : {out_path} ({args.format}, {len(filtered)} lignes)")
    else:
        if args.format == "table":
            print_table(filtered)
        elif args.format == "csv":
            write_csv(filtered, sys.stdout)  # non interactif; on garde table par défaut
        elif args.format == "json":
            print(json.dumps(filtered, ensure_ascii=False, indent=2))
        elif args.format == "ndjson":
            for r in filtered:
                print(json.dumps(r, ensure_ascii=False))

if __name__ == "__main__":
    main()