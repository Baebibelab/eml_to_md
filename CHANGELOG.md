Toutes les modifications notables de ce projet sont documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

## [Non publié]

### À venir
- Gestion des emails imbriqués (mail transféré en `.eml`)
- Extraction optionnelle des pièces jointes non-image

## [1.0.0] - 2026-09-22

### Ajouté
- Conversion `.eml` → `.md` avec front-matter YAML (from, to, cc, date, subject)
- Extraction des images intégrées (`cid:`) dans un dossier dédié
- Slugification automatique des noms de fichiers/dossiers (suppression espaces/accents)
- Parsing DOM via BeautifulSoup pour un remplacement fiable des images (corrige les duplications de chemins)
- Support du traitement en lot (dossier entier)
- Interface en ligne de commande avec `argparse`