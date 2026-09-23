# Changelog

Toutes les modifications notables de ce projet sont documentées dans ce fichier.
Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

## [2.0.0] - 2026-09-23

### Ajouté

- Décodage des en-têtes MIME encoded-words (`=?utf-8?Q?...?=`) : objet, expéditeur,
  destinataires avec accents corrects dans le front-matter et le titre
- Gestion des pièces jointes non-image : listées en fin de document (nom, type MIME,
  taille humanisée) ; flag `--extract-attachments` (`EmlToMarkdownConverter(extract_attachments=True)`
  et `batch_convert(extract_attachments=True)`) pour les sauvegarder dans un dossier
  `<fichier>_pieces-jointes/` avec liens de téléchargement
- Mode batch récursif : flag `-r`/`--recursive`, arborescence recréée en sortie
- Détection insensible à la casse des extensions `.eml` en mode batch (`.EML` reconnu)
- `batch_convert` retourne un tuple `(réussis, échecs)` et la CLI sort avec un code
  d'erreur non nul en cas d'échec (1 fichier en échec ⇒ exit 1)
- Paquet pip-installable : métadonnées PEP 621 dans `pyproject.toml`, commande
  console `eml2markdown` (`eml-to-md` étant déjà pris sur PyPI)
- Suite de tests `pytest` (33 tests) couvrant le front-matter, le décodage des
  en-têtes, les images inline, les pièces jointes, le mode batch et les codes de sortie
- CI GitHub Actions : lint `ruff` + tests sur Python 3.9, 3.11 et 3.13
- Workflow de publication PyPI `publish.yml` (tests + build + publish au push d'un tag `v*`,
  secret `PYPI_API_TOKEN` requis)

### Modifié

- Le module ne configure plus le logging global à l'import (`logging.basicConfig`
  déplacé dans `main()`) : utilisable comme bibliothèque
- `main()` accepte une liste d'arguments optionnelle (`main(argv)`) pour être testable
  sans sous-processus
- Front-matter YAML robuste : quoting systématique des valeurs, valeurs contenant `:`
  ou guillemets correctement neutralisées (parsing YAML garanti)
- Les exceptions attrapées en batch/CLI sont restreintes à
  `(OSError, ValueError, UnicodeError)` : les bugs de code remontent au lieu d'être
  silencieusement loggés
- En-têtes absents omis du front-matter (plus de `cc: ""` vide)

### À venir

- Gestion des emails imbriqués (mail transféré en `.eml`)

## [1.0.0] - 2026-09-22

### Ajouté

- Conversion `.eml` → `.md` avec front-matter YAML (from, to, cc, date, subject)
- Extraction des images intégrées (`cid:`) dans un dossier dédié
- Slugification automatique des noms de fichiers/dossiers (suppression espaces/accents)
- Parsing DOM via BeautifulSoup pour un remplacement fiable des images (corrige les duplications de chemins)
- Support du traitement en lot (dossier entier)
- Interface en ligne de commande avec `argparse`
