# eml_to_md

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)

Un outil Python simple et robuste pour convertir des fichiers `.eml` (emails exportés) en fichiers Markdown, avec extraction automatique des images intégrées et gestion des pièces jointes.

## ✨ Fonctionnalités

- Conversion `.eml` → `.md` avec préservation de la mise en forme (gras, liens, listes...)
- Extraction des métadonnées (expéditeur, destinataire, date, objet) sous forme de front-matter YAML
- Décodage des en-têtes MIME encoded-words (`=?utf-8?Q?...?=`) : accents et objets non-ASCII corrects
- Extraction automatique des images intégrées (`cid:`) dans un dossier dédié
- Pièces jointes non-image listées en fin de document (nom, type MIME, taille) ; `--extract-attachments` les sauvegarde dans un dossier dédié avec liens de téléchargement
- Gestion robuste de l'encodage (UTF-8, ISO-8859-1...)
- Noms de fichiers/dossiers "slugifiés" (sans espace ni accent) pour compatibilité maximale
- Conversion unitaire ou en lot (dossier entier), avec mode récursif (`-r`)
- Interface en ligne de commande simple, avec codes de sortie exploitables (0 = succès, 1 = échec)
- Suite de tests (`pytest`) et intégration continue (lint `ruff` + tests sur Python 3.9–3.13)

## 📦 Installation

### Depuis PyPI (recommandé)

```bash
pip install eml2markdown
```

La commande `eml2markdown` est ensuite disponible depuis n'importe quel dossier :

```bash
eml2markdown chemin/vers/email.eml
```

Mise à jour : `pip install --upgrade eml2markdown`

### Depuis GitHub (version de développement)

```bash
pip install git+https://github.com/Baebibelab/eml_to_md.git
```

### Sans installation (script autonome)

Clonez le dépôt et installez les dépendances dans un environnement virtuel :

```bash
git clone https://github.com/Baebibelab/eml_to_md.git
cd eml_to_md

python -m venv venv
source venv/bin/activate      # macOS / Linux
venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

## 🚀 Utilisation

### Convertir un seul fichier

```bash
python eml_to_md.py chemin/vers/mail.eml
```

Un fichier mail.md et un dossier mail_images/ (si des images sont présentes) seront créés à côté du fichier source.

### Spécifier un fichier de sortie

```bash
python eml_to_md.py mail.eml -o sortie.md
```

### Convertir un dossier entier (traitement par lot)

```bash
python eml_to_md.py dossier_mails/
```

Un échec n'interrompt pas le reste : chaque fichier est traité isolément, et la commande
sort avec un code d'erreur si au moins un fichier a échoué.

### Spécifier un dossier de sortie

```bash
python eml_to_md.py dossier_mails/ -o dossier_markdown/
```

### Parcours récursif des sous-dossiers

```bash
python eml_to_md.py dossier_mails/ -o dossier_markdown/ -r
```

L'arborescence des sous-dossiers est recréée dans le dossier de sortie.

### Extraire les pièces jointes

```bash
python eml_to_md.py mail.eml --extract-attachments
```

Les pièces jointes non-image sont sauvegardées dans un dossier `mail_pieces-jointes/`
à côté du Markdown, et listées en fin de document avec un lien de téléchargement.
Sans ce flag, elles sont simplement listées (nom, type, taille).

## 📄 Exemple de résultat

```
Entrée : exemple.eml
```

```
Sortie : exemple.md
---
from: "Alice Dupont <alice@example.com>"
to: "Bob Martin <bob@example.com>"
cc: "carol@example.com"
date: "Mon, 22 Sep 2026 10:00:00 +0000"
subject: "Compte-rendu réunion"
---

# Compte-rendu réunion

Bonjour Bob,

Voici le compte-rendu de notre réunion...

![schema](exemple_images/schema_1.png)

## Pièces jointes

- **rapport.pdf** (application/pdf, 16 o) — [télécharger](exemple_pieces-jointes/rapport.pdf)
```

## 🗂️ Structure du projet

```
eml-to-md/
├── eml_to_md.py             # Script principal
├── tests/                   # Suite de tests pytest
├── .github/workflows/       # CI (ruff + pytest) et publication PyPI
├── pyproject.toml           # Packaging PEP 621
├── requirements.txt         # Dépendances Python
├── README.md
├── LICENSE
└── CHANGELOG.md
```

## 🛠️ Dépendances

* [html2text](https://github.com/Alir3z4/html2text) — conversion HTML → Markdown
* [beautifulsoup4](https://www.crummy.com/software/BeautifulSoup/) — parsing et manipulation du DOM HTML

## ⚠️ Limitations connues

* Les emails imbriqués (mail transféré en pièce jointe .eml) ne sont pas traités récursivement.
* Certains rendus HTML très spécifiques à Outlook (tableaux complexes, styles conditionnels mso-) peuvent ne pas se convertir parfaitement en Markdown.
