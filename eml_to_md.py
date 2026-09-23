import argparse
import email
import email.header
import logging
import re
import sys
import unicodedata
from email.policy import default
from pathlib import Path
from typing import ClassVar, Optional

import html2text
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def slugify(text: str) -> str:
    """Convertit un texte en identifiant sûr pour fichiers/dossiers (sans espace ni accent)."""
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^\w\-]', '_', text)
    text = re.sub('_+', '_', text)
    return text.strip('_')


def _decode_header(value: str) -> str:
    """Décode les MIME encoded-words (`=?utf-8?Q?...?=`) d'un en-tête.

    Avec `policy=default` la plupart des en-têtes sont déjà décodés, mais
    certaines valeurs mal formées arrivent encore brutes : ce décodage
    défensif les normalise sans jamais lever d'exception.
    """
    try:
        decoded = email.header.decode_header(value)
    except (LookupError, UnicodeError):
        return value.strip()
    parts = []
    for text, charset in decoded:
        if isinstance(text, bytes):
            for candidate in (charset, 'utf-8', 'iso-8859-1'):
                if not candidate:
                    continue
                try:
                    text = text.decode(candidate)
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            if isinstance(text, bytes):
                text = text.decode('iso-8859-1', errors='replace')
        parts.append(text)
    return ''.join(parts).strip()


class EmlToMarkdownConverter:
    """Convertit un fichier EML en fichier Markdown (front-matter + images extraites)."""

    IMAGE_TYPES: ClassVar[frozenset] = frozenset(
        {'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'}
    )

    def __init__(self, eml_path: str, extract_images: bool = True,
                 extract_attachments: bool = False):
        self.eml_path = Path(eml_path)
        self.msg = None
        self.extract_images = extract_images
        self.extract_attachments = extract_attachments
        self.attachment_dir = None

    def load(self):
        with open(self.eml_path, 'rb') as f:
            self.msg = email.message_from_binary_file(f, policy=default)
        return self

    def _decode_body(self, body_part) -> str:
        raw_bytes = body_part.get_payload(decode=True)
        if raw_bytes is None:
            raise ValueError("Corps du message vide ou illisible.")

        declared_charset = body_part.get_content_charset()
        candidates = [declared_charset, 'utf-8', 'iso-8859-1']
        candidates = [c for c in candidates if c]

        for charset in candidates:
            try:
                return raw_bytes.decode(charset)
            except (UnicodeDecodeError, LookupError):
                continue

        logger.warning(
            "Impossible de décoder avec les charsets %s, fallback 'iso-8859-1' avec 'replace'.",
            ", ".join(candidates) or "inconnus",
        )
        return raw_bytes.decode('iso-8859-1', errors='replace')

    def _extract_metadata(self) -> dict:
        metadata = {}
        for key in ('from', 'to', 'cc', 'date'):
            raw_value = self.msg.get(key.capitalize(), '')
            if raw_value:
                metadata[key] = _decode_header(str(raw_value))
        subject = _decode_header(self.msg.get('Subject', '')) or 'Sans objet'
        metadata['subject'] = subject
        return metadata

    def _extract_images(self, html_content: str, images_dir: Path) -> str:
        """Extrait les images avec BeautifulSoup (parsing DOM, pas de replace() fragile)."""
        images_dir.mkdir(parents=True, exist_ok=True)
        soup = BeautifulSoup(html_content, 'html.parser')

        cid_to_path = {}
        img_counter = 0

        for part in self.msg.walk():
            content_type = part.get_content_type()
            if content_type not in self.IMAGE_TYPES:
                continue

            image_data = part.get_payload(decode=True)
            if not image_data:
                continue

            img_counter += 1
            ext = content_type.split('/')[-1]
            original_name = part.get_filename()
            if original_name:
                base_name = slugify(Path(original_name).stem)
            else:
                base_name = f"image_{img_counter}"
            filename = f"{base_name}_{img_counter}.{ext}"

            image_path = images_dir / filename
            with open(image_path, 'wb') as img_f:
                img_f.write(image_data)

            relative_path = f"{images_dir.name}/{filename}"
            content_id = part.get('Content-ID')
            if content_id:
                cid_to_path[content_id.strip('<>')] = relative_path
            if original_name:
                cid_to_path[original_name] = relative_path

        for img_tag in soup.find_all('img'):
            src = img_tag.get('src', '')
            if src.startswith('cid:'):
                cid = src.replace('cid:', '')
                if cid in cid_to_path:
                    img_tag['src'] = cid_to_path[cid]
            else:
                filename_in_src = Path(src).name
                if filename_in_src in cid_to_path:
                    img_tag['src'] = cid_to_path[filename_in_src]

        return str(soup)

    def _html_to_markdown(self, html_content: str) -> str:
        converter = html2text.HTML2Text()
        converter.body_width = 0
        converter.ignore_images = False
        converter.ignore_links = False
        converter.unicode_snob = True
        return converter.handle(html_content)

    @staticmethod
    def _yaml_quote(value: str) -> str:
        """Quote une valeur pour un front-matter YAML valide.

        Les guillemets doubles sont remplacés par des guillemets simples (pas
        d'échappement YAML nécessaire) et les sauts de ligne par des espaces.
        """
        cleaned = str(value).replace('"', "'").replace('\n', ' ')
        cleaned = cleaned.rstrip()
        return f'"{cleaned}"'

    def _build_front_matter(self, metadata: dict) -> str:
        lines = ['---']
        for key, value in metadata.items():
            lines.append(f'{key}: {self._yaml_quote(value)}')
        lines.append('---\n')
        return '\n'.join(lines)

    @staticmethod
    def _safe_filename(name: str, fallback: str = 'piece-jointe') -> str:
        name = (name or '').replace('\\', '/')
        name = name.split('/')[-1].strip()
        name = re.sub(r'[\x00-\x1f\x7f"*/:<>?|]', '_', name)
        name = name.strip('. ')
        return name or fallback

    @staticmethod
    def _human_size(size: int) -> str:
        if size < 1024:
            return f'{size} o'
        if size < 1024 * 1024:
            return f'{size / 1024:.1f} Ko'
        return f'{size / (1024 * 1024):.1f} Mo'

    def _collect_attachments(self):
        attachments = []
        seen_names = {}
        body_part = self.msg.get_body(preferencelist=('html', 'plain'))
        for part in self.msg.walk():
            if part.is_multipart() or part.get_content_maintype() == 'multipart':
                continue
            if part is body_part:
                continue
            content_type = part.get_content_type()
            if content_type in self.IMAGE_TYPES:
                continue
            filename = part.get_filename()
            if not filename:
                continue
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            safe_name = self._safe_filename(filename)
            seen_names[safe_name] = seen_names.get(safe_name, 0) + 1
            if seen_names[safe_name] > 1:
                stem, dot, ext = safe_name.rpartition('.')
                if not stem:
                    stem, ext = safe_name, ''
                    dot = ''
                safe_name = f'{stem}-{seen_names[safe_name]}{dot}{ext}'
            attachments.append({
                'filename': safe_name,
                'content_type': content_type,
                'size': len(payload),
                'payload': payload,
            })
        return attachments

    def _attachments_markdown(self, attachments) -> str:
        if not attachments:
            return ''
        lines = ['', '## Pièces jointes', '']
        for att in attachments:
            link = ''
            if self.attachment_dir is not None:
                target = f"{self.attachment_dir.name}/{att['filename']}"
                target = target.replace(' ', '%20')
                link = f" — [télécharger]({target})"
            size = self._human_size(att['size'])
            lines.append(f"- **{att['filename']}** ({att['content_type']}, {size}){link}")
        return '\n'.join(lines) + '\n'

    def _write_attachments(self, attachments, md_file: Path):
        if not attachments:
            return
        attachment_dir = md_file.parent / (slugify(md_file.stem) + '_pieces-jointes')
        attachment_dir.mkdir(parents=True, exist_ok=True)
        self.attachment_dir = attachment_dir
        for att in attachments:
            target = attachment_dir / att['filename']
            with open(target, 'wb') as f:
                f.write(att['payload'])
            logger.info("Pièce jointe extraite : %s", target)

    def convert(self, images_dir: Optional[Path] = None) -> str:
        if self.msg is None:
            self.load()

        body_part = self.msg.get_body(preferencelist=('html', 'plain'))
        if body_part is None:
            raise ValueError("Impossible de trouver un corps HTML ou texte dans cet email.")

        html_content = self._decode_body(body_part)
        content_type = body_part.get_content_type()

        if content_type == 'text/html':
            if self.extract_images and images_dir is not None:
                html_content = self._extract_images(html_content, images_dir)
            markdown_body = self._html_to_markdown(html_content)
        else:
            markdown_body = html_content

        metadata = self._extract_metadata()
        front_matter = self._build_front_matter(metadata)
        subject = metadata.get('subject', 'Sans objet')

        markdown = f"{front_matter}\n# {subject}\n\n{markdown_body}"

        attachments = self._collect_attachments()
        section = self._attachments_markdown(attachments)
        if section:
            markdown = markdown.rstrip() + '\n\n' + section

        return markdown

    def save(self, md_file: Optional[str] = None) -> str:
        if self.msg is None:
            self.load()
        md_file = Path(md_file) if md_file else self.eml_path.with_suffix('.md')

        safe_stem = slugify(md_file.stem)
        images_dir = md_file.parent / f"{safe_stem}_images"

        attachments = self._collect_attachments() if self.extract_attachments else []
        if attachments:
            self._write_attachments(attachments, md_file)

        markdown_content = self.convert(images_dir=images_dir)
        self.attachment_dir = None

        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        return str(md_file)


def batch_convert(input_dir: str, output_dir: Optional[str] = None,
                  extract_attachments: bool = False, recursive: bool = False):
    """Convertit tous les fichiers .eml d'un dossier. Retourne (réussis, échecs).

    En mode récursif, les sous-dossiers sont parcourus et la structure est
    recréée dans le dossier de sortie.
    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir) if output_dir else input_dir

    if recursive:
        eml_files = sorted(p for p in input_dir.rglob('*.eml') if p.is_file())
    else:
        eml_files = sorted(
            p for p in input_dir.iterdir()
            if p.is_file() and p.suffix.lower() == '.eml'
        )

    if not eml_files:
        logger.warning("Aucun fichier .eml trouvé dans %s", input_dir)
        return 0, 0

    succeeded, failed = 0, 0
    for eml_file in eml_files:
        try:
            md_file = _output_path_for(eml_file, input_dir, output_dir)
            md_file.parent.mkdir(parents=True, exist_ok=True)
            converter = EmlToMarkdownConverter(eml_file, extract_attachments=extract_attachments)
            converter.save(md_file)
            succeeded += 1
            logger.info("✓ %s → %s", eml_file, md_file)
        except (OSError, ValueError, UnicodeError) as e:
            failed += 1
            logger.error("✗ Échec pour %s : %s", eml_file.name, e)
    return succeeded, failed


def _output_path_for(eml_file: Path, input_dir: Path, output_dir: Path) -> Path:
    """Chemin du Markdown de sortie : à plat hors récursif, miroir de l'arborescence en récursif."""
    if eml_file.parent == input_dir:
        return output_dir / (eml_file.stem + '.md')
    relative = eml_file.parent.relative_to(input_dir)
    return output_dir / relative / (eml_file.stem + '.md')


def main(argv=None):
    parser = argparse.ArgumentParser(description="Convertit des fichiers EML en Markdown.")
    parser.add_argument('path', help="Chemin d'un fichier .eml ou d'un dossier")
    parser.add_argument('-o', '--output', help="Fichier ou dossier de sortie", default=None)
    parser.add_argument(
        '--extract-attachments',
        action='store_true',
        help="Sauvegarde les pièces jointes non-image dans un dossier à côté du Markdown "
             "et les liste en fin de fichier avec un lien de téléchargement"
    )
    parser.add_argument(
        '-r', '--recursive',
        action='store_true',
        help="Parcourt aussi les sous-dossiers (l'arborescence est recréée dans la sortie)"
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    path = Path(args.path)

    if not path.exists():
        logger.error("Le chemin spécifié n'existe pas : %s", path)
        return 1

    if path.is_dir():
        succeeded, failed = batch_convert(
            path, args.output,
            extract_attachments=args.extract_attachments,
            recursive=args.recursive,
        )
        if failed:
            logger.error("%d fichier(s) en échec sur %d traité(s).", failed, succeeded + failed)
            return 1
        return 0

    try:
        converter = EmlToMarkdownConverter(path, extract_attachments=args.extract_attachments)
        md_file = converter.save(args.output)
        logger.info("Fichier Markdown enregistré : %s", md_file)
    except (OSError, ValueError, UnicodeError) as e:
        logger.error("Erreur lors de la conversion : %s", e)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
