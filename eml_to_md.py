import email
from email.policy import default
import os
import re
import argparse
from pathlib import Path
import logging

import html2text

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class EmlToMarkdownConverter:
    """Convertit un fichier EML en fichier Markdown (front-matter + images extraites)."""

    IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'}

    def __init__(self, eml_path: str, extract_images: bool = True):
        self.eml_path = Path(eml_path)
        self.msg = None
        self.extract_images = extract_images

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

        logger.warning("Impossible de décoder proprement, fallback avec 'replace'.")
        return raw_bytes.decode('iso-8859-1', errors='replace')

    def _extract_metadata(self) -> dict:
        return {
            'from': self.msg.get('From', ''),
            'to': self.msg.get('To', ''),
            'cc': self.msg.get('Cc', ''),
            'date': self.msg.get('Date', ''),
            'subject': self.msg.get('Subject', 'Sans objet'),
        }

    def _extract_images(self, html_content: str, images_dir: Path) -> str:
        """Extrait les images en fichiers séparés et remplace les références (cid: ou nom) dans le HTML."""
        images_dir.mkdir(parents=True, exist_ok=True)
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
            filename = part.get_filename() or f"image_{img_counter}.{ext}"
            filename = re.sub(r'[^\w.\-]', '_', filename)
            image_path = images_dir / filename

            with open(image_path, 'wb') as img_f:
                img_f.write(image_data)

            relative_path = f"{images_dir.name}/{filename}"
            content_id = part.get('Content-ID')

            if content_id:
                cid = content_id.strip('<>')
                if f'cid:{cid}' in html_content:
                    html_content = html_content.replace(f'cid:{cid}', relative_path)
                    continue

            image_name = part.get_filename()
            if image_name and image_name in html_content:
                html_content = html_content.replace(image_name, relative_path)

        return html_content

    def _html_to_markdown(self, html_content: str) -> str:
        converter = html2text.HTML2Text()
        converter.body_width = 0       # pas de retour à la ligne forcé
        converter.ignore_images = False
        converter.ignore_links = False
        converter.unicode_snob = True  # préserve les accents/unicode
        return converter.handle(html_content)

    def _build_front_matter(self, metadata: dict) -> str:
        lines = ['---']
        for key, value in metadata.items():
            value_clean = value.replace('"', "'").replace('\n', ' ')
            lines.append(f'{key}: "{value_clean}"')
        lines.append('---\n')
        return '\n'.join(lines)

    def convert(self, images_dir: Path = None) -> str:
        if self.msg is None:
            self.load()

        body_part = self.msg.get_body(preferencelist=('html', 'plain'))
        if body_part is None:
            raise ValueError("Impossible de trouver un corps HTML ou texte dans cet email.")

        html_content = self._decode_body(body_part)
        content_type = body_part.get_content_type()

        if content_type == 'text/html':
            if self.extract_images and images_dir:
                html_content = self._extract_images(html_content, images_dir)
            markdown_body = self._html_to_markdown(html_content)
        else:
            markdown_body = html_content  # déjà en texte brut

        metadata = self._extract_metadata()
        front_matter = self._build_front_matter(metadata)
        subject = metadata.get('subject', 'Sans objet')

        return f"{front_matter}\n# {subject}\n\n{markdown_body}"

    def save(self, md_file: str = None) -> str:
        md_file = Path(md_file) if md_file else self.eml_path.with_suffix('.md')
        images_dir = md_file.parent / f"{md_file.stem}_images"

        markdown_content = self.convert(images_dir=images_dir)

        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        return str(md_file)


def batch_convert(input_dir: str, output_dir: str = None):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir) if output_dir else input_dir

    eml_files = list(input_dir.glob('*.eml'))
    if not eml_files:
        logger.warning("Aucun fichier .eml trouvé dans %s", input_dir)
        return

    for eml_file in eml_files:
        try:
            md_file = output_dir / (eml_file.stem + '.md')
            converter = EmlToMarkdownConverter(eml_file)
            converter.save(md_file)
            logger.info("✓ %s → %s", eml_file.name, md_file.name)
        except Exception as e:
            logger.error("✗ Échec pour %s : %s", eml_file.name, e)


def main():
    parser = argparse.ArgumentParser(description="Convertit des fichiers EML en Markdown.")
    parser.add_argument('path', help="Chemin d'un fichier .eml ou d'un dossier")
    parser.add_argument('-o', '--output', help="Fichier ou dossier de sortie", default=None)
    args = parser.parse_args()

    path = Path(args.path)

    if not path.exists():
        logger.error("Le chemin spécifié n'existe pas : %s", path)
        return

    if path.is_dir():
        batch_convert(path, args.output)
    else:
        try:
            converter = EmlToMarkdownConverter(path)
            md_file = converter.save(args.output)
            logger.info("Fichier Markdown enregistré : %s", md_file)
        except Exception as e:
            logger.error("Erreur lors de la conversion : %s", e)


if __name__ == "__main__":
    main()