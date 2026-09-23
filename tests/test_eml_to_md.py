import base64
import subprocess
import sys
from email.message import EmailMessage
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from eml_to_md import EmlToMarkdownConverter, batch_convert
from eml_to_md import main as eml_to_md_main

PNG_1PX = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
)

BODYLESS_EML = (
    b'Subject: Fichier binaire\r\n'
    b'From: a@b.c\r\n'
    b'MIME-Version: 1.0\r\n'
    b'Content-Type: application/octet-stream\r\n'
    b'Content-Transfer-Encoding: base64\r\n'
    b'\r\n'
    b'AAAA\r\n'
)


def make_html_eml(html_body, charset='utf-8', subject='Test'):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = 'expediteur@example.com'
    msg['To'] = 'destinataire@example.com'
    msg.set_content('Fallback texte', subtype='plain', charset=charset)
    msg.add_alternative(html_body, subtype='html', charset=charset)
    return msg


def write_eml(tmp_path, msg, name='test.eml'):
    eml_path = tmp_path / name
    eml_path.write_bytes(msg.as_bytes())
    return eml_path


class TestFrontMatter:
    def test_metadata_present(self, tmp_path):
        msg = make_html_eml('<p>Bonjour</p>', subject='Compte-rendu')
        eml_path = write_eml(tmp_path, msg)
        result = EmlToMarkdownConverter(eml_path).convert()
        assert result.startswith('---\n')
        assert 'from: "expediteur@example.com"' in result
        assert 'to: "destinataire@example.com"' in result
        assert 'subject: "Compte-rendu"' in result
        assert '\n---\n' in result

    def test_headers_mime_decoded(self, tmp_path):
        raw = (
            b'Subject: =?UTF-8?Q?Compte=2Drendu_r=C3=A9union?=\r\n'
            b'From: =?ISO-8859-1?Q?Alice_Dupont?= <alice@example.com>\r\n'
            b'To: bob@example.com\r\n'
            b'MIME-Version: 1.0\r\n'
            b'Content-Type: text/plain; charset=utf-8\r\n'
            b'\r\n'
            b'Bonjour\r\n'
        )
        eml_path = tmp_path / 'encoded.eml'
        eml_path.write_bytes(raw)
        result = EmlToMarkdownConverter(eml_path).convert()
        assert 'subject: "Compte-rendu réunion"' in result
        assert '# Compte-rendu réunion' in result
        assert 'Alice Dupont' in result
        assert '=?' not in result

    def test_colon_in_value_does_not_break_yaml(self, tmp_path):
        raw = (
            b'Subject: Bonjour\r\n'
            b'From: a@example.com\r\n'
            b'To: "Dupont: Bob" <bob@example.com>\r\n'
            b'MIME-Version: 1.0\r\n'
            b'Content-Type: text/plain; charset=utf-8\r\n'
            b'\r\n'
            b'Corps\r\n'
        )
        eml_path = tmp_path / 'colon.eml'
        eml_path.write_bytes(raw)
        result = EmlToMarkdownConverter(eml_path).convert()
        to_line = next(line for line in result.splitlines() if line.startswith('to:'))
        assert to_line.startswith('to: "')
        assert to_line.endswith('"')

    def test_missing_subject_fallback(self, tmp_path):
        msg = EmailMessage()
        msg['From'] = 'a@example.com'
        msg['To'] = 'b@example.com'
        msg.set_content('Corps seul')
        eml_path = write_eml(tmp_path, msg)
        result = EmlToMarkdownConverter(eml_path).convert()
        assert 'subject: "Sans objet"' in result
        assert '# Sans objet' in result

    def test_quote_in_value(self, tmp_path):
        raw = (
            b'Subject: =?utf-8?Q?Il_a_dit_=22bonjour=22?=\r\n'
            b'From: a@example.com\r\n'
            b'MIME-Version: 1.0\r\n'
            b'Content-Type: text/plain; charset=utf-8\r\n'
            b'\r\n'
            b'Corps\r\n'
        )
        eml_path = tmp_path / 'quote.eml'
        eml_path.write_bytes(raw)
        result = EmlToMarkdownConverter(eml_path).convert()
        assert "Il a dit 'bonjour'" in result


class TestBodyConversion:
    def test_html_to_markdown(self, tmp_path):
        msg = make_html_eml('<p>Bonjour <b>monde</b></p><ul><li>un</li><li>deux</li></ul>')
        eml_path = write_eml(tmp_path, msg)
        result = EmlToMarkdownConverter(eml_path).convert()
        assert '**monde**' in result
        assert '- un' in result or '* un' in result

    def test_plain_body_kept(self, tmp_path):
        msg = EmailMessage()
        msg['Subject'] = 'Texte'
        msg['From'] = 'a@example.com'
        msg['To'] = 'b@example.com'
        msg.set_content('Ligne une\nLigne deux')
        eml_path = write_eml(tmp_path, msg)
        result = EmlToMarkdownConverter(eml_path).convert()
        assert 'Ligne une\nLigne deux' in result

    def test_declared_iso8859_charset(self, tmp_path):
        msg = make_html_eml('<p>Éàü çàé</p>', charset='iso-8859-1')
        eml_path = write_eml(tmp_path, msg)
        result = EmlToMarkdownConverter(eml_path).convert()
        assert 'Éàü çàé' in result

    def test_invalid_declared_charset_falls_back(self, tmp_path):
        raw = (
            b'Subject: Test\n'
            b'MIME-Version: 1.0\n'
            b'Content-Type: text/html; charset="bogus-charset"\n'
            b'Content-Transfer-Encoding: 8bit\n'
            b'\n'
            + b'Texte correct <b>HTML</b>'
        )
        eml_path = tmp_path / 'broken.eml'
        eml_path.write_bytes(raw)
        result = EmlToMarkdownConverter(eml_path).convert()
        assert 'Texte correct **HTML**' in result


class TestImages:
    def make_image_eml(self, html_body, cid='<logo@example.com>', filename='logo.png'):
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Avec image'
        msg['From'] = 'a@example.com'
        msg['To'] = 'b@example.com'
        msg.attach(MIMEText('Fallback texte', 'plain', 'utf-8'))
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        image = MIMEImage(PNG_1PX, 'png')
        image.add_header('Content-ID', cid)
        if filename:
            image.add_header('Content-Disposition', 'inline', filename=filename)
        msg.attach(image)
        return msg

    def test_cid_image_extracted_and_rewritten(self, tmp_path):
        msg = self.make_image_eml('<p>Logo</p><img src="cid:logo@example.com" alt="logo">')
        eml_path = write_eml(tmp_path, msg)
        images_dir = tmp_path / 'out_images'
        result = EmlToMarkdownConverter(eml_path).convert(images_dir=images_dir)
        assert '![logo](out_images/logo_1.png)' in result
        assert (images_dir / 'logo_1.png').read_bytes() == PNG_1PX

    def test_images_not_extracted_without_dir(self, tmp_path):
        msg = self.make_image_eml('<p>Logo</p><img src="cid:logo@example.com">')
        eml_path = write_eml(tmp_path, msg)
        result = EmlToMarkdownConverter(eml_path).convert()
        assert 'cid:logo@example.com' in result
        assert not (tmp_path / 'out_images').exists()

    def test_extract_images_false_leaves_cid(self, tmp_path):
        msg = self.make_image_eml('<p>Logo</p><img src="cid:logo@example.com">')
        eml_path = write_eml(tmp_path, msg)
        images_dir = tmp_path / 'images'
        converter = EmlToMarkdownConverter(eml_path, extract_images=False)
        result = converter.convert(images_dir=images_dir)
        assert 'cid:logo@example.com' in result
        assert not images_dir.exists()

    def test_save_creates_images_dir(self, tmp_path):
        msg = self.make_image_eml('<p>Logo</p><img src="cid:logo@example.com">')
        eml_path = write_eml(tmp_path, msg, name='mon mail.eml')
        md_file = tmp_path / 'mon mail.md'
        EmlToMarkdownConverter(eml_path).save(md_file)
        images_dir = tmp_path / 'mon_mail_images'
        assert (images_dir / 'logo_1.png').exists()


class TestAttachments:
    def make_attachment_eml(self, filename='rapport.pdf', content=b'%PDF-1.4 fake'):
        msg = EmailMessage()
        msg['Subject'] = 'Avec PDF'
        msg['From'] = 'a@example.com'
        msg['To'] = 'b@example.com'
        msg.set_content('Corps du message')
        msg.add_attachment(content, maintype='application', subtype='pdf', filename=filename)
        return msg

    def test_attachment_listed_without_extraction(self, tmp_path):
        msg = self.make_attachment_eml()
        eml_path = write_eml(tmp_path, msg)
        result = EmlToMarkdownConverter(eml_path).convert()
        assert '## Pièces jointes' in result
        assert 'rapport.pdf' in result
        assert 'application/pdf' in result
        assert 'télécharger' not in result
        assert not (tmp_path / 'test_pieces-jointes').exists()

    def test_attachment_extracted_with_flag(self, tmp_path):
        msg = self.make_attachment_eml()
        eml_path = write_eml(tmp_path, msg, name='mail.eml')
        converter = EmlToMarkdownConverter(eml_path, extract_attachments=True)
        converter.save(tmp_path / 'mail.md')
        att_dir = tmp_path / 'mail_pieces-jointes'
        assert (att_dir / 'rapport.pdf').read_bytes() == b'%PDF-1.4 fake'
        result = (tmp_path / 'mail.md').read_text(encoding='utf-8')
        assert '[télécharger](mail_pieces-jointes/rapport.pdf)' in result

    def test_image_inline_not_listed_as_attachment(self, tmp_path):
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Image inline'
        msg['From'] = 'a@example.com'
        msg['To'] = 'b@example.com'
        msg.attach(MIMEText('<p>Logo</p>', 'html', 'utf-8'))
        image = MIMEImage(PNG_1PX, 'png')
        image.add_header('Content-ID', '<logo@example.com>')
        msg.attach(image)
        eml_path = write_eml(tmp_path, msg)
        result = EmlToMarkdownConverter(eml_path).convert()
        assert 'Pièces jointes' not in result

    def test_duplicate_filenames_suffixed(self, tmp_path):
        msg = EmailMessage()
        msg['Subject'] = 'Doublons'
        msg['From'] = 'a@example.com'
        msg['To'] = 'b@example.com'
        msg.set_content('Corps')
        msg.add_attachment(b'un', maintype='application', subtype='octet-stream',
                           filename='doc.txt')
        msg.add_attachment(b'deux', maintype='application', subtype='octet-stream',
                           filename='doc.txt')
        eml_path = write_eml(tmp_path, msg)
        converter = EmlToMarkdownConverter(eml_path, extract_attachments=True)
        converter.save(tmp_path / 'mail.md')
        att_dir = tmp_path / 'mail_pieces-jointes'
        assert (att_dir / 'doc.txt').read_bytes() == b'un'
        assert (att_dir / 'doc-2.txt').read_bytes() == b'deux'

    def test_unsafe_filename_sanitized(self, tmp_path):
        msg = self.make_attachment_eml(filename='../../evil.sh')
        eml_path = write_eml(tmp_path, msg)
        converter = EmlToMarkdownConverter(eml_path, extract_attachments=True)
        converter.save(tmp_path / 'mail.md')
        att_dir = tmp_path / 'mail_pieces-jointes'
        files = sorted(p.name for p in att_dir.iterdir())
        assert files == ['evil.sh']
        assert not (tmp_path / 'evil.sh').exists()


class TestBatch:
    def test_batch_converts_all(self, tmp_path):
        for i in range(3):
            msg = make_html_eml(f'<p>Mail {i}</p>', subject=f'Mail {i}')
            write_eml(tmp_path, msg, name=f'mail{i}.eml')
        succeeded, failed = batch_convert(tmp_path)
        assert (succeeded, failed) == (3, 0)
        assert (tmp_path / 'mail0.md').exists()
        assert (tmp_path / 'mail1.md').exists()
        assert (tmp_path / 'mail2.md').exists()

    def test_batch_isolated_failures(self, tmp_path):
        msg = make_html_eml('<p>OK</p>')
        write_eml(tmp_path, msg, name='good.eml')
        (tmp_path / 'bad.eml').write_bytes(BODYLESS_EML)
        succeeded, failed = batch_convert(tmp_path)
        assert failed == 1
        assert succeeded == 1
        assert (tmp_path / 'good.md').exists()

    def test_batch_uppercase_extension(self, tmp_path):
        msg = make_html_eml('<p>Mail</p>')
        write_eml(tmp_path, msg, name='mail.EML')
        succeeded, failed = batch_convert(tmp_path)
        assert (succeeded, failed) == (1, 0)
        assert (tmp_path / 'mail.md').exists()

    def test_batch_empty_dir(self, tmp_path):
        succeeded, failed = batch_convert(tmp_path)
        assert (succeeded, failed) == (0, 0)

    def test_batch_recursive_mirrors_tree(self, tmp_path):
        sub = tmp_path / 'input'
        (sub / 'a' / 'b').mkdir(parents=True)
        out = tmp_path / 'output'
        msg = make_html_eml('<p>Racine</p>')
        write_eml(sub, msg, name='root.eml')
        write_eml(sub / 'a', msg, name='lvl1.eml')
        write_eml(sub / 'a' / 'b', msg, name='lvl2.eml')
        succeeded, failed = batch_convert(sub, str(out), recursive=True)
        assert (succeeded, failed) == (3, 0)
        assert (out / 'root.md').exists()
        assert (out / 'a' / 'lvl1.md').exists()
        assert (out / 'a' / 'b' / 'lvl2.md').exists()

    def test_batch_non_recursive_ignores_subdirs(self, tmp_path):
        sub = tmp_path / 'input'
        nested = sub / 'sous'
        nested.mkdir(parents=True)
        msg = make_html_eml('<p>Mail</p>')
        write_eml(sub, msg, name='top.eml')
        write_eml(nested, msg, name='inner.eml')
        succeeded, failed = batch_convert(sub)
        assert (succeeded, failed) == (1, 0)
        assert (sub / 'top.md').exists()
        assert not (nested / 'inner.md').exists()


class TestCli:
    def run_main(self, argv):
        return eml_to_md_main(argv)

    def test_single_file_conversion(self, tmp_path, capsys):
        msg = make_html_eml('<p>Bonjour CLI</p>', subject='Sujet CLI')
        eml_path = write_eml(tmp_path, msg, name='cli.eml')
        code = self.run_main([str(eml_path)])
        assert code == 0
        capsys.readouterr()
        assert (tmp_path / 'cli.md').exists()

    def test_single_file_custom_output(self, tmp_path):
        msg = make_html_eml('<p>Sortie</p>')
        eml_path = write_eml(tmp_path, msg, name='in.eml')
        code = self.run_main([str(eml_path), '-o', str(tmp_path / 'custom.md')])
        assert code == 0
        assert (tmp_path / 'custom.md').exists()

    def test_directory_exit_code_success(self, tmp_path):
        msg = make_html_eml('<p>OK</p>')
        write_eml(tmp_path, msg, name='ok.eml')
        code = self.run_main([str(tmp_path)])
        assert code == 0

    def test_directory_exit_code_failure(self, tmp_path):
        (tmp_path / 'bad.eml').write_bytes(BODYLESS_EML)
        code = self.run_main([str(tmp_path)])
        assert code == 1

    def test_missing_path_exit_code(self, tmp_path):
        code = self.run_main([str(tmp_path / 'inexistant.eml')])
        assert code == 1

    def test_recursive_flag(self, tmp_path):
        sub = tmp_path / 'input'
        (sub / 'dossier').mkdir(parents=True)
        out = tmp_path / 'output'
        msg = make_html_eml('<p>Récursif</p>')
        write_eml(sub, msg, name='top.eml')
        write_eml(sub / 'dossier', msg, name='nested.eml')
        code = self.run_main([str(sub), '-o', str(out), '-r'])
        assert code == 0
        assert (out / 'dossier' / 'nested.md').exists()

    def test_extract_attachments_flag(self, tmp_path):
        msg = EmailMessage()
        msg['Subject'] = 'PJ'
        msg['From'] = 'a@example.com'
        msg['To'] = 'b@example.com'
        msg.set_content('Corps')
        msg.add_attachment(b'donnees', maintype='application', subtype='octet-stream',
                           filename='note.txt')
        eml_path = write_eml(tmp_path, msg, name='pj.eml')
        code = self.run_main([str(eml_path), '--extract-attachments'])
        assert code == 0
        assert (tmp_path / 'pj_pieces-jointes' / 'note.txt').read_bytes() == b'donnees'

    def test_script_direct_invocation(self, tmp_path):
        msg = make_html_eml('<p>Script</p>')
        eml_path = write_eml(tmp_path, msg, name='script.eml')
        repo_root = Path(__file__).resolve().parent.parent
        proc = subprocess.run(
            [sys.executable, str(repo_root / 'eml_to_md.py'), str(eml_path)],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0, proc.stderr
        assert (tmp_path / 'script.md').exists()


class TestLibraryUsage:
    def test_no_logging_config_at_import(self, caplog):
        import logging

        root = logging.getLogger()
        handlers_before = list(root.handlers)
        import eml_to_md

        root.handlers[:] = handlers_before
        assert logging.getLogger('eml_to_md').handlers == []
        assert eml_to_md.logger.name == 'eml_to_md'
