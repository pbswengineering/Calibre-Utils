# -*- coding: utf-8 -*-
#
# Download the current month's Crypto-Gram issue, import it in my
# Calibre library and publish it on my website.
#
# ImageMagick, Calibre
#

import codecs
import datetime
import glob
import locale
import os
import re
import shutil
import subprocess
import sys
from typing import List, Optional
import zipfile

from lxml import etree, html
import requests


# Since lately I'm more and more unable to keep up with
# the monthly schedule I've decided to parametrize the
# current date, so as to make late runs easier
now = datetime.datetime.now()
current_month = now.month
month = int(input(f"Month (1-12, default {current_month}): ") or current_month)
now = now.replace(month=month)


def zipdir(path, ziph):
    # Thanks to https://stackoverflow.com/a/1855118
    for root, _, files in os.walk(path):
        for file in files:
            ziph.write(
                os.path.join(root, file),
                os.path.relpath(os.path.join(root, file), path),
            )


class ExternalCommand:

    init_errors: List[str]

    def __init__(self):
        self.init_errors = []

    def add_init_error(self, error: str):
        self.init_errors.append(error)

    def get_init_errors(self) -> List[str]:
        return self.init_errors

    def which(self, exe: str):
        res = shutil.which(exe)
        if not res:
            self.init_errors.append(f"{exe} not found")
        return res


class ImageMagick(ExternalCommand):

    cmd_montage: List[str]
    cmd_mogrify: List[str]

    def __init__(self):
        super().__init__()
        magick = self.which("magick")
        if magick:
             self.cmd_montage = [magick, "montage"]
             self.cmd_mogrify = [magick, "mogrify"]
        else:
            self.cmd_montage = [self.which("montage")]
            self.cmd_mogrify = [self.which("mogrify")]
        if self.get_init_errors():
            self.add_init_error("Please install ImageMagick")

    def create_cover(self, title: str, outfile: str):
        dir_script = os.path.dirname(os.path.abspath(__file__))
        cover_template = os.path.join(dir_script, "cryptogram-cover-template.jpg")
        subprocess.run(
            self.cmd_montage
            + [
                "-label",
                title,
                cover_template,
                "-geometry",
                "+0+0",
                "-pointsize",
                "21",
                "-frame",
                "3",
                outfile,
            ]
        )
        subprocess.run(self.cmd_mogrify + ["-resize", "590x754!", "outfile"])


class Calibre(ExternalCommand):

    cmd_calibredb: str
    cmd_ebook_convert: str
    cmd_ebook_meta: str
    cmd_web2disk: str
    dir_tmp: str
    dir_html: str

    def __init__(self):
        super().__init__()
        dir_home = os.path.expanduser("~")
        self.dir_tmp = os.path.join(dir_home, ".cryptogram2calibre")
        self.dir_html = os.path.join(self.dir_tmp, "html")
        if os.path.exists(self.dir_tmp):
            shutil.rmtree(self.dir_tmp)
        os.makedirs(self.dir_html)
        self.cmd_calibredb = self.which("calibredb")
        self.cmd_ebook_convert = self.which("ebook-convert")
        self.cmd_ebook_meta = self.which("ebook-meta")
        self.cmd_web2disk = self.which("web2disk")
        if self.get_init_errors():
            self.add_init_error("Please install Calibre")

    def web2disk(self, url: str):
        subprocess.run(
            [self.cmd_web2disk, "-d", self.dir_html, "-r", "0", "--verbose", url]
        )

    def get_index_xhtml(self) -> Optional[str]:
        candidates = glob.glob(os.path.join(self.dir_html, "*.xhtml"))
        if not candidates:
            return None
        return candidates[0]

    def zip_to_mobi_and_epub(
        self, zip_file: str, cover_file: str, mobi_file: str, epub_file: str
    ):
        subprocess.run(
            [
                self.cmd_ebook_convert,
                zip_file,
                mobi_file,
                "--no-inline-toc",
                "--cover=" + cover_file,
            ]
        )
        subprocess.run(
            [
                self.cmd_ebook_convert,
                mobi_file,
                epub_file,
                "--preserve-cover-aspect-ratio",
                "--dont-split-on-page-breaks",
                "--cover=" + cover_file,
            ]
        )

    def set_ebook_meta(
        self,
        ebook_file: str,
        cover_file: str,
        title: str,
        authors: str,
        authors_sort: str,
        tags: str,
    ):
        cmd = [
            self.cmd_ebook_meta,
            ebook_file,
            f"--cover={cover_file}",
            f"--authors={authors}",
            f"--author-sort={authors_sort}",
            f"--tags={tags}",
        ]
        subprocess.run(cmd)

    def get_calibre_id(self, title: str):
        cmd = ["calibredb", "list", "--search", f"title:{title}"]
        res = subprocess.run(cmd, capture_output=True)
        output = res.stdout.decode("utf-8")
        book_ids = re.findall(r"^\d+", output, re.MULTILINE)
        if book_ids:
            return book_ids[0]
        else:
            return None

    def add_to_calibre(self, book_id: Optional[str], ebook_file: str):
        cmd = [self.cmd_calibredb]
        if book_id:
            cmd += ["add_format", book_id]
        else:
            cmd.append("add")
        cmd.append(ebook_file)
        subprocess.run(cmd)


class SchneierDotCom:
    def get_latest_issue_url(self) -> Optional[str]:
        page = requests.get("https://www.schneier.com/crypto-gram/")
        tree = html.fromstring(page.content)
        archive_as = tree.xpath(
            "//a[contains(@href, 'https://www.schneier.com/crypto-gram/archives/')]"
        )
        if not archive_as:
            return None
        archive_url = archive_as[(current_month - month) * 2].attrib["href"]
        print("   DEBUG: ---------> ARCHIVE_URL", archive_url)
        print("\n".join(["   DEBUG: " + a.attrib["href"] for a in archive_as]))
        return archive_url

    def declutterize(self, title: str, index_xhtml: str) -> bool:
        with codecs.open(index_xhtml, "r", "utf-8") as f:
            content = f.read()
        tree = html.fromstring(content)
        article_list = tree.xpath("//article")
        if not article_list:
            return False
        article = article_list[0]
        article_str = etree.tostring(article).decode("utf-8")
        content_str = f"""<html>
<head>
<title>{title}</title>
</head>
<body>
<h1>Crypto-Gram</h1>
{article_str}
</body>
</html>"""
        with codecs.open(index_xhtml, "w", "utf-8") as f:
            f.write(content_str)
        return True


class BernardiDotCloud:
    def publish_crypto_gram(self, epub_file: str, mobi_file: str):
        print("\n\n")
        # I assume that Calibre-Utils is in the github directory,
        # which is on the same level as the bernardi.cloud repo
        dir_base = os.path.join("..", "..", "bernardi.cloud")
        if not os.path.exists(dir_base):
            print(
                f"The directory {dir_base} doesn't exist, I will not updated the bernardi.cloud website"
            )
            return
        # Generate the Hugo post template
        yyyy = now.strftime("%Y")
        mm = now.strftime("%m")
        dd = now.strftime("%d")
        month = now.strftime("%B")
        month_lower = month.lower()
        dir_script = os.path.dirname(os.path.abspath(__file__))
        path_template = os.path.join(dir_script, "hugo-template.md")
        with codecs.open(path_template, "r", "utf-8") as f:
            template = f.read()
        template = template.replace("_YYYY_", yyyy)
        template = template.replace("_MM_", mm)
        template = template.replace("_DD_", dd)
        template = template.replace("_MONTH_", month)
        template = template.replace("_month_", month_lower)
        dir_article = os.path.join(dir_base, "content", "crypto-gram-for-e-readers")
        file_article = f"{yyyy}-{mm}-{dd}-crypto-gram-{month_lower}-{yyyy}-in-epub-and-mobi-format.md"
        path_article = os.path.join(dir_article, file_article)
        with codecs.open(path_article, "w", "utf-8") as f:
            f.write(template)
        # Copy the EPUB and MOBI files to the website repository
        dir_static = os.path.join(dir_base, "static", "cryptogram")
        shutil.copyfile(epub_file, os.path.join(dir_static, "cryptogram-last.epub"))
        shutil.copyfile(mobi_file, os.path.join(dir_static, "cryptogram-last.mobi"))
        shutil.copyfile(
            epub_file, os.path.join(dir_static, f"cryptogram-{yyyy}-{mm}.epub")
        )
        shutil.copyfile(
            mobi_file, os.path.join(dir_static, f"cryptogram-{yyyy}-{mm}.mobi")
        )
        print(f"BERNARDI:CLOUD: new article created as {path_article}")
        print("Remember to publish it!\n\n")


class Cryptogram2Calibre:

    bernardi_dot_cloud: BernardiDotCloud
    calibre: Calibre
    magick: ImageMagick
    schneier_dot_com: SchneierDotCom

    def __init__(self):
        self.bernardi_dot_cloud = BernardiDotCloud()
        self.calibre = Calibre()
        self.magick = ImageMagick()
        self.schneier_dot_com = SchneierDotCom()
        init_errors = self.calibre.get_init_errors() + self.magick.get_init_errors()
        if init_errors:
            print("\n".join(init_errors))
            sys.exit(1)

    def run(self):
        date_str = now.strftime("%B %Y")
        title = f"Crypto-Gram - {date_str} issue"
        # Get the URL of the latest Crypto-Gram issue
        latest_issue_url = self.schneier_dot_com.get_latest_issue_url()
        if not latest_issue_url:
            print("Cannot find the URL of the latest Crypto-Gram issue")
            sys.exit(1)
        # Download the web page
        self.calibre.web2disk(latest_issue_url)
        # Clean the web page
        index_xhtml = self.calibre.get_index_xhtml()
        if not index_xhtml:
            print("Crypto-Gram current issue download error")
            sys.exit(1)
        if not self.schneier_dot_com.declutterize(title, index_xhtml):
            print(f'Could not find <div id="content"> in {index_xhtml}')
            sys.exit(1)
        # Create a ZIP bundle with the HTML page and its dependencies
        pippo_zip = os.path.join(self.calibre.dir_tmp, "pippo.zip")
        with zipfile.ZipFile(pippo_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipdir(self.calibre.dir_html, zipf)
        # Create the MOBI and EPUB versions of the newsletter
        pippo_mobi = os.path.join(self.calibre.dir_tmp, "pippo.mobi")
        pippo_epub = os.path.join(self.calibre.dir_tmp, "pippo.epub")
        cover_file = os.path.join(self.calibre.dir_tmp, "cover.jpg")
        self.magick.create_cover(title, cover_file)
        self.calibre.zip_to_mobi_and_epub(pippo_zip, cover_file, pippo_mobi, pippo_epub)
        self.calibre.set_ebook_meta(
            pippo_epub,
            cover_file,
            title,
            "Bruce Schneier",
            "Schneier, Bruce",
            "Crypto-Gram",
        )
        self.calibre.set_ebook_meta(
            pippo_mobi,
            cover_file,
            title,
            "Bruce Schneier",
            "Schneier, Bruce",
            "Crypto-Gram",
        )
        # Add the MOBI and EPUB files to Calibre
        self.calibre.add_to_calibre(None, pippo_epub)
        book_id = self.calibre.get_calibre_id(title)
        if not book_id:
            print("Error while adding the EPUB newsletter to Calibre")
        self.calibre.add_to_calibre(book_id, pippo_mobi)
        # Try to updated the bernardi.cloud Hugo repository
        self.bernardi_dot_cloud.publish_crypto_gram(pippo_epub, pippo_mobi)


if __name__ == "__main__":
    try:
       locale.setlocale(category=locale.LC_ALL, locale="English")
    except:
       locale.setlocale(category=locale.LC_ALL, locale="en_US")
    Cryptogram2Calibre().run()
