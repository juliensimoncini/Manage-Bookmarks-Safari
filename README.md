# Scripts de gestion des signets Safari (macOS)

## 📘 Présentation

Ce dépôt contient deux scripts Python pour **analyser, exporter et nettoyer** les signets Safari sur macOS (compatible jusqu’à **Safari 26.1 / macOS Sonoma**).

- `list_safari_bookmarks.py`  
  → Liste, filtre et exporte les signets (table, CSV, JSON, NDJSON)

- `check_safari_bookmarks_http.py`  
  → Teste les URLs, affiche le statut HTTP et détecte les liens cassés

- `prune_broken_safari_bookmarks.py`  
  → Supprime automatiquement les signets dont l’URL ne répond pas ou renvoie un statut HTTP ≥ *seuil* (par défaut 300)

- `remove_safari_bookmarks_by_domains.py`
  → Supprime automatiquement les signets correspondant à un ou plusieurs domaines.

🧠 Ces scripts manipulent directement le fichier `Bookmarks.plist` de Safari, situé dans `~/Library/Safari/Bookmarks.plist`.

> ⚠️ Safari doit être **fermé** avant toute modification, et l’accès **Full Disk Access** doit être donné à Terminal pour que Python puisse lire ce fichier.

---

## ⚙️ Pré-requis

- macOS Catalina ou supérieur (testé sur Sonoma 14.x)
- Python 3.9+ installé (par défaut sur macOS)
- Terminal / Python autorisé via **Accès complet au disque**
- Safari **fermé** avant toute modification de ses signets

---

## 🔒 Autorisation d’accès (obligatoire)

macOS bloque par défaut l’accès au dossier `~/Library/Safari` pour les scripts en ligne de commande.

### 🧩 Étapes pour activer “Accès complet au disque”
1. Ouvre **Réglages Système → Sécurité et confidentialité → Confidentialité → Accès complet au disque**  
2. Clique sur **+** puis ajoute :
   - `Terminal.app` (ou `iTerm.app` si tu utilises iTerm)
   - et/ou ton interpréteur Python (ex : `/usr/local/bin/python3` ou `/opt/homebrew/bin/python3`)
3. Redémarre ton terminal.

---

## 📂 Structure du projet

```
/
├── list_safari_bookmarks.py
├── check_safari_bookmarks_http.py
├── prune_broken_safari_bookmarks.py
├── remove_safari_bookmarks_by_domains.py
└── README.md
```

---

## 🧾 1. Lister les signets – `list_safari_bookmarks.py`

### 🎯 Description

Ce script lit le fichier `Bookmarks.plist` et exporte tous les signets Safari :
- avec leur **chemin de dossier complet**
- le **titre**
- l’**URL**
- le **domaine**
- les **dates d’ajout et de modification**

Il prend en charge le **filtrage** par domaine et par mots-clés, et plusieurs **formats de sortie** : table lisible, CSV, JSON et NDJSON.

---

### 💻 Commandes principales

#### 📋 Lister simplement tous les signets
```bash
python3 list_safari_bookmarks.py
```

#### 🔍 Filtrer par domaine
```bash
python3 list_safari_bookmarks.py -d github.com -d developer.apple.com
```

#### 🔎 Rechercher par mots-clés (ET logique)
```bash
python3 list_safari_bookmarks.py -s laravel -s filament
```

#### 🧩 Combiner filtres domaine + recherche
```bash
python3 list_safari_bookmarks.py -d x.com -d twitter.com -s profil
```

#### 📤 Exporter en CSV
```bash
python3 list_safari_bookmarks.py   --format csv   --output ~/Desktop/safari_bookmarks.csv
```

#### 📤 Exporter en JSON
```bash
python3 list_safari_bookmarks.py   --format json   --output ~/Desktop/safari_bookmarks.json
```

#### 📤 Exporter en NDJSON (une ligne JSON par signet)
```bash
python3 list_safari_bookmarks.py   --format ndjson   --output ~/Desktop/safari_bookmarks.ndjson
```

#### 📁 Utiliser un fichier Bookmarks spécifique
```bash
python3 list_safari_bookmarks.py   --bookmarks-path ~/Desktop/Bookmarks.plist
```

#### 🧱 Exemple de sortie (mode table)
```
path                     | title                      | url                           | domain            | added_at
--------------------------+----------------------------+--------------------------------+-------------------+----------------------------
Barre de favoris/Dev      | GitHub                     | https://github.com             | github.com        | 2024-08-15T18:34:12
Barre de favoris/Docs     | Apple Developer            | https://developer.apple.com    | developer.apple.com | 2024-09-10T14:22:50
```

---

## 🧪 2. Tester les URLs — `check_safari_bookmarks_http.py`

Ce script teste chaque signet HTTP/HTTPS et affiche :

- statut HTTP (200, 301, 404, 500…)
- erreurs réseau
- chemin complet du signet

---

### 💻 Commandes principales

#### Tester un dossier précis
```bash
python3 check_safari_bookmarks_http.py --folder "Barre de favoris/Dev"
```

#### Export CSV
```bash
python3 check_safari_bookmarks_http.py   --folder "Barre de favoris/Dev"   --output-csv ~/Desktop/check_dev.csv
```

#### 🧱 Exemple de sortie :
```
[1/12] Barre de favoris / Dev / Laravel / Docs
   URL → https://laravel.com/docs
   Statut → 200 (OK)

[2/12] Barre de favoris / Dev / API / Old
   URL → http://my-old-api.com
   Statut → 404 (Erreur client)
```

---

## 🔥 3. Supprimer les signets cassés — `prune_broken_safari_bookmarks.py`

#### Objectif :
Supprimer automatiquement les signets :
- dont l’URL ne répond pas,
- ou répond un statut HTTP ≥ `min-status` (par défaut : 300).

#### Le script :
- teste chaque signet
- construit le chemin complet
- marque les signets cassés pour suppression
- crée automatiquement une **sauvegarde horodatée**
- supprime (sauf en `--dry-run`)
- réécrit le fichier `Bookmarks.plist`

---

### 💻 Commandes principales

#### 🧪 Simulation : voir ce qui serait supprimé
```bash
python3 prune_broken_safari_bookmarks.py --dry-run
```

#### 🔍 Cibler uniquement un dossier
```bash
python3 prune_broken_safari_bookmarks.py   --folder "Barre de favoris/Dev"   --dry-run
```

#### 🔥 Suppression réelle dans le dossier ciblé
```bash
python3 prune_broken_safari_bookmarks.py   --folder "Barre de favoris/Dev"
```

#### 🔥 Supprimer partout (tous les signets)
```bash
python3 prune_broken_safari_bookmarks.py
```

#### ❗ Ne supprimer qu’à partir de statut ≥ 400
```bash
python3 prune_broken_safari_bookmarks.py --min-status 400
```

---

## 🧹 4. Supprimer des signets – `remove_safari_bookmarks_by_domains.py`

### 🎯 Description

Ce script permet de **supprimer automatiquement** tous les signets Safari correspondant à un ou plusieurs domaines.

Caractéristiques :
- suppression récursive dans tous les dossiers
- possibilité d’**ignorer certains dossiers** (ex. “Favoris”)
- **sauvegarde automatique** du fichier original
- mode **dry-run** pour simuler sans rien supprimer

---

### 💻 Commandes principales

#### 🧪 Simulation (dry-run)
```bash
python3 remove_safari_bookmarks_by_domains.py   -d facebook.com -d x.com -d tiktok.com   --ignore-folder "Favoris"   --dry-run
```
→ Affiche la liste des signets qui seraient supprimés, sans rien modifier.

#### 🧼 Suppression réelle
```bash
python3 remove_safari_bookmarks_by_domains.py   -d facebook.com -d x.com -d tiktok.com   --ignore-folder "Favoris"
```

#### 📁 Fichier personnalisé (copie locale)
```bash
python3 remove_safari_bookmarks_by_domains.py   -d reddit.com -d linkedin.com   --bookmarks-path ~/Desktop/Bookmarks.plist
```

---

## 🛡️ 5. Sauvegardes automatiques

Chaque exécution crée une sauvegarde dans le même dossier :
```
~/Library/Safari/Bookmarks.backup.YYYYMMDD-HHMMSS.plist
```

Pour restaurer :
```bash
cp ~/Library/Safari/Bookmarks.backup.20251112-154200.plist    ~/Library/Safari/Bookmarks.plist
```

---

## ⚠️ 6. Conseils avant exécution

1. **Fermer Safari** avant de modifier le fichier.
2. **Désactiver temporairement la synchronisation iCloud Safari**, sinon iCloud risque de réinjecter les anciens signets.
3. Exécuter le script (dry-run d’abord).
4. **Relancer Safari** et réactiver iCloud ensuite.

---

## 🕐 7. Exécution automatique (optionnel)

Pour planifier un nettoyage régulier, tu peux créer une tâche `launchd` ou `cron`.

Exemple hebdomadaire (chaque dimanche à 3h du matin) :

```bash
crontab -e
```
et ajoute :
```bash
0 3 * * 0 /usr/bin/python3 ~/bin/remove_safari_bookmarks_by_domains.py -d facebook.com -d x.com -d tiktok.com --ignore-folder "Favoris"
```

---

## 🔧 8. Dépannage

### ❌ `Operation not permitted`
macOS bloque Python d’accéder au dossier `~/Library/Safari`.
➡️ Active **l’accès complet au disque** pour ton Terminal (voir plus haut).

### ❌ “Impossible de lire le plist”
Vérifie :
- que **Safari est fermé** ;
- que tu as bien le **droit de lecture** sur `~/Library/Safari/Bookmarks.plist` ;
- que tu n’as pas ouvert la copie avec une app (Safari ou TextEdit) en parallèle.

---

## ✨ 9. Commandes récapitulatives (copy-paste ready)

```bash
# Fermer Safari
osascript -e 'tell application "Safari" to quit'

# Sauvegarde manuelle
cp ~/Library/Safari/Bookmarks.plist ~/Library/Safari/Bookmarks_backup_$(date +%F).plist

# Lister tous les signets
python3 list_safari_bookmarks.py

# Filtrer par domaine
python3 list_safari_bookmarks.py -d github.com -d apple.com

# Exporter en CSV
python3 list_safari_bookmarks.py --format csv --output ~/Desktop/safari_bookmarks.csv

# Tester les signets d'un dossier
python3 check_safari_bookmarks_http.py --folder "Barre de favoris/Dev"

# Simuler la suppression
python3 prune_broken_safari_bookmarks.py --dry-run

# Nettoyer réellement
python3 prune_broken_safari_bookmarks.py

# Simulation de suppression
python3 remove_safari_bookmarks_by_domains.py -d facebook.com -d x.com --dry-run

# Suppression réelle
python3 remove_safari_bookmarks_by_domains.py -d facebook.com -d x.com

# Restaurer une sauvegarde
cp ~/Library/Safari/Bookmarks.backup.*.plist ~/Library/Safari/Bookmarks.plist
```

---

## 👨‍💻 Auteur
**Julien SIMONCINI**  
*with ChatGPT*
