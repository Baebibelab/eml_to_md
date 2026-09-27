# Emails de démonstration

Trois emails **synthétiques et inoffensifs** pour tester `eml2markdown` en conditions
réelles, sans risquer ses propres emails. Aucune donnée personnelle, tout est fictif.

## Principe

Chaque fichier met en scène un comportement clé de l'outil. La commande produit un
`.md` que vous ouvrez dans votre visualiseur Markdown : le comportement attendu est
décrit point par point.

```bash
# Depuis la racine du dépôt (ou avec `pip install eml2markdown` installé)
python eml_to_md.py examples/demo-urls-dangereuses.eml -o /tmp/test1.md
```

---

## Démo 1 — URLs dangereuses : `demo-urls-dangereuses.eml`

Cet email contient l'arsenal classique d'un email malveillant côté liens :
`javascript:` direct et obfusqué (casse mélangée + entité HTML `&#58;`), `vbscript:`,
data URI `text/html` piégé, image SVG en data URI, `srcset` avec une URL dangereuse.

```bash
python eml_to_md.py examples/demo-urls-dangereuses.eml -o /tmp/test1.md
```

Ouvrez `/tmp/test1.md` dans un visualiseur Markdown :

| Point de contrôle | Attendu |
|---|---|
| Le texte « Texte legitime contenant javascript: void 0 (doit rester intact). » apparaît tel quel | ✅ |
| Aucun lien `javascript:` ou `vbscript:` n'est cliquable (les libellés restent, sans URL active) | ✅ |
| Aucune data URI `data:text/html` ou `data:image/svg+xml` ne figure dans le fichier (Ctrl+F `javascript:`, `data:text`) | ✅ |
| Le lien « lien normal (doit rester) » pointe toujours vers `https://example.com` | ✅ |
| Le lien mailto est préservé | ✅ |

---

## Démo 2 — Images inline et charset : `demo-images-cid.eml`

Cet email est encodé en **ISO-8859-1** et contient trois images PNG embarquées :
deux référencées par `Content-ID` (`cid:`) et une par son nom de fichier.

```bash
python eml_to_md.py examples/demo-images-cid.eml -o /tmp/test2.md
```

| Point de contrôle | Attendu |
|---|---|
| Le dossier `/tmp/test2_images/` contient trois fichiers PNG (`logo_1.png`, `schema_2.png`, `banniere_3.png`) | ✅ |
| Le Markdown référence ces fichiers par un chemin relatif `test2_images/...` | ✅ |
| Plus aucune référence `cid:` ne subsiste dans le Markdown | ✅ |
| Les accents du corps s'affichent correctement (charset ISO-8859-1 décodé) | ✅ |

---

## Démo 3 — Pièces jointes actives : `demo-pieces-jointes.eml`

Cet email a deux pièces jointes : `page.html` (contient un script — **active**) et
`rapport.pdf` (inoffensif).

```bash
python eml_to_md.py examples/demo-pieces-jointes.eml -o /tmp/test3.md --extract-attachments
```

| Point de contrôle | Attendu |
|---|---|
| La section « Pièces jointes » en fin de document liste les deux fichiers (nom, type, taille) | ✅ |
| Sur le disque, le dossier `/tmp/test3_pieces-jointes/` contient `page.html.txt` (suffixe `.txt` ajouté) et `rapport.pdf` (nom inchangé) | ✅ |
| Le lien de téléchargement pointe vers `page.html.txt` | ✅ |
| Ouvrir `page.html.txt` affiche le code source, n'exécute pas le script | ✅ |

---

## Tester avec vos propres emails

Une fois les démos validées, le flux est identique sur vos archives :

```bash
# Dossier complet d'exports
python eml_to_md.py chemin/vers/exports/ -o chemin/vers/sortie/ --recursive

# Un email précis, avec extraction des pièces jointes
python eml_to_md.py chemin/vers/email.eml --extract-attachments
```

## En cas de comportement inattendu

Ouvrez une issue sur https://github.com/Baebibelab/eml_to_md/issues avec :

1. La commande exacte utilisée
2. Le Markdown de sortie (ou un extrait)
3. Si possible, un `.eml` minimal reproduisant le problème (**sans données sensibles**)
