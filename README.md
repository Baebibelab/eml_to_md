# eml_to_md

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)
![GitHub last commit](https://img.shields.io/github/last-commit/Baebibelab/eml-to-md)
![GitHub issues](https://img.shields.io/github/issues/Baebibelab/eml-to-md)
![GitHub stars](https://img.shields.io/github/stars/Baebibelab/eml-to-md?style=social)

Un outil Python simple et robuste pour convertir des fichiers `.eml` (emails exportés) en fichiers Markdown, avec extraction automatique des images intégrées.

## ✨ Fonctionnalités

- Conversion `.eml` → `.md` avec préservation de la mise en forme (gras, liens, listes...)
- Extraction des métadonnées (expéditeur, destinataire, date, objet) sous forme de front-matter YAML
- Extraction automatique des images intégrées (`cid:`) dans un dossier dédié
- Gestion robuste de l'encodage (UTF-8, ISO-8859-1...)
- Noms de fichiers/dossiers "slugifiés" (sans espace ni accent) pour compatibilité maximale
- Conversion unitaire ou en lot (dossier entier)
- Interface en ligne de commande simple

## 📦 Installation

Clonez le dépôt et installez les dépendances dans un environnement virtuel :

```bash
git clone https://github.com/Baebibelab/eml-to-md.git
cd eml-to-md

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

### Spécifier un dossier de sortie

```bash
python eml_to_md.py dossier_mails/ -o dossier_markdown/
```

## 📄 Exemple de résultat

```
Entrée : exemple.eml
```

```
Sortie : exemple.md
---
from: "Alice Dupont <alice@example.com>"
to: "Bob Martin <bob@example.com>"
cc: ""
date: "Mon, 22 Sep 2026 10:00:00 +0000"
subject: "Compte-rendu réunion"
---

# Compte-rendu réunion

Bonjour Bob,

Voici le compte-rendu de notre réunion...

![schema](exemple_images/schema_1.png)
```

## 🗂️ Structure du projet

```
eml-to-md/
├── eml_to_md.py        # Script principal
├── requirements.txt    # Dépendances Python
├── README.md
├── LICENSE
└── CHANGELOG.md
```

## 🛠️ Dépendances

* [html2text](https://github.com/Alir3z4/html2text) — conversion HTML → Markdown
* [beautifulsoup4](https://www.crummy.com/software/BeautifulSoup/) — parsing et manipulation du DOM HTML

## ⚠️ Limitations connues

* Les emails imbriqués (mail transféré en pièce jointe .eml) ne sont pas traités récursivement.
* Les pièces jointes non-image (PDF, Word, etc.) ne sont pas extraites (uniquement mentionnées si présentes dans le corps du message).
* Certains rendus HTML très spécifiques à Outlook (tableaux complexes, styles conditionnels mso-) peuvent ne pas se convertir parfaitement en Markdown.

